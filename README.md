<div align="center">

<picture>
  <img alt="Smoothing Wall Speed Along Z logo" src="resources/images/icon.png" width="128" height="128">
</picture>

# Smoothing Wall Speed Along Z — OrcaSlicer Plugin

[![CI](https://github.com/persano/smooth-z-wall-speed-plugin/actions/workflows/ci.yml/badge.svg)](https://github.com/persano/smooth-z-wall-speed-plugin/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/persano/smooth-z-wall-speed-plugin)](https://github.com/persano/smooth-z-wall-speed-plugin/releases)
[![OrcaCloud](https://img.shields.io/badge/OrcaCloud-Plugin%20Hub-teal.svg)](https://cloud.orcaslicer.com/app/plugins/plugin-hub/5f796029-31f3-4be8-88ce-29a0cf2d6724)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPLv3-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![OrcaSlicer](https://img.shields.io/badge/OrcaSlicer-v2.4%2B%20%7C%20v2.5%20nightly-orange.svg)](https://github.com/OrcaSlicer/OrcaSlicer)

<p>An OrcaSlicer Python plugin bringing Bambu Studio and Creality Print 5's <b>"Smoothing Wall Speed Along Z"</b> (<code>z_direction_outwall_speed_continuous</code>) feature to OrcaSlicer.</p>

</div>

---

## OrcaSlicer UI Integration

![Smoothing Wall Speed Along Z Plugin Tab in OrcaSlicer](resources/images/orcaslicer_plugin_tab_preview.jpg)

The plugin provides a dedicated interactive top-level tab (**`Smooth Z Speed`**) inside OrcaSlicer to configure Simple (1:1 Bambu/Creality) and Advanced modes, visualize the Gaussian kernel, and synchronize settings across slicing sessions.

---

## Why This Exists

In 3D slicing, sudden geometry changes (overhangs, small features, cooling layer-time thresholds) force the slicer to abruptly drop outer wall speeds from e.g. 200 mm/s to 40 mm/s.

When outer wall speed changes sharply between adjacent layers:
- **Gloss & Sheen Inconsistency**: Filament (especially Silk PLA, PETG, ABS) appears shiny at slow speeds and matte at fast speeds.
- **Speed Banding / Hull Lines**: Melt zone pressure differences cause horizontal ring artifacts or layer bulging.

Bambu Studio and Creality Print 5 (`CrealityOfficial/CrealityPrint`) implement a dedicated C++ engine algorithm (`libslic3r/GCode/Smoothing.cpp`) to solve this using an iterative 1D Gaussian kernel relaxation, but OrcaSlicer lacks the C++ engine implementation.

This plugin bridges the gap using OrcaSlicer's modern `slicing-pipeline` plugin system. It runs at the G-code post-processing seam (`psGCodePostProcess`), enforcing continuous, gradual speed transitions along the vertical $Z$ axis matching the official C++ slicer behavior.

```mermaid
flowchart LR
    A["Raw Slicer Output: Sharp Step Jump<br>(200 mm/s ➔ 40 mm/s)"] --> B["Bambu / Creality Gaussian Relaxation Filter<br>(Kernel W=11, r=2.0)"]
    B --> C["Continuous Z Ramp<br>(200 ➔ 160 ➔ 120 ➔ 80 ➔ 40 mm/s)"]
    C --> D["Uniform Wall Finish & No Speed Lines"]
```

---

## Simple vs Advanced Mode

In Bambu Studio and Creality Print, this feature is a single checkbox with no tunable parameters. This plugin provides both:

1. **Simple Mode (Default — Zero Config)**:
   - Exactly matches Bambu Studio and Creality Print (`libslic3r/GCode/Smoothing.cpp`).
   - Uses the hardcoded iterative 1D Gaussian kernel relaxation ($W=11, r=2.0$, stop threshold $5.0\text{ mm/s}$).
   - No settings to adjust: just enable and slice.

2. **Advanced Mode**:
   - Set `"mode": "advanced"` in Plugin Configuration.
   - Fine-tune Gaussian standard deviation `gaussian_radius`, kernel window `gaussian_window_size`, and convergence threshold `gaussian_stop_threshold_mm_s`.
   - Or switch to linear gradient ramp limiting (`"smoothing_algorithm": "gradient"`).

---

## Features

- **1:1 Match with Bambu Studio & Creality Print 5**: Direct Python implementation of `libslic3r/GCode/Smoothing.cpp` iterative Gaussian filter ($W=11, r=2.0$, stop threshold $5\text{ mm/s}$).
- **Safe Velocity Clamping**: Fast layers are smoothly ramped down towards slow layers. Safe slow speeds on overhangs and small details are never sped up.
- **Preserves Critical Moves**: Inner walls, sparse infill, solid infill, bridges, and travels keep their exact slicer speeds.
- **Spiral Vase Mode Detection**: Automatically bypasses spiral vase prints as intended.
- **First-Layer Safety**: Configurable exclusion of initial layers to protect bed adhesion feedrates.
- **Zero Recompilation**: Installs directly into stock or portable OrcaSlicer builds.

---

## Installation

### Method 1: OrcaCloud Plugin Hub (Recommended)
1. Subscribe on the [OrcaCloud Plugin Page](https://cloud.orcaslicer.com/app/plugins/plugin-hub/5f796029-31f3-4be8-88ce-29a0cf2d6724).
2. In OrcaSlicer, open **File** -> **Plugins** and click **Refresh**.
3. Check **Activate** for **Smoothing Wall Speed Along Z**.
4. Restart OrcaSlicer.

### Method 2: Manual Zip Install
1. Download `smooth_z_wall_speed_plugin.zip` from [Releases](https://github.com/persano/smooth-z-wall-speed-plugin/releases/latest).
2. Unpack into your OrcaSlicer plugins folder:
   - **Windows**: `%APPDATA%\OrcaSlicer\orca_plugins\smooth_z_wall_speed\`
   - **Linux**: `~/.config/OrcaSlicer/orca_plugins/smooth_z_wall_speed/`
   - **macOS**: `~/Library/Application Support/OrcaSlicer/orca_plugins/smooth_z_wall_speed/`
3. Restart OrcaSlicer.

### Method 3: Python Wheel Install
1. Open OrcaSlicer -> **File** -> **Plugins**.
2. Click **Install from Wheel...** and select `smooth_z_wall_speed-<version>-py3-none-any.whl` from the [latest release](https://github.com/persano/smooth-z-wall-speed-plugin/releases/latest) (or your OS-specific wheel).
3. Restart OrcaSlicer.

---

## Dedicated UI Tab & Configuration

This plugin registers an interactive top-level tab in OrcaSlicer named **`Smooth Z Speed`**:
- **Simple Mode**: One-click 1:1 match with Bambu Studio & Creality Print 5. Zero configuration required.
- **Advanced Mode**: Tune Gaussian radius, kernel window size, convergence threshold, or switch to linear gradient ramp.
- **Interactive Curve Visualizer**: Live canvas chart of the Gaussian filter kernel.
- **Persistent Storage**: Saved settings automatically sync to the slicing pipeline.

### How to Apply to a Print
1. In OrcaSlicer, open your **Process** profile (left sidebar).
2. Navigate to **Others** -> scroll to **Slicing Pipeline Plugin**.
3. In the dropdown picker, select **Smoothing Wall Speed Along Z**.
4. Slice and export/print.

> [!NOTE]
> **Is the smoothing visible in the preview?**
> Yes. After slicing, switch the preview legend to **Speed**: the outer wall speeds show the continuous Z ramp instead of sharp steps. The plugin runs at `psGCodePostProcess` and the preview shows its result. It is also in the exported `.gcode` (outer wall `F...` feedrates).

---

## Configuration Options

Inside OrcaSlicer (**Process -> Others -> Plugin Configuration**), the following parameters are available:

| Parameter | Default | Description |
|---|---|---|
| `enabled` | `true` | Master toggle for the plugin. |
| `mode` | `"simple"` | `"simple"` (zero-config 1:1 match) or `"advanced"` (custom parameters). |
| `smoothing_algorithm` | `"gaussian"` | `"gaussian"` (1:1 match with Bambu/Creality C++ algorithm) or `"gradient"` (linear slope). |
| `gaussian_radius` | `2.0` | Gaussian standard deviation radius $r$ (Bambu/Creality default: `2.0`). |
| `gaussian_window_size` | `11` | Gaussian filter window size (Bambu/Creality default: `11`). |
| `gaussian_stop_threshold_mm_s` | `5.0` | Stop convergence threshold between adjacent layers in mm/s (Bambu/Creality default: `5.0`). |
| `max_steps_count` | `1000` | Maximum relaxation iterations. |
| `max_speed_change_per_mm` | `50.0` | Maximum speed change in mm/s per 1 mm Z when in `"gradient"` mode. |
| `min_outer_wall_speed_mm_s` | `10.0` | Floor speed clamp in mm/s. |
| `skip_first_layers` | `1` | Number of initial layers to leave untouched (ensures bed adhesion). |
| `smooth_overhang_layers` | `true` | If true, overhang moves faster than the smoothing target are clamped down to it. Overhangs are never included in the smoothing seed, matching Bambu/Creality behavior. |
| `smooth_outer_walls` | `true` | If true, outer wall speeds are smoothed along Z. Uncheck to leave the outer wall alone. |
| `smooth_internal_walls` | `false` | If true, inner wall speeds are smoothed along Z as well. Inner walls use their own series, so fast inner moves never weaken the outer wall target and slow inner moves are never raised. With both wall toggles off the plugin does nothing. |

---

## CLI Usage (Standalone / Post-Processing Script)

The script can also be executed outside of OrcaSlicer as a standalone post-processing script:

```bash
python smooth_z_wall_speed.py input.gcode -o output.gcode --mode simple
```

---

## License

GPL-3.0 License. See [LICENSE](LICENSE) for details.
