# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
