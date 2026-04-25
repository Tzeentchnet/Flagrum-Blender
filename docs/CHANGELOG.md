# Changelog — Flagrum Blender (this fork)

All notable changes to the **Flagrum Blender** add-on (the Blender-side companion plugin) are tracked in this file. The C# Flagrum Desktop application is *not* covered here.

This fork diverges from upstream `Kizari/Flagrum` starting at `2.0.0`. The reference snapshot under `modules/Flagrum/` is retained for historical comparison only.

## [Unreleased]

### Fixed

- **Release documentation is version-agnostic.** Release and source-build instructions now reference `flagrum-*.zip` so they do not go stale after every manifest version bump.
- **Rendering emission strength no longer crashes on non-Principled materials.** The Rendering panel now skips materials without a `Principled BSDF` node and reports a warning instead of raising `KeyError`.
- **Material copy/paste/reset now handles missing preset data.** The Material panel now guards empty or mismatched Flagrum material preset state and cancels with a user-visible warning instead of dereferencing `None`.
- **Environment and terrain imports now close JSON files and use portable paths.** Import operators and path discovery no longer rely on Windows-only backslash splitting for model, material, texture, and terrain paths.
- **Malformed mesh data now fails earlier with clearer errors.** GMDL import validates triangle index counts before reshaping, missing part IDs get deterministic fallback names, and FMD export supports mesh-only scenes without requiring an armature.

### Changed

- **Moved the changelog into `docs/`.** The fork changelog now lives at [docs/CHANGELOG.md](CHANGELOG.md), next to the modernization plan.

## [2.0.2] - 2026-04-19 — Cherry-picked fixes from CybersoulXIII fork

Reviewed [CybersoulXIII/Flagrum-Blender](https://github.com/CybersoulXIII/Flagrum-Blender) (which forked upstream `Kizari/Flagrum-Blender` and added Blender 5.0+ support on top of unmodified `1.3.0`). The bulk of that fork — Principled BSDF socket renames, `ShaderNodeSeparate/CombineColor`, `interface.new_socket`, the `use_auto_smooth` guard — was already covered by our own Phase 2 surgery and the `utilities/blender_compat.py` shim. Six **orthogonal** behaviour improvements remained worth borrowing; this release ports those.

Credit: CybersoulXIII for the upstream patches.

### Fixed

- **Emissive textures now glow on import.** Blender 4.x+ defaults the Principled BSDF `Emission Strength` socket to `0`, which silently swallows any emissive texture link. After wiring `Emission Color` we now also set `Emission Strength = 1.0` so the surface renders as authored. Affects both [import_export/generate_material.py](../src/Flagrum.Blender/import_export/generate_material.py) (env path) and [import_export/gmtlimporter.py](../src/Flagrum.Blender/import_export/gmtlimporter.py) (model path).
- **Pre-2022 GMDL skin weights no longer collapse onto a single bone.** Legacy assets sometimes ship with multiple bones whose `unique_index` is the sentinel `65535`; indexing the bone table by `unique_index` then overwrote every collided entry. [import_export/gmdlimporter.py](../src/Flagrum.Blender/import_export/gmdlimporter.py) now detects that case and falls back to sequential numbering, preserving the original weight mapping.
- **`L_UpperArm` is no longer eligible for cleanup-pass deletion.** Added to the canonical keep-list in [panel/cleanup_panel.py](../src/Flagrum.Blender/panel/cleanup_panel.py).

### Added

- **Smarter AMDL discovery.** [import_export/import_context.py](../src/Flagrum.Blender/import_export/import_context.py) now probes the model folder, the parent folder, and a sibling `common/` folder when locating the matching `.amdl`. When a folder contains more than one `.amdl`, the model name (and its underscore prefix — e.g. `nh00_010` → `nh00`) is used to disambiguate. When no match is found, `amdl_path` is left as `None` and the import operator surfaces a friendly error instead of crashing.
- **Friendly error when a rigged model is missing its AMDL.** [import_export/menu.py](../src/Flagrum.Blender/import_export/menu.py) now imports the gfxbin and bone table first, then aborts with `self.report({'ERROR'}, ...)` if bones exist but no AMDL was resolved. Mesh-only props (empty bone tables) continue to import fine without an AMDL.
- **Texture path fallback near the model.** When the canonical asset-tree lookup fails, [import_export/import_context.py](../src/Flagrum.Blender/import_export/import_context.py) now also probes `<model_dir>/highimages/<name>_$h.<ext>`, `sourceimages/<name>_$h.<ext>`, `_$m1.<ext>`, plain `<name>.<ext>` and the `.1001.<ext>` UDIM variants. Helps when textures are dropped beside a model rather than in the canonical folder layout.
- **Texture file picker now accepts `.tga` and `.dds`.** Updated `filter_glob` in [panel/material_panel.py](../src/Flagrum.Blender/panel/material_panel.py).

### Changed

- **`GmdlImporter` import pipeline split into three public methods** (`import_gfxbin`, `generate_bone_table`, `import_meshes`) so callers can interleave validation. The legacy `run()` wrapper is kept as a convenience that drives all three in order. `set_base_directory(...)` is now folded into `import_gfxbin()` since it's a pure post-parse step.
- **`read_armature_data` is now `None`-safe.** Hardened against the new `amdl_path = None` sentinel even though the menu operator already guards against it.

## [2.0.1] - 2026-04-19 — Post-release docs & formatting

### Documentation

- **Top-level [README.md](../README.md) overhauled.**
  - Removed a stale duplicated copy of the upstream Kizari README that had been concatenated to the bottom of the file (along with its misleading "please use Blender 3.0" warning that contradicted the modern Blender 5+ section).
  - Repointed all repo URLs (clone, releases) from `Kizari/Flagrum-Blender` to `Tzeentchnet/Flagrum-Blender`.
  - Clarified that `.fed` / `.ftd` packs come from Flagrum Desktop's existing export workflow rather than a separate tool.
  - Added a drag-to-install note for the Blender Extensions UI.
  - Documented the per-import asset-catalog dedupe behaviour delivered in Phase 3.
  - Added a "no in-app auto-updater" entry under Known Limitations so users don't hunt for the removed CGCookie panel.
- **License section expanded** with the full SPDX identifier (`GPL-3.0-or-later`, matching [`blender_manifest.toml`](../src/Flagrum.Blender/blender_manifest.toml)), explicit upstream attribution (Kizari, 2021–2025), and fork attribution (Kenneth Peters / Tzeentchnet, 2026).

### Code style

- **Ruff format sweep** — `py -3.13 -m ruff format src\Flagrum.Blender` reformatted 48 files (1 already clean). Style-only; no behaviour changes. `ruff check` continues to pass and `compileall -q` is silent. Landed as a single dedicated commit so behaviour blame remains intact.

### Notes

- **Tag scheme going forward**: future releases will use semver tags (`v2.0.1`, `v2.1.0`, …). The original `flagrum` tag for the 2.0.0 release stays as a one-off.

## [2.0.0] - 2026-04-18 — Blender 5+ modernization

### Highlights

- **Blender 5.0+ only.** All legacy compatibility shims and version branches are removed.
- **Packaged as a Blender Extension** (`blender_manifest.toml`). The legacy `bl_info` block has been removed.
- **C#/.NET runtime eliminated.** The companion `Flagrum.Blender.exe`, the C# `Importer.cs` / `Program.cs`, the `Flagrum.Blender.csproj`, and the root `Flagrum.Blender.sln` are gone. All GMDL/GMTL/GPUBIN parsing happens in pure Python via the existing `import_export/gfxbin/` package.
- **No external Python dependencies.** The bundled hand-rolled MessagePack reader continues to be used; NumPy ships with Blender.

### Phase 0 — Eliminate C#/.NET interop *(complete)*

- **Deleted**: `src/Flagrum.Blender/Importer.cs`, `src/Flagrum.Blender/Program.cs`, `src/Flagrum.Blender/Flagrum.Blender.csproj`, `Flagrum.Blender.sln`.
- **Rewritten** [src/Flagrum.Blender/import_export/interop.py](../src/Flagrum.Blender/import_export/interop.py):
  - Removed `subprocess.Popen` calls into `Flagrum.Blender.exe`.
  - Removed JSON temp-file round-trip.
  - `Interop.import_material_inputs()` now reads `.gmtl.gfxbin` directly via the existing `Gmtl` parser and returns `shader_gen_name → values` from the parsed buffer table (the Python equivalent of the C# `InterfaceInputs` collection).
  - Removed dead `Interop.import_mesh()` (was hard-coded to a developer's local desktop path; mesh import has long been driven by `GmdlImporter` directly).
  - `Interop.export_mesh()` retained; templates path repointed from the removed `lib/templates/` to the in-repo `src/Flagrum.Blender/templates/`.

### Phase 1 — Extensions packaging & Blender 5 API floor *(complete)*

- **Added** [src/Flagrum.Blender/blender_manifest.toml](../src/Flagrum.Blender/blender_manifest.toml):
  - `schema_version = "1.0.0"`, `id = "flagrum"`, `version = "2.0.0"`, `blender_version_min = "5.0.0"`, `type = "add-on"`, `tags = ["Import-Export"]`, SPDX `GPL-3.0-or-later` license.
  - Declares minimal `files` permission (model/texture I/O via Blender file pickers).
  - Excludes `__pycache__/`, `*.pyc`, `venv/`, `addon_updater*.py` from the build.
- **Rewrote** [src/Flagrum.Blender/__init__.py](../src/Flagrum.Blender/__init__.py):
  - Removed `bl_info` (now in the manifest).
  - Removed `FlagrumPreferences`, all `addon_updater_ops` registration, and the auto-update interval properties.
  - Fixed two latent bugs in `unregister()`: it previously deleted `import_menu_item` from `MT_file_import` twice (instead of removing the export item from `MT_file_export`), and it never deleted `Object.flagrum_parts`.
- **Deleted** the CGCookie addon-updater plumbing (`addon_updater.py`, `addon_updater_ops.py`); future updates flow through a Blender Extensions repository.
- Removed the corresponding `addon_updater_ops` import and `check_for_update_background()` / `update_notice_box_ui()` calls from [src/Flagrum.Blender/panel/material_panel.py](../src/Flagrum.Blender/panel/material_panel.py).
- All 43 Python files in the addon parse cleanly under Python 3.12.

### Phase 2 — Blender 5 API surgery *(complete)*

- **Added** [src/Flagrum.Blender/utilities/blender_compat.py](../src/Flagrum.Blender/utilities/blender_compat.py): a centralised compat shim covering Principled BSDF v2 socket renames, the new `ShaderNodeSeparateColor` / `ShaderNodeCombineColor` / `ShaderNodeMix` node families, the 4.0+ node-group `interface` API, EEVEE-Next's `surface_render_method`, the byte-color attribute API, and a `Mesh.use_auto_smooth` replacement.
- **Rewrote** [src/Flagrum.Blender/import_export/generate_armature.py](../src/Flagrum.Blender/import_export/generate_armature.py):
  - Removed dead helpers `createEmptyTree`, `createRootNub`, `createNub`, `_generate_armature` that depended on removed APIs (`scene.objects.link`, `scene.update`, `Object.show_x_ray`, `Object.empty_draw_size`). Nothing referenced them outside of each other.
- **Updated** [src/Flagrum.Blender/import_export/generate_mesh.py](../src/Flagrum.Blender/import_export/generate_mesh.py):
  - Vertex colors now created via `mesh.color_attributes.new(...)` (Blender 4.0+) rather than the removed `mesh.vertex_colors.new(...)`.
  - Custom split normals applied via `apply_custom_split_normals()` from the compat shim — `Mesh.use_auto_smooth` is gone in 4.1+.
- **Updated** [src/Flagrum.Blender/import_export/gmdlimporter.py](../src/Flagrum.Blender/import_export/gmdlimporter.py): same color-attribute and custom-normals migrations.
- **Modernised** [src/Flagrum.Blender/import_export/gmtlimporter.py](../src/Flagrum.Blender/import_export/gmtlimporter.py):
  - `ShaderNodeMixRGB` → `ShaderNodeMix` (RGBA mode, sockets `A`/`B`/`Result`).
  - `ShaderNodeSeparateRGB` / `ShaderNodeCombineRGB` → `ShaderNodeSeparateColor` / `ShaderNodeCombineColor` with sockets `Color` / `Red` / `Green` / `Blue`.
  - Principled BSDF v2 sockets routed via `principled_input(bsdf, role)` (`'specular'`, `'transmission'`, `'emission'`).
  - `material.blend_method = 'CLIP'` → `set_alpha_clip(material)` (uses EEVEE Next's `surface_render_method`).
  - Node-group socket creation routed through `node_group_add_input` / `node_group_add_output` (4.0+ `group.interface` API).
- **Modernised** [src/Flagrum.Blender/import_export/generate_material.py](../src/Flagrum.Blender/import_export/generate_material.py): same shader-node and socket migrations as `gmtlimporter.py`. The two helper node groups (`_setup_normalise_group`, `_setup_split_normal_group`) now use the `group.interface` API and the new color/mix node families.
- **Modernised** [src/Flagrum.Blender/panel/rendering_panel.py](../src/Flagrum.Blender/panel/rendering_panel.py):
  - Emission link comparisons routed through a new `is_principled_socket(socket, role)` helper — the v2 socket display name is `Emission Color`, not `Emission`.
  - Emission/Specular socket reads/writes routed through `principled_input(bsdf, role)`.
  - `bsdf.inputs[20].default_value = …` (emission strength) now goes through `principled_input(bsdf, 'emission_strength')` rather than relying on socket index ordering.
- **Added** `is_principled_socket(socket, role)` to `utilities/blender_compat.py`.
- **Added** [src/Flagrum.Blender/utilities/bpy_context.py](../src/Flagrum.Blender/utilities/bpy_context.py): `set_object_mode(obj, mode)` wraps `bpy.ops.object.mode_set` in `bpy.context.temp_override(...)` for headless safety. Applied to all 18 mode-switch sites across [generate_armature.py](../src/Flagrum.Blender/import_export/generate_armature.py), [pack_mesh.py](../src/Flagrum.Blender/import_export/pack_mesh.py), [panel/cleanup_panel.py](../src/Flagrum.Blender/panel/cleanup_panel.py), [panel/normals_panel.py](../src/Flagrum.Blender/panel/normals_panel.py), and [panel/parts_panel.py](../src/Flagrum.Blender/panel/parts_panel.py) (10 sites).
- **Cleaned up** the lingering `Mesh.use_auto_smooth = True` writes in [pack_mesh.py](../src/Flagrum.Blender/import_export/pack_mesh.py) (export pipeline) and [panel/normals_panel.py](../src/Flagrum.Blender/panel/normals_panel.py): replaced with `apply_custom_split_normals(...)` or a direct `polygons.foreach_set("use_smooth", …)` write where the data-transfer modifier was the only consumer.
- **Verified** that `MeshVertex.select` / `MeshUVLoop.select` direct writes in `pack_mesh.py` and `normals_panel.py` remain valid in Blender 5 (the `select_set(...)` migration only applied to `Object.select`, which the addon never used). The earlier plan note was incorrect; no code change required.
- **Modernised** [src/Flagrum.Blender/import_export/generate_terrain.py](../src/Flagrum.Blender/import_export/generate_terrain.py): the same shader-node migrations applied to `gmtlimporter.py` / `generate_material.py` (Mix/Separate/Combine RGB → new color/mix node families with `A`/`B`/`Result` and `Color`/`Red`/`Green`/`Blue` sockets), the `_setup_blur_group` and `_setup_texture_array_group` node-group socket declarations now go through `node_group_add_input` / `node_group_add_output`, and the `bsdf.inputs[7]` / `bsdf.inputs[9]` indexed reads (Specular / Roughness) are routed through `principled_input(bsdf, role)` so they survive Principled BSDF v2's socket reordering.
- **Verified** all 46 Python files in the addon parse cleanly under Python 3.13.

### Still to do (this phase)

_Nothing outstanding — Phase 2 is closed._

### Phase 3 — Per-import root collection structure *(in progress)*

- **Added** [src/Flagrum.Blender/utilities/import_collections.py](../src/Flagrum.Blender/utilities/import_collections.py): `RootCollections` dataclass that owns the root collection plus lazily-created `LOD<n>` / `VEMs` / `Parts` sub-collections and applies a consistent `color_tag` palette (red root, green LODs, blue VEMs, purple Parts). Includes `create_part_empties(rc, names, parent)` for the Parts sub-collection.
- **Added** [src/Flagrum.Blender/utilities/asset_catalog.py](../src/Flagrum.Blender/utilities/asset_catalog.py): asset-marks the root collection and every imported material under deterministic catalog paths `Flagrum/<model>` and `Flagrum/<model>/Materials`. Catalog UUIDs are derived via `uuid.uuid5` so re-imports reuse the same catalog entries instead of duplicating them. Writes/updates a `blender_assets.cats.txt` next to the imported `.gmdl.gfxbin` so users who add the model's directory as an Asset Library see the catalogs by name.
- **Updated** [src/Flagrum.Blender/import_export/import_context.py](../src/Flagrum.Blender/import_export/import_context.py): exposes `model_name` and `root_collections: RootCollections` so every collaborator (importer, armature, materials) shares one collection bundle.
- **Refactored** [src/Flagrum.Blender/import_export/gmdlimporter.py](../src/Flagrum.Blender/import_export/gmdlimporter.py):
  - LOD / VEM sub-collections are now created via `RootCollections` and named `<model>.LOD0` / `<model>.VEMs` (was bare `LOD0` / `VEMs`, which collided across imports of different models).
  - VEMs collection is created lazily on first VEM mesh rather than during a separate scan pass.
  - After mesh import, builds a `<model>.Parts` sub-collection containing one Empty per `game_model.parts` entry, parented to the armature when present.
  - Removed dead `lods` / `has_vems` / `vems` instance fields (now lives on `RootCollections`).
  - Marks the root collection as an asset and writes `blender_assets.cats.txt` once all sub-collections are populated.
- **Updated** [src/Flagrum.Blender/import_export/gmtlimporter.py](../src/Flagrum.Blender/import_export/gmtlimporter.py): every imported `Material` is asset-marked with `catalog_simple_name = "Flagrum/<model>/Materials"`.
- **Updated** [src/Flagrum.Blender/import_export/generate_armature.py](../src/Flagrum.Blender/import_export/generate_armature.py): scene linking goes through `context.root_collections.link_to_scene()` (idempotent) rather than a raw `bpy.context.scene.collection.children.link(...)` call, matching the no-armature fallback path in `gmdlimporter`.
- **Verified** all 48 Python files in the addon parse cleanly under Python 3.13 (`py -3.13 -m compileall -q src\Flagrum.Blender`).
- **Backward-compat note**: existing user blends that referenced the bare `LOD0` / `VEMs` collection names will not auto-rename. Users should re-import affected models to pick up the new `<model>.LOD0` / `<model>.VEMs` naming.

### Phase 4 — NumPy hot-path vectorization *(in progress)*

- **Added** [src/Flagrum.Blender/import_export/gfxbin/vertex_decode.py](../src/Flagrum.Blender/import_export/gfxbin/vertex_decode.py): a structured-dtype `np.frombuffer` decoder that reads an entire `GmdlVertexStream` in a single call. Previously each vertex element was read with one `np.frombuffer` per vertex (≥ N×E Python iterations per stream); the new path issues one read per stream and converts each element to its final dtype with a single vectorised expression.
- **Rewrote** the per-mesh hot path in [src/Flagrum.Blender/import_export/gmdlimporter.py](../src/Flagrum.Blender/import_export/gmdlimporter.py) (`_import_mesh`):
  - **Vertex streams**: replaced the per-vertex per-element `np.frombuffer` loop with a single `decode_vertex_streams(...)` call. Removed the large block of dead/commented-out experimental decoders that lived above it.
  - **Position correction**: `correction_matrix @ Vector(...)` per vertex collapsed to one `(N,3) @ M.T` matmul (a `correction_matrix_np_T` mirror of the mathutils matrix is cached on the importer).
  - **Face winding**: `for face in face_indices: faces.append([face[2], face[1], face[0]])` → `face_indices[:, ::-1].tolist()`.
  - **UV expansion**: per-loop dict + Python flatten replaced with one `mesh.loops.foreach_get("vertex_index", ...)` + numpy fancy-index. The post-`20220707` UDIM tile branch is now a vectorised `np.where`.
  - **Color expansion**: same fancy-index pattern; out-of-range corners (older content with fewer color entries than vertices) are clamped + zero-filled vectorised.
  - **Normals**: per-normal `Matrix @ Vector` + normalize loop replaced with `(N,3) @ M.T` + `np.linalg.norm` divide.
  - **Parts mask**: `for i in range(len(polygons)): sequence.append(start <= i < end)` replaced with a `np.zeros(bool)` slice-assign + `foreach_set("value", mask)`.
  - **Vertex weights** (the dominant phase of import time on hero meshes): replaced the per-vertex per-slot per-component `vertex_group.add([j], w, 'ADD')` loop with a bucketed apply. Each (bone, vertex) pair is summed across both BLENDWEIGHT slots via `np.bincount` keyed on `bone * n_verts + vertex`, then `np.lexsort` groups runs of equal `(bone, integer-weight)` values so each bone makes ≤ 256 `vertex_group.add(verts, w, 'REPLACE')` calls instead of one per non-zero weight slot. Empty vertex groups are still pre-created for every bone in the bone table to preserve the cleanup-panel's expected roster.
  - Removed a dead `mesh.loops.foreach_get("normal", clnors)` read whose result was never used. Removed the now-unused `from array import array` and `mathutils.Vector` imports.
- **Rewrote** [src/Flagrum.Blender/import_export/generate_mesh.py](../src/Flagrum.Blender/import_export/generate_mesh.py) (the environment/JSON import path) with the same patterns: dataclass→numpy boundary helpers (`_positions_to_array`, `_uvs_to_array`, `_colors_to_array`, `_normals_to_array`), vectorised position/normal correction, fancy-indexed UV/color per-loop expansion, vectorised parts mask, and the same bucketed weight-application path.
- Decoder behaviour is unit-verified against a naive reference: bucket grouping correctly sums duplicate (bone, vertex) pairs across BLENDWEIGHT0/1, runs of equal weights are coalesced into a single `vertex_group.add(...)` call, and integer weight buckets match the float `ADD`-mode result (including the slot-overlap case).
- All 49 Python files in the addon parse cleanly under Python 3.13 (`py -3.13 -m compileall -q src\Flagrum.Blender`).

### Phase 5 — Cleanup & release prep *(complete)*

- **Ruff sweep** (`ruff check src\Flagrum.Blender --select F821,F841,B006,F401,UP035`) cleared the targeted-rule tree:
  - [src/Flagrum.Blender/import_export/generate_armature.py](../src/Flagrum.Blender/import_export/generate_armature.py): `createBone(..., per=[1,2,0,3])` → tuple default (B006).
  - [src/Flagrum.Blender/import_export/gmtlimporter.py](../src/Flagrum.Blender/import_export/gmtlimporter.py): dropped unused `import os` (F401).
  - [src/Flagrum.Blender/import_export/read_armature_data.py](../src/Flagrum.Blender/import_export/read_armature_data.py): removed three never-read locals (`offset_to_end_of_names`, `unk_count`, `offset`); the underlying `amdl_file.read(4)` advances are preserved (F841).
  - [src/Flagrum.Blender/panel/parts_panel.py](../src/Flagrum.Blender/panel/parts_panel.py): added `Context`, `UILayout`, `AnyType` to the `bpy.types` import list and dropped the string-quoted forward refs in `PartsGroupsList.draw_item` (F821).
  - [src/Flagrum.Blender/utilities/asset_catalog.py](../src/Flagrum.Blender/utilities/asset_catalog.py): `from typing import Iterable` → `from collections.abc import Iterable` (UP035).
  - [src/Flagrum.Blender/utilities/blender_compat.py](../src/Flagrum.Blender/utilities/blender_compat.py): dropped unused `import bpy` left over from earlier shim work (F401).
- **Full ruff sweep** — `py -3.13 -m ruff check src\Flagrum.Blender` reports **all checks passed**:
  - 49 issues auto-fixed via `ruff --fix --unsafe-fixes` (import sorting, `UP015` redundant open modes, `W292` trailing newlines, `UP045` `Optional[X]` → `X | None`, `W293` blank-line whitespace).
  - 15 manual fixes:
    - [src/Flagrum.Blender/import_export/generate_armature.py](../src/Flagrum.Blender/import_export/generate_armature.py): three `"..." % (...)` strings → f-strings (`UP031`).
    - [src/Flagrum.Blender/import_export/gfxbin/gmdl/gmdl.py](../src/Flagrum.Blender/import_export/gfxbin/gmdl/gmdl.py), [src/Flagrum.Blender/import_export/gfxbin/gmtl/gmtl.py](../src/Flagrum.Blender/import_export/gfxbin/gmtl/gmtl.py), [src/Flagrum.Blender/import_export/read_armature_data.py](../src/Flagrum.Blender/import_export/read_armature_data.py): `for i in range(...)` / `for p in range(...)` → `for _ in range(...)` where the index was unused (`B007`, 12 sites).
- **`pyproject.toml`** carries the addon-wide `[tool.ruff]` config (line-length 120, `target-version = "py313"`, `select = ["E", "F", "W", "I", "UP", "B"]`, scoped ignores for `__init__.py` re-exports and bpy idioms). `modules/`, `__pycache__/`, and `task_script.py` are excluded.
- **`ruff format`** deferred: would touch 48 files for whitespace-only churn unrelated to behaviour. Held back to keep the `2.0.0` diff focused.
- **Compile sanity** — `py -3.13 -m compileall -q src\Flagrum.Blender` clean across all 49 Python files.
- **Code-cleanup audit** — verified there are no `addon_updater_ops` references left, no commented `_pack_*` blocks in `pack_mesh.py`, no bare `except:` in the addon, and that all 14 templates under `templates/` are referenced (via `panel/material_data.py` enum and `import_export/interop.py` export packer).
- **`bpy.types` import audit** — swept all 16 unique `from bpy.types import …` symbols against Blender 5.1's exposed API; one stale name removed:
  - [src/Flagrum.Blender/panel/parts_panel.py](../src/Flagrum.Blender/panel/parts_panel.py): dropped the `AttributeGroup` import and decorative annotation (the type is no longer exposed via `bpy.types` in Blender 5; the underlying `mesh.attributes` collection works the same without the hint). This was the cause of an `ImportError: cannot import name 'AttributeGroup' from 'bpy.types'` at install time on the first `2.0.0` build.

### Documentation

- **Rewrote** [README.md](../README.md) for the Blender 5+ fork: drops the .NET install steps, documents the Extensions install flow, adds a feature matrix (skinned models, static props, materials, environments, terrain, bones), known limitations (double-sided normal autocorrection, UDIM color tiles, no `.amdl` clips, no GMTL writer), repository layout, and a developer cheat-sheet for `ruff` / `compileall` / `blender --command extension build`.
- **Rewrote** [src/Flagrum.Blender/README.md](../src/Flagrum.Blender/README.md) as an addon-local layout / conventions guide (collection bundle, asset catalogs, NumPy hot paths, no third-party deps, frozen `modules/` snapshot).

### Packaging

- **`blender_manifest.toml`** finalised: `version = "2.0.0"`, `blender_version_min = "5.0.0"`, SPDX `GPL-3.0-or-later`, `permissions.files`, and a `[build]` section excluding `__pycache__/`, `*.pyc`, `.git*`, `venv/`, `.vscode/`, `.idea/`, and the legacy `addon_updater*.py` files. Tagline and permissions strings shortened to satisfy Blender's 64-character manifest limit.
- **Built `flagrum-2.0.0.zip`** via `blender --command extension build --source-dir src/Flagrum.Blender` on Blender 5.1 (65 entries, ~370 KB). Verified via PowerShell zip inspection that none of the excluded patterns leak into the produced archive.
- **Install verified** by drag-and-drop into Blender 5.1 (post-`AttributeGroup` fix) — no errors at register time.
