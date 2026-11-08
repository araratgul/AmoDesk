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
    for old, new in pairs:  # read_text uses universal newlines, so CRLF checkouts match too
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

# 5. Brand colours: RustDesk blue -> Amo Red. MyTheme.accent paints the ID and
#    password side bars and icons, MyTheme.button the filled buttons
#    ("Connect"), colorScheme.primary focus rings, switches and progress bars.
C = BRAND["colors"]
RED, RED_DARK = C["accent"], C["accent_dark"]
patch("flutter/lib/common.dart", [
    ("static const Color accent = Color(0xFF0071FF);", f"static const Color accent = Color(0xFF{RED});"),
    ("static const Color accent50 = Color(0x770071FF);", f"static const Color accent50 = Color(0x77{RED});"),
    ("static const Color accent80 = Color(0xAA0071FF);", f"static const Color accent80 = Color(0xAA{RED});"),
    ("static const Color idColor = Color(0xFF00B6F0);", f"static const Color idColor = Color(0xFF{RED});"),
    ("static const Color button = Color(0xFF2C8CFF);", f"static const Color button = Color(0xFF{RED});"),
    # default (info) message box colour
    ("  return Color(0xFF2C8CFF);\n}", f"  return Color(0xFF{RED});\n}}"),
    ("primary: Colors.blue, secondary: accent, background: grayBg)",
     "primary: accent, secondary: accent, background: grayBg)"),
    ("      primary: Colors.blue,\n      secondary: accent,", "      primary: accent,\n      secondary: accent,"),
    # links inside dialogs
    ("        color: Colors.blue,\n        decoration: TextDecoration.underline,",
     "        color: MyTheme.accent,\n        decoration: TextDecoration.underline,"),
])
patch("flutter/lib/desktop/pages/desktop_home_page.dart", [
    ("const borderColor = Color(0xFF2F65BA);", f"const borderColor = Color(0xFF{RED_DARK});"),
    # "install AmoDesk" / UAC banner in the left panel: pink gradient -> brand red
    ("Color.fromARGB(255, 226, 66, 188),\n                  Color.fromARGB(255, 244, 114, 124),",
     f"Color(0xFF{RED}),\n                  Color(0xFF{RED_DARK}),"),
])
patch("flutter/lib/desktop/widgets/update_progress.dart", [
    ("AlwaysStoppedAnimation<Color>(Colors.blue)", "AlwaysStoppedAnimation<Color>(MyTheme.accent)"),
])

# 5b. Brand neutrals (brand book: Deep Graphite #1E293B, Cloud White #F8FAFC,
#     Slate Neutral #64748B). Light theme: cool slate greys instead of plain
#     greys; dark theme: graphite surfaces instead of RustDesk's near-black.
patch("flutter/lib/common.dart", [
    # light
    ("static const Color grayBg = Color(0xFFEFEFF2);", "static const Color grayBg = Color(0xFFF1F5F9);"),
    ("hoverColor: Color.fromARGB(255, 224, 224, 224),", "hoverColor: Color(0xFFE2E8F0),"),
    ("hintColor: Color(0xFFAAAAAA),", "hintColor: Color(0xFF94A3B8),"),
    ("border: Color(0xFFCCCCCC),\n    border2: Color(0xFFBBBBBB),",
     "border: Color(0xFFCBD5E1),\n    border2: Color(0xFF94A3B8),"),
    ("highlight: Color(0xFFE5E5E5),", "highlight: Color(0xFFE2E8F0),"),
    ("static const Color border = Color(0xFFCCCCCC);", "static const Color border = Color(0xFFCBD5E1);"),
    # dark
    ("hoverColor: Color.fromARGB(255, 45, 46, 53),", "hoverColor: Color(0xFF273449),"),
    ("Color(0xFF18191E)", "Color(0xFF0F172A)"),
    ("Color(0xFF24252B)", "Color(0xFF1E293B)"),
    ("MaterialStatePropertyAll(Color(0xFF121212))", "MaterialStatePropertyAll(Color(0xFF0B1220))"),
    ("static const Color canvasColor = Color(0xFF212121);", "static const Color canvasColor = Color(0xFF0F172A);"),
    ("border: Color(0xFF555555),", "border: Color(0xFF334155),"),
    ("highlight: Color(0xFF3F3F3F),", "highlight: Color(0xFF273449),"),
])

# 5c. Brand typeface Inter (SIL OFL 1.1, rsms/inter 4.1, static TTFs in
#     amodesk/branding/fonts). Bundled as a Flutter font and set on both themes.
import shutil
FONT_SRC = ROOT / "amodesk" / "branding" / "fonts"
FONT_DST = ROOT / "flutter" / "assets" / "fonts"
FONT_DST.mkdir(parents=True, exist_ok=True)
for f in FONT_SRC.iterdir():
    shutil.copy2(f, FONT_DST / f.name)
patch("flutter/pubspec.yaml", [
    ("  fonts:\n    - family: GestureIcons\n",
     "  fonts:\n    - family: Inter\n      fonts:\n"
     "        - asset: assets/fonts/Inter-Regular.ttf\n"
     "        - asset: assets/fonts/Inter-Medium.ttf\n          weight: 500\n"
     "        - asset: assets/fonts/Inter-SemiBold.ttf\n          weight: 600\n"
     "        - asset: assets/fonts/Inter-Bold.ttf\n          weight: 700\n"
     "    - family: GestureIcons\n"),
])
patch("flutter/lib/common.dart", [
    ("  static ThemeData lightTheme = ThemeData(\n", "  static ThemeData lightTheme = ThemeData(\n    fontFamily: 'Inter',\n"),
    ("  static ThemeData darkTheme = ThemeData(\n", "  static ThemeData darkTheme = ThemeData(\n    fontFamily: 'Inter',\n"),
])

# 6. "Powered by RustDesk" link above the main window. The About page keeps
#    the "Based on RustDesk (AGPL-3.0)" note and the license files stay.
if BRAND.get("hide_powered_by"):
    patch("flutter/lib/common.dart", [
        ('Widget loadPowered(BuildContext context) {\n  if (bind.mainGetBuildinOption(key: "hide-powered-by-me") == \'Y\') {',
         'Widget loadPowered(BuildContext context) {\n  if (true) {'),
    ])

# 7. No RustDesk marketing or services in the product.
WIKI = BRAND.get("docs_url", "https://amodesk.amobit.io/wiki/")
DOWNLOAD = BRAND["download_url"]
PRIVACY = BRAND["privacy_url"]
#    7a. With our server baked in, the client must not consider itself to be on
#        the public RustDesk server: that shows "set up your own server" under
#        the ID with a link to rustdesk.com/pricing.
if server:
    patch("src/common.rs", [
        ('pub fn using_public_server() -> bool {\n'
         '    crate::get_custom_rendezvous_server(get_option("custom-rendezvous-server")).is_empty()\n}',
         'pub fn using_public_server() -> bool {\n'
         '    // AmoDesk: the rendezvous server is built in, never the public RustDesk one.\n'
         '    false\n}'),
    ])
#    7b. Updates come from AmoDesk, never from api.rustdesk.com (a RustDesk
#        update would replace the AmoDesk client). Automatic checks are already
#        off for custom clients; this closes the manual "check for updates" path.
patch("src/common.rs", [
    ('pub async fn do_check_software_update() -> hbb_common::ResultType<()> {\n',
     'pub async fn do_check_software_update() -> hbb_common::ResultType<()> {\n'
     '    if is_custom_client() {\n        return Ok(());\n    }\n'),
])
#    7c. Every remaining rustdesk.com link in the UI goes to AmoDesk resources.
LINKS = [
    (r"https?://rustdesk\.com/docs/[^'\"\s)]*", WIKI),
    (r"https?://rustdesk\.com/privacy(?:\.html)?", PRIVACY),
    (r"https?://rustdesk\.com/pricing/?", SITE),
    (r"https?://rustdesk\.com/download/?", DOWNLOAD),
    (r"https?://rustdesk\.com/blog/[^'\"\s)]*", WIKI),
    (r"https?://rustdesk\.com/?(?=['\"])", SITE),
]
ui_files = [p for p in (ROOT / "flutter" / "lib").rglob("*.dart")]
ui_files += [ROOT / "src" / "lang" / "en.rs", ROOT / "src" / "client.rs", ROOT / "libs" / "hbb_common" / "src" / "config.rs"]
for path in ui_files:
    text = path.read_text(encoding="utf-8")
    new = text
    for pattern, repl in LINKS:
        new = re.sub(pattern, repl, new)
    if new != text:
        path.write_text(new, encoding="utf-8", newline="")
        print(f"relinked {path.relative_to(ROOT)}")
    if path.suffix == ".dart" and "Text('rustdesk.com'" in new:
        new = new.replace("Text('rustdesk.com'", "Text('amodesk.amobit.io'")
        path.write_text(new, encoding="utf-8", newline="")
    for m in re.finditer(r"https?://(?:www\.)?rustdesk\.com[^'\"\s)]*|'rustdesk\.com'", new):
        errors.append(f"{path.relative_to(ROOT)}: rustdesk.com link left: {m.group(0)}")

# 7. Open-source hbbs compatibility. The OSS rendezvous server (rustdesk-server
#    1.1.x) never starts a TCP key exchange; only RustDesk Server Pro does. A
#    client logged in to the console (it then carries an access token) insists
#    on that exchange and fails with "Failed to secure tcp: deadline has
#    elapsed". OSS hbbs ignores the token too, so: never wait for the exchange
#    on the punch/relay paths and never put the token on that unencrypted socket.
#    Elsewhere a server that stays silent counts as "no exchange" after 3 s
#    instead of an error after 18 s.
patch("src/client.rs", [
    ("let legacy_secure = !key.is_empty() && (!token.is_empty() || !switch_code.is_empty());",
     "let legacy_secure = false; // AmoDesk: OSS hbbs has no key exchange"),
    ("            if !key.is_empty() && (!token.is_empty() || !switch_code.is_empty()) {\n"
     "                secure_tcp(&mut socket, key).await?;",
     "            if false {\n"
     "                secure_tcp(&mut socket, key).await?;"),
    ("            token: token.to_owned(),\n            nat_type: nat_type.into(),",
     "            token: String::new(), // AmoDesk: never sent in the clear\n            nat_type: nat_type.into(),"),
    ("                token: token.to_owned(),\n                uuid: uuid.clone(),",
     "                token: String::new(), // AmoDesk: never sent in the clear\n                uuid: uuid.clone(),"),
])
patch("src/common.rs", [
    ("    match timeout(READ_TIMEOUT, conn.next()).await? {\n        Some(Ok(bytes)) => {\n            if let Ok(msg_in) = RendezvousMessage::parse_from_bytes(&bytes) {",
     "    match timeout(3_000, conn.next()).await.unwrap_or(None) {\n        Some(Ok(bytes)) => {\n            if let Ok(msg_in) = RendezvousMessage::parse_from_bytes(&bytes) {"),
])

if errors:
    print("\nRebrand failed, upstream sources changed:", file=sys.stderr)
    for e in errors:
        print("  " + e, file=sys.stderr)
    sys.exit(1)
print(f"\n{APP} branding applied.")
