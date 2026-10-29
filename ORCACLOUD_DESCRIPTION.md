Smoothing Wall Speed Along Z brings the continuous Z-axis outer wall speed smoothing feature found in Bambu Studio and Creality Print 5 (`z_direction_outwall_speed_continuous`) directly to OrcaSlicer via the native Python slicing-pipeline plugin architecture.

It eliminates vertical speed banding, uneven gloss, and bulging lines on tall vertical perimeters caused by abrupt layer-to-layer speed drops from overhangs or cooling thresholds.

---

## What it does

When 3D printing models with overhangs, small features, or varying layer times, the slicer abruptly slows down outer walls from e.g. 200 mm/s to 40 mm/s.

On materials sensitive to print velocity and melt temperature (such as Silk PLA, PETG, ABS, and translucent filaments), abrupt speed jumps create visible horizontal bands, gloss variations, and localized layer lines.

This plugin executes at the slicing post-processing seam (`psGCodePostProcess`), evaluating outer wall feedrates layer by layer and applying a continuous 1D Gaussian relaxation filter along the vertical Z axis.

- **Eliminates Speed Discontinuities**: Blends outer wall speeds across vertical layers so speed changes transition gradually instead of stepping sharply.
- **Safe Monotonic Clamping**: Faster adjacent layers are smoothly ramped down towards slower layers. Safe slow speeds required for steep overhangs or cooling limits are never sped up.
- **Selective & Clean**: Inner walls, infill, bridges, and travels keep their exact slicer speeds.
- **Spiral Vase Mode Aware**: Automatically bypasses spiral vase mode prints (matching Bambu Studio & Creality Print behavior).
- **First-Layer Safe**: Leaves initial bed adhesion layers untouched.
- **Pure Python**: Zero native binaries or C++ compilation required. Runs cross-platform on Windows, macOS, and Linux.

---

## Two Operating Modes

In Bambu Studio and Creality Print, this feature is locked to a single checkbox with no tunable parameters. This plugin provides both:

### 1. Simple Mode (Default — Zero Config)
- **1:1 match with Bambu Studio & Creality Print**: Exactly mirrors the official C++ engine implementation (`libslic3r/GCode/Smoothing.cpp`).
- **Plug-and-play**: Uses the built-in iterative 1D Gaussian kernel relaxation ($W=11, r=2.0$, stop threshold $5.0\text{ mm/s}$, 1-layer bed adhesion skip).
- No tuning or configuration needed: just enable the plugin and slice.

### 2. Advanced Mode
For power users who want fine-grained control over the smoothing curve:
- Set `"mode": "advanced"` in Plugin Configuration.
- Custom **Gaussian Radius** (`gaussian_radius`): adjust smoothness (default `2.0`).
- Custom **Kernel Window** (`gaussian_window_size`): adjust window width (default `11`).
- Custom **Stop Threshold** (`gaussian_stop_threshold_mm_s`): convergence threshold (default `5.0 mm/s`).
- Alternative **Linear Gradient Mode** (`"smoothing_algorithm": "gradient"`): limits maximum speed delta per millimeter of Z height (`max_speed_change_per_mm`).
- Configurable **Floor Velocity Clamp** (`min_outer_wall_speed_mm_s`) and **Bed Adhesion Layer Skip** (`skip_first_layers`).

---

## How to use

1. Install this plugin from OrcaCloud.
2. In OrcaSlicer, open your **Process** settings.
3. Navigate to **Others** -> **Slicing Pipeline Plugin**.
4. In the plugin picker, select **Smoothing Wall Speed Along Z**.
5. Slice your plate and print normally. Simple mode is active by default.

*(Optional)* To adjust parameters, open **Plugin Configuration** right below the picker.

---

## Requirements and compatibility

- **OrcaSlicer versions**: OrcaSlicer v2.4.2+, v2.5.0-dev, and nightly builds.
- **Operating systems**: Windows 10/11 (x64), Linux (x64), and macOS (Apple Silicon arm64 / Intel x64).
- **Supported printers**: All FDM printers supported by OrcaSlicer (Bambu Lab, Creality, Voron, Prusa, Qidi, Anycubic, Elegoo, etc.).
- **Filament compatibility**: Recommended especially for Silk PLA, glossy PLA, PETG, ABS, ASA, and translucent filaments.

---

## FAQ & Troubleshooting

- **Does this increase print time?** Yes, slightly. Because adjacent faster layers are smoothly ramped down towards slower layers to create a uniform speed gradient, overall print time increases by a small margin depending on model geometry (identical to Bambu Studio and Creality Print).
- **Why does it skip Vase Mode?** In spiral vase mode, the Z axis is in continuous motion without discrete layer boundaries; speed smoothing between distinct layer steps does not apply.
- **Can it print overhangs too fast?** Never. The filter is mathematically monotonic: $v_{\text{new}}(i) \le v_{\text{orig}}(i)$. It only slows down faster layers leading into and out of slow sections; it never increases the speed of an overhang or cooling-constrained move.

---

## Open Source & Attribution

- **License**: GPL-3.0 License.
- **Core Reference**: Based on the slicing research and `Smoothing.cpp` implementation in [BambuStudio](https://github.com/bambulab/BambuStudio) and [CrealityPrint](https://github.com/CrealityOfficial/CrealityPrint).
- **GitHub Repository**: [persano/smooth-z-wall-speed-plugin](https://github.com/persano/smooth-z-wall-speed-plugin)
