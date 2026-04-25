# Flagrum-Blender

A Blender add-on for importing **Final Fantasy XV** (Luminous Engine) models, materials, environments, and terrain — and for exporting outfit/prop mods back into Flagrum's `.fmd` model-pack format.

This repository is a **Blender 5+ fork** of [Kizari/Flagrum](https://github.com/Kizari/Flagrum)'s Blender add-on. The companion **Flagrum Desktop** application (Windows, .NET) lives upstream and is unchanged; this fork only ships the Blender plugin.

> [!IMPORTANT]
> Starting at `2.0.0`, Flagrum-Blender targets **Blender 5.0 and newer only** and is distributed as a [Blender Extension](https://docs.blender.org/manual/en/latest/extensions/index.html). It no longer ships any C#/.NET runtime — all GMDL/GMTL/GPUBIN parsing happens in pure Python. If you need Blender 3.0–4.x support, install the upstream `1.x` release from [Kizari/Flagrum](https://github.com/Kizari/Flagrum/releases) instead.

## Requirements

- **Blender 5.0** or newer.
- The **Flagrum Desktop** application from [Kizari/Flagrum](https://github.com/Kizari/Flagrum) for unpacking the game's archives. GMDL/GMTL files (the per-model formats) can be opened directly without the desktop tool; environment (`.fed`) and terrain (`.ftd`) packs are produced by Flagrum Desktop's existing export workflow and then read by this add-on.

## Installation

### From a release zip

1. Download `flagrum-2.0.2.zip` from the [Releases page](https://github.com/Tzeentchnet/Flagrum-Blender/releases/latest).
2. In Blender, open `Edit > Preferences > Get Extensions`.
3. Click the dropdown in the top-right → `Install from Disk...` and choose the downloaded zip. Alternatively, drag the zip directly onto the Blender window — the Extensions UI accepts drops.

### From source (developer)

```powershell
# Clone the fork
git clone https://github.com/Tzeentchnet/Flagrum-Blender.git
cd Flagrum-Blender

# Build the extension zip (requires Blender 5+ on PATH)
blender --command extension build --source-dir src/Flagrum.Blender --output-dir dist
```

The resulting `dist/flagrum-2.0.2.zip` can be installed via `Get Extensions > Install from Disk...`.

## Features

| Area              | Import | Export | Notes                                                                  |
|-------------------|:------:|:------:|------------------------------------------------------------------------|
| Skinned models    | ✅     | ✅     | `.gmdl.gfxbin` + `.gpubin`; LODs and VEMs are optional on import.      |
| Static props      | ✅     | ✅     | Same pipeline; armature is skipped when no `.amdl` is present.         |
| Materials         | ✅     | ✅     | `.gmtl.gfxbin`; Principled BSDF graph; 14 export templates ship.       |
| Environments      | ✅     | ❌     | `.fed` packs produced by Flagrum Desktop.                              |
| Terrain           | ✅     | ❌     | `.ftd` packs; configurable mesh resolution.                            |
| Bones / armature  | ✅     | ✅     | `.amdl` skeleton; cycle-detection on import.                           |
| Animation clips   | ❌     | ❌     | Out of scope; bones-only.                                              |

Per-import collections are created with deterministic naming (`<model>`, `<model>.LOD0`, `<model>.VEMs`, `<model>.Parts`) and asset-marked under `Flagrum/<model>` so re-importing the same model reuses its catalog entries instead of duplicating them.

The fork no longer bundles an in-app auto-updater. Updates are published as new release zips (or, in the future, through a Blender Extensions repository) and installed via the same `Get Extensions > Install from Disk...` flow.

## Usage

After installation, FFXV import/export entries appear under:

- `File > Import > Flagrum` — GMDL, environment (`.fed`), terrain (`.ftd`)
- `File > Export > Flagrum` — `.fmd` model pack

The N-panel in the 3D viewport gains five Flagrum tabs once a Flagrum mesh is selected:

- **Material Editor** — texture slots and template selection
- **Normals** — custom normals and seam handling
- **Parts** — face-group editing for swappable mesh parts
- **Cleanup** — weight normalisation, removal of unused bones / vertex groups
- **Rendering** — emission toggle and strength

The upstream [Flagrum wiki](https://github.com/Kizari/Flagrum/wiki) covers the artist-side workflow in detail; the pipelines documented there still apply.

## Known limitations

- **Double-sided meshes** — the export-time normal autocorrection (the `Autocorrect Seam Normals` toggle on `File > Export`) can flip normals on double-sided geometry. Disable the toggle for those assets.
- **UDIM tiles on color attributes** are decoded but not round-tripped on export.
- **`.amdl` animation clips** are not imported; only the rest-pose skeleton is read.
- **GMTL writer** is not implemented; authored shader graphs cannot be re-packed into `.gmtl.gfxbin`.
- **No in-app auto-updater** — the legacy CGCookie updater panel was removed in `2.0.0`. Check the Releases page (or your Extensions repository, once configured) for new versions.

## Repository layout

```
src/Flagrum.Blender/      # the active add-on source — this is what ships
modules/Flagrum/          # frozen upstream snapshot, kept for historical comparison
docs/PLAN.md              # modernization plan and phase tracker
docs/CHANGELOG.md         # fork-specific changelog (starts at 2.0.0)
pyproject.toml            # ruff configuration for the addon source
```

Only `src/Flagrum.Blender/` is edited; `modules/Flagrum/` is intentionally read-only.

## Development

```powershell
# Lint
py -3.13 -m ruff check src\Flagrum.Blender

# Byte-compile sanity check
py -3.13 -m compileall -q src\Flagrum.Blender
```

## License

Licensed under the **GNU General Public License v3.0 or later** (`SPDX: GPL-3.0-or-later`, as declared in [`blender_manifest.toml`](src/Flagrum.Blender/blender_manifest.toml)). See [LICENSE](LICENSE) for the full text.

- Copyright © 2021–2025 **Kizari** and the original Flagrum contributors — upstream code (the entire pre-fork history).
- Copyright © 2026 **Kenneth Peters (Tzeentchnet)** — Blender 5+ fork modifications (everything in [src/Flagrum.Blender/](src/Flagrum.Blender/) starting at `2.0.0`, plus repository tooling).

Because the project is GPLv3-or-later, any redistribution — including derivative add-ons or repackaged builds — must remain under a compatible GPL-3.0-or-later license and preserve these copyright notices alongside the [LICENSE](LICENSE) file.

## Credits

- Original Flagrum project: **Kizari** and contributors — <https://github.com/Kizari/Flagrum>
- **CybersoulXIII** — <https://github.com/CybersoulXIII/Flagrum-Blender>. Several small import-path and material fixes in the `2.0.2` release were adapted from that fork; see the [CHANGELOG](docs/CHANGELOG.md#202---2026-04-19--cherry-picked-fixes-from-cybersoulxiii-fork) for the full list.
- This Blender 5+ fork is maintained separately from the desktop application.
