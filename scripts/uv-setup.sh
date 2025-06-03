#!/bin/bash

check_command() {
    command -v "$1" >/dev/null 2>&1
}

if ! check_command uv; then
    echo "Error: 'uv' command not found. Please install 'uv' to proceed."
    echo "Visit 'https://docs.astral.sh/uv/getting-started/installation/' for installation instructions."
    exit 1
fi

uv init --app

BROWSERS=("$@")
if [ ${#BROWSERS[@]} -eq 0 ]; then
    BROWSERS=("chromium")
fi

VALID_BROWSERS=("chromium" "firefox" "webkit" "msedge")

VALID_TO_INSTALL=()
for browser in "${BROWSERS[@]}"; do
    if [[ " ${VALID_BROWSERS[*]} " =~ " ${browser} " ]]; then
        VALID_TO_INSTALL+=("$browser")
    else
        echo "Error: Invalid browser '${browser}'. Valid options are: ${VALID_BROWSERS[*]}"
        exit 1
    fi
done

echo "Setting up Playwright for: ${VALID_TO_INSTALL[*]}..."
export PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT="120000"
uv run playwright install --with-deps "${VALID_TO_INSTALL[@]}"

echo "Setup completed successfully"
