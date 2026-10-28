#!/bin/bash
# chameleon-preview-install.sh
#
# Installs the cached Chameleon preview shell app onto the booted simulator.
# Reads the version from the local shell app package so it always installs
# the right build for the current project.
#
# Assumes build-preview-shell.sh has already been run.
# Future: will download from Nexus instead of reading from local cache.
#
# Usage: bash scripts/chameleon-preview-install.sh

set -e

SHELL_APP_DIR="$(cd "$(dirname "$0")/../node_modules/@barclays/chameleon-shell-app" && pwd)"
VERSION=$(grep '"version"' "$SHELL_APP_DIR/package.json" | head -1 | sed 's/.*"\([0-9.]*\)".*/\1/')
CACHE_DIR="$HOME/.chameleon-preview"
APP_CACHE="$CACHE_DIR/ShellApp-${VERSION}.app"

echo "Chameleon Preview Shell Installer"
echo "  Shell app version : $VERSION"
echo "  App cache         : $APP_CACHE"
echo ""

# Check cached build exists
if [ ! -d "$APP_CACHE" ]; then
  echo "❌ No cached build found for version $VERSION."
  echo "   Run first: bash scripts/build-preview-shell.sh"
  exit 1
fi

# Check a simulator is booted
BOOTED=$(xcrun simctl list devices | grep Booted | head -1)
if [ -z "$BOOTED" ]; then
  echo "❌ No booted simulator found."
  echo "   Boot one via Xcode → Simulator, or run:"
  echo "   xcrun simctl boot 'iPhone 17 Pro'"
  exit 1
fi

echo "Installing onto: $BOOTED"
xcrun simctl install booted "$APP_CACHE"

echo ""
echo "✅ Installed. Shell app bundle ID: com.barclays.chameleon.preview"
echo ""
echo "Next steps:"
echo "  1. Start Metro:  npm run start"
echo "  2. Launch app:   press 'i' in the Metro terminal (or tap the app on the simulator)"
echo "  3. Run previews: bash scripts/chameleon-preview.sh --screen ScreenName"
