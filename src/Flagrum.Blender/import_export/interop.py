"""Pure-Python replacement for the former C#/.NET interop layer.

Historically this module shelled out to ``Flagrum.Blender.exe`` to parse
GMTL/GMDL/GPUBIN files and round-tripped data through JSON temp files.
All of that work is now performed in Python via the parsers under
``import_export/gfxbin``.

The :class:`Interop` shim is preserved so callers (panels, operators)
continue to work unchanged.
"""

import json
from os.path import dirname, join, splitext
from zipfile import ZIP_STORED, ZipFile

from ..entities import Gpubin
from .gfxbin.gmtl.gmtl import Gmtl
from .gfxbin.msgpack_reader import MessagePackReader


class Interop:

    @staticmethod
    def import_material_inputs(gfxbin_path: str) -> dict[str, list[float]]:
        """Read a ``.gmtl.gfxbin`` file and return shader-gen-name -> values.

        Replaces the C# ``material`` command. The Python :class:`Gmtl`
        parser already exposes ``buffers`` keyed by ``shader_gen_name`` with
        their unpacked float ``values`` (equivalent to the C# notion of
        ``InterfaceInputs``).
        """
        with open(gfxbin_path, mode="rb") as file:
            reader = MessagePackReader(file.read())

        gmtl = Gmtl(reader)

        result: dict[str, list[float]] = {}
        for buffer in gmtl.buffers:
            if buffer.shader_gen_name:
                result[buffer.shader_gen_name] = buffer.values
        return result

    @staticmethod
    def export_mesh(target_path: str, data: Gpubin):
        json_data = json.dumps(data, default=lambda o: o.__dict__, sort_keys=True, indent=0)

        templates_root = join(dirname(__file__), "..", "templates")

        with ZipFile(target_path, mode="w", compression=ZIP_STORED, allowZip64=True, compresslevel=None) as fmd:
            fmd.writestr("data.json", json_data)
            templates: list[str] = []

            for mesh in data.Meshes:
                if mesh.Material:
                    template_path = join(templates_root, mesh.Material.Id + ".json")
                    if mesh.Material.Id not in templates:
                        fmd.write(template_path, arcname="materials/" + mesh.Material.Id + ".json")
                        templates.append(mesh.Material.Id)

                    for texture_id in mesh.Material.Textures:
                        texture_path = mesh.Material.Textures[texture_id]
                        if texture_path != "":
                            _, file_extension = splitext(texture_path)
                            fmd.write(texture_path, arcname=mesh.Name + "/" + texture_id + file_extension)
