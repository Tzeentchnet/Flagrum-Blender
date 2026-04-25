from dataclasses import dataclass

import bpy
import numpy as np
from mathutils import Matrix

from ..utilities.asset_catalog import (
    ensure_model_catalogs,
    mark_collection_asset,
)
from ..utilities.blender_compat import (
    apply_custom_split_normals,
    new_corner_color_attribute,
)
from ..utilities.import_collections import create_part_empties
from ..utilities.timer import Timer
from .gfxbin.gmdl.gmdl import Gmdl
from .gfxbin.gmdl.gmdlmesh import GmdlMesh
from .gfxbin.gmdl.gmdlvertexelementformat import ElementFormat
from .gfxbin.msgpack_reader import MessagePackReader
from .gfxbin.vertex_decode import decode_vertex_streams
from .gmtlimporter import GmtlImporter
from .import_context import ImportContext


@dataclass
class GmdlImporter:
    gpubins: dict[int, bytes]
    context: ImportContext
    game_model: Gmdl
    correction_matrix: Matrix
    bone_table: dict[int, str]
    timer: Timer
    format_strings: dict[ElementFormat, str]

    def __init__(self, context):
        self.gpubins = {}
        self.context = context
        self.correction_matrix = Matrix([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
        # NumPy mirror of ``correction_matrix`` for vectorised row-vector
        # multiplication (``positions @ correction_matrix_np_T``).  Stored as
        # ``float32`` so it does not silently widen vertex/normal arrays.
        self.correction_matrix_np_T = np.array(
            [
                [1, 0, 0],
                [0, 0, 1],
                [0, -1, 0],
            ],
            dtype=np.float32,
        )

        self.format_strings = {
            ElementFormat.XYZ32_Float: "fff",
            ElementFormat.XY16_SintN: "hh",
            ElementFormat.XY16_UintN: "HH",
            ElementFormat.XY16_Float: "f2f2",
            ElementFormat.XYZW8_UintN: "BBBB",
            ElementFormat.XYZW8_SintN: "bbbb",
            ElementFormat.XYZW16_Uint: "HHHH",
            ElementFormat.XYZW32_Uint: "IIII",
        }

    def run(self):
        """Convenience: run the full import pipeline in one call.

        Equivalent to ``import_gfxbin()`` → ``generate_bone_table()`` →
        ``import_meshes()``. Callers that need to insert validation between
        steps (e.g. checking ``context.amdl_path`` once the bone table is
        known) should invoke the three methods directly instead.
        """
        timer = Timer()
        self.timer = Timer()
        self.import_gfxbin()
        self.timer.print("Importing gfxbin")
        self.generate_bone_table()
        self.timer.print("Generating bone table")
        self.import_meshes()
        timer.print("Overall import")

    def import_gfxbin(self):
        with open(self.context.gfxbin_path, mode="rb") as file:
            reader = MessagePackReader(file.read())
        self.game_model = Gmdl(reader)
        self.context.set_base_directory(self.game_model.header)

    def generate_bone_table(self):
        self.bone_table = {}
        counter = 0
        if self.game_model.header.version >= 20220707:
            for bone in self.game_model.bones:
                self.bone_table[counter] = bone.name
                counter += 1
        else:
            # Legacy assets sometimes ship with multiple bones whose
            # ``unique_index`` is the sentinel 65535. Indexing the bone table
            # by ``unique_index`` then collapses every collided entry onto a
            # single key, destroying skin weights. Detect that case and fall
            # back to sequential numbering — the first sentinel keeps key 0
            # in the single-collision case to preserve the original mapping.
            sentinel_count = 0
            for bone in self.game_model.bones:
                if bone.unique_index == 65535:
                    sentinel_count += 1
                    if sentinel_count > 1:
                        break
            if sentinel_count > 1:
                for bone in self.game_model.bones:
                    self.bone_table[counter] = bone.name
                    counter += 1
            else:
                for bone in self.game_model.bones:
                    if bone.unique_index == 65535:
                        self.bone_table[0] = bone.name
                    else:
                        self.bone_table[bone.unique_index] = bone.name

    def import_meshes(self):
        rc = self.context.root_collections

        # Pre-create the LOD sub-collections in the order they appear in the
        # source so the visible names (LOD0, LOD1, ...) line up with the
        # ``lod_near`` ordering.
        if self.context.import_lods:
            seen_lods: list[float] = []
            for mesh_object in self.game_model.mesh_objects:
                for mesh in mesh_object.meshes:
                    if mesh.lod_near not in seen_lods:
                        seen_lods.append(mesh.lod_near)
            for ordinal, lod_near in enumerate(seen_lods):
                rc.get_or_create_lod(lod_near, ordinal)

        if self.context.import_vems:
            for mesh_object in self.game_model.mesh_objects:
                for mesh in mesh_object.meshes:
                    if (mesh.flags & 67108864) > 0:
                        rc.ensure_vems()
                        break
                else:
                    continue
                break

        for mesh_object in self.game_model.mesh_objects:
            for mesh in mesh_object.meshes:
                self._import_mesh(mesh)

        # Build Parts sub-collection (one Empty per named part). Parent each
        # Empty to the armature when present so Outliner selection cascades.
        if self.game_model.parts:
            armature_obj = bpy.data.objects.get(self.context.collection.name)
            create_part_empties(
                rc,
                [part.name for part in self.game_model.parts],
                parent=armature_obj,
            )

        # Asset Browser tagging — mark the root collection and (re)write the
        # adjacent ``blender_assets.cats.txt`` so the catalog name resolves
        # in any user-registered Asset Library that includes this folder.
        mark_collection_asset(self.context.collection, self.context.model_name)
        ensure_model_catalogs(self.context.base_directory, self.context.model_name)

        layer = bpy.context.view_layer
        layer.update()

    def _import_mesh(self, mesh_data: GmdlMesh):
        context = self.context
        game_model = self.game_model

        # Skip LODs if setting is not checked
        if not context.import_lods and mesh_data.lod_near != 0:
            return

        # Skip VEMs if setting is not checked
        if not context.import_vems and (mesh_data.flags & 67108864) > 0:
            return

        print("")
        print(f"Importing {mesh_data.name}...")
        buffer = self._get_gpubin_buffer(mesh_data.gpubin_index)

        # Get face indices
        if mesh_data.face_index_type == 0:
            data_type = "<H"
        else:
            data_type = "<I"

        if mesh_data.face_index_count % 3 != 0:
            raise ValueError(
                f"Unable to import {mesh_data.name}: face index count "
                f"{mesh_data.face_index_count} is not divisible by 3"
            )

        face_indices = np.frombuffer(
            buffer, dtype=data_type, offset=mesh_data.face_index_offset, count=mesh_data.face_index_count
        ).reshape((mesh_data.face_index_count // 3, 3))

        self.timer.print("Reading face indices")

        # Reverse the winding order of the faces so the normals face the
        # right direction.  Vectorised stride flip (was a per-triangle
        # Python loop on the order of 100k iterations for hero meshes).
        # ``.tolist()`` is needed because ``from_pydata`` iterates and
        # rebuilds tuples; bulk Python conversion is faster than letting
        # the C side iterate the numpy array element-wise.
        faces = face_indices[:, ::-1].tolist()

        self.timer.print("Unwinding triangles")

        # Read the vertex streams in a single structured ``np.frombuffer``
        # call per stream rather than one ``np.frombuffer`` per element per
        # vertex.  Decoded floats are ``float32``; integer semantics keep
        # their on-disk dtype so they can be used as bone-table indices.
        semantics = decode_vertex_streams(buffer, mesh_data)

        # Apply the FBX-axis correction matrix to vertex positions in one
        # vectorised matmul.  The previous implementation called
        # ``correction_matrix @ Vector(...)`` per vertex.
        if "POSITION0" in semantics:
            semantics["POSITION0"] = semantics["POSITION0"] @ self.correction_matrix_np_T

        self.timer.print("Reading vertex streams")

        # Create the mesh
        mesh = bpy.data.meshes.new(mesh_data.name)
        mesh.from_pydata(semantics["POSITION0"].tolist(), [], faces)

        self.timer.print("Creating mesh")

        # Pre-fetch loop → vertex_index once; every per-loop attribute below
        # is just numpy fancy-indexing into the per-vertex arrays.
        loop_count = len(mesh.loops)
        loop_vertex_index = np.empty(loop_count, dtype=np.int32)
        mesh.loops.foreach_get("vertex_index", loop_vertex_index)

        # Generate each of the UV Maps
        has_light_map = False
        uv_map_index = 0
        for i in range(8):
            key = "TEXCOORD" + str(i)
            if key not in semantics:
                continue

            if i == 0:
                new_name = "map1"
            elif i == 1:
                new_name = "mapLM"
                has_light_map = True
            else:
                new_name = "map" + str(i + 1)
            mesh.uv_layers.new(name=new_name)

            uv_data = semantics[key]
            u = uv_data[:, 0]
            v = uv_data[:, 1]

            if game_model.header.version >= 20220707:
                # UDIM tile encoding: positive ``v`` packs a 10-wide tile
                # grid index.  Vectorised rewrite of the per-vertex branch.
                positive = v >= 0
                v_tile = np.floor(v).astype(np.int32)
                u_pos = u + (v_tile % 10)
                v_pos = (v_tile + (v_tile // 10) + 1).astype(np.float32) - v
                coord_u = np.where(positive, u_pos, u).astype(np.float32, copy=False)
                coord_v = np.where(positive, v_pos, 1.0 - v).astype(np.float32, copy=False)
                coords = np.stack((coord_u, coord_v), axis=1)
            else:
                # The V coordinate is set as 1-V to flip from FBX coordinate system
                coords = np.empty_like(uv_data)
                coords[:, 0] = u
                coords[:, 1] = 1.0 - v

            per_loop = coords[loop_vertex_index]
            mesh.uv_layers[uv_map_index].data.foreach_set("uv", per_loop.ravel())
            uv_map_index += 1

        self.timer.print("Generating UV maps")

        # Generate each of the color maps
        for i in range(4):
            key = "COLOR" + str(i)
            if key not in semantics:
                continue

            colors = semantics[key]
            # ``loop_vertex_index`` may legitimately reference vertices
            # that exist in the mesh but were not present in the original
            # color stream (older content).  Clamp to the available range
            # to preserve the legacy behaviour of leaving such corners at
            # the default zero color.
            if colors.shape[0] < (loop_vertex_index.max(initial=-1) + 1):
                safe_index = np.minimum(loop_vertex_index, colors.shape[0] - 1)
                per_loop = colors[safe_index]
                missing = loop_vertex_index >= colors.shape[0]
                if np.any(missing):
                    per_loop = per_loop.copy()
                    per_loop[missing] = 0.0
            else:
                per_loop = colors[loop_vertex_index]

            new_name = "colorSet"
            if i > 0:
                new_name += str(i)
            color_attr = new_corner_color_attribute(mesh, new_name)
            color_attr.data.foreach_set("color", per_loop.ravel())

        self.timer.print("Generating vertex colours")

        mesh.validate()
        mesh.update()

        self.timer.print("Validating and updating mesh")

        mesh_object = bpy.data.objects.new(mesh_data.name, mesh)

        rc = context.root_collections
        if (mesh_data.flags & 67108864) > 0:
            rc.ensure_vems().objects.link(mesh_object)
        elif context.import_lods:
            rc.lods[mesh_data.lod_near].objects.link(mesh_object)
        else:
            context.collection.objects.link(mesh_object)

        self.timer.print("Linking mesh object")

        # Add the parts system
        model_parts = {}
        for model_part in game_model.parts:
            model_parts[model_part.id] = model_part.name

        polygon_count = len(mesh.polygons)
        for parts_group in mesh_data.parts:
            parts_name = model_parts.get(parts_group.parts_id)
            if parts_name is None:
                parts_name = f"part_{parts_group.parts_id}"
                print(f"[WARNING] Missing part name for ID {parts_group.parts_id}; using {parts_name}")
            parts_layer = mesh.attributes.new(name=parts_name, type="BOOLEAN", domain="FACE")

            start_index = int(parts_group.start_index / 3)
            index_count = int(parts_group.index_count / 3)
            end_index = start_index + index_count
            mask = np.zeros(polygon_count, dtype=bool)
            mask[start_index:end_index] = True
            parts_layer.data.foreach_set("value", mask)

        self.timer.print("Generating parts data")

        # Import custom normals.  ``calc_edges`` is required before split
        # normals can be assigned for the first time.
        mesh.update(calc_edges=True)

        if "NORMAL0" in semantics:
            raw_normals = semantics["NORMAL0"][:, :3]
            normals = raw_normals @ self.correction_matrix_np_T
            length = np.linalg.norm(normals, axis=1, keepdims=True)
            np.divide(normals, length, out=normals, where=length > 0)
            apply_custom_split_normals(mesh, normals.tolist())

        self.timer.print("Generating custom normals")

        # Add the vertex weights from each weight map.  The previous
        # implementation called ``vertex_group.add(...)`` once per non-zero
        # weight (millions of Python calls for a hero mesh).  Bucketing by
        # (bone, integer-weight) collapses that to ≤256 calls per bone.
        if len(self.bone_table) > 0:
            n_verts = mesh_data.vertex_count
            slot_v: list[np.ndarray] = []
            slot_b: list[np.ndarray] = []
            slot_w: list[np.ndarray] = []

            for slot in range(2):
                bw_key = "BLENDWEIGHT" + str(slot)
                if bw_key not in semantics:
                    continue
                bi_key = "BLENDINDICES" + str(slot)
                blend_weight = semantics[bw_key]  # (N, 4) float
                blend_indices = semantics[bi_key]  # (N, 4) int

                # Convert to integer 0..255 bucket keys for stable grouping.
                bw_int = np.rint(blend_weight * 255.0).astype(np.uint16)
                nz = bw_int > 0
                if not np.any(nz):
                    continue

                v_grid = np.broadcast_to(np.arange(n_verts, dtype=np.int64)[:, None], bw_int.shape)
                slot_v.append(v_grid[nz])
                slot_b.append(blend_indices[nz].astype(np.int64, copy=False))
                slot_w.append(bw_int[nz].astype(np.int64, copy=False))

            # Pre-create a vertex group for every bone in the table so the
            # cleanup panel and any downstream tooling that scans for
            # missing groups continues to see the full bone roster.
            vertex_groups = {key: mesh_object.vertex_groups.new(name=name) for key, name in self.bone_table.items()}

            if slot_v:
                v_arr = np.concatenate(slot_v)
                b_arr = np.concatenate(slot_b)
                w_arr = np.concatenate(slot_w)

                # Sum duplicate (bone, vertex) pairs (a vertex can appear
                # in both BLENDWEIGHT slots referencing the same bone).
                key_arr = b_arr * np.int64(n_verts) + v_arr
                summed = np.bincount(key_arr, weights=w_arr).astype(np.int64)
                populated = np.flatnonzero(summed > 0)
                if populated.size:
                    bones = (populated // n_verts).astype(np.int64, copy=False)
                    verts = (populated % n_verts).astype(np.int64, copy=False)
                    wts = summed[populated]

                    # Sort by (bone, weight) to extract contiguous run
                    # boundaries; one ``vertex_group.add`` call per run.
                    order = np.lexsort((wts, bones))
                    bones_s = bones[order]
                    wts_s = wts[order]
                    verts_s = verts[order]

                    # Run start indices: where (bone, weight) changes.
                    run_starts = np.concatenate(
                        (
                            [0],
                            np.flatnonzero((bones_s[1:] != bones_s[:-1]) | (wts_s[1:] != wts_s[:-1])) + 1,
                            [bones_s.size],
                        )
                    )

                    inv_255 = 1.0 / 255.0
                    for r in range(run_starts.size - 1):
                        a = run_starts[r]
                        b = run_starts[r + 1]
                        bone_id = int(bones_s[a])
                        weight = float(wts_s[a]) * inv_255
                        vg = vertex_groups.get(bone_id)
                        if vg is None:
                            continue
                        vg.add(verts_s[a:b].tolist(), weight, "REPLACE")

        self.timer.print("Generating weight data")

        # Link the mesh to the armature
        if len(self.bone_table) > 0:
            mod = mesh_object.modifiers.new(type="ARMATURE", name=context.collection.name)
            mod.use_vertex_groups = True

            armature = bpy.data.objects[context.collection.name]
            mod.object = armature

            mesh_object.parent = armature
        else:
            # Collection wasn't linked on armature set, so do it now
            context.root_collections.link_to_scene()

        self.timer.print("Linking mesh to armature")

        # Process the material
        material_uri = self._get_material_uri(mesh_data.material_hash)

        try:
            material_importer = GmtlImporter(self.context, material_uri)
            material = material_importer.generate_material(has_light_map)

            if material is not None:
                mesh_object.data.materials.append(material)
        except Exception as ex:
            print(f"[ERROR] Failed to import GMTL data from {material_uri}: {ex}")

        self.timer.print("Generating automatic materials")

    def _get_gpubin_buffer(self, index: int) -> bytes:
        if self.game_model.header.version < 20220707:
            file_path = self.context.path_without_extension + ".gpubin"
        else:
            file_path = self.context.path_without_extension + "_" + str(index) + ".gpubin"

        if index not in self.gpubins:
            with open(file_path, mode="rb") as file:
                self.gpubins[index] = file.read()

        return self.gpubins[index]

    def _get_material_uri(self, uri_hash: int):
        return self.game_model.header.dependencies[str(uri_hash)]
