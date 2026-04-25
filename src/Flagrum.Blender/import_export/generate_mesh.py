import bpy
import numpy as np
from bpy.types import Collection, IntAttribute

from ..entities import MeshData
from ..utilities.blender_compat import (
    apply_custom_split_normals,
    new_corner_color_attribute,
)
from .generate_material import generate_material
from .import_context import ImportContext

# Row-vector form of the FBX-axis correction matrix used throughout the
# importer.  ``v @ _CORRECTION_T`` is equivalent to ``correction_matrix @ v``
# for the original ``[[1,0,0],[0,0,-1],[0,1,0]]`` matrix.
_CORRECTION_T = np.array(
    [
        [1, 0, 0],
        [0, 0, 1],
        [0, -1, 0],
    ],
    dtype=np.float32,
)


def _positions_to_array(vertex_positions) -> np.ndarray:
    """Convert a ``list[Vector3]`` from the JSON parser to a ``(N, 3)`` array."""
    out = np.empty((len(vertex_positions), 3), dtype=np.float32)
    for i, v in enumerate(vertex_positions):
        out[i, 0] = v.X
        out[i, 1] = v.Y
        out[i, 2] = v.Z
    return out


def _uvs_to_array(uvs) -> np.ndarray:
    out = np.empty((len(uvs), 2), dtype=np.float32)
    for i, c in enumerate(uvs):
        out[i, 0] = c.U
        out[i, 1] = c.V
    return out


def _colors_to_array(colors) -> np.ndarray:
    out = np.empty((len(colors), 4), dtype=np.float32)
    inv_255 = np.float32(1.0 / 255.0)
    for i, c in enumerate(colors):
        out[i, 0] = c.R
        out[i, 1] = c.G
        out[i, 2] = c.B
        out[i, 3] = c.A
    return out * inv_255


def _normals_to_array(normals) -> np.ndarray:
    out = np.empty((len(normals), 3), dtype=np.float32)
    inv_127 = np.float32(1.0 / 127.0)
    for i, n in enumerate(normals):
        out[i, 0] = n.X
        out[i, 1] = n.Y
        out[i, 2] = n.Z
    return out * inv_127


def generate_mesh(
    context: ImportContext,
    collection: Collection,
    mesh_data: MeshData,
    bone_table,
    parts,
    use_correction_matrix: bool = True,
):
    # Correct the vertex positions in one vectorised matmul (was a per-vertex
    # ``Matrix @ Vector`` loop).
    positions = _positions_to_array(mesh_data.VertexPositions)
    if use_correction_matrix:
        positions = positions @ _CORRECTION_T

    # Reverse the winding order of the faces so the normals face the right
    # direction.  ``FaceIndices`` is a list of ``[i0, i1, i2]`` lists, kept
    # as Python lists here because ``from_pydata`` accepts them directly and
    # the legacy in-place swap relied on list mutability.
    for face in mesh_data.FaceIndices:
        face[0], face[2] = face[2], face[0]

    # Create the mesh
    mesh = bpy.data.meshes.new(mesh_data.Name)
    mesh.from_pydata(positions.tolist(), [], mesh_data.FaceIndices)

    # Pre-fetch loop → vertex_index once for vectorised per-loop expansion.
    loop_count = len(mesh.loops)
    loop_vertex_index = np.empty(loop_count, dtype=np.int32)
    mesh.loops.foreach_get("vertex_index", loop_vertex_index)

    # Generate each of the UV Maps
    for i in range(len(mesh_data.UVMaps)):
        if i == 0:
            new_name = "map1"
        elif i == 1:
            new_name = "mapLM"
        else:
            new_name = "map" + str(i + 1)
        mesh.uv_layers.new(name=new_name)

        uv_data = _uvs_to_array(mesh_data.UVMaps[i].UVs)
        # The V coordinate is set as 1-V to flip from FBX coordinate system
        uv_data[:, 1] = 1.0 - uv_data[:, 1]

        per_loop = uv_data[loop_vertex_index]
        mesh.uv_layers[i].data.foreach_set("uv", per_loop.ravel())

    # Generate each of the color maps
    for i in range(len(mesh_data.ColorMaps)):
        colors = _colors_to_array(mesh_data.ColorMaps[i].Colors)

        # Older content can have fewer color entries than the mesh has
        # vertices; clamp + zero-fill the missing corners.
        if colors.shape[0] < (loop_vertex_index.max(initial=-1) + 1):
            safe_index = np.minimum(loop_vertex_index, colors.shape[0] - 1)
            per_loop = colors[safe_index].copy()
            missing = loop_vertex_index >= colors.shape[0]
            if np.any(missing):
                per_loop[missing] = 0.0
        else:
            per_loop = colors[loop_vertex_index]

        new_name = "colorSet"
        if i > 0:
            new_name += str(i)
        color_attr = new_corner_color_attribute(mesh, new_name)
        color_attr.data.foreach_set("color", per_loop.ravel())

    mesh.validate()
    mesh.update()

    mesh_object = bpy.data.objects.new(mesh_data.Name, mesh)
    collection.objects.link(mesh_object)

    # Add the parts system
    polygon_count = len(mesh.polygons)
    if len(parts) > 0:
        for parts_group in mesh_data.MeshParts:
            part_name = parts.get(str(parts_group.PartsId), parts.get(parts_group.PartsId))
            if part_name is None:
                part_name = f"part_{parts_group.PartsId}"
                print(f"[WARNING] Missing part name for ID {parts_group.PartsId}; using {part_name}")
            parts_layer: IntAttribute = mesh.attributes.new(name=part_name, type="BOOLEAN", domain="FACE")

            start_index = int(parts_group.StartIndex / 3)
            index_count = int(parts_group.IndexCount / 3)
            end_index = start_index + index_count
            mask = np.zeros(polygon_count, dtype=bool)
            mask[start_index:end_index] = True
            parts_layer.data.foreach_set("value", mask)

    # Import custom normals
    mesh.update(calc_edges=True)

    normals = _normals_to_array(mesh_data.Normals)
    if use_correction_matrix:
        normals = normals @ _CORRECTION_T
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    np.divide(normals, length, out=normals, where=length > 0)

    apply_custom_split_normals(mesh, normals.tolist())

    layer = bpy.context.view_layer
    layer.update()

    # Add the vertex weights from each weight map.  The legacy implementation
    # called ``vertex_group.add(...)`` once per non-zero weight slot per
    # vertex; bucketing by (bone, integer-weight) collapses that to ≤256
    # calls per bone.
    if len(bone_table) > 0:
        n_verts = len(mesh.vertices)
        slot_v: list[np.ndarray] = []
        slot_b: list[np.ndarray] = []
        slot_w: list[np.ndarray] = []

        for slot in range(len(mesh_data.WeightValues)):
            wv = np.asarray(mesh_data.WeightValues[slot], dtype=np.uint16)
            wi = np.asarray(mesh_data.WeightIndices[slot], dtype=np.int64)
            if wv.size == 0:
                continue
            nz = wv > 0
            if not np.any(nz):
                continue

            v_grid = np.broadcast_to(np.arange(wv.shape[0], dtype=np.int64)[:, None], wv.shape)
            slot_v.append(v_grid[nz])
            slot_b.append(wi[nz])
            slot_w.append(wv[nz].astype(np.int64, copy=False))

        # Pre-create vertex groups for every bone in the table to preserve
        # the legacy behaviour of always emitting the full bone roster.
        vertex_groups = {}
        for key in bone_table:
            vertex_groups[int(key)] = mesh_object.vertex_groups.new(name=bone_table[key])

        if slot_v:
            v_arr = np.concatenate(slot_v)
            b_arr = np.concatenate(slot_b)
            w_arr = np.concatenate(slot_w)

            key_arr = b_arr * np.int64(n_verts) + v_arr
            summed = np.bincount(key_arr, weights=w_arr).astype(np.int64)
            populated = np.flatnonzero(summed > 0)
            if populated.size:
                bones = (populated // n_verts).astype(np.int64, copy=False)
                verts = (populated % n_verts).astype(np.int64, copy=False)
                wts = summed[populated]

                order = np.lexsort((wts, bones))
                bones_s = bones[order]
                wts_s = wts[order]
                verts_s = verts[order]

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

    # Link the mesh to the armature
    if len(bone_table) > 0:
        mod = mesh_object.modifiers.new(type="ARMATURE", name=collection.name)
        mod.use_vertex_groups = True

        armature = bpy.data.objects[collection.name]
        mod.object = armature

        mesh_object.parent = armature
    else:
        # Collection wasn't linked on armature set, so do it now
        if collection.name not in bpy.context.scene.collection.children:
            bpy.context.scene.collection.children.link(collection)

    # Skip the material if we have no material data
    if mesh_data.BlenderMaterial is None or mesh_data.BlenderMaterial.Name is None:
        return mesh_object

    if mesh_data.BlenderMaterial.Hash in context.materials:
        material = context.materials[mesh_data.BlenderMaterial.Hash]
    else:
        material = generate_material(context, mesh_data)
        context.materials[mesh_data.BlenderMaterial.Hash] = material

    mesh_object.data.materials.append(material)
    return mesh_object
