# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-10-29

### Added
- **Dedicated UI Configuration Tab ("Smooth Z Speed")**:
  - Registered native `PagesPluginCapabilityBase` adding a top-level tab in OrcaSlicer's main navigation bar.
  - Interactive dark-mode control panel eliminating the need to edit raw JSON strings in plugin preferences.
  - One-click toggle between **Simple Mode** (1:1 Bambu/Creality engine logic) and **Advanced Mode** (custom kernel tuning).
  - Built-in HTML5 Canvas Gaussian kernel curve visualizer dynamically rendering weight distribution and simulated velocity smoothing ramps.
  - Dedicated **Restore Defaults** and **Save Configuration** buttons with visual status indicators.
- **Persistent Two-Way Configuration Synchronization**:
  - Automatically syncs settings between the UI tab and slicing pipeline executions via `smooth_z_wall_speed_config.json`.
  - Zero-restart workflow: saving changes in the UI tab immediately applies to the next slice/export.
- **High-Resolution Full-Bleed Plugin Icon**:
  - Replaced squircle-framed icon with an edge-to-edge 3D gradient nozzle artwork (`1024x1024` master and `320x320` OrcaCloud square) avoiding nested container frames.
- **Reference Test Model**:
  - Added `resources/models/speed_smoothing_test_tower.stl` (wide base $\rightarrow$ steep overhangs $\rightarrow$ narrow cooling spire $\rightarrow$ top flare) to easily verify and inspect smoothed outer wall feedrates (`F...`) in exported G-code.
- **Documentation Overhaul**:
  - Replaced legacy/third-party slicer references in `README.md` with actual OrcaSlicer UI preview screenshots.
  - Added explicit guide on setting location (**Process $\rightarrow$ Others $\rightarrow$ Slicing Pipeline Plugin**) and clarified why in-memory 3D preview displays un-smoothed toolpaths while post-processed exported G-code contains the continuous Z-ramped speeds.

### Changed
- Refactored plugin entrypoint to export dual capability registrations (`SmoothZWallSpeedPage` and `SmoothZWallSpeedCapability`) cleanly under `@orca.plugin`.

---

## [1.2.0] - 2026-10-29

### Added
- **Dual Operating Modes**:
  - **Simple Mode (Default)**: 1:1 match with Bambu Studio & Creality Print 5 (`libslic3r/GCode/Smoothing.cpp`). Uses hardcoded iterative 1D Gaussian kernel relaxation ($W=11, r=2.0$, stop threshold $5.0\text{ mm/s}$). Zero configuration required.
  - **Advanced Mode**: Unlocks fine-tuning for Gaussian standard deviation radius (`gaussian_radius`), kernel window size (`gaussian_window_size`), convergence stop threshold (`gaussian_stop_threshold_mm_s`), max iterations (`max_steps_count`), and linear gradient ramp limiting.
- **Multi-Platform OrcaCloud Wheels**:
  - Automated building of platform-suffixed wheels (`_win_x86_64.whl`, `_linux_x86_64.whl`, `_macosx_arm64.whl`) strictly required by OrcaCloud plugin validation rules.
- **First-Layer Safety Guard**:
  - Added `skip_first_layers` configuration (default: 1) to protect first-layer print speeds and bed adhesion.

---

## [1.1.0] - 2026-10-29

### Added
- Direct Python implementation of `libslic3r/GCode/Smoothing.cpp` iterative 1D Gaussian kernel relaxation algorithm.
- Discrete 1D Gaussian kernel generation ($W=11, r=2.0$) with boundary reflection clamping.
- Iterative convergence stopping condition ($\le 5\text{ mm/s}$ or 300 mm/min max adjacent layer delta).
- Configuration parameters: `gaussian_radius`, `gaussian_window_size`, `gaussian_stop_threshold_mm_s`, `max_steps_count`.
- Comprehensive test coverage for kernel symmetry, convergence limits, and G-code parser speed extraction.

---

## [1.0.0] - 2026-10-29

### Added
- Initial release of **Smoothing Wall Speed Along Z** plugin for OrcaSlicer.
- Native `slicing-pipeline` capability hook at `psGCodePostProcess`.
- Bidirectional vertical gradient speed smoothing algorithm (forward and backward passes).
- Automatic detection and preservation of inner walls, infill, bridges, travels, and vase mode prints.
- Configurable settings: `max_speed_change_per_mm`, `min_outer_wall_speed_mm_s`, `skip_first_layers`, `smooth_overhang_layers`.
- Standalone CLI execution support (`python smooth_z_wall_speed.py input.gcode -o output.gcode`).
- Packaging scripts for wheel (`.whl`) and archive (`.zip`) distribution.
