#!/usr/bin/env bash
# Render AmoDesk icons from amodesk/branding/icon.svg into the source tree.
#   amodesk/gen_icons.sh desktop   res/*.png, res/scalable.svg, flutter/assets/icon.svg
#   amodesk/gen_icons.sh android   launcher, adaptive and notification icons
#   amodesk/gen_icons.sh macos     flutter/macos/Runner/AppIcon.icns (needs iconutil, macOS only)
# Needs rsvg-convert (librsvg). Run from the repository root.
set -euo pipefail
SVG=amodesk/branding/icon.svg
RED=E11D48
r() { rsvg-convert -w "$2" -h "$2" "$1" -o "$3"; }

# White glyph without the red squircle, scaled by $1 and centred in a 130x130 box.
glyph_svg() {
  local s=$1 off
  off=$(awk "BEGIN{print 65*(1-$s)}")
  cat <<EOF
<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 130 130">
  <g transform="translate($off $off) scale($s)">
$(sed -n '/<g /,/<\/g>/p' "$SVG")
  </g>
</svg>
EOF
}

case "${1:-}" in
desktop)
  r "$SVG" 512 res/icon.png
  r "$SVG" 32 res/32x32.png
  r "$SVG" 64 res/64x64.png
  r "$SVG" 128 res/128x128.png
  r "$SVG" 256 res/128x128@2x.png
  cp res/icon.png res/mac-icon.png
  cp "$SVG" res/scalable.svg
  cp "$SVG" flutter/assets/icon.svg
  ;;
android)
  RES=flutter/android/app/src/main/res
  TMP=$(mktemp -d)
  glyph_svg 0.62 > "$TMP/fg.svg"     # adaptive foreground: keep inside the 66dp safe zone
  glyph_svg 1.0 > "$TMP/stat.svg"    # notification icon: white on transparent
  for d in mdpi:48:108:24 hdpi:72:162:36 xhdpi:96:216:48 xxhdpi:144:324:72 xxxhdpi:192:432:96; do
    IFS=: read -r name icon fg stat <<<"$d"
    r "$SVG" "$icon" "$RES/mipmap-$name/ic_launcher.png"
    r "$SVG" "$icon" "$RES/mipmap-$name/ic_launcher_round.png"
    r "$TMP/fg.svg" "$fg" "$RES/mipmap-$name/ic_launcher_foreground.png"
    r "$TMP/stat.svg" "$stat" "$RES/mipmap-$name/ic_stat_logo.png"
  done
  sed -i "s/<color name=\"ic_launcher_background\">#[0-9a-fA-F]*</<color name=\"ic_launcher_background\">#$RED</" \
    "$RES/values/ic_launcher_background.xml"
  grep -q "#$RED" "$RES/values/ic_launcher_background.xml"
  rm -rf "$TMP"
  ;;
macos)
  # macOS icons keep ~10% transparent margin around the squircle.
  TMP=$(mktemp -d)
  cat > "$TMP/mac.svg" <<EOF
<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 130 130">
  <g transform="translate(13 13) scale(0.8)">
$(sed -e '1d' -e '$d' -e '/<!--/d' "$SVG")
  </g>
</svg>
EOF
  SET="$TMP/AppIcon.iconset"
  mkdir -p "$SET"
  for s in 16 32 128 256 512; do
    r "$TMP/mac.svg" "$s" "$SET/icon_${s}x${s}.png"
    r "$TMP/mac.svg" $((s * 2)) "$SET/icon_${s}x${s}@2x.png"
  done
  iconutil -c icns "$SET" -o flutter/macos/Runner/AppIcon.icns
  r "$TMP/mac.svg" 1024 res/mac-icon.png
  rm -rf "$TMP"
  ;;
*)
  echo "usage: $0 desktop|android|macos" >&2; exit 2 ;;
esac
echo "icons: $1 done"
