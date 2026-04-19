# Flagrum-Blender

A Blender add-on for importing **Final Fantasy XV** (Luminous Engine) models, materials, environments, and terrain — and for exporting outfit/prop mods back into Flagrum's `.fmd` model-pack format.

This repository is a **Blender 5+ fork** of [Kizari/Flagrum](https://github.com/Kizari/Flagrum)'s Blender add-on. The companion **Flagrum Desktop** application (Windows, .NET) lives upstream and is unchanged; this fork only ships the Blender plugin.

> [!IMPORTANT]
> Starting at `2.0.0`, Flagrum-Blender targets **Blender 5.0 and newer only** and is distributed as a [Blender Extension](https://docs.blender.org/manual/en/latest/extensions/index.html). It no longer ships any C#/.NET runtime — all GMDL/GMTL/GPUBIN parsing happens in pure Python. If you need Blender 3.0–4.x support, install the upstream `1.x` release from [Kizari/Flagrum](https://github.com/Kizari/Flagrum/releases) instead.

## Requirements

- **Blender 5.0** or newer
- The **Flagrum Desktop** application from [Kizari/Flagrum](https://github.com/Kizari/Flagrum) for unpacking the game's archives and producing `.fed` (environment) and `.ftd` (terrain) packs that this add-on can read. GMDL/GMTL files (the per-model formats) can be opened directly without the desktop tool.

## Installation

### From a release zip

1. Download `flagrum-2.0.0.zip` from the [Releases page](https://github.com/Kizari/Flagrum-Blender/releases/latest).
2. In Blender, open `Edit > Preferences > Get Extensions`.
3. Click the dropdown in the top-right → `Install from Disk...` and choose the downloaded zip.

### From source (developer)

```powershell
# Clone the fork
git clone https://github.com/Kizari/Flagrum-Blender.git
cd Flagrum-Blender

# Build the extension zip (requires Blender 5+ on PATH)
blender --command extension build --source-dir src/Flagrum.Blender --output-dir dist
```

The resulting `dist/flagrum-2.0.0.zip` can be installed via `Get Extensions > Install from Disk...`.

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

Per-import collections are created with deterministic naming (`<model>`, `<model>.LOD0`, `<model>.VEMs`, `<model>.Parts`) and asset-marked so re-imports do not duplicate catalog entries.

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

## Repository layout

```
src/Flagrum.Blender/      # the active add-on source — this is what ships
modules/Flagrum/          # frozen upstream snapshot, kept for historical comparison
docs/PLAN.md              # modernization plan and phase tracker
CHANGELOG.md              # fork-specific changelog (starts at 2.0.0)
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

GPL-3.0-or-later. See [LICENSE](LICENSE).

## Credits

- Original Flagrum project: **Kizari** and contributors — <https://github.com/Kizari/Flagrum>
- This Blender 5+ fork is maintained separately from the desktop application.
# Flagrum-Blender

[Flagrum's](https://github.com/Kizari/Flagrum) companion Blender Add-on.

Enables importing of FFXV models, environments, and terrain into Blender—as well as exporting of outfit mods to Flagrum's model pack format.

> [!WARNING]  
> Flagrum-Blender does not work in newer versions of Blender due to breaking changes in Blender's API.  
> **Please use Blender 3.0 for best results.**

## Installation

1. Go to the [Releases page](https://github.com/Kizari/Flagrum-Blender/releases/latest) and download `Flagrum-Blender.zip`
2. Launch Blender and go to `Edit > Preferences` from the top menu
3. Select the `Add-ons` tab from the left menu
4. Click the `Install...` button in the top-right of the preferences window
5. Select `Flagrum-Blender.zip` that you downloaded in the first step, then click `Install Add-on`

## Usage

There are numerous guides on the [Flagrum wiki](https://github.com/Kizari/Flagrum/wiki) that demonstrate the usage of this add-on.
Please read the sidebar carefully to find which guides are most relevant to you.
