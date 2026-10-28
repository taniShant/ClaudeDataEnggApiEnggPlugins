#!/usr/bin/env bash
# Resets an SDF test project to a clean state for re-testing the ui-engineer agent.
# Removes any generated screens (keeping template screens: start, second).
# Resets routes.tsx, App.interface.ts, and src/screens/index.ts to template defaults.
#
# Usage:
#   bash scripts/reset-test-project.sh [project-path]
#   Default project-path: current directory

set -euo pipefail

PROJECT_PATH=${1:-$(pwd)}
SRC="$PROJECT_PATH/src"

if [ ! -f "$PROJECT_PATH/package.json" ]; then
  echo "ERROR: $PROJECT_PATH does not look like a project (no package.json)"
  exit 1
fi

if ! grep -q "chameleon-blueprint\|chameleon-router" "$PROJECT_PATH/package.json" 2>/dev/null; then
  echo "ERROR: $PROJECT_PATH does not look like a Chameleon SDF project"
  exit 1
fi

echo "Resetting $PROJECT_PATH to clean state..."

# --- Remove generated screen directories ---
# Keep: start, second (template screens)
KEEP_SCREENS="start second"
if [ -d "$SRC/screens" ]; then
  for dir in "$SRC/screens"/*/; do
    name=$(basename "$dir")
    keep=false
    for k in $KEEP_SCREENS; do
      [ "$name" = "$k" ] && keep=true && break
    done
    if [ "$keep" = false ]; then
      rm -rf "$dir"
      echo "  Removed: src/screens/$name"
    fi
  done
fi

# --- Reset routes.tsx ---
cat > "$SRC/routes.tsx" << 'EOF'
import { ScreenData } from '@barclays/chameleon-router';
import { RootStackParamList } from './App.interface';
import { StartScreen } from './screens/start';
import { SecondScreen } from './screens/second';

export const routes: ScreenData<RootStackParamList>[] = [
  {
    name: 'StartScreen',
    component: StartScreen,
    options: {
      headerShown: true,
      title: 'Start Screen',
    },
  },
  {
    name: 'SecondScreen',
    component: SecondScreen,
    options: {
      headerShown: true,
      title: 'Second Screen',
    },
  },
];

export default { routes };
EOF
echo "  Reset: src/routes.tsx"

# --- Reset App.interface.ts ---
cat > "$SRC/App.interface.ts" << 'EOF'
export type RootStackParamList = {
  StartScreen: undefined;
  SecondScreen: undefined;
};
EOF
echo "  Reset: src/App.interface.ts"

# --- Reset src/screens/index.ts ---
cat > "$SRC/screens/index.ts" << 'EOF'
export { SecondScreen } from './second/Second';
export { StartScreen } from './start/Start';
EOF
echo "  Reset: src/screens/index.ts"

echo ""
echo "Done. Project is clean and ready for re-testing."
