# /// script
# requires-python = ">=3.12"
#
# [tool.orcaslicer.plugin]
# name = "Smoothing Wall Speed Along Z"
# description = "Smooths outer wall speed transitions across adjacent Z layers to eliminate speed banding and gloss lines."
# author = "persano"
# version = "1.0.0"
# type = "slicing-pipeline"
# ///
"""Smoothing Wall Speed Along Z Plugin for OrcaSlicer.

Smooths outer wall speed transitions across adjacent Z layers to eliminate
speed banding and gloss mismatches on vertical walls caused by abrupt cooling
slowdowns or overhang transitions.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

try:
    import orca
except ImportError:
    orca = None

PLUGIN_NAME = "Smoothing Wall Speed Along Z"
PLUGIN_VERSION = "1.0.0"

DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "max_speed_change_per_mm": 50.0,    # Max velocity delta in mm/s per 1 mm Z change
    "min_outer_wall_speed_mm_s": 10.0,  # Floor clamp in mm/s
    "skip_first_layers": 1,             # Number of first layers to leave untouched (bed adhesion)
    "smooth_overhang_layers": True,     # Factor overhang outer wall slowdowns into Z smoothing
}

RE_LAYER_CHANGE = re.compile(r"^;LAYER_CHANGE")
RE_Z_HEIGHT     = re.compile(r"^;(?:Z|HEIGHT):([0-9.]+)")
RE_Z_GCODE_MOVE = re.compile(r"^[Gg][01]\s+[^;\n]*Z([0-9.]+)")
RE_TYPE_OUTER   = re.compile(r"^;TYPE:(?:Outer wall|Outer perimeter)", re.IGNORECASE)
RE_TYPE_OVERHANG= re.compile(r"^;TYPE:(?:Overhang wall|Overhang perimeter)", re.IGNORECASE)
RE_TYPE_ANY     = re.compile(r"^;TYPE:", re.IGNORECASE)
RE_SPIRAL_VASE  = re.compile(r"^;\s*(?:spiral_mode|spiral_vase)\s*=\s*1", re.IGNORECASE)
RE_G_CMD        = re.compile(r"^([Gg][01])(\s+[^;\n]*)?")
RE_FEEDRATE     = re.compile(r"([Ff])([0-9.]+)")
RE_EXTRUSION    = re.compile(r"([Ee])([0-9.-]+)")


def parse_feedrate(line: str) -> Optional[float]:
    """Extract feedrate value (mm/min) from G-code line if present."""
    match = RE_FEEDRATE.search(line)
    if match:
        try:
            return float(match.group(2))
        except ValueError:
            return None
    return None


def has_extrusion(line: str) -> bool:
    """Return True if line contains an extrusion movement."""
    match = RE_EXTRUSION.search(line)
    if match:
        try:
            val = float(match.group(2))
            return val > 0.0
        except ValueError:
            return False
    return False


def set_feedrate_on_line(line: str, new_f: float) -> str:
    """Replace existing feedrate or append new feedrate before comment."""
    f_str = f"F{new_f:.1f}"
    if RE_FEEDRATE.search(line):
        return RE_FEEDRATE.sub(f_str, line)
    
    # Insert before comment or newline
    comment_pos = line.find(";")
    if comment_pos != -1:
        code_part = line[:comment_pos].rstrip()
        comment_part = line[comment_pos:]
        return f"{code_part} {f_str} {comment_part}"
    return f"{line.rstrip()} {f_str}\n"


def smooth_gcode_lines(
    lines: List[str],
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[List[str], Dict[str, Any]]:
    """Process G-code lines and apply Z-direction wall speed smoothing.

    Returns:
        (modified_lines, stats_dict)
    """
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)

    stats: Dict[str, Any] = {
        "enabled": cfg.get("enabled", True),
        "total_layers": 0,
        "smoothed_layers": 0,
        "updated_moves": 0,
        "skipped_reason": None,
    }

    if not cfg.get("enabled", True):
        stats["skipped_reason"] = "disabled"
        return lines, stats

    max_accel_z = float(cfg.get("max_speed_change_per_mm", 50.0))
    min_speed_mm_s = float(cfg.get("min_outer_wall_speed_mm_s", 10.0))
    skip_layers = int(cfg.get("skip_first_layers", 1))
    smooth_overhang = bool(cfg.get("smooth_overhang_layers", True))

    # Convert mm/s to mm/min
    min_f = min_speed_mm_s * 60.0

    # Quick scan for vase mode
    for line in lines[:500]:
        if RE_SPIRAL_VASE.search(line):
            stats["skipped_reason"] = "spiral_vase_mode"
            return lines, stats

    # Layer representation:
    # {
    #   'z': float,
    #   'outer_speeds': List[float],
    #   'outer_move_indices': List[int],
    #   'overhang_speeds': List[float],
    # }
    layers: List[Dict[str, Any]] = []
    current_layer = -1
    current_z = 0.0
    modal_f = 3000.0
    is_outer_wall = False
    is_overhang_wall = False

    for idx, line in enumerate(lines):
        if RE_LAYER_CHANGE.match(line):
            current_layer += 1
            layers.append({
                "z": current_z,
                "outer_speeds": [],
                "outer_move_indices": [],
                "overhang_speeds": [],
            })
            is_outer_wall = False
            is_overhang_wall = False
            continue

        z_match = RE_Z_HEIGHT.match(line)
        if z_match:
            current_z = float(z_match.group(1))
            if layers:
                layers[-1]["z"] = current_z
            continue

        z_move = RE_Z_GCODE_MOVE.match(line)
        if z_move:
            current_z = float(z_move.group(1))
            if layers:
                layers[-1]["z"] = current_z

        f_val = parse_feedrate(line)
        if f_val is not None and f_val > 0.0:
            modal_f = f_val

        if RE_TYPE_OUTER.match(line):
            is_outer_wall = True
            is_overhang_wall = False
            continue
        elif RE_TYPE_OVERHANG.match(line):
            is_outer_wall = False
            is_overhang_wall = True
            continue
        elif RE_TYPE_ANY.match(line):
            is_outer_wall = False
            is_overhang_wall = False
            continue

        if not layers:
            continue

        if is_outer_wall and RE_G_CMD.match(line):
            if has_extrusion(line):
                layers[-1]["outer_speeds"].append(modal_f)
                layers[-1]["outer_move_indices"].append(idx)
        elif is_overhang_wall and RE_G_CMD.match(line) and smooth_overhang:
            if has_extrusion(line):
                layers[-1]["overhang_speeds"].append(modal_f)

    total_layers = len(layers)
    stats["total_layers"] = total_layers

    if total_layers <= skip_layers + 1:
        stats["skipped_reason"] = "not_enough_layers"
        return lines, stats

    # Compute baseline outer wall speed per layer (mm/min)
    baseline_f: List[float] = []
    constraint_f: List[float] = []

    for i, lyr in enumerate(layers):
        all_speeds = list(lyr["outer_speeds"])
        if smooth_overhang and lyr["overhang_speeds"]:
            all_speeds.extend(lyr["overhang_speeds"])

        if lyr["outer_speeds"]:
            # Nominal speed is the dominant/median outer wall speed
            sorted_speeds = sorted(lyr["outer_speeds"])
            nominal = sorted_speeds[len(sorted_speeds) // 2]
            baseline_f.append(nominal)
        else:
            prev = baseline_f[-1] if baseline_f else 6000.0
            baseline_f.append(prev)

        if all_speeds:
            constraint_f.append(min(all_speeds))
        else:
            prev_c = constraint_f[-1] if constraint_f else 6000.0
            constraint_f.append(prev_c)

    # Bidirectional gradient smoothing along Z:
    # We smooth target_f such that:
    # target_f[i] <= baseline_f[i]  (never speed up beyond user's slicer speed)
    # target_f[i] <= constraint_f[i] if layer i had a slowdown
    # |target_f[i] - target_f[i-1]| <= max_df
    smoothed_f = [min(baseline_f[i], constraint_f[i]) for i in range(total_layers)]

    # Forward pass: propagate slowdown constraints upward
    for i in range(skip_layers + 1, total_layers):
        dz = abs(layers[i]["z"] - layers[i - 1]["z"])
        if dz < 1e-4:
            dz = 0.2  # sensible fallback layer height
        max_df = max_accel_z * 60.0 * dz
        if smoothed_f[i] > smoothed_f[i - 1] + max_df:
            smoothed_f[i] = smoothed_f[i - 1] + max_df

    # Backward pass: propagate slowdown constraints downward
    for i in range(total_layers - 2, skip_layers - 1, -1):
        dz = abs(layers[i + 1]["z"] - layers[i]["z"])
        if dz < 1e-4:
            dz = 0.2
        max_df = max_accel_z * 60.0 * dz
        if smoothed_f[i] > smoothed_f[i + 1] + max_df:
            smoothed_f[i] = smoothed_f[i + 1] + max_df

    # Apply minimum floor clamp
    smoothed_f = [max(min_f, val) for val in smoothed_f]

    # Rewrite G-code lines
    output_lines = list(lines)
    updated_moves = 0
    smoothed_layers_count = 0

    for i in range(skip_layers, total_layers):
        target_speed = smoothed_f[i]
        orig_nominal = baseline_f[i]

        # Only modify if delta is significant (>= 30 mm/min, or 0.5 mm/s)
        if target_speed < (orig_nominal - 30.0):
            smoothed_layers_count += 1
            for line_idx in layers[i]["outer_move_indices"]:
                orig_line = output_lines[line_idx]
                line_f = parse_feedrate(orig_line) or orig_nominal
                # Only clamp down faster moves, never speed up existing slower detail moves
                if line_f > target_speed:
                    output_lines[line_idx] = set_feedrate_on_line(orig_line, target_speed)
                    updated_moves += 1

    stats["smoothed_layers"] = smoothed_layers_count
    stats["updated_moves"] = updated_moves
    return output_lines, stats


def smooth_gcode_file(
    input_path: str,
    output_path: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Smooth outer wall speed in G-code file in-place or to output_path."""
    target_path = output_path or input_path
    with open(input_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    modified_lines, stats = smooth_gcode_lines(lines, config)

    with open(target_path, "w", encoding="utf-8") as f:
        f.writelines(modified_lines)

    return stats


# ---------------------------------------------------------------------------
# OrcaSlicer Plugin Integration
# ---------------------------------------------------------------------------

if orca:
    class SmoothZWallSpeedCapability(orca.slicing.SlicingPipelineCapabilityBase):
        """OrcaSlicer SlicingPipeline capability for Z wall speed smoothing."""

        def get_name(self) -> str:
            return PLUGIN_NAME

        def get_default_config(self) -> Dict[str, Any]:
            return DEFAULT_CONFIG

        def _get_active_config(self) -> Dict[str, Any]:
            cfg = dict(DEFAULT_CONFIG)
            try:
                raw = self.get_config()
                if raw:
                    loaded = json.loads(raw)
                    if isinstance(loaded, dict):
                        cfg.update(loaded)
            except Exception:
                pass
            return cfg

        def execute(self, ctx: Any) -> Any:
            # Only execute at post-process step where G-code file is emitted
            if ctx.step != orca.slicing.Step.psGCodePostProcess:
                return orca.ExecutionResult.success()

            if not getattr(ctx, "gcode_path", None):
                return orca.ExecutionResult.success(
                    f"{PLUGIN_NAME}: no gcode_path provided, skipped"
                )

            cfg = self._get_active_config()
            try:
                stats = smooth_gcode_file(ctx.gcode_path, config=cfg)
                msg = (
                    f"{PLUGIN_NAME}: processed {stats['total_layers']} layers, "
                    f"smoothed {stats['smoothed_layers']} layers ({stats['updated_moves']} moves modified)"
                )
                return orca.ExecutionResult.success(msg)
            except Exception as e:
                return orca.ExecutionResult.failure(
                    orca.PluginResult.RecoverableError,
                    f"{PLUGIN_NAME} error: {e}"
                )

    @orca.plugin
    class SmoothZWallSpeedPluginPackage(orca.base):
        """Plugin package registration entrypoint for OrcaSlicer."""

        def register_capabilities(self) -> None:
            orca.register_capability(SmoothZWallSpeedCapability)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=f"{PLUGIN_NAME} CLI")
    parser.add_argument("gcode", help="Path to input .gcode file")
    parser.add_argument("-o", "--output", help="Optional output .gcode path (default: in-place)")
    parser.add_argument("--max-accel-z", type=float, default=50.0, help="Max speed delta mm/s per mm Z")
    parser.add_argument("--min-speed", type=float, default=10.0, help="Floor speed in mm/s")
    parser.add_argument("--skip-first", type=int, default=1, help="Number of first layers to skip")
    args = parser.parse_args()

    cli_config = {
        "enabled": True,
        "max_speed_change_per_mm": args.max_accel_z,
        "min_outer_wall_speed_mm_s": args.min_speed,
        "skip_first_layers": args.skip_first,
    }

    res = smooth_gcode_file(args.gcode, args.output, cli_config)
    print(f"Processed: {res}")
