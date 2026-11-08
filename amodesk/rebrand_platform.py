#!/usr/bin/env python3
"""Platform-specific AmoDesk branding, run after amodesk/rebrand.py.

    python amodesk/rebrand_platform.py linux|android|macos

rebrand.py changes APP_NAME, so on Linux the app looks for an `amodesk`
systemd unit, `amodesk.desktop` and an `amodesk --tray` process. Packaging
files therefore have to say `amodesk` too, and macOS needs `AmoDesk.app`.
Missing patterns fail the run, as in rebrand.py.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "amodesk" / "brand.json").read_text(encoding="utf-8"))
APP, EXE, ORG = BRAND["app_name"], BRAND["exe_name"], BRAND["org"]
COMPANY, SITE = BRAND["company"], BRAND["website"]
BUNDLE_ID = f"{ORG}.{EXE}"  # io.amobit.amodesk
MAINTAINER = f"{COMPANY} <info@amobit.ru>"
errors = []

# `rustdesk` as a name, not as part of librustdesk, rustdesk-org, rustdesk.com
# or the org.rustdesk.rustdesk Flutter channel names.
NAME_RE = re.compile(r"(?<![\w.])rustdesk(?![\w-]*\.com)(?!-org)")


def patch(rel, pairs, regex=False):
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    orig = text
    for old, new in pairs:
        if regex:
            text, n = re.subn(old, new, text)
        else:
            n = text.count(old)
            text = text.replace(old, new)
        if n == 0 and new not in text:
            errors.append(f"{rel}: pattern not found: {old!r}")
    if text != orig:
        path.write_text(text, encoding="utf-8", newline="")
        print(f"patched {rel}")


def rename_names(rel):
    """Upstream URLs and vendor first, then every bare rustdesk/RustDesk name."""
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    text = text.replace("rustdesk <info@rustdesk.com>", MAINTAINER)
    text = text.replace("https://rustdesk.com", SITE)
    text = text.replace(
        "The best open-source remote desktop client software, written in Rust.",
        f"{APP} remote desktop by {COMPANY}, based on RustDesk.")
    text = NAME_RE.sub(EXE, text).replace("RustDesk", APP)
    path.write_text(text, encoding="utf-8", newline="")
    print(f"renamed names in {rel}")


def move(old_rel, new_rel):
    (ROOT / old_rel).rename(ROOT / new_rel)
    print(f"renamed {old_rel} -> {new_rel}")


def linux():
    for rel in ["res/rustdesk.service", "res/rustdesk.desktop", "res/rustdesk-link.desktop",
                "res/rpm-flutter.spec", "res/rpm-flutter-suse.spec",
                "appimage/AppImageBuilder-x86_64.yml", "appimage/AppImageBuilder-aarch64.yml",
                *[str(p.relative_to(ROOT)) for p in (ROOT / "res/DEBIAN").iterdir() if p.is_file()]]:
        rename_names(rel)
    move("res/rustdesk.service", f"res/{EXE}.service")
    move("res/rustdesk.desktop", f"res/{EXE}.desktop")
    move("res/rustdesk-link.desktop", f"res/{EXE}-link.desktop")

    patch("build.py", [
        ("tmpdeb/usr/share/rustdesk", f"tmpdeb/usr/share/{EXE}"),
        ("tmpdeb/usr/bin/rustdesk", f"tmpdeb/usr/bin/{EXE}"),
        ("../res/rustdesk", f"../res/{EXE}"),
        ("/apps/rustdesk.", f"/apps/{EXE}."),
        ("applications/rustdesk", f"applications/{EXE}"),
        ("Package: rustdesk\n", f"Package: {EXE}\n"),
        ("Maintainer: rustdesk <info@rustdesk.com>", f"Maintainer: {MAINTAINER}"),
        ("Homepage: https://rustdesk.com", f"Homepage: {SITE}"),
        ("rustdesk.deb", f"{EXE}.deb"),
        ("'../rustdesk-%s.deb'", f"'../{EXE}-%s.deb'"),
    ])
    patch("flutter/linux/CMakeLists.txt", [
        ('set(BINARY_NAME "rustdesk")', f'set(BINARY_NAME "{EXE}")'),
    ])
    patch("flutter/linux/my_application.cc", [
        ('gtk_icon_theme_load_icon(theme, "rustdesk",', f'gtk_icon_theme_load_icon(theme, "{EXE}",'),
        ('gtk_header_bar_set_title(header_bar, "rustdesk");', f'gtk_header_bar_set_title(header_bar, "{APP}");'),
        ('gtk_window_set_title(window, "rustdesk");', f'gtk_window_set_title(window, "{APP}");'),
    ])


def android():
    patch("flutter/android/app/build.gradle", [
        ('applicationId "com.carriez.flutter_hbb"', f'applicationId "{BUNDLE_ID}"'),
    ])
    patch("flutter/android/app/src/main/AndroidManifest.xml", [
        ('android:label="RustDesk"', f'android:label="{APP}"'),
        ('android:label="RustDesk Input"', f'android:label="{APP} Input"'),
    ])
    patch("flutter/android/app/src/main/res/values/strings.xml", [
        ("RustDesk", APP),
    ])


def macos():
    patch("flutter/macos/Runner/Configs/AppInfo.xcconfig", [
        ("PRODUCT_NAME = RustDesk", f"PRODUCT_NAME = {APP}"),
        ("PRODUCT_BUNDLE_IDENTIFIER = com.carriez.flutterHbb", f"PRODUCT_BUNDLE_IDENTIFIER = {BUNDLE_ID}"),
    ])
    patch("flutter/macos/Runner/Configs/AppInfo.xcconfig", [
        (r"Copyright © (\d+) Purslane Tech Pte\. Ltd\.", rf"Copyright © \1 {COMPANY}"),
    ], regex=True)
    patch("build.py", [
        ("Release/RustDesk.app/Contents/MacOS/", f"Release/{APP}.app/Contents/MacOS/"),
    ])


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else ""
    {"linux": linux, "android": android, "macos": macos}.get(target, lambda: sys.exit(
        "usage: rebrand_platform.py linux|android|macos"))()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)
