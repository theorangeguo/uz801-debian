#!/bin/bash
set -euo pipefail
BOARD="${1:?board required}"
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
STAGE=$(mktemp -d)
trap 'rm -rf -- "$STAGE"' EXIT
python3 "$ROOT/tools/build_inputs.py" prepare --board "$BOARD" --packages-only --package-dir "$STAGE/packages"
PACKAGE="$STAGE/packages/$BOARD-firmware.deb"
dpkg-deb --info "$PACKAGE"
mkdir -p "$STAGE/root/var/lib/dpkg/updates"
touch "$STAGE/root/var/lib/dpkg/status"
# The new firmware packages contain data only, without maintainer scripts.
# Install into a disposable isolated root, never the runner's host root.
sudo dpkg --root="$STAGE/root" --install "$PACKAGE"
python3 - "$ROOT" "$STAGE/root" "$BOARD" <<'PY'
import hashlib,json,sys
from pathlib import Path
repo, root, board = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
lock=json.loads((repo/'config/dependencies.lock.json').read_text())
manifest=json.loads((repo/lock['boards'][board]['firmware']['manifest']).read_text())
for name, expected in manifest['files'].items():
    data=(root/name).read_bytes()
    if len(data)!=expected['bytes'] or hashlib.sha256(data).hexdigest()!=expected['sha256']:
        raise SystemExit('Installed dependency payload mismatch: '+name)
print('Native dpkg installation and every payload hash verified: '+board)
PY
