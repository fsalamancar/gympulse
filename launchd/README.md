# GymPulse launchd agent

Fetches every 30 min and writes `~/.gympulse/latest.json`.

## Install
```bash
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$REPO/.venv/bin/python"
DEST=~/Library/LaunchAgents/dev.francisco.gympulse.plist
sed -e "s#__REPO__#$REPO#g" -e "s#__PY__#$PY#g" \
    "$REPO/launchd/dev.francisco.gympulse.plist" > "$DEST"
launchctl unload "$DEST" 2>/dev/null || true
launchctl load "$DEST"
launchctl list | grep gympulse
```

## Uninstall
```bash
DEST=~/Library/LaunchAgents/dev.francisco.gympulse.plist
launchctl unload "$DEST"; rm -f "$DEST"
```
