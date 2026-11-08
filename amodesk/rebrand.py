#!/usr/bin/env python3
"""Apply AmoDesk branding to a RustDesk source tree.

Run from the repository root before building:

    python amodesk/rebrand.py

Branding is applied at build time instead of being committed into the sources,
so the fork stays a small diff on top of upstream RustDesk and rebases cleanly.

Server settings come from environment variables (all optional):
    AMODESK_RENDEZVOUS_SERVER  host of hbbs, e.g. desk.amobit.io
    AMODESK_RS_PUB_KEY         content of id_ed25519.pub from the server
    AMODESK_API_SERVER         console URL, e.g. https://desk.amobit.io

A replacement whose pattern is missing fails the run, so upstream changes
are noticed instead of silently producing a half-branded client.

The upstream copyright and AGPL-3.0 license files are left untouched.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = json.loads((ROOT / "amodesk" / "brand.json").read_text(encoding="utf-8"))

APP = BRAND["app_name"]
EXE = BRAND["exe_name"]
COMPANY = BRAND["company"]
SITE = BRAND["website"]

UPSTREAM_KEY = "OeVuKk5nlHiXp+APNn0Y3pC1Iwpwn44JGqrQCsWqmBw="
errors = []


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


# 1. Core identity: app name drives install dir, service, IPC, config paths
#    and the "RustDesk" -> app name substitution in every translation.
patch("libs/hbb_common/src/config.rs", [
    ('RwLock::new("RustDesk".to_owned())', f'RwLock::new("{APP}".to_owned())'),
    ('RwLock::new("com.carriez".to_owned())', f'RwLock::new("{BRAND["org"]}".to_owned())'),
])

# 2. Server, key and console.
server = os.environ.get("AMODESK_RENDEZVOUS_SERVER", "").strip()
key = os.environ.get("AMODESK_RS_PUB_KEY", "").strip()
api = os.environ.get("AMODESK_API_SERVER", "").strip().rstrip("/")
if server:
    patch("libs/hbb_common/src/config.rs", [
        ('&["rs-ny.rustdesk.com"]', f'&["{server}"]'),
    ])
if key:
    patch("libs/hbb_common/src/config.rs", [(UPSTREAM_KEY, key)])
if api:
    patch("src/common.rs", [('"https://admin.rustdesk.com".to_owned()', f'"{api}".to_owned()')])
if not (server and key):
    print("WARNING: AMODESK_RENDEZVOUS_SERVER / AMODESK_RS_PUB_KEY not set - "
          "the client keeps upstream public servers. Do not ship such a build.")

# 3. Windows binary metadata.
for rel in ("Cargo.toml", "libs/portable/Cargo.toml"):
    patch(rel, [
        ('description = "RustDesk Remote Desktop"', f'description = "{APP}"'),
        ('ProductName = "RustDesk"', f'ProductName = "{APP}"'),
        ('FileDescription = "RustDesk Remote Desktop"', f'FileDescription = "{APP}"'),
        ('OriginalFilename = "rustdesk.exe"', f'OriginalFilename = "{EXE}.exe"'),
        ("Purslane Tech Pte. Ltd. All", f"{COMPANY}. All"),
    ])
patch("libs/portable/src/main.rs", [
    ('const APP_PREFIX: &str = "rustdesk";', f'const APP_PREFIX: &str = "{EXE}";'),
])
patch("flutter/windows/runner/Runner.rc", [
    ('"Purslane Tech Pte. Ltd."', f'"{COMPANY}"'),
    ("Purslane Tech Pte. Ltd. All", f"{COMPANY}. All"),
    ('"RustDesk Remote Desktop"', f'"{APP}"'),
    ('VALUE "InternalName", "rustdesk"', f'VALUE "InternalName", "{EXE}"'),
    ('"rustdesk.exe"', f'"{EXE}.exe"'),
    ('VALUE "ProductName", "RustDesk"', f'VALUE "ProductName", "{APP}"'),
])
patch("flutter/windows/runner/main.cpp", [
    ('std::wstring app_name = L"RustDesk";', f'std::wstring app_name = L"{APP}";'),
])

# 4. Links and About page. The About page keeps a "based on RustDesk" note.
patch("flutter/lib/desktop/pages/desktop_setting_page.dart", [
    ("Purslane Tech Pte. Ltd.\\n", f"{COMPANY}\\nBased on RustDesk (AGPL-3.0)\\n"),
    ("launchUrlString('https://rustdesk.com/privacy.html')", f"launchUrlString('{BRAND['privacy_url']}')"),
    ("launchUrlString('https://rustdesk.com')", f"launchUrlString('{SITE}')"),
])
patch("flutter/lib/common.dart", [
    ("launchUrl(Uri.parse('https://rustdesk.com'))", f"launchUrl(Uri.parse('{SITE}'))"),
])
patch("flutter/lib/desktop/pages/desktop_home_page.dart", [
    ("Uri.parse('https://rustdesk.com/download')", f"Uri.parse('{BRAND['download_url']}')"),
])
patch("flutter/lib/mobile/pages/connection_page.dart", [
    ("'https://rustdesk.com/download'", f"'{BRAND['download_url']}'"),
])
patch("flutter/lib/desktop/pages/install_page.dart", [
    ("'https://rustdesk.com/privacy.html'", f"'{BRAND['privacy_url']}'"),
])

if errors:
    print("\nRebrand failed, upstream sources changed:", file=sys.stderr)
    for e in errors:
        print("  " + e, file=sys.stderr)
    sys.exit(1)
print(f"\n{APP} branding applied.")
