# Flagrum Blender — Modernization Plan

Active source: `src/Flagrum.Blender/`. Reference snapshot at `modules/Flagrum/Flagrum.Blender/` is **frozen** (do not edit).
Target: Blender 5.0+, Python 3.13, no .NET, no external Python deps.

## Status

| Phase | Title                                      | State        |
|------:|--------------------------------------------|--------------|
| 0     | Eliminate C#/.NET interop                  | ✅ complete  |
| 1     | Extensions packaging & Blender 5 floor     | ✅ complete  |
| 2     | Blender 5 API surgery                      | ✅ complete  |
| 3     | Per-import root collection structure       | ✅ complete  |
| 4     | NumPy hot-path vectorization               | ✅ complete  |
| 5     | Cleanup, README, lint, smoke matrix        | 🚧 in progress |
| 6+    | Stretch / post-2.0                         | ⏳ pending   |

## Phase 5 — Cleanup & release prep

Goal: ship `2.0.0` as a Blender Extension.

### 5a. Code cleanup
- [x] Verified `addon_updater_ops` references are gone (re-grepped 2026-04-18 — clean).
- [x] No `_pack_*` style commented blocks remain in `pack_mesh.py` (only real function definitions).
- [x] Audited `import_export/menu.py`: env (`.fed`) and terrain (`.ftd`) JSON paths read files produced by **Flagrum Desktop**, not the removed C# tooling — paths are legitimate.
- [x] All 14 templates resolve via `panel/material_data.py` enum + `interop.py` export packer (no orphans).
- [x] No bare `except:` blocks in `src/Flagrum.Blender/**` (verified via regex sweep).
- [x] Unused-imports audit clean (covered by ruff `F401`).
- [x] First targeted ruff sweep clean: `ruff check src\Flagrum.Blender --select F821,F841,B006,F401,UP035` (2026-04-18).

### 5b. Lint & static checks
- [x] `pyproject.toml` `[tool.ruff]` already in place (line-length 120, py313, sensible ignores).
- [x] `py -3.13 -m ruff check src\Flagrum.Blender` — **all checks passed** (2026-04-18).
  - 49 issues auto-fixed via `--fix --unsafe-fixes` (imports, UP015, W292, UP045, W293).
  - 15 manual fixes: UP031 `%`-format → f-strings in `generate_armature.py`; B007 `for i in range(...)` → `for _ in range(...)` across `gmdl.py`, `gmtl.py`, `read_armature_data.py`.
- [ ] `ruff format src/Flagrum.Blender` — **deferred**: would reformat 48 files (large diff churn unrelated to behaviour). Run before tagging if desired.
- [x] `py -3.13 -m compileall -q src\Flagrum.Blender` — clean (2026-04-18).

### 5c. Documentation
- [x] Top-level `README.md` rewritten for the fork (Blender 5+ install, feature matrix, known limitations, link to upstream `Kizari/Flagrum`).
- [x] `src/Flagrum.Blender/README.md` rewritten as addon-local layout/conventions guide.
- [ ] Add a short `CONTRIBUTING.md` if we expect outside PRs (optional — skipped for now).
- [ ] Roll changelog `[Unreleased]` → `[2.0.0] - YYYY-MM-DD` once smoke matrix passes.

### 5d. Manual smoke matrix
Execute on Blender 5.0 (and 5.1 if available) with `--factory-startup`:

| # | Asset                                  | Import | Export | Notes                       |
|--:|----------------------------------------|:------:|:------:|-----------------------------|
| 1 | Hero character (skinned, multi-LOD, VEMs) |        |        | Confirm parts empties, weights |
| 2 | Outfit / cloth (transmission, alpha)   |        |        | Material socket sanity        |
| 3 | Eye / glass (named-human templates)    |        |        | Specular IOR, emission        |
| 4 | Static prop (no armature)              |        |        | Root collection link         |
| 5 | Environment .ebex prefab (env path)    |        |        | `generate_mesh.py` path      |
| 6 | Terrain tile                           |        |        | `generate_terrain.py` shaders|
| 7 | Re-import same model twice             |        |        | Asset catalog dedupe         |
| 8 | Round-trip export → reimport (FMD)     |        |        | Normals/tangents preserved   |

For each row capture: import time (Timer output), Blender console errors, visual diff vs. reference render.

### 5e. Packaging
- [x] `blender_manifest.toml` already at `version = "2.0.0"`, `blender_version_min = "5.0.0"`. Tagline + permissions strings shortened to satisfy the 64-char manifest limit; added `.idea/` to `paths_exclude_pattern`.
- [x] Built `flagrum-2.0.0.zip` via `blender --command extension build --source-dir src/Flagrum.Blender --output-dir dist` on Blender 5.1 (2026-04-18, 65 entries, ~370 KB).
- [x] Verified `__pycache__`, `*.pyc`, `venv/`, `.git*`, `.idea/`, `.vscode/` correctly excluded from the produced zip.
- [ ] Smoke-install the produced zip via Extensions UI on a clean Blender profile.
- [ ] Tag `v2.0.0`, attach zip to GitHub release, update CHANGELOG date.

## Phase 6+ — Post-2.0 candidates (not scheduled)

- **Async import** — chunk per-mesh work behind a modal operator so the UI stays responsive on large hero imports.
- **Bulk import operator** — point at a folder, import every `.gmdl.gfxbin` with progress bar.
- **GMTL writer** — currently we only read; round-tripping authored shader graphs back to GMTL would unblock material editing.
- **Skeletal animation** — `.amdl` clip import (bones-only is in; clips are not).
- **Tangent reuse on export** — the legacy `_pack_normals_and_tangents` recomputes from Blender; using stored tangents from import would be lossless for re-export of unmodified meshes.
- **Profiling pass** — use `cProfile` against the smoke matrix and confirm Phase 4 actually delivered the targeted speedups; record numbers in CHANGELOG.
- **Type hints across `panel/`** — currently bpy property descriptors are bare; modern `Annotated` syntax would help Pylance.
- **Drop hand-rolled `MessagePackReader`** — only if a stdlib-only alternative exists; we cannot add 3rd-party deps under the Extensions sandbox.
- **i18n** — upstream had `.resx` files for Web; addon UI strings are not translated. Probably out of scope.

## Operating notes (for future sessions)

- Two source trees exist; only edit `src/Flagrum.Blender/`. Treat `modules/Flagrum/Flagrum.Blender/` as historical.
- Compile check command: `py -3.13 -m compileall -q src\Flagrum.Blender` (49 files as of Phase 4).
- Timer instrumentation lives in `utilities/timer.py`; `gmdlimporter._import_mesh` already prints per-stage durations — useful for benchmarking Phase 4 / Phase 6 changes.
- `repo memory` (`/memories/repo/flagrum_blender_architecture.md`) has the up-to-date map of the addon; keep it in sync if structural changes land.
