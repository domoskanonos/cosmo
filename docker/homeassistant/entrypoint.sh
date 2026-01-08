#!/bin/bash
set -e

# Target directory for custom components
TARGET_DIR="/config/custom_components/extended_openai_conversation"
SOURCE_DIR="/tmp/custom_components/extended_openai_conversation"

echo "Checking for Extended OpenAI Conversation component..."

# Copy if it doesn't exist in the volume
if [ ! -d "$TARGET_DIR" ]; then
    echo "Installing Extended OpenAI Conversation to $TARGET_DIR..."
    mkdir -p "$TARGET_DIR"
    cp -r "$SOURCE_DIR"/* "$TARGET_DIR/"
    echo "Installation complete."
else
    echo "Component already exists. Checking for updates or leaving as is..."
fi

exec /init "$@"
