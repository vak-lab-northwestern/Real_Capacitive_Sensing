#!/usr/bin/env python3
"""
Debug script to analyze raw capacitance CSV data.
Shows statistics, variations, and identifies potential issues.
Uses only standard library - no pandas required.
"""

import csv
import sys
import os
from collections import defaultdict
import statistics

def analyze_csv(csv_file):
    """Analyze CSV file for capacitance data patterns."""
    
    print(f"\n{'='*60}")
    print(f"Analyzing: {os.path.basename(csv_file)}")
    print(f"{'='*60}\n")
    
    # Read CSV data
    data = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'timestamp': float(row['timestamp']),
                'row': int(row['row_index']),
                'col': int(row['col_index']),
                'cap': float(row['capacitance_pF'])
            })
    
    print(f"Total samples: {len(data)}")
    print(f"\nFirst 5 rows:")
    for i, row in enumerate(data[:5]):
        print(f"  {i+1}. t={row['timestamp']:.2f}s, node=({row['row']},{row['col']}), cap={row['cap']:.3f} pF")
    
    print(f"\nLast 5 rows:")
    for i, row in enumerate(data[-5:]):
        print(f"  {i+1}. t={row['timestamp']:.2f}s, node=({row['row']},{row['col']}), cap={row['cap']:.3f} pF")
    
    # Overall statistics
    all_caps = [d['cap'] for d in data]
    print(f"\n{'='*60}")
    print("OVERALL STATISTICS")
    print(f"{'='*60}")
    print(f"Capacitance range: {min(all_caps):.3f} - {max(all_caps):.3f} pF")
    print(f"Mean: {statistics.mean(all_caps):.3f} pF")
    print(f"Std dev: {statistics.stdev(all_caps):.3f} pF")
    print(f"Median: {statistics.median(all_caps):.3f} pF")
    
    # Statistics per node
    print(f"\n{'='*60}")
    print("STATISTICS PER NODE")
    print(f"{'='*60}")
    
    node_data = defaultdict(list)
    for row in data:
        node_key = (row['row'], row['col'])
        node_data[node_key].append(row['cap'])
    
    node_stats = []
    for (row, col) in sorted(node_data.keys()):
        caps = node_data[(row, col)]
        if len(caps) > 0:
            min_val = min(caps)
            max_val = max(caps)
            mean_val = statistics.mean(caps)
            std_val = statistics.stdev(caps) if len(caps) > 1 else 0.0
            range_val = max_val - min_val
            cv = (std_val / mean_val * 100) if mean_val > 0 else 0
            
            print(f"Node ({row},{col}): mean={mean_val:.3f} pF, "
                  f"std={std_val:.3f} pF, range=[{min_val:.3f}, {max_val:.3f}] "
                  f"({range_val:.3f} pF, {cv:.2f}% CV), samples={len(caps)}")
            
            node_stats.append({
                'node': (row, col),
                'mean': mean_val,
                'std': std_val,
                'range': range_val,
                'min': min_val,
                'max': max_val,
                'samples': len(caps)
            })
            
            # Check for significant variations
            if range_val > 1.0:
                print(f"  ⚠️  SIGNIFICANT VARIATION! Range = {range_val:.3f} pF")
                # Find samples with large deviations
                for d in data:
                    if d['row'] == row and d['col'] == col:
                        dev = abs(d['cap'] - mean_val)
                        if dev > 0.5:
                            print(f"    Time {d['timestamp']:.2f}s: {d['cap']:.3f} pF "
                                  f"(deviation: {d['cap'] - mean_val:+.3f} pF)")
    
    # Temporal analysis
    print(f"\n{'='*60}")
    print("TEMPORAL ANALYSIS")
    print(f"{'='*60}")
    
    timestamps = [d['timestamp'] for d in data]
    time_range = max(timestamps) - min(timestamps)
    print(f"Duration: {time_range:.2f}s")
    print(f"Time range: {min(timestamps):.2f}s - {max(timestamps):.2f}s")
    
    # Divide into segments
    num_segments = 5
    segment_size = time_range / num_segments
    print(f"\nDividing into {num_segments} time segments:")
    
    for i in range(num_segments):
        t_start = min(timestamps) + i * segment_size
        t_end = min(timestamps) + (i+1) * segment_size
        segment_caps = [d['cap'] for d in data if t_start <= d['timestamp'] < t_end]
        
        if len(segment_caps) > 0:
            print(f"  Segment {i+1} [{t_start:.1f}s - {t_end:.1f}s]: "
                  f"mean={statistics.mean(segment_caps):.3f} pF, "
                  f"std={statistics.stdev(segment_caps) if len(segment_caps) > 1 else 0:.3f} pF, "
                  f"range=[{min(segment_caps):.3f}, {max(segment_caps):.3f}] pF, "
                  f"samples={len(segment_caps)}")
    
    # Node variation ranking
    print(f"\n{'='*60}")
    print("NODE VARIATION RANKING (Top 10)")
    print(f"{'='*60}")
    
    node_stats.sort(key=lambda x: x['range'], reverse=True)
    for i, ns in enumerate(node_stats[:10]):
        print(f"  {i+1}. Node {ns['node']}: range={ns['range']:.3f} pF, "
              f"std={ns['std']:.3f} pF, mean={ns['mean']:.3f} pF")
    
    # Recommendations
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print(f"{'='*60}")
    
    max_range = max([ns['range'] for ns in node_stats]) if node_stats else 0
    mean_range = statistics.mean([ns['range'] for ns in node_stats]) if node_stats else 0
    
    if max_range < 0.5:
        print("⚠️  VERY LOW VARIATION: All nodes show < 0.5 pF variation")
        print("   Possible issues:")
        print("   - No touches occurred during recording")
        print("   - Baseline was collected while touching (baseline = touch state)")
        print("   - Hardware not properly connected")
        print("   - Sensor sensitivity too low")
        print("   Solutions:")
        print("   - Re-collect baseline with sensor untouched")
        print("   - Check hardware connections for 4 nodes")
        print("   - Try touching nodes during recording")
        print("   - Lower detection threshold in code")
    elif max_range < 2.0:
        print("⚠️  LOW VARIATION: Maximum variation is < 2.0 pF")
        print("   - Small capacitance changes detected")
        print("   - May need to:")
        print("     • Lower detection threshold (currently 0.005 = 0.5%)")
        print("     • Increase touch force/proximity")
        print("     • Check if conductive yarn is making good contact")
    else:
        print(f"✓ SIGNIFICANT VARIATIONS DETECTED")
        print(f"   - Maximum variation: {max_range:.3f} pF")
        print(f"   - Mean variation: {mean_range:.3f} pF")
        print("   - Data looks good for touch detection")
    
    # Check frame completeness
    print(f"\n{'='*60}")
    print("FRAME COMPLETENESS")
    print(f"{'='*60}")
    
    # Group by timestamp (frames)
    frames = defaultdict(list)
    for d in data:
        frames[d['timestamp']].append(d)
    
    complete_frames = sum(1 for f in frames.values() if len(f) == 64)
    incomplete_frames = sum(1 for f in frames.values() if len(f) != 64)
    
    print(f"Total frames (unique timestamps): {len(frames)}")
    print(f"Complete frames (64 samples): {complete_frames}")
    print(f"Incomplete frames: {incomplete_frames}")
    
    if incomplete_frames > 0:
        print("⚠️  Incomplete frames detected!")
        frame_sizes = defaultdict(int)
        for f in frames.values():
            frame_sizes[len(f)] += 1
        print(f"   Frame size distribution: {dict(frame_sizes)}")
    
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Find most recent CSV file
        import glob
        csv_files = sorted(glob.glob("../data/*_raw_realtime_cap_data.csv"), reverse=True)
        if csv_files:
            csv_file = csv_files[0]
            print(f"No file specified. Using most recent: {os.path.basename(csv_file)}")
        else:
            print("Error: No CSV files found and no file specified.")
            print("Usage: python debug_csv.py <csv_file>")
            sys.exit(1)
    else:
        csv_file = sys.argv[1]
    
    analyze_csv(csv_file)
