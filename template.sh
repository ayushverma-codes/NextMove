#!/bin/bash

echo "🚀 Creating directory structure in the current directory..."

# Create core directories
mkdir -p core/interfaces
mkdir -p core/services
mkdir -p core/models

# Create infrastructure directories
mkdir -p infrastructure/persistence
mkdir -p infrastructure/web
mkdir -p infrastructure/authentication

# Create other top-level directories
mkdir -p api
mkdir -p config
mkdir -p tests

# Create top-level files
touch requirements.txt
touch README.md

# Add __init__.py files to subdirectories to make them Python packages.
# (This skips the root directory and any hidden folders like .git)
find . -mindepth 1 -type d -not -path '*/\.*' -exec touch {}/__init__.py \;

echo "✅ Folder structure created successfully!"

# Display the created tree (if the 'tree' command is installed)
if command -v tree &> /dev/null; then
    echo "---"
    tree -a -I '.git' .
fi