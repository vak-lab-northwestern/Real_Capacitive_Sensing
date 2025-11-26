#!/bin/bash
# Quick build and upload script for main_E.cpp

ENV_NAME="nanoatmega328_C"  # Change to "leonardo_E" for Leonardo board
UPLOAD_PORT=""  # Leave empty for auto-detect, or set to e.g., "/dev/cu.usbserial-2110"

echo "=================================="
echo "Building main_E.cpp for Arduino"
echo "=================================="
echo ""

# Check PlatformIO
if ! command -v pio &> /dev/null; then
    echo "[ERROR] PlatformIO not found. Install with: pip install platformio"
    exit 1
fi

# Build
echo "[1/3] Building..."
if [ -z "$UPLOAD_PORT" ]; then
    pio run -e $ENV_NAME
else
    pio run -e $ENV_NAME --upload-port $UPLOAD_PORT
fi

if [ $? -ne 0 ]; then
    echo "[ERROR] Build failed!"
    exit 1
fi

echo ""
echo "[2/3] Build successful!"
echo ""

# Ask for upload
read -p "Upload to Arduino? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "[3/3] Uploading..."
    if [ -z "$UPLOAD_PORT" ]; then
        pio run -e $ENV_NAME -t upload
    else
        pio run -e $ENV_NAME -t upload --upload-port $UPLOAD_PORT
    fi
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Upload successful!"
        echo ""
        read -p "Open serial monitor? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Opening serial monitor (Press CTRL+] to exit)..."
            pio device monitor -e $ENV_NAME
        fi
    else
        echo "[ERROR] Upload failed!"
        exit 1
    fi
else
    echo "Skipping upload. Run manually with:"
    echo "  pio run -e $ENV_NAME -t upload"
fi

