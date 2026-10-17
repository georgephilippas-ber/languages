#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$ROOT/bin"
OUT_DIR="${1:-$BIN}"
APP="$OUT_DIR/Languages.app"
STUB="/System/Library/CoreServices/Automator Application Stub.app"

[[ -d "$STUB" ]] || { echo "Automator stub not found at $STUB" >&2; exit 1; }
[[ -x "$BIN/languages" ]] || echo "Warning: $BIN/languages not built yet — run scripts/build.sh." >&2

read -r -d '' COMMAND <<EOF || true
BIN="$BIN"
PORT=8100
if [ ! -x "\$BIN/languages" ]; then
  osascript -e 'display alert "Languages" message "No app found at '"\$BIN"'/languages. Run scripts/build.sh first."'
  exit 1
fi
if lsof -nP -iTCP:\$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  open "http://127.0.0.1:\$PORT"
else
  open -a Terminal "\$BIN/languages"
fi
EOF

rm -rf "$APP"
mkdir -p "$OUT_DIR"
cp -R "$STUB" "$APP"

cat > "$APP/Contents/document.wflow" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>AMApplicationBuild</key>
	<string>528</string>
	<key>AMApplicationVersion</key>
	<string>2.10</string>
	<key>AMDocumentVersion</key>
	<string>2</string>
	<key>actions</key>
	<array>
		<dict>
			<key>action</key>
			<dict>
				<key>AMAccepts</key>
				<dict>
					<key>Container</key>
					<string>List</string>
					<key>Optional</key>
					<true/>
					<key>Types</key>
					<array>
						<string>com.apple.cocoa.string</string>
					</array>
				</dict>
				<key>AMActionVersion</key>
				<string>2.0.3</string>
				<key>AMApplication</key>
				<array>
					<string>Automator</string>
				</array>
				<key>AMParameterProperties</key>
				<dict>
					<key>COMMAND_STRING</key>
					<dict/>
					<key>CheckedForUserDefaultShell</key>
					<dict/>
					<key>inputMethod</key>
					<dict/>
					<key>shell</key>
					<dict/>
					<key>source</key>
					<dict/>
				</dict>
				<key>AMProvides</key>
				<dict>
					<key>Container</key>
					<string>List</string>
					<key>Types</key>
					<array>
						<string>com.apple.cocoa.string</string>
					</array>
				</dict>
				<key>ActionBundlePath</key>
				<string>/System/Library/Automator/Run Shell Script.action</string>
				<key>ActionName</key>
				<string>Run Shell Script</string>
				<key>ActionParameters</key>
				<dict>
					<key>COMMAND_STRING</key>
					<string>PLACEHOLDER</string>
					<key>CheckedForUserDefaultShell</key>
					<true/>
					<key>inputMethod</key>
					<integer>0</integer>
					<key>shell</key>
					<string>/bin/bash</string>
					<key>source</key>
					<string></string>
				</dict>
				<key>BundleIdentifier</key>
				<string>com.apple.RunShellScript</string>
				<key>CFBundleVersion</key>
				<string>2.0.3</string>
				<key>CanShowSelectedItemsWhenRun</key>
				<false/>
				<key>CanShowWhenRun</key>
				<true/>
				<key>Category</key>
				<array>
					<string>AMCategoryUtilities</string>
				</array>
				<key>Class Name</key>
				<string>RunShellScriptAction</string>
				<key>InputUUID</key>
				<string>8A1F2C3D-1111-4A5B-9C6D-000000000001</string>
				<key>Keywords</key>
				<array>
					<string>Shell</string>
					<string>Script</string>
					<string>Command</string>
					<string>Run</string>
					<string>Unix</string>
				</array>
				<key>OutputUUID</key>
				<string>8A1F2C3D-1111-4A5B-9C6D-000000000002</string>
				<key>UUID</key>
				<string>8A1F2C3D-1111-4A5B-9C6D-000000000003</string>
				<key>UnlocalizedApplications</key>
				<array>
					<string>Automator</string>
				</array>
				<key>arguments</key>
				<dict/>
				<key>isViewVisible</key>
				<integer>1</integer>
				<key>location</key>
				<string>309.000000:253.000000</string>
				<key>nibPath</key>
				<string>/System/Library/Automator/Run Shell Script.action/Contents/Resources/Base.lproj/main.nib</string>
			</dict>
			<key>isViewVisible</key>
			<integer>1</integer>
		</dict>
	</array>
	<key>connectors</key>
	<dict/>
	<key>workflowMetaData</key>
	<dict>
		<key>workflowTypeIdentifier</key>
		<string>com.apple.Automator.application</string>
	</dict>
</dict>
</plist>
EOF
plutil -replace actions.0.action.ActionParameters.COMMAND_STRING -string "$COMMAND" "$APP/Contents/document.wflow"

PLIST="$APP/Contents/Info.plist"
plutil -replace CFBundleIdentifier -string "local.languages.launcher" "$PLIST"
plutil -replace CFBundleName -string "Languages" "$PLIST"

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

codesign --force --deep --sign - "$APP" >/dev/null 2>&1
touch "$APP"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP" >/dev/null 2>&1 || true

echo "Created: $APP"
echo "Drag it to the Desktop (or Dock) and double-click to launch."
