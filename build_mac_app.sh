#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
project_dir="$(pwd)"
export PYINSTALLER_CONFIG_DIR="$project_dir/build/pyinstaller-config"

.venv/bin/python3 -m PyInstaller \
  --noconfirm --clean --onedir --windowed \
  --name 拼好题 \
  --icon "$project_dir/assets/pinhaoti.png" \
  --osx-bundle-identifier org.pinhaoti.local \
  --add-data "$project_dir/sources:sources" \
  --add-data "$project_dir/data:data" \
  --distpath build/dist \
  --workpath build/pyinstaller \
  --specpath build \
  app_entry.py
