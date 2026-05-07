#!/bin/zsh
set -euo pipefail

REPO_DIR="$(cd -- "$(dirname -- "$0")/.." && pwd)"
PLIST_SOURCE="$REPO_DIR/launchd/com.josephruocco.profile-branch-graph.plist"
PLIST_TARGET="$HOME/Library/LaunchAgents/com.josephruocco.profile-branch-graph.plist"

mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SOURCE" "$PLIST_TARGET"
launchctl unload "$PLIST_TARGET" >/dev/null 2>&1 || true
launchctl load "$PLIST_TARGET"
launchctl start com.josephruocco.profile-branch-graph >/dev/null 2>&1 || true

echo "Installed launch agent at $PLIST_TARGET"
