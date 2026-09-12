#!/usr/bin/env bash

set -Eeuo pipefail

#-----------------------------------------------------------------------
# Somi setup script
#-----------------------------------------------------------------------

# Always work from the directory containing this script
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
SOMI_CONFIG_DIR="$CONFIG_HOME/somi"
KOKORO_DIR="$SOMI_CONFIG_DIR/kokoro"
CONFIG_FILE="$SOMI_CONFIG_DIR/config.toml"

KOKORO_MODEL_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
KOKORO_VOICES_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

echo
echo "================================================================"
echo "                      Somi setup script"
echo "================================================================"
echo


# -----------------------------------------------------------------------
# 1. Install basic system dependencies
# -----------------------------------------------------------------------

echo "-> Checking system dependencies..."

if command -v dnf >/dev/null 2>&1; then
    echo "Fedora detected."

    sudo dnf install -y \
        git \
        curl \
        portaudio \
        libnotify
else
    echo
    echo "WARNING"
    echo "Automatic system dependency installation currently"
    echo "supports Fedora only."
    echo
    echo "Make sure Git, curl, and PortAudio are installed."
    echo
fi


# -----------------------------------------------------------------------
# 2. Install uv
# -----------------------------------------------------------------------

echo
echo "-> Checking for uv..."

if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found. Installing uv..."

    curl -LsSf https://astral.sh/uv/install.sh | sh

    # uv normally installs here.
    export PATH="$HOME/.local/bin:$PATH"
    hash -r
fi

if ! command -v uv >/dev/null 2>&1; then
    echo
    echo "ERROR: uv installation failed."
    echo
    echo "Restart your terminal and try again."
    exit 1
fi

echo "✓ $(uv --version)"


# -----------------------------------------------------------------------
# 3. Create/sync Python environment
# -----------------------------------------------------------------------

echo
echo "-> Setting up SOMI Python environment..."

uv sync

echo "✓ Python environment is ready."


# -----------------------------------------------------------------------
# 4. Download OpenWakeWord model
# -----------------------------------------------------------------------

echo
echo "-> Checking wake-word model..."

mkdir -p "$WAKE_DIR"

WAKE_MODEL_SOURCE="$SCRIPT_DIR/assets/wake/hey_somi.onnx"
WAKE_DATA_SOURCE="$SCRIPT_DIR/assets/wake/hey_somi.onnx.data"

WAKE_MODEL_DEST="$WAKE_DIR/hey_somi.onnx"
WAKE_MODEL_DEST="WAKE_DIR/hey_somi.onnx.data"

if [[ ! -f "$WAKE_MODEL_SOURCE" || ! -f "$WAKE_DATA_SOURCE" ]]; then
    echo "ERROR: Somi wake-word model files are missing from the repository."
    exit 1
fi

cp "$WAKE_MODEL_SOURCE" "$WAKE_MODEL_DEST"
cp "$WAKE_MODEL_SOURCE" "$WAKE_DATA_DEST"

echo "✓ Somi wake-word model installed."


# -----------------------------------------------------------------------
# 5. Download Kokoro model and voices
# -----------------------------------------------------------------------

echo
echo "-> Checking Kokoro TTS model..."

mkdir -p "$KOKORO_DIR"

download_file() {
    local url="$1"
    local destination="$2"
    local name="$3"

    if [[ -s "$destination" ]]; then
        echo "✓ $name already installed."
        return
    fi

    echo "Downloading $name..."

    curl \
        --fail \
        --location \
        --retry 3 \
        --progress-bar \
        "$url" \
        --output "${destination}.part"

    mv "${destination}.part" "$destination"

    echo "✓ $name installed"
}

download_file \
    "$KOKORO_MODEL_URL" \
    "$KOKORO_DIR/kokoro-v1.0.onnx" \
    "Kokoro model"

download_file \
    "$KOKORO_VOICES_URL" \
    "$KOKORO_DIR/voices-v1.0.bin" \
    "Kokoro voices"


# -----------------------------------------------------------------------
# 6. Create SOMI configuration
# -----------------------------------------------------------------------

echo
echo "-> Checking SOMI configuration..."

mkdir -p "$SOMI_CONFIG_DIR"

if [[ ! -f "$CONFIG_FILE" ]]; then

    cp "$SCRIPT_DIR/config.example.toml" "$CONFIG_FILE"

    echo "✓ Created:"
    echo "  $CONFIG_FILE"
else
    echo "✓ Existing config found."
    
    # Migrate the old default wake word to Somi.
    # Custom wake-word settings are left untouched.
    if grep -q '^word = "hey_jarvis"$' "$CONFIG_FILE"; then
        sed -i \
            's|^word = "hey_jarvis"$|word = "~/.config/somi/wake/hey_somi.onnx"|' \
            "$CONFIG_FILE"

        echo "✓ Updated default wake word to Hey Somi."
    else
        echo "  Leaving existing wake-word configuration unchanged."
    fi
    
fi


# -----------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------

echo
echo "================================================================"
echo "                  Somi setup complete!"
echo "================================================================"
echo
echo "IMPORTANT:"
echo
echo "Review your SOMI configuration:"
echo
echo "  $CONFIG_FILE"
echo
echo "If you use an API:"
echo "  - set backend = \"api\""
echo "  - enter your API base URL"
echo "  - enter your API key"
echo "  - select your model"
echo
echo "If you use a local LLM server:"
echo "  - set backend = \"local\""
echo "  - enter your local LLM server URL"
echo "  - select your model"
echo
echo "If you use SOMI's desktop/local llama-server mode:"
echo "  - set backend = \"desktop\""
echo "  - configure the model path if needed"
echo
echo "Then start SOMI with:"
echo
echo "  uv run somi"
echo


# -----------------------------------------------------------------------
# Desktop notification (when supported)
# -----------------------------------------------------------------------

if command -v notify-send >/dev/null 2>&1; then
    if [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]]; then
        notify-send \
            "SOMI setup complete!" \
            "Review ~/.config/somi/config.toml to configure your LLM/API then run: uv run somi" \
            || true
    fi
fi
    
