# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-10-29

### Added
- Added dual operating modes: **Simple** (default) and **Advanced**.
  - **Simple Mode**: 1:1 match with Bambu Studio & Creality Print slicers. Zero parameter tuning needed; applies the exact Gaussian kernel relaxation ($W=11, r=2.0$, threshold $5.0\text{ mm/s}$).
  - **Advanced Mode**: Allows fine-tuning Gaussian radius, kernel window size, convergence threshold, or switching to linear gradient ramp limiting.
- Generated platform-suffixed wheels (`_win_x86_64.whl`, `_linux_x86_64.whl`, `_macosx_arm64.whl`) matching OrcaCloud validation requirements.

## [1.1.0] - 2026-10-29

### Added
- Implemented 1:1 match of Bambu Studio and Creality Print (`libslic3r/GCode/Smoothing.cpp`) iterative 1D Gaussian kernel relaxation algorithm.
- Discrete 1D Gaussian kernel ($W=11, r=2.0$) with boundary clamping.
- Iterative convergence stopping condition ($\le 5\text{ mm/s}$ or 300 mm/min max adjacent delta).
- New configuration options: `smoothing_mode`, `gaussian_radius`, `gaussian_window_size`, `gaussian_stop_threshold_mm_s`, `max_steps_count`.
- Comprehensive test coverage for Gaussian kernel symmetry and iterative relaxation.

## [1.0.0] - 2026-10-29

### Added
- Initial release of **Smoothing Wall Speed Along Z** plugin for OrcaSlicer.
- Native `slicing-pipeline` capability hook at `psGCodePostProcess`.
- Bidirectional vertical gradient speed smoothing algorithm (forward and backward pass).
- Automatic detection and preservation of inner walls, infill, bridges, travels, and vase mode prints.
- Configurable settings:
  - `max_speed_change_per_mm`: Maximum velocity ramp slope in mm/s per mm Z.
  - `min_outer_wall_speed_mm_s`: Safety floor velocity clamp.
  - `skip_first_layers`: Excludes first layers to guarantee bed adhesion.
  - `smooth_overhang_layers`: Incorporates overhang slowdowns into adjacent wall smoothing.
- CLI execution mode for testing and external post-processing pipelines.
- Packaging tools for `.whl` and `.zip` distribution.
