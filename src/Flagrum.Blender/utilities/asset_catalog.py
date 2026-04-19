"""Asset Browser tagging for imported Flagrum models.

Phase 3 of the Blender 5 modernisation: every GMDL import marks its root
``Collection`` and each imported ``Material`` as an asset, sorted into a
deterministic catalog tree.

Catalog layout
--------------
::

    Flagrum/<model>                 (root collection)
    Flagrum/<model>/Materials       (every Material from the import)

Catalog UUIDs are derived deterministically via ``uuid.uuid5`` so re-importing
the same model reuses the same catalog entries (assets stay in place rather
than getting duplicated alongside fresh UUIDs).

Catalog file (``blender_assets.cats.txt``)
------------------------------------------
Blender discovers catalog names by reading a ``blender_assets.cats.txt`` file
at the root of any registered Asset Library. We write/append entries to a
``blender_assets.cats.txt`` next to the imported ``.gmdl.gfxbin`` so users who
add the model's directory as an Asset Library see proper named catalogs in
the Asset Browser.

If the user has not registered the directory as an Asset Library the catalog
file is harmless and the assets still carry ``catalog_simple_name`` as a
display fallback.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterable

import bpy

# Stable namespace for derived catalog UUIDs. Do not change — changing this
# value would orphan every existing catalog tagged by previous imports.
_CATALOG_NAMESPACE = uuid.UUID("7f1c1b1e-7a3a-4b6a-9d8a-f2a7c0c7b001")

_CATS_VERSION_LINE = "VERSION 1\n"
_CATS_FILENAME = "blender_assets.cats.txt"


# ---------------------------------------------------------------------------
# Catalog UUID derivation
# ---------------------------------------------------------------------------

def catalog_uuid(catalog_path: str) -> str:
    """Return a stable canonical UUID string for ``catalog_path``."""
    return str(uuid.uuid5(_CATALOG_NAMESPACE, catalog_path))


def model_catalog_path(model_name: str) -> str:
    """Catalog path for the root collection of ``model_name``."""
    return f"Flagrum/{model_name}"


def materials_catalog_path(model_name: str) -> str:
    """Catalog path for every material imported alongside ``model_name``."""
    return f"Flagrum/{model_name}/Materials"


# ---------------------------------------------------------------------------
# Asset marking
# ---------------------------------------------------------------------------

def _apply_catalog(asset_owner, catalog_path: str, simple_name: str) -> None:
    """Mark ``asset_owner`` as an asset and assign catalog metadata."""
    if asset_owner.asset_data is None:
        asset_owner.asset_mark()

    asset_owner.asset_data.catalog_id = catalog_uuid(catalog_path)
    asset_owner.asset_data.catalog_simple_name = simple_name


def mark_collection_asset(collection: bpy.types.Collection, model_name: str) -> None:
    """Asset-mark ``collection`` under ``Flagrum/<model_name>``."""
    _apply_catalog(collection, model_catalog_path(model_name), model_name)


def mark_material_asset(material: bpy.types.Material, model_name: str) -> None:
    """Asset-mark ``material`` under ``Flagrum/<model_name>/Materials``."""
    _apply_catalog(material, materials_catalog_path(model_name), material.name)


# ---------------------------------------------------------------------------
# blender_assets.cats.txt management
# ---------------------------------------------------------------------------

def _existing_uuids(cats_path: str) -> set[str]:
    """Return the set of catalog UUIDs already present in ``cats_path``."""
    seen: set[str] = set()
    if not os.path.isfile(cats_path):
        return seen

    with open(cats_path, encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("VERSION"):
                continue
            uuid_part = stripped.split(":", 1)[0]
            if uuid_part:
                seen.add(uuid_part)
    return seen


def ensure_cats_file(directory: str, catalog_paths: Iterable[str]) -> None:
    """Append entries for ``catalog_paths`` to ``directory``'s cats.txt.

    Creates the file with the required ``VERSION 1`` header if it does not
    exist. Existing entries (matched by UUID) are not duplicated. Failures
    here are non-fatal — Blender still shows assets without catalog names.
    """
    if not directory or not os.path.isdir(directory):
        return

    cats_path = os.path.join(directory, _CATS_FILENAME)

    try:
        existing = _existing_uuids(cats_path)
        new_lines: list[str] = []
        for path in catalog_paths:
            cat_uuid = catalog_uuid(path)
            if cat_uuid in existing:
                continue
            simple_name = path.replace("/", "-")
            new_lines.append(f"{cat_uuid}:{path}:{simple_name}\n")
            existing.add(cat_uuid)

        if not new_lines and os.path.isfile(cats_path):
            return

        if not os.path.isfile(cats_path):
            with open(cats_path, "w", encoding="utf-8") as handle:
                handle.write(_CATS_VERSION_LINE)
                handle.write("\n")
                handle.writelines(new_lines)
        elif new_lines:
            with open(cats_path, "a", encoding="utf-8") as handle:
                handle.writelines(new_lines)
    except OSError as exc:
        print(f"[WARNING] Could not update {cats_path}: {exc}")


def ensure_model_catalogs(directory: str, model_name: str) -> None:
    """Convenience: register both root and Materials catalogs for ``model_name``."""
    ensure_cats_file(
        directory,
        (model_catalog_path(model_name), materials_catalog_path(model_name)),
    )
