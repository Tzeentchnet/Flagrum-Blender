import os
from dataclasses import dataclass

import bpy
from bpy.types import Material

from ..utilities.import_collections import RootCollections, build_root_collections
from .gfxbin.gfxbinheader import GfxbinHeader


def _path_name(path: str) -> str:
    return os.path.basename(path.replace("\\", os.sep).replace("/", os.sep))


@dataclass(init=False)
class ImportContext:
    gfxbin_path: str
    import_lods: bool
    import_vems: bool
    path_without_extension: str
    amdl_path: str
    model_name: str
    collection: bpy.types.Collection
    root_collections: RootCollections
    materials: dict[str, Material]
    texture_slots: dict[str, bool]
    base_directory: str
    base_uri: str

    def __init__(self, gfxbin_file_path, import_lods=False, import_vems=False):
        self.gfxbin_path = gfxbin_file_path
        self.import_lods = import_lods
        self.import_vems = import_vems
        self.path_without_extension = gfxbin_file_path.replace(".gmdl.gfxbin", "")
        self.materials = {}
        self.texture_slots = {}

        file_name = _path_name(gfxbin_file_path)
        group_name = ""
        for string in file_name.split("."):
            if string != "gmdl" and string != "gfxbin":
                if len(group_name) > 0:
                    group_name += "."
                group_name += string

        self.model_name = group_name
        self.collection = bpy.data.collections.new(group_name)
        self.root_collections = build_root_collections(group_name, self.collection)
        self._set_amdl_path()

    def _set_amdl_path(self):
        """Locate the matching ``.amdl`` next to the ``.gmdl.gfxbin``.

        Probes (in order) the model folder, the parent folder, and a sibling
        ``common`` folder. When a folder contains more than one ``.amdl``,
        disambiguates by matching against ``model_name`` and its underscore
        prefix. Sets ``self.amdl_path`` to ``None`` when nothing is found so
        callers can surface a friendly error.
        """
        folder = os.path.dirname(self.gfxbin_path)
        self.amdl_path = self._find_amdl_in_folder(folder)
        if self.amdl_path is None:
            up_folder = os.path.split(folder)[0]
            self.amdl_path = self._find_amdl_in_folder(up_folder)
            if self.amdl_path is None:
                common = os.path.join(up_folder, "common")
                if os.path.exists(common):
                    self.amdl_path = self._find_amdl_in_folder(common)

    def _find_amdl_in_folder(self, folder: str) -> str | None:
        if not os.path.isdir(folder):
            return None

        result = None
        file_count = 0
        for file in os.listdir(folder):
            if file.endswith(".amdl"):
                file_count += 1
                result = os.path.join(folder, file)

        if file_count < 2:
            return result

        # Multiple amdls in this folder — disambiguate by model name and its
        # underscore prefix (e.g. ``nh00_010`` then ``nh00``).
        names = [self.model_name]
        underscore = self.model_name.find("_")
        if underscore > 0:
            names.append(self.model_name[:underscore])

        for file in os.listdir(folder):
            if file.endswith(".amdl"):
                for name in names:
                    if name in file:
                        return os.path.join(folder, file)

        return None

    def set_base_directory(self, header: GfxbinHeader):
        # Get the URI of the first gpubin
        gpubin_uri = None
        for key in header.dependencies:
            if header.dependencies[key].endswith(".gpubin"):
                gpubin_uri = header.dependencies[key]
                break

        self.base_uri = gpubin_uri[: gpubin_uri.rfind("/")]
        self.base_directory = os.path.dirname(self.gfxbin_path)

    def get_absolute_path_from_uri(self, uri: str):
        if (
            uri.endswith(".tif")
            or uri.endswith(".exr")
            or uri.endswith(".png")
            or uri.endswith(".dds")
            or uri.endswith(".btex")
        ):
            return self._resolve_texture_path(uri)
        else:
            path = self._get_absolute_path_from_uri(uri)

            if not os.path.exists(path):
                print(f"[WARNING] File did not exist at {path}")
                return None
            else:
                return path

    def _get_absolute_path_from_uri(self, uri: str):
        # Get tokens for the part of the URIs that match
        tokens1 = uri.replace("://", "/").split("/")
        tokens2 = self.base_uri.replace("://", "/").split("/")
        target_tokens = []

        for i in range(min(len(tokens1), len(tokens2))):
            if tokens1[i] == tokens2[i]:
                target_tokens.append(tokens1[i])
            else:
                break

        # Get the folder name of the deepest matching folder
        if len(target_tokens) > 0:
            target_token = target_tokens[-1]
        else:
            target_token = ""

        # Get the index of the highest folder the URIs have in common
        index = -1
        counter = 0
        base_tokens = self.base_uri.replace("://", "/").split("/")

        for i in range(len(base_tokens) - 1, -1, -1):
            if base_tokens[i] == target_token:
                index = i
                break

            counter += 1

        if index == -1:
            return None

        # Calculate the absolute path of the highest common folder
        base_path = self.base_directory
        for _ in range(counter):
            base_path = os.path.dirname(base_path)

        # Assemble the common URI start
        target = ""
        for i in range(len(target_tokens)):
            target += target_tokens[i]
            if i == 0:
                target += "://"
            else:
                target += "/"

        target = target[:-1]

        # Calculate the final absolute path
        remaining_path = uri.replace(target, "").replace("://", "/").lstrip("/")
        return os.path.join(base_path, remaining_path.replace(".gmtl", ".gmtl.gfxbin"))

    def _resolve_texture_path(self, uri: str):
        extensions = ["dds", "tga", "png"]

        high = uri[: uri.rfind(".")] + "_$h" + uri[uri.rfind(".") :]
        highest = high.replace("/sourceimages/", "/highimages/")
        medium = uri[: uri.rfind(".")] + "_$m1" + uri[uri.rfind(".") :]
        low = uri

        uris = [highest, high, medium, low]
        paths_checked = []

        for i in range(len(uris)):
            path = self._get_absolute_path_from_uri(uris[i])
            if path is not None:
                for j in range(len(extensions)):
                    without_extension = path[: path.rfind(".")]
                    with_extension = without_extension + "." + extensions[j]
                    paths_checked.append(with_extension)

                    if os.path.exists(with_extension):
                        return with_extension
                    else:
                        name = _path_name(without_extension)
                        udim = os.path.join(without_extension, f"{name}.1001.{extensions[j]}")
                        paths_checked.append(udim)
                        if os.path.exists(udim):
                            return udim

        # Fallback: the asset tree didn't yield a match. Probe well-known
        # texture sub-folders directly next to the ``.gmdl.gfxbin`` so users
        # can drop loose textures alongside a model and have them picked up.
        directory = os.path.dirname(self.gfxbin_path)
        slash = uri.rfind("/")
        dot = uri.rfind(".")
        if slash != -1 and dot > slash:
            file_name = uri[slash + 1 : dot]
            local_paths = [
                os.path.join(directory, "highimages", f"{file_name}_$h"),
                os.path.join(directory, "sourceimages", f"{file_name}_$h"),
                os.path.join(directory, "sourceimages", f"{file_name}_$m1"),
                os.path.join(directory, "sourceimages", file_name),
            ]
            for base in local_paths:
                for ext in extensions:
                    with_extension = base + "." + ext
                    paths_checked.append(with_extension)
                    if os.path.exists(with_extension):
                        return with_extension
                    name = _path_name(base)
                    udim = os.path.join(base, f"{name}.1001.{ext}")
                    paths_checked.append(udim)
                    if os.path.exists(udim):
                        return udim

        print("")
        print(f"[WARNING] Could not find texture for {uri} - checked:")
        for i in range(len(paths_checked)):
            print(f" {paths_checked[i]}")
        print("")
        return None
