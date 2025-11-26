# Building and Uploading main_E.cpp to Arduino with PlatformIO

## Quick Start

### For Arduino Nano (ATmega328)
```bash
cd /Users/cathdxx/cap-sensing/sensing
pio run -e nanoatmega328_C -t upload
```

### For Arduino Leonardo
```bash
cd /Users/cathdxx/cap-sensing/sensing
pio run -e leonardo_E -t upload
```

---

## Step-by-Step Instructions

### 1. Verify PlatformIO Installation

Check if PlatformIO is installed:
```bash
pio --version
```

If not installed, install PlatformIO Core:
```bash
pip install platformio
```

### 2. Identify Your Arduino Board

Determine which board you're using:
- **Arduino Nano** (ATmega328) → Use environment: `nanoatmega328_C`
- **Arduino Leonardo** → Use environment: `leonardo_E`

### 3. Build the Code

```bash
cd /Users/cathdxx/cap-sensing/sensing

# For Arduino Nano
pio run -e nanoatmega328_C

# For Arduino Leonardo  
pio run -e leonardo_E
```

This will:
- Install dependencies (FDC2214 library)
- Compile `main_E.cpp`
- Create `.hex` file in `.pio/build/` directory

### 4. Upload to Arduino

```bash
# For Arduino Nano
pio run -e nanoatmega328_C -t upload

# For Arduino Leonardo
pio run -e leonardo_E -t upload
```

**Note**: PlatformIO will auto-detect the serial port. If you have multiple ports, specify it:

```bash
pio run -e nanoatmega328_C -t upload --upload-port /dev/cu.usbserial-2110
```

### 5. Monitor Serial Output (Optional)

Watch the serial output to verify it's working:

```bash
# For Arduino Nano
pio device monitor -e nanoatmega328_C

# For Arduino Leonardo
pio device monitor -e leonardo_E
```

Or specify port:
```bash
pio device monitor --port /dev/cu.usbserial-2110 --baud 115200
```

**Expected output**:
```
FDC READY
Row_index, Column_index, Node_Value
0,0,123456
0,1,123789
...
```

---

## PlatformIO Configuration

The configuration is in `platformio.ini`:

### Arduino Nano Configuration
```ini
[env:nanoatmega328_C]
platform = atmelavr
board = nanoatmega328
monitor_speed = 115200
framework = arduino
lib_deps = zharijs/FDC2214@^1.1
build_src_filter = 
    +<main_E.cpp>
    -<main_*.cpp>  # Excludes other main files
```

### Arduino Leonardo Configuration
```ini
[env:leonardo_E]
platform = atmelavr
board = leonardo
monitor_speed = 115200
framework = arduino
upload_protocol = avr109
lib_deps = zharijs/FDC2214@^1.1
build_src_filter = 
    +<main_E.cpp>
    -<main_*.cpp>
```

---

## Troubleshooting

### Build Fails: "Library not found"
```bash
# Manually install library
pio lib install zharijs/FDC2214@^1.1
```

### Upload Fails: "Port not found"
1. Check Arduino is connected: `ls /dev/cu.* | grep usb`
2. Find your port: `pio device list`
3. Specify port explicitly: `pio run -e nanoatmega328_C -t upload --upload-port /dev/cu.usbserial-XXXX`

### Upload Fails: "Permission denied"
```bash
sudo chmod 666 /dev/cu.usbserial-XXXX
```

Or add your user to dialout group:
```bash
sudo usermod -a -G dialout $USER
# Then log out and log back in
```

### Wrong Board Selected
Update `platformio.ini` to use correct environment or create new one for your board.

---

## Available Commands

```bash
# List available environments
pio run --list-targets

# Clean build files
pio run -t clean

# Build without uploading
pio run -e nanoatmega328_C

# Upload only (assuming already built)
pio run -e nanoatmega328_C -t upload

# Build + Upload + Monitor (all-in-one)
pio run -e nanoatmega328_C -t upload && pio device monitor -e nanoatmega328_C

# Check connected devices
pio device list
```

---

## Verify After Upload

1. **Check Serial Monitor**: You should see:
   ```
   FDC READY
   Row_index, Column_index, Node_Value
   0,0,123456
   0,1,123789
   ...
   ```

2. **Test with Python**: Run test script:
   ```bash
   cd node_processing
   python serial_read_diff.py --test --test-duration 5
   ```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Build | `pio run -e nanoatmega328_C` |
| Upload | `pio run -e nanoatmega328_C -t upload` |
| Monitor | `pio device monitor -e nanoatmega328_C` |
| Clean | `pio run -t clean` |
| List devices | `pio device list` |

**Ready to go!** 🚀

