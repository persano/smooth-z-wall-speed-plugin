# /// script
# requires-python = ">=3.12"
#
# [tool.orcaslicer.plugin]
# name = "Smoothing Wall Speed Along Z"
# description = "Smooths outer wall speed transitions across adjacent Z layers. Features Simple (1:1 Bambu/Creality) and Advanced modes with interactive UI tab."
# author = "persano"
# version = "1.3.0"
# ///
"""Smoothing Wall Speed Along Z Plugin for OrcaSlicer.

Smooths outer wall speed transitions across adjacent Z layers to eliminate
speed banding and gloss mismatches on vertical walls caused by abrupt cooling
slowdowns or overhang transitions.

Modes:
- "simple" (default): 1:1 match with Bambu Studio & Creality Print (zero tuning required).
- "advanced": Full control over Gaussian filter radius, kernel window, stop threshold,
  or linear gradient ramp.
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
PLUGIN_VERSION = "1.3.0"

# Bambu Studio & Creality Print exact defaults (libslic3r/GCode/Smoothing.cpp)
BAMBU_CREALITY_DEFAULTS = {
    "smoothing_mode": "gaussian",
    "gaussian_radius": 2.0,
    "gaussian_window_size": 11,
    "gaussian_stop_threshold_mm_s": 5.0,  # 5.0 mm/s max adjacent layer delta
    "max_steps_count": 1000,
    "min_outer_wall_speed_mm_s": 10.0,
    "skip_first_layers": 1,
    "smooth_overhang_layers": True,
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "mode": "simple",                     # "simple" (zero-config Bambu/Creality match) or "advanced"
    # --- Advanced options (used when mode == "advanced") ---
    "smoothing_algorithm": "gaussian",    # "gaussian" or "gradient"
    "gaussian_radius": 2.0,               # Gaussian standard deviation / radius r
    "gaussian_window_size": 11,           # Kernel window size
    "gaussian_stop_threshold_mm_s": 5.0,  # Convergence threshold in mm/s
    "max_steps_count": 1000,              # Maximum relaxation iterations
    "max_speed_change_per_mm": 50.0,      # For gradient mode: max speed delta mm/s per 1 mm Z
    "min_outer_wall_speed_mm_s": 10.0,    # Floor clamp in mm/s
    "skip_first_layers": 1,               # Number of initial layers to leave untouched
    "smooth_overhang_layers": True,       # Factor overhang outer wall slowdowns into Z smoothing
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


def get_config_file_path() -> str:
    """Return path to persistent plugin config JSON."""
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(plugin_dir, "smooth_z_wall_speed_config.json")
    try:
        if os.path.exists(candidate):
            if os.access(candidate, os.W_OK):
                return candidate
        else:
            with open(candidate, "a", encoding="utf-8") as f:
                pass
            return candidate
    except Exception:
        pass

    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            base_dir = os.path.join(appdata, "OrcaSlicer", "orca_plugins", "smooth_z_wall_speed")
        else:
            base_dir = os.path.expanduser("~/.config/OrcaSlicer/orca_plugins/smooth_z_wall_speed")
    else:
        base_dir = os.path.expanduser("~/.config/OrcaSlicer/orca_plugins/smooth_z_wall_speed")

    try:
        os.makedirs(base_dir, exist_ok=True)
    except Exception:
        pass
    return os.path.join(base_dir, "smooth_z_wall_speed_config.json")


def load_config() -> Dict[str, Any]:
    """Load persistent configuration or return defaults."""
    cfg = dict(DEFAULT_CONFIG)
    path = get_config_file_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    cfg.update(loaded)
        except Exception:
            pass
    return cfg


def save_config(new_config: Dict[str, Any]) -> Tuple[bool, str]:
    """Save persistent configuration to JSON file."""
    path = get_config_file_path()
    try:
        merged = load_config()
        merged.update(new_config)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
        return True, f"Saved to {path}"
    except Exception as e:
        return False, f"Failed to save: {e}"


def generate_gaussian_kernel(window_size: int = 11, radius: float = 2.0) -> Tuple[List[float], float]:
    """Generate 1D Gaussian filter kernel identical to libslic3r/GCode/Smoothing.cpp."""
    half_win = window_size // 2
    kernel = []
    total_sum = 0.0
    for x in range(-half_win, half_win + 1):
        val = math.exp(- (x * x) / (2.0 * radius * radius)) / (radius * math.sqrt(2.0 * math.pi))
        kernel.append(val)
        total_sum += val
    return kernel, total_sum


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
    
    comment_pos = line.find(";")
    if comment_pos != -1:
        code_part = line[:comment_pos].rstrip()
        comment_part = line[comment_pos:]
        return f"{code_part} {f_str} {comment_part}"
    return f"{line.rstrip()} {f_str}\n"


def apply_gaussian_smoothing(
    speeds: List[float],
    skip_layers: int,
    window_size: int = 11,
    radius: float = 2.0,
    stop_threshold_mm_min: float = 300.0,
    max_steps: int = 1000,
) -> Tuple[List[float], int]:
    """Iterative Gaussian filter relaxation identical to Creality Print / Bambu Studio.

    Speeds are in mm/min. Stop threshold is in mm/min (5.0 mm/s * 60 = 300.0 mm/min).
    Monotonically clamps: only reduces speed, never increases.
    """
    kernel, kernel_sum = generate_gaussian_kernel(window_size, radius)
    half_win = window_size // 2
    smoothed = list(speeds)
    total_layers = len(smoothed)
    layer_start = skip_layers
    layer_end = total_layers - 1

    if layer_end <= layer_start:
        return smoothed, 0

    step_count = 0
    while step_count < max_steps:
        max_diff = 0.0
        for i in range(layer_start, layer_end):
            diff = abs(smoothed[i + 1] - smoothed[i])
            if diff > max_diff:
                max_diff = diff

        if max_diff <= stop_threshold_mm_min:
            break

        step_count += 1
        new_smoothed = list(smoothed)

        for layer_id in range(layer_start, layer_end + 1):
            conv_sum = 0.0
            for k_idx, offset in enumerate(range(-half_win, half_win + 1)):
                pos = layer_id + offset
                if pos < layer_start:
                    pos = layer_start
                elif pos > layer_end:
                    pos = layer_end
                conv_sum += kernel[k_idx] * smoothed[pos]

            filtered_speed = conv_sum / kernel_sum
            if filtered_speed < new_smoothed[layer_id]:
                new_smoothed[layer_id] = filtered_speed

        smoothed = new_smoothed

    return smoothed, step_count


def smooth_gcode_lines(
    lines: List[str],
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[List[str], Dict[str, Any]]:
    """Parse G-code lines, smooth outer wall speeds along Z, and return updated lines."""
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)

    stats: Dict[str, Any] = {
        "enabled": cfg.get("enabled", True),
        "mode": cfg.get("mode", "simple"),
        "total_layers": 0,
        "smoothed_layers": 0,
        "updated_moves": 0,
        "steps_converged": 0,
        "skipped_reason": None,
    }

    if not cfg.get("enabled", True):
        stats["skipped_reason"] = "plugin_disabled"
        return lines, stats

    mode = cfg.get("mode", "simple")
    if mode == "simple":
        smoothing_algorithm = "gaussian"
        win_size = BAMBU_CREALITY_DEFAULTS["gaussian_window_size"]
        radius = BAMBU_CREALITY_DEFAULTS["gaussian_radius"]
        stop_thresh_mm_min = BAMBU_CREALITY_DEFAULTS["gaussian_stop_threshold_mm_s"] * 60.0
        max_steps = BAMBU_CREALITY_DEFAULTS["max_steps_count"]
        min_f = BAMBU_CREALITY_DEFAULTS["min_outer_wall_speed_mm_s"] * 60.0
        skip_layers = BAMBU_CREALITY_DEFAULTS["skip_first_layers"]
        smooth_overhang = BAMBU_CREALITY_DEFAULTS["smooth_overhang_layers"]
        max_accel_z = 50.0
    else:
        smoothing_algorithm = cfg.get("smoothing_algorithm", "gaussian")
        win_size = int(cfg.get("gaussian_window_size", 11))
        radius = float(cfg.get("gaussian_radius", 2.0))
        stop_thresh_mm_min = float(cfg.get("gaussian_stop_threshold_mm_s", 5.0)) * 60.0
        max_steps = int(cfg.get("max_steps_count", 1000))
        min_f = float(cfg.get("min_outer_wall_speed_mm_s", 10.0)) * 60.0
        skip_layers = int(cfg.get("skip_first_layers", 1))
        smooth_overhang = bool(cfg.get("smooth_overhang_layers", True))
        max_accel_z = float(cfg.get("max_speed_change_per_mm", 50.0))

    stats["algorithm"] = smoothing_algorithm

    for line in lines[:250]:
        if RE_SPIRAL_VASE.search(line):
            stats["skipped_reason"] = "spiral_vase_mode"
            return lines, stats

    layers: List[Dict[str, Any]] = []
    current_z: float = 0.0
    modal_f: float = 6000.0
    is_outer_wall = False
    is_overhang_wall = False

    for idx, line in enumerate(lines):
        if RE_LAYER_CHANGE.search(line):
            layers.append({
                "z": current_z,
                "start_line": idx,
                "outer_speeds": [],
                "outer_move_indices": [],
                "overhang_speeds": [],
            })
            is_outer_wall = False
            is_overhang_wall = False
            continue

        m_z = RE_Z_HEIGHT.search(line)
        if m_z:
            current_z = float(m_z.group(1))
            if layers:
                layers[-1]["z"] = current_z
        else:
            m_zg = RE_Z_GCODE_MOVE.search(line)
            if m_zg:
                current_z = float(m_zg.group(1))
                if layers:
                    layers[-1]["z"] = current_z

        if RE_TYPE_OUTER.search(line):
            is_outer_wall = True
            is_overhang_wall = False
            continue
        elif RE_TYPE_OVERHANG.search(line):
            is_outer_wall = False
            is_overhang_wall = True
            continue
        elif RE_TYPE_ANY.search(line):
            is_outer_wall = False
            is_overhang_wall = False
            continue

        f_val = parse_feedrate(line)
        if f_val is not None:
            modal_f = f_val

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

    baseline_f: List[float] = []
    constraint_f: List[float] = []

    for lyr in layers:
        all_speeds = list(lyr["outer_speeds"])
        if smooth_overhang and lyr["overhang_speeds"]:
            all_speeds.extend(lyr["overhang_speeds"])

        if lyr["outer_speeds"]:
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

    initial_f = [min(baseline_f[i], constraint_f[i]) for i in range(total_layers)]

    if smoothing_algorithm == "gaussian":
        smoothed_f, steps = apply_gaussian_smoothing(
            initial_f,
            skip_layers=skip_layers,
            window_size=win_size,
            radius=radius,
            stop_threshold_mm_min=stop_thresh_mm_min,
            max_steps=max_steps,
        )
        stats["steps_converged"] = steps
    else:
        smoothed_f = list(initial_f)
        for i in range(skip_layers + 1, total_layers):
            dz = abs(layers[i]["z"] - layers[i - 1]["z"])
            if dz < 1e-4:
                dz = 0.2
            max_df = max_accel_z * 60.0 * dz
            if smoothed_f[i] > smoothed_f[i - 1] + max_df:
                smoothed_f[i] = smoothed_f[i - 1] + max_df

        for i in range(total_layers - 2, skip_layers - 1, -1):
            dz = abs(layers[i + 1]["z"] - layers[i]["z"])
            if dz < 1e-4:
                dz = 0.2
            max_df = max_accel_z * 60.0 * dz
            if smoothed_f[i] > smoothed_f[i + 1] + max_df:
                smoothed_f[i] = smoothed_f[i + 1] + max_df

    # Floor speed clamp
    smoothed_f = [max(min_f, val) for val in smoothed_f]

    output_lines = list(lines)
    updated_moves = 0
    smoothed_layers_count = 0

    for i in range(skip_layers, total_layers):
        target_speed = smoothed_f[i]
        orig_nominal = baseline_f[i]

        if target_speed < (orig_nominal - 30.0):
            smoothed_layers_count += 1
            for line_idx in layers[i]["outer_move_indices"]:
                orig_line = output_lines[line_idx]
                line_f = parse_feedrate(orig_line) or orig_nominal
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
    class SmoothZWallSpeedPage(orca.pages.PagesPluginCapabilityBase):
        """Dedicated top-level UI tab for configuring Smooth Z Wall Speed."""

        def get_name(self) -> str:
            return "Smooth Z Speed"

        def get_icon(self) -> str:
            root = os.path.dirname(os.path.abspath(__file__))
            p = os.path.join(root, "icon.png")
            return p if os.path.exists(p) else ""

        def on_message(self, message: Any) -> None:
            try:
                data = message if isinstance(message, dict) else json.loads(message)
            except Exception:
                data = {"action": str(message)}

            action = data.get("action", "")
            reply: Dict[str, Any] = {"action": action, "success": True, "message": ""}

            if action == "get_config":
                reply["config"] = load_config()
                reply["message"] = "Config loaded."
            elif action == "save_config":
                new_cfg = data.get("config", {})
                success, msg = save_config(new_cfg)
                reply["success"] = success
                reply["message"] = msg
                reply["config"] = load_config()
                if hasattr(orca, "host") and hasattr(orca.host, "ui"):
                    try:
                        orca.host.ui.message("Smoothing Wall Speed Along Z settings saved successfully!", "Smooth Z Wall Speed", buttons="ok", icon="info")
                    except Exception:
                        pass
            elif action == "restore_defaults":
                success, msg = save_config(DEFAULT_CONFIG)
                reply["success"] = success
                reply["message"] = "Defaults restored."
                reply["config"] = load_config()

            try:
                self.post_message(reply)
            except Exception:
                pass

        def get_ui(self) -> str:
            active_cfg = load_config()
            cfg_json = json.dumps(active_cfg)

            return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Smoothing Wall Speed Along Z</title>
<script>
(function() {{
  if (window.orca) return;
  var handlers = [];
  function send(data) {{
    var payload = JSON.stringify({{ channel: 'orca', kind: 'message', data: (data === undefined ? null : data) }});
    if (window.wx && typeof window.wx.postMessage === 'function') {{ window.wx.postMessage(payload); return true; }}
    if (window.chrome && window.chrome.webview && typeof window.chrome.webview.postMessage === 'function') {{ window.chrome.webview.postMessage(payload); return true; }}
    return false;
  }}
  window.orca = {{
    postMessage: function(data) {{
      if (!send(data)) {{
        var attempts = 0;
        var timer = setInterval(function() {{
          attempts++;
          if (send(data) || attempts > 60) clearInterval(timer);
        }}, 50);
      }}
    }},
    onMessage: function(callback) {{
      if (typeof callback === 'function') handlers.push(callback);
    }}
  }};
  window.__orcaDispatch = function(payload) {{
    var data = payload ? payload.data : null;
    for (var i = 0; i < handlers.length; i++) {{
      try {{ handlers[i](data); }} catch(e) {{}}
    }}
  }};
}})();
</script>
<style>
  :root {{
    --bg: #14171d;
    --card-bg: #1e222b;
    --card-border: #2d3341;
    --accent: #00ae72;
    --accent-hover: #009360;
    --teal: #00b4d8;
    --text: #f0f3f8;
    --text-muted: #8b94a5;
    --input-bg: #12151a;
    --input-border: #384052;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    padding: 24px;
    line-height: 1.5;
  }}
  .container {{ max-width: 980px; margin: 0 auto; }}
  .header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--card-border);
    margin-bottom: 24px;
  }}
  .header-left {{ display: flex; align-items: center; gap: 16px; }}
  .header-icon {{ width: 52px; height: 52px; border-radius: 12px; }}
  .header-title h1 {{ font-size: 22px; font-weight: 700; color: #fff; }}
  .header-title p {{ font-size: 13px; color: var(--text-muted); }}
  .badge {{
    background: rgba(0, 174, 114, 0.15);
    color: var(--accent);
    border: 1px solid rgba(0, 174, 114, 0.3);
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
  }}
  .card {{
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
  }}
  .card-title {{
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 14px;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .mode-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 20px;
  }}
  .mode-card {{
    background: var(--input-bg);
    border: 2px solid var(--card-border);
    border-radius: 10px;
    padding: 16px;
    cursor: pointer;
    transition: all 0.2s ease;
  }}
  .mode-card:hover {{ border-color: var(--teal); }}
  .mode-card.active {{
    border-color: var(--accent);
    background: rgba(0, 174, 114, 0.08);
  }}
  .mode-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }}
  .mode-title {{ font-size: 15px; font-weight: 700; color: #fff; }}
  .mode-desc {{ font-size: 12.5px; color: var(--text-muted); }}
  .ctrl-group {{ margin-bottom: 16px; }}
  .ctrl-label {{
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 6px;
    color: var(--text);
  }}
  .ctrl-val {{ color: var(--teal); font-weight: 600; }}
  input[type="range"] {{
    width: 100%;
    accent-color: var(--accent);
    height: 6px;
    border-radius: 3px;
    background: #2b3140;
    outline: none;
  }}
  select, input[type="number"] {{
    width: 100%;
    background: var(--input-bg);
    border: 1px solid var(--input-border);
    color: #fff;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 13px;
    outline: none;
  }}
  .switch-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid var(--card-border);
  }}
  .switch {{
    position: relative;
    display: inline-block;
    width: 44px;
    height: 24px;
  }}
  .switch input {{ opacity: 0; width: 0; height: 0; }}
  .slider {{
    position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
    background-color: #384052;
    transition: .3s;
    border-radius: 24px;
  }}
  .slider:before {{
    position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px;
    background-color: white;
    transition: .3s;
    border-radius: 50%;
  }}
  input:checked + .slider {{ background-color: var(--accent); }}
  input:checked + .slider:before {{ transform: translateX(20px); }}
  .callout {{
    background: rgba(0, 180, 216, 0.08);
    border-left: 4px solid var(--teal);
    padding: 14px 16px;
    border-radius: 0 8px 8px 0;
    font-size: 13px;
    margin-bottom: 20px;
  }}
  .callout h4 {{ font-size: 14px; margin-bottom: 4px; color: #fff; }}
  .callout p {{ color: var(--text-muted); }}
  .btn-bar {{
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
  }}
  button {{
    padding: 10px 20px;
    border-radius: 8px;
    font-size: 13.5px;
    font-weight: 600;
    cursor: pointer;
    border: none;
    transition: all 0.2s;
  }}
  .btn-primary {{ background: var(--accent); color: #fff; }}
  .btn-primary:hover {{ background: var(--accent-hover); }}
  .btn-secondary {{ background: #2d3341; color: var(--text); }}
  .btn-secondary:hover {{ background: #384052; }}
  #toast {{
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #00ae72;
    color: #fff;
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    opacity: 0;
    transition: opacity 0.3s;
    pointer-events: none;
  }}
  #toast.show {{ opacity: 1; }}
  canvas {{ width: 100%; height: 120px; background: var(--input-bg); border-radius: 8px; margin-top: 10px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="header-left">
      <img class="header-icon" src="icon.png" alt="Smooth Z Logo" onerror="this.style.display='none'">
      <div class="header-title">
        <h1>Smoothing Wall Speed Along Z</h1>
        <p>Outer Perimeter Z-Velocity Continuous Relaxer for OrcaSlicer v{PLUGIN_VERSION}</p>
      </div>
    </div>
    <div class="badge">● Slicing Pipeline Ready</div>
  </div>

  <div class="callout">
    <h4>💡 Where to enable in your Print Settings</h4>
    <p>In OrcaSlicer, open <b>Process</b> &rarr; <b>Others</b> &rarr; scroll to <b>Slicing Pipeline Plugin</b> and select <code>Smoothing Wall Speed Along Z</code> in the dropdown picker.</p>
  </div>

  <div class="callout" style="border-left-color: #f59e0b; background: rgba(245, 158, 11, 0.08);">
    <h4>ℹ️ Why doesn't the internal 3D Preview show speed changes?</h4>
    <p>OrcaSlicer's in-memory 3D viewer renders raw toolpaths directly from the slicer core before post-processing. Slicing pipeline plugins run at <code>psGCodePostProcess</code> to safely modify the exported G-code on disk without causing memory sharing locks. When you click <b>Export G-code file</b> or print, the outer wall speeds are smoothly relaxed!</p>
  </div>

  <div class="card">
    <div class="card-title">⚙️ Plugin Mode</div>
    <div class="mode-grid">
      <div id="mode-simple-card" class="mode-card active" onclick="setMode('simple')">
        <div class="mode-header">
          <span class="mode-title">Simple Mode</span>
          <span style="color: var(--accent); font-size: 18px;">✓</span>
        </div>
        <p class="mode-desc"><b>1:1 Match with Bambu Studio & Creality Print 5.</b> Zero tuning needed. Uses standard 1D Gaussian kernel relaxation (W=11, r=2.0, threshold=5.0 mm/s) with monotonic overhang protection.</p>
      </div>
      <div id="mode-adv-card" class="mode-card" onclick="setMode('advanced')">
        <div class="mode-header">
          <span class="mode-title">Advanced Mode</span>
          <span style="color: var(--teal); font-size: 14px;">Custom</span>
        </div>
        <p class="mode-desc">Full manual control over Gaussian radius, kernel window size, convergence delta threshold, first-layer skip count, and speed floor clamps.</p>
      </div>
    </div>

    <div id="advanced-panel" style="display: none;">
      <div class="ctrl-group">
        <div class="ctrl-label">
          <span>Smoothing Algorithm</span>
        </div>
        <select id="adv-algo" onchange="updateCurve()">
          <option value="gaussian">Gaussian Filter (Bambu Studio / Creality engine)</option>
          <option value="gradient">Linear Gradient Ramp</option>
        </select>
      </div>

      <div class="ctrl-group">
        <div class="ctrl-label">
          <span>Gaussian Radius (r / σ)</span>
          <span id="lbl-radius" class="ctrl-val">2.0</span>
        </div>
        <input type="range" id="adv-radius" min="0.5" max="5.0" step="0.1" value="2.0" oninput="syncVal('adv-radius', 'lbl-radius'); updateCurve();">
      </div>

      <div class="ctrl-group">
        <div class="ctrl-label">
          <span>Kernel Window Size (W)</span>
          <span id="lbl-window" class="ctrl-val">11</span>
        </div>
        <input type="range" id="adv-window" min="3" max="21" step="2" value="11" oninput="syncVal('adv-window', 'lbl-window'); updateCurve();">
      </div>

      <div class="ctrl-group">
        <div class="ctrl-label">
          <span>Stop Convergence Threshold (mm/s)</span>
          <span id="lbl-thresh" class="ctrl-val">5.0</span>
        </div>
        <input type="range" id="adv-thresh" min="1.0" max="15.0" step="0.5" value="5.0" oninput="syncVal('adv-thresh', 'lbl-thresh');">
      </div>

      <div class="ctrl-group">
        <div class="ctrl-label">
          <span>Skip First Layers</span>
          <span id="lbl-skip" class="ctrl-val">1</span>
        </div>
        <input type="range" id="adv-skip" min="0" max="5" step="1" value="1" oninput="syncVal('adv-skip', 'lbl-skip');">
      </div>

      <div class="switch-row">
        <div>
          <div style="font-size: 13.5px; font-weight: 600;">Smooth Overhang Layers</div>
          <div style="font-size: 12px; color: var(--text-muted);">Factor outer wall slowdowns at overhangs into vertical smoothing</div>
        </div>
        <label class="switch">
          <input type="checkbox" id="adv-overhang" checked>
          <span class="slider"></span>
        </label>
      </div>

      <div class="ctrl-group" style="margin-top: 16px;">
        <div class="ctrl-label">
          <span>Live Gaussian Kernel Distribution Curve</span>
        </div>
        <canvas id="curveCanvas" width="600" height="120"></canvas>
      </div>
    </div>
  </div>

  <div class="btn-bar">
    <button class="btn-secondary" onclick="restoreDefaults()">Restore Defaults</button>
    <button class="btn-primary" onclick="saveSettings()">Save Configuration</button>
  </div>
</div>

<div id="toast">Settings saved successfully!</div>

<script>
var currentConfig = {cfg_json};

function syncVal(sliderId, labelId) {{
  document.getElementById(labelId).innerText = document.getElementById(sliderId).value;
}}

function setMode(mode) {{
  currentConfig.mode = mode;
  var simpleCard = document.getElementById('mode-simple-card');
  var advCard = document.getElementById('mode-adv-card');
  var advPanel = document.getElementById('advanced-panel');
  if (mode === 'simple') {{
    simpleCard.classList.add('active');
    advCard.classList.remove('active');
    advPanel.style.display = 'none';
  }} else {{
    simpleCard.classList.remove('active');
    advCard.classList.add('active');
    advPanel.style.display = 'block';
    updateCurve();
  }}
}}

function applyConfigToUI(cfg) {{
  if (!cfg) return;
  currentConfig = cfg;
  setMode(cfg.mode || 'simple');
  if (cfg.gaussian_radius !== undefined) {{
    document.getElementById('adv-radius').value = cfg.gaussian_radius;
    syncVal('adv-radius', 'lbl-radius');
  }}
  if (cfg.gaussian_window_size !== undefined) {{
    document.getElementById('adv-window').value = cfg.gaussian_window_size;
    syncVal('adv-window', 'lbl-window');
  }}
  if (cfg.gaussian_stop_threshold_mm_s !== undefined) {{
    document.getElementById('adv-thresh').value = cfg.gaussian_stop_threshold_mm_s;
    syncVal('adv-thresh', 'lbl-thresh');
  }}
  if (cfg.skip_first_layers !== undefined) {{
    document.getElementById('adv-skip').value = cfg.skip_first_layers;
    syncVal('adv-skip', 'lbl-skip');
  }}
  if (cfg.smoothing_algorithm !== undefined) {{
    document.getElementById('adv-algo').value = cfg.smoothing_algorithm;
  }}
  if (cfg.smooth_overhang_layers !== undefined) {{
    document.getElementById('adv-overhang').checked = !!cfg.smooth_overhang_layers;
  }}
  updateCurve();
}}

function updateCurve() {{
  var canvas = document.getElementById('curveCanvas');
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext('2d');
  var w = canvas.width;
  var h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  var r = parseFloat(document.getElementById('adv-radius').value) || 2.0;
  var win = parseInt(document.getElementById('adv-window').value) || 11;
  var half = Math.floor(win / 2);

  var weights = [];
  var maxW = 0;
  for (var x = -half; x <= half; x++) {{
    var val = Math.exp(-(x * x) / (2.0 * r * r));
    weights.push(val);
    if (val > maxW) maxW = val;
  }}

  var step = w / (weights.length + 1);
  ctx.beginPath();
  ctx.strokeStyle = '#00ae72';
  ctx.lineWidth = 3;

  for (var i = 0; i < weights.length; i++) {{
    var px = (i + 1) * step;
    var py = h - 20 - (weights[i] / maxW) * (h - 40);
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }}
  ctx.stroke();

  for (var i = 0; i < weights.length; i++) {{
    var px = (i + 1) * step;
    var py = h - 20 - (weights[i] / maxW) * (h - 40);
    ctx.beginPath();
    ctx.arc(px, py, 4, 0, Math.PI * 2);
    ctx.fillStyle = '#00b4d8';
    ctx.fill();
  }}
}}

function saveSettings() {{
  currentConfig.mode = document.getElementById('mode-adv-card').classList.contains('active') ? 'advanced' : 'simple';
  currentConfig.smoothing_algorithm = document.getElementById('adv-algo').value;
  currentConfig.gaussian_radius = parseFloat(document.getElementById('adv-radius').value);
  currentConfig.gaussian_window_size = parseInt(document.getElementById('adv-window').value);
  currentConfig.gaussian_stop_threshold_mm_s = parseFloat(document.getElementById('adv-thresh').value);
  currentConfig.skip_first_layers = parseInt(document.getElementById('adv-skip').value);
  currentConfig.smooth_overhang_layers = document.getElementById('adv-overhang').checked;

  if (window.orca && typeof window.orca.postMessage === 'function') {{
    window.orca.postMessage({{ action: 'save_config', config: currentConfig }});
  }}
  showToast('Settings saved successfully!');
}}

function restoreDefaults() {{
  if (window.orca && typeof window.orca.postMessage === 'function') {{
    window.orca.postMessage({{ action: 'restore_defaults' }});
  }}
  applyConfigToUI({json.dumps(DEFAULT_CONFIG)});
  showToast('Defaults restored.');
}}

function showToast(msg) {{
  var toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('show');
  setTimeout(function() {{ toast.classList.remove('show'); }}, 3000);
}}

if (window.orca && typeof window.orca.onMessage === 'function') {{
  window.orca.onMessage(function(reply) {{
    if (reply && reply.config) {{
      applyConfigToUI(reply.config);
    }}
  }});
  window.orca.postMessage({{ action: 'get_config' }});
}}

applyConfigToUI(currentConfig);
</script>
</body>
</html>"""

    class SmoothZWallSpeedCapability(orca.slicing.SlicingPipelineCapabilityBase):
        """OrcaSlicer SlicingPipeline capability for Z wall speed smoothing."""

        def get_name(self) -> str:
            return PLUGIN_NAME

        def get_default_config(self) -> Dict[str, Any]:
            return DEFAULT_CONFIG

        def _get_active_config(self) -> Dict[str, Any]:
            cfg = load_config()
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
                    f"{PLUGIN_NAME} [{stats['mode'].upper()}]: processed {stats['total_layers']} layers, "
                    f"smoothed {stats['smoothed_layers']} layers ({stats['updated_moves']} moves modified) "
                    f"via {stats['algorithm']} (converged in {stats.get('steps_converged', 0)} steps)"
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
            orca.register_capability(SmoothZWallSpeedPage)
            orca.register_capability(SmoothZWallSpeedCapability)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=f"{PLUGIN_NAME} CLI")
    parser.add_argument("gcode", help="Path to input .gcode file")
    parser.add_argument("-o", "--output", help="Optional output .gcode path (default: in-place)")
    parser.add_argument("--mode", choices=["simple", "advanced"], default="simple",
                        help="Operation mode: 'simple' (Bambu/Creality 1:1 match) or 'advanced'")
    parser.add_argument("--algorithm", choices=["gaussian", "gradient"], default="gaussian",
                        help="Advanced mode algorithm (default: gaussian)")
    parser.add_argument("--radius", type=float, default=2.0, help="Gaussian radius r (default: 2.0)")
    parser.add_argument("--window", type=int, default=11, help="Gaussian window size (default: 11)")
    parser.add_argument("--stop-threshold", type=float, default=5.0, help="Stop threshold in mm/s (default: 5.0)")
    parser.add_argument("--min-speed", type=float, default=10.0, help="Floor speed in mm/s (default: 10.0)")
    parser.add_argument("--skip-first", type=int, default=1, help="Number of first layers to skip")
    args = parser.parse_args()

    cli_config = {
        "enabled": True,
        "mode": args.mode,
        "smoothing_algorithm": args.algorithm,
        "gaussian_radius": args.radius,
        "gaussian_window_size": args.window,
        "gaussian_stop_threshold_mm_s": args.stop_threshold,
        "min_outer_wall_speed_mm_s": args.min_speed,
        "skip_first_layers": args.skip_first,
    }

    res = smooth_gcode_file(args.gcode, args.output, cli_config)
    print(f"Processed: {res}")
