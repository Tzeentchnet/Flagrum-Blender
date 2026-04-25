# Flagrum.Blender (add-on source)

This directory is the **active source tree** for the Flagrum-Blender add-on (`flagrum`, version `2.0.2`). It is shipped as a [Blender Extension](https://docs.blender.org/manual/en/latest/extensions/index.html) and targets **Blender 5.0+**.

For installation, feature matrix, and usage notes, see the [top-level README](../../README.md).

## Layout

```
src/Flagrum.Blender/
├── __init__.py             # Extension registration (no bl_info — see manifest)
├── blender_manifest.toml   # Extension metadata, permissions, build excludes
├── entities.py             # Dataclasses shared across import/export
├── globals.py              # Module-level singletons / lookup tables
├── helpers.py              # UI helpers (e.g. wrapped-text labels)
├── import_export/          # File pipelines
│   ├── gfxbin/             # Pure-Python GMDL/GMTL/GPUBIN parsers
│   ├── gmdlimporter.py     # Skinned mesh import
│   ├── gmtlimporter.py     # Material import (Principled BSDF)
│   ├── generate_*.py       # Armature / mesh / material / terrain builders
│   ├── pack_mesh.py        # FMD export — triangulation, edge-splits, weights
│   ├── interop.py          # Pure-Python shim (replaces former C# tooling)
│   ├── menu.py             # Blender file-import / file-export operators
│   └── ...
├── panel/                  # N-panel UI (material, normals, parts, cleanup, rendering)
├── templates/              # 14 JSON material templates used at export time
└── utilities/              # Compat shim, asset catalog, collections, timer
```

## Conventions

- **Pure Python only.** No external dependencies; NumPy ships with Blender. The hand-rolled `MessagePackReader` under `import_export/gfxbin/` covers the binary format.
- **Blender 5+ APIs only.** Compatibility with older Blender is not maintained. The `utilities/blender_compat.py` shim still exists, but it now centralises 5.x-era socket/role lookups (Principled BSDF v2, EEVEE-Next render method, etc.) rather than versioned branches.
- **Per-import collection bundle.** `utilities/import_collections.RootCollections` owns the root collection plus `LOD<n>` / `VEMs` / `Parts` sub-collections; everything that adds objects during import goes through it for consistent naming and color tags.
- **Asset catalogs.** Imported root collections and materials are asset-marked under deterministic catalog paths so re-imports of the same model coalesce into the same library entries (`utilities/asset_catalog.py`).
- **Hot paths are vectorised.** Vertex streams, UV/color expansion, normal correction, and weight bucketing are all NumPy-driven (`import_export/gfxbin/vertex_decode.py`, `gmdlimporter._import_mesh`).

## Local development

From the repo root:

```powershell
# Lint with ruff (configuration lives in ../../pyproject.toml)
py -3.13 -m ruff check src\Flagrum.Blender

# Byte-compile sanity check (49 files)
py -3.13 -m compileall -q src\Flagrum.Blender

# Build the extension zip (requires Blender 5+ on PATH)
blender --command extension build --source-dir src/Flagrum.Blender --output-dir dist
```

The `[build]` table in [blender_manifest.toml](blender_manifest.toml) excludes `__pycache__/`, `*.pyc`, IDE folders, and the legacy `addon_updater*.py` files from the produced zip.

## Notes for contributors

- **Do not edit** `modules/Flagrum/Flagrum.Blender/` — that is a frozen historical snapshot of the upstream tree.
- Multi-step changes are tracked in [docs/PLAN.md](../../docs/PLAN.md). Update phase status when starting or finishing work.
- The repo memory (`/memories/repo/flagrum_blender_assessment_2026-04-25.md`) holds the latest accuracy/usability assessment; keep repo memory in sync if structural changes land.