#!/usr/bin/env bash
# Install the GymPulse RUNTIME outside macOS-protected folders (~/Documents etc.),
# so the launchd daemon and SwiftBar never trigger "allow access to Documents"
# privacy prompts. The repo stays where it is for development; this deploys:
#
#   ~/.gympulse/app/          code (fetcher/, scrape/) + its own venv
#   ~/.gympulse/icons/        menu-bar glyphs the plugin embeds
#   ~/SwiftBar/gympulse.10m.py   a real file copy (not a symlink into Documents)
#   ~/Library/LaunchAgents/dev.francisco.gympulse.plist  -> runs the installed app
#
# Idempotent: re-run after any code change to redeploy.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/.gympulse/app"
ICONS="$HOME/.gympulse/icons"
PLUGIN_DIR="$HOME/SwiftBar"
PLIST="$HOME/Library/LaunchAgents/dev.francisco.gympulse.plist"

echo "==> Deploying runtime to $APP"
mkdir -p "$APP" "$ICONS" "$PLUGIN_DIR"
rsync -a --delete "$REPO/fetcher" "$REPO/scrape" "$APP/"
rsync -a --delete "$REPO/assets/icons/" "$ICONS/"

echo "==> Python venv (created once; deps synced)"
if [ ! -x "$APP/.venv/bin/python" ]; then
  uv venv "$APP/.venv"
fi
uv pip install --python "$APP/.venv/bin/python" -q "playwright>=1.40"

echo "==> SwiftBar plugin (real file copy, reads ~/.gympulse only)"
rm -f "$PLUGIN_DIR/gympulse.10m.py"           # replace any old symlink into the repo
cp "$REPO/swiftbar/gympulse.10m.py" "$PLUGIN_DIR/gympulse.10m.py"
chmod +x "$PLUGIN_DIR/gympulse.10m.py"

echo "==> launchd daemon -> installed app"
sed -e "s#__REPO__#$APP#g" -e "s#__PY__#$APP/.venv/bin/python#g" \
    "$REPO/launchd/dev.francisco.gympulse.plist" > "$PLIST"
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "==> Verify"
launchctl list | grep gympulse || { echo "daemon not loaded!"; exit 1; }
sleep 3
ls -la "$HOME/.gympulse/latest.json" || true
echo "Done. Runtime lives in ~/.gympulse — no Documents access at runtime."
