#!/usr/bin/env bash
# Put the current commit into a clone on legion that is used only for checking ported methods:
# /root/innovation_port. The clone the user's queues run in (/root/innovation) is not touched; only its
# Python environment is used, read-only. Run from the Mac after committing.
set -euo pipefail
ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
B="$(mktemp -t fg_port).bundle"
git -C "$ROOT" bundle create "$B" HEAD >/dev/null 2>&1
ssh -o ConnectTimeout=15 legion "wsl -d Ubuntu -- dd of=/root/innovation_port.bundle status=none" < "$B"
rm -f "$B"
ssh -o ConnectTimeout=15 legion "wsl -d Ubuntu -- bash -s" <<'REMOTE'
set -e
rm -rf /root/innovation_port
git clone -q /root/innovation_port.bundle /root/innovation_port
cd /root/innovation_port && git log --oneline | head -1
REMOTE
