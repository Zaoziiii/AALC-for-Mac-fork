#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python_bin="${PYTHON_BIN:-.venv/bin/python}"
stage="$(mktemp -d /private/tmp/aalc-build.XXXXXX)"
export PYINSTALLER_CONFIG_DIR="$PWD/.build/cache"
"$python_bin" -m PyInstaller --noconfirm --distpath "$stage/dist" --workpath "$PWD/.build/work" macos.spec
/usr/bin/codesign --force --deep --sign - "$stage/dist/AALC Mac.app"
/usr/bin/codesign --verify --deep --strict "$stage/dist/AALC Mac.app"
mkdir -p dist
/usr/bin/ditto -c -k --norsrc --noextattr --keepParent "$stage/dist/AALC Mac.app" "$PWD/dist/AALC-Mac-arm64.zip"
printf 'Built: %s/dist/AALC-Mac-arm64.zip\n' "$PWD"
