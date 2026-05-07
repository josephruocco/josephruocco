#!/bin/zsh
set -euo pipefail

REPO_DIR="$(cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$REPO_DIR"

python3 generate_graph.py

if [[ -z "$(git status --porcelain -- assets/branch-contributions.svg README.md generate_graph.py .github/workflows/update-branch-contributions.yml 2>/dev/null)" ]]; then
  echo "No graph changes to commit"
  exit 0
fi

git add assets/branch-contributions.svg README.md generate_graph.py .github/workflows/update-branch-contributions.yml

git commit -m "Update profile branch contributions"
git push
