Smoothing Wall Speed Along Z is an advanced print quality plugin for OrcaSlicer that eliminates vertical speed banding and gloss lines on tall outer perimeters.

It brings the continuous Z-axis outer wall speed smoothing algorithm found in Bambu Studio and Creality Print 5 (`z_direction_outwall_speed_continuous`) directly to OrcaSlicer via the native Python slicing-pipeline architecture.

## Why this exists

When 3D printing complex geometry with overhangs, cooling slowdowns, or small cross-sections, the slicer abruptly drops outer wall speeds from e.g. 200 mm/s to 40 mm/s.

On materials with sensitive sheen (Silk PLA, PETG, ABS, translucent filaments), abrupt speed jumps create visible horizontal bands, gloss variations, and localized bulging lines.

This plugin runs during the slicing post-process phase (`psGCodePostProcess`), evaluating outer wall feedrates layer by layer and applying continuous Z-direction speed smoothing.

## Two Operating Modes

- **Simple Mode (Default — Zero Config)**: Operates identically to Bambu Studio and Creality Print. Uses the exact built-in 1D Gaussian kernel relaxation ($W=11, r=2.0$, stop threshold $5\text{ mm/s}$). Just turn it on and slice.
- **Advanced Mode**: Unlocks full parameter control for power users wishing to customize the Gaussian radius, kernel window, convergence delta threshold, or use linear gradient ramp limiting.

## Key Features

- **Safe Monotonic Clamping**: Adjacent fast layers are smoothly ramped down towards slower layers. Safe slow speeds required for overhangs or cooling thresholds are never sped up.
- **1:1 Bambu & Creality Algorithm**: Direct implementation of the iterative 1D Gaussian kernel relaxation ($W=11, r=2.0$) used in Bambu Studio and Creality Print (`libslic3r/GCode/Smoothing.cpp`).
- **Selective & Clean**: Inner walls, infill, bridges, and travels keep their exact slicer speeds.
- **Vase Mode Aware**: Automatically bypasses spiral vase mode prints.
- **First-Layer Safe**: Leaves initial bed adhesion layers untouched.
- **Pure Python**: Zero native binaries or compilation needed. Runs cross-platform on Windows, macOS, and Linux.

## How to use

1. Enable the plugin in OrcaSlicer (**Process** -> **Others** -> **Slicing Pipeline Plugin**).
2. Select **Smoothing Wall Speed Along Z**.
3. Slice your plate and print normally. Simple mode is active by default.
