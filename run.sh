#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "Realtime Voice Changer (TD-PSOLA)"
echo "--------------------------------"

if ! command -v python3 &>/dev/null; then
    echo "[Error] python3 not found."
    exit 1
fi

# Platform audio backend hint
case "$OSTYPE" in
    darwin*) command -v brew &>/dev/null && brew list portaudio &>/dev/null || \
             echo "Tip: 'brew install portaudio' if sounddevice fails to load." ;;
    linux*)  dpkg -s libportaudio2 &>/dev/null 2>&1 || \
             echo "Tip: 'sudo apt install libportaudio2' if sounddevice fails to load." ;;
esac

echo "[1/2] Installing dependencies..."
python3 -m pip install -r requirements.txt --quiet 2>/dev/null || \
python3 -m pip install -r requirements.txt --quiet --break-system-packages

echo "[2/2] Launching..."
python3 -m voicechanger "$@"
