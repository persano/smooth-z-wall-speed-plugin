# OrcaCloud Release Changelog

## v1.3.0 — Interactive UI Tab, Live Curve Visualizer & Slicing Pipeline Sync (2026-10-29)

### 🎨 Dedicated UI Configuration Tab ("Smooth Z Speed")
- **Top-Level Slicer Tab**: Registered native `PagesPluginCapabilityBase` (`Smooth Z Speed`), embedding a polished dark-themed configuration page directly in OrcaSlicer's top navigation bar.
- **Mode Switching at a Glance**:
  - **Simple Mode (Default)**: 1:1 match with Bambu Studio & Creality Print 5 (`libslic3r/GCode/Smoothing.cpp`). Uses the hardcoded iterative 1D Gaussian kernel relaxation ($W=11, r=2.0, \Delta \le 5.0\text{ mm/s}$). Zero parameter tuning required.
  - **Advanced Mode**: Unlocks full slider and numeric controls for Gaussian standard deviation radius (`gaussian_radius`), kernel window size (`gaussian_window_size`), convergence delta threshold (`gaussian_stop_threshold_mm_s`), max relaxation iterations (`max_steps_count`), speed floor clamps (`min_outer_wall_speed_mm_s`), and initial layer skip count (`skip_first_layers`).
- **Interactive Gaussian Curve Visualizer**: Embedded HTML5 Canvas dynamically plots the discrete Gaussian weight distribution and simulated layer velocity ramp in real time.
- **One-Click Actions**: Includes **Restore Defaults** and **Save Configuration** with persistent status feedback.

### 🔄 Automatic Slicing Pipeline Synchronization
- Configuration changes saved in the `Smooth Z Speed` tab immediately persist to `smooth_z_wall_speed_config.json` and sync with `psGCodePostProcess` without requiring an OrcaSlicer restart.
- Both plugin capabilities (`PagesPluginCapabilityBase` and `SlicingPipelineCapabilityBase`) now cleanly co-exist under the same plugin registration.

### 🖼️ High-Resolution Edge-to-Edge Icon & UI Assets
- Replaced squircle-framed icon with a crisp, full-bleed 3D gradient nozzle artwork (`1024x1024` master and `320x320` OrcaCloud square) that fills the icon slot without awkward double-borders.
- Updated documentation and screenshots with actual OrcaSlicer UI preview.

### 🧪 Test Model Included
- Added `resources/models/speed_smoothing_test_tower.stl` (variable-speed geometry with wide base, steep overhangs, and narrow cooling spire) to easily demonstrate and verify smoothed outer wall feedrates (`F...`) in exported G-code.

---

## v1.2.0 — Dual Operating Modes & Multi-Platform Packaging (2026-10-29)

- **Simple vs Advanced Modes**: Added mode switch allowing users to stick with the proven zero-config Bambu/Creality algorithm or customize parameters for specialized filaments.
- **Platform-Tagged Wheel Distribution**: Built platform-specific wheels (`win_x86_64`, `linux_x86_64`, `macosx_arm64`) to comply with OrcaCloud packaging standards.
- **Initial Layer Protection**: Configurable first-layer skip count (`skip_first_layers`) to safeguard bed adhesion feedrates.

---

## v1.1.0 — 1:1 Bambu Studio & Creality Print Gaussian Engine (2026-10-29)

- Direct Python implementation of `libslic3r/GCode/Smoothing.cpp` iterative 1D Gaussian relaxation filter ($W=11, r=2.0$, stop threshold $5.0\text{ mm/s}$).
- Eliminates horizontal speed banding, sheen mismatches, and pressure bulges on Silk PLA, PETG, and ABS by smoothing sudden velocity drops along the vertical Z axis.
- Boundary reflection clamping for robust smoothing at top and bottom layer edges.
- Full unit test suite covering Gaussian kernel symmetry, convergence limits, and G-code parsing.

---

## v1.0.0 — Initial Release (2026-10-29)

- Native OrcaSlicer `slicing-pipeline` plugin capability hooking into `psGCodePostProcess`.
- Preserves inner walls, infill, bridges, and travel speeds while continuously smoothing outer perimeter velocities.
- Automatic spiral vase mode bypass.
- Standalone CLI execution support (`python smooth_z_wall_speed.py input.gcode -o output.gcode`).
