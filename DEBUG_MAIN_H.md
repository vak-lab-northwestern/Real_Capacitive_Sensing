# Debugging main_H.cpp - High Capacitance Readings

## Issues Fixed

### 1. **Missing Discard Reads** ✅
- **Problem**: `main_H.cpp` was reading immediately after MUX switching, capturing unstable values
- **Fix**: Added `DISCARD_READS` mechanism (2 reads) like in `main_E.cpp` to allow FDC to stabilize
- **Impact**: Readings should now be more stable and accurate

### 2. **Insufficient Settle Times** ✅
- **Problem**: Using 5500μs settle time, which may not be enough for oscillator stabilization
- **Fix**: Increased to 8000μs for both row and column switching (matching `main_E.cpp`)
- **Impact**: Better oscillator stability after MUX channel changes

### 3. **Added Debug Mode** ✅
- **Problem**: Hard to diagnose issues without visibility into intermediate values
- **Fix**: Added `DEBUG_MODE` flag (line 31) - set to `1` to enable debug output
- **Usage**: When enabled, prints discard values and final values for each node

## Understanding the Readings

### Raw Frequency Values
- **Node_Value** is a **raw 28-bit frequency count**, NOT capacitance in pF
- Lower frequency values = **higher capacitance**
- Higher frequency values = **lower capacitance**
- Typical range: 100,000 - 15,000,000 for sensors in 10-500pF range

### Conversion Formula
```
freq_Hz = Node_Value * (40,000,000 / 2^28)  ≈ Node_Value * 0.149 Hz
C_F = 1 / ((2π * freq_Hz)^2 * L)
C_pF = C_F * 1e12
```
Where `L` is your inductor value (typically 18μH or 180nH)

## Debugging Steps

### Step 1: Enable Debug Mode
1. Set `#define DEBUG_MODE 1` (line 31)
2. Recompile and upload
3. Monitor serial output to see:
   - Discard read values (should stabilize after 2 reads)
   - Final values for each node
   - Any unexpected patterns

### Step 2: Check Expected Values
- **Floating/unconnected nodes**: Will show very high frequency (low capacitance)
- **Shorted nodes**: Will show very low frequency (high capacitance)  
- **Normal nodes**: Should show values in expected range based on your sensor setup

### Step 3: Compare with main_E.cpp
- Both should now use same timing: 8000μs settle, 2 discard reads
- If `main_E.cpp` works but `main_H.cpp` doesn't, check:
  - MUX wiring connections
  - Whether differential sensing configuration is correct
  - If both MUX1 and MUX2 are properly connected

## Potential Causes of "Too High" Readings

1. **Interpretation**: If raw frequency values look large, that's normal - they're frequency counts
2. **Actual high capacitance**: If capacitance is truly too high, could be:
   - Shorted nodes
   - Wiring issues
   - Sensor placement too close
   - Parasitic capacitance from long wires

3. **Unstable readings**: If readings fluctuate wildly:
   - Insufficient settle time (now fixed with 8000μs)
   - Missing discard reads (now fixed)
   - EMI/noise issues
   - Power supply noise

## Next Steps

1. Recompile and upload the fixed code
2. Enable DEBUG_MODE if needed to diagnose
3. Collect sample data and check if readings stabilize
4. Convert raw values to capacitance to see actual pF values
5. Compare baseline readings between connected and floating nodes

