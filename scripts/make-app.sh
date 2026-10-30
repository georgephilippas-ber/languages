#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/bin/.build/package/Languages.app"
RUNTIME="$ROOT/bin/.dist/languages"
[[ -x "$RUNTIME/languages" ]] || { echo "Run scripts/build.sh first." >&2; exit 1; }
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/runtime"
cp -R "$RUNTIME" "$APP/Contents/Resources/runtime/languages"
swiftc -O "$ROOT/bin/App.swift" -o "$APP/Contents/MacOS/Languages" -framework Cocoa
PLIST="$APP/Contents/Info.plist"
cat > "$PLIST" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>Languages</string>
<key>CFBundleIdentifier</key><string>local.languages.app</string>
<key>CFBundleName</key><string>Languages</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>1.0</string>
<key>CFBundleVersion</key><string>1</string>
<key>NSHighResolutionCapable</key><true/>
</dict></plist>
EOF
ICON_SVG="$ROOT/frontend/public/favicon.svg"
if [[ -f "$ICON_SVG" ]]; then
  WORK="$(mktemp -d)"
  read -r VX VY VW VH < <(sed -n 's/.*viewBox="\([^"]*\)".*/\1/p' "$ICON_SVG" | head -1)
  PADDED_VIEWBOX="$(awk -v x="$VX" -v y="$VY" -v w="$VW" -v h="$VH" \
    'BEGIN { pw = w * 0.12; ph = h * 0.12; printf "%g %g %g %g", x - pw, y - ph, w + 2 * pw, h + 2 * ph }')"
  sed "s/viewBox=\"[^\"]*\"/viewBox=\"$PADDED_VIEWBOX\"/" "$ICON_SVG" > "$WORK/icon.svg"
  sips -s format png -z 1024 1024 "$WORK/icon.svg" --out "$WORK/icon-1024.png" >/dev/null
  mkdir "$WORK/AppIcon.iconset"
  for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$WORK/icon-1024.png" --out "$WORK/AppIcon.iconset/icon_${size}x${size}.png" >/dev/null
    sips -z $((size * 2)) $((size * 2)) "$WORK/icon-1024.png" --out "$WORK/AppIcon.iconset/icon_${size}x${size}@2x.png" >/dev/null
  done
  iconutil -c icns "$WORK/AppIcon.iconset" -o "$APP/Contents/Resources/AppIcon.icns"
  plutil -replace CFBundleIconFile -string "AppIcon" "$PLIST"
  plutil -remove CFBundleIconName "$PLIST" 2>/dev/null || true
  rm -rf "$WORK"
fi

codesign --force --deep --sign - "$APP"
# Publish only once the complete bundle has built and signed successfully.
rm -rf "$ROOT/bin/Languages.app"
mv "$APP" "$ROOT/bin/Languages.app"
echo "Built $ROOT/bin/Languages.app"
