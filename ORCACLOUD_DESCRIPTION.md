Smoothing Wall Speed Along Z is an advanced print quality plugin for OrcaSlicer that eliminates vertical speed banding and gloss lines on tall outer perimeters.

It brings the continuous Z-axis outer wall speed smoothing algorithm found in Bambu Studio and Creality Print 5 (`z_direction_outwall_speed_continuous`) directly to OrcaSlicer via the native Python slicing-pipeline architecture.

## Why this exists

When 3D printing complex geometry with overhangs, cooling slowdowns, or small cross-sections, the slicer abruptly drops outer wall speeds from e.g. 200 mm/s to 40 mm/s.

On materials with sensitive sheen (Silk PLA, PETG, ABS, translucent filaments), abrupt speed jumps create visible horizontal bands, gloss variations, and localized bulging lines.

This plugin runs during the slicing post-process phase (`psGCodePostProcess`), evaluating outer wall feedrates layer by layer and applying a continuous 1D Gaussian kernel relaxation across the vertical Z axis.

## What it does

- **Eliminates Speed Discontinuities**: Blends outer wall speeds across vertical layers so transitions happen gradually rather than stepping sharply.
- **Safe Monotonic Clamping**: Adjacent fast layers are smoothly ramped down towards slower layers. Safe slow speeds required for overhangs or cooling thresholds are never sped up.
- **1:1 Bambu & Creality Algorithm**: Direct implementation of the iterative 1D Gaussian kernel relaxation ($W=11, r=2.0$, stop threshold $5\text{ mm/s}$) used in Bambu Studio and Creality Print (`libslic3r/GCode/Smoothing.cpp`).
- **Selective & Clean**: Inner walls, infill, bridges, and travels keep their exact slicer speeds.
- **Vase Mode Aware**: Automatically bypasses spiral vase mode prints.
- **First-Layer Safe**: Leaves initial bed adhesion layers untouched.
- **Pure Python**: Zero native binaries or compilation needed. Runs cross-platform on Windows, macOS, and Linux.

## How to use

1. Enable the plugin in OrcaSlicer.
2. Open **Process** settings -> **Others** -> **Slicing Pipeline Plugin**.
3. Select **Smoothing Wall Speed Along Z**.
4. Slice your plate and print normally.

## Configuration

Adjustable under **Plugin Configuration**:
- `smoothing_mode`: `"gaussian"` (default, 1:1 match) or `"gradient"`.
- `gaussian_radius`: `2.0` (standard deviation).
- `gaussian_window_size`: `11` (kernel window).
- `gaussian_stop_threshold_mm_s`: `5.0` (convergence threshold in mm/s).
- `min_outer_wall_speed_mm_s`: `10.0` (safety floor speed).
- `skip_first_layers`: `1` (preserves bed adhesion).
