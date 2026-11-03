#!/usr/bin/env python3
"""Build wheel (.whl) and zip distributions for Smoothing Wall Speed Along Z plugin.

Produces both platform-suffixed wheels for OrcaCloud (win_x86_64, linux_x86_64, macosx_arm64)
and a universal purelib wheel + drop-in zip package.
"""

import base64
import hashlib
import os
import zipfile

VERSION = "1.3.1"
PLUGIN_MODULE = "smooth_z_wall_speed"
DIST_INFO = f"{PLUGIN_MODULE}-{VERSION}.dist-info"

METADATA_CONTENT = f"""Metadata-Version: 2.1
Name: {PLUGIN_MODULE}
Version: {VERSION}
Summary: Smoothing Wall Speed Along Z plugin for OrcaSlicer. Smooths outer wall velocity transitions across vertical layers to prevent banding and gloss lines.
Author: persano
License: GPL-3.0-only
Requires-Python: >=3.12
"""

WHEEL_CONTENT = """Wheel-Version: 1.0
Generator: custom
Root-Is-Purelib: true
Tag: py3-none-any
"""

TOP_LEVEL_CONTENT = f"{PLUGIN_MODULE}\n"


def build_wheel(whl_filename: str):
    files = {}

    with open(f"{PLUGIN_MODULE}.py", "rb") as f:
        code_data = f.read()

    files[f"{PLUGIN_MODULE}/__init__.py"] = code_data
    files[f"{PLUGIN_MODULE}/{PLUGIN_MODULE}.py"] = code_data

    for src, arcname in (
        ("assets/icon.png", "icon.png"),
        ("assets/icon.jpg", "icon.jpg"),
        ("assets/icon_orcacloud_320x320.png", "icon_orcacloud_320x320.png"),
        ("assets/icon_orcacloud_320x320.jpg", "icon_orcacloud_320x320.jpg"),
        ("CHANGELOG.md", "CHANGELOG.md"),
        ("docs/ORCACLOUD_CHANGELOG.md", "ORCACLOUD_CHANGELOG.md"),
        ("docs/ORCACLOUD_DESCRIPTION.md", "ORCACLOUD_DESCRIPTION.md"),
        (".install_state.json", ".install_state.json"),
        ("README.md", "README.md"),
        ("resources/images/icon.png", "resources/images/icon.png"),
        ("resources/images/icon_1024.jpg", "resources/images/icon_1024.jpg"),
        ("resources/images/orcaslicer_plugin_tab_preview.jpg", "resources/images/orcaslicer_plugin_tab_preview.jpg"),
    ):
        # arcname stays the original path: the plugin loads icon.png from its
        # own package root at runtime.
        if os.path.exists(src):
            with open(src, "rb") as f:
                files[f"{PLUGIN_MODULE}/{arcname}"] = f.read()

    files[f"{DIST_INFO}/METADATA"] = METADATA_CONTENT.encode("utf-8")
    files[f"{DIST_INFO}/WHEEL"] = WHEEL_CONTENT.encode("utf-8")
    files[f"{DIST_INFO}/top_level.txt"] = TOP_LEVEL_CONTENT.encode("utf-8")

    for lic in ("LICENSE", "NOTICE"):
        if os.path.exists(lic):
            with open(lic, "rb") as f:
                files[f"{DIST_INFO}/{lic}"] = f.read()

    record_lines = []
    for arcname, data in files.items():
        digest = hashlib.sha256(data).digest()
        b64 = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        record_lines.append(f"{arcname},sha256={b64},{len(data)}")

    record_lines.append(f"{DIST_INFO}/RECORD,,")
    record_bytes = ("\n".join(record_lines) + "\n").encode("utf-8")
    files[f"{DIST_INFO}/RECORD"] = record_bytes

    with zipfile.ZipFile(whl_filename, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for arcname, data in sorted(files.items()):
            z.writestr(arcname, data)

    print(f"Built {whl_filename}: {os.path.getsize(whl_filename):,} bytes (RECORD entries: {len(record_lines)})")


def build_zip(zip_filename: str = f"dist/{PLUGIN_MODULE}_plugin.zip"):
    items_to_pack = [
        (f"{PLUGIN_MODULE}.py", f"{PLUGIN_MODULE}.py"),
        (".install_state.json", ".install_state.json"),
        ("README.md", "README.md"),
        ("CHANGELOG.md", "CHANGELOG.md"),
        ("docs/ORCACLOUD_CHANGELOG.md", "ORCACLOUD_CHANGELOG.md"),
        ("docs/ORCACLOUD_DESCRIPTION.md", "ORCACLOUD_DESCRIPTION.md"),
        ("LICENSE", "LICENSE"),
        ("assets/icon.png", "icon.png"),
        ("assets/icon.jpg", "icon.jpg"),
        ("assets/icon_orcacloud_320x320.png", "icon_orcacloud_320x320.png"),
        ("assets/icon_orcacloud_320x320.jpg", "icon_orcacloud_320x320.jpg"),
        ("resources/images/icon.png", "resources/images/icon.png"),
        ("resources/images/icon_1024.jpg", "resources/images/icon_1024.jpg"),
        ("resources/images/orcaslicer_plugin_tab_preview.jpg", "resources/images/orcaslicer_plugin_tab_preview.jpg"),
    ]

    with zipfile.ZipFile(zip_filename, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for src, arcname in items_to_pack:
            if os.path.exists(src):
                z.write(src, arcname)

    print(f"Built {zip_filename}: {os.path.getsize(zip_filename):,} bytes")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.makedirs("dist", exist_ok=True)

    # Standard Python universal wheel
    build_wheel(f"dist/{PLUGIN_MODULE}-{VERSION}-py3-none-any.whl")

    # OrcaCloud platform-tagged wheels (matching OrcaCloud validator convention)
    build_wheel(f"dist/{PLUGIN_MODULE}_win_x86_64.whl")
    build_wheel(f"dist/{PLUGIN_MODULE}_linux_x86_64.whl")
    build_wheel(f"dist/{PLUGIN_MODULE}_macosx_arm64.whl")

    # Drop-in zip package
    build_zip(f"dist/{PLUGIN_MODULE}_plugin.zip")
