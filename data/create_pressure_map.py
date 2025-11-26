"""
Create Pressure Sensing Map for 10122025 Data
Process capacitance data to create pressure maps using a 4x4 contact node mesh
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
import glob
import os

def create_4x4_mesh(spacing=1.0):
    """
    Create a 4x4 mesh of contact nodes with specified spacing
    
    Args:
        spacing: Spacing between nodes in centimeters (default: 1.0 cm)
    
    Returns:
        node_positions: Array of (x, y) positions for 16 nodes
        node_ids: Array of node IDs (0-15)
    """
    # Create 4x4 grid of nodes
    n_nodes_per_side = 4
    node_positions = []
    node_ids = []
    
    for i in range(n_nodes_per_side):
        for j in range(n_nodes_per_side):
            x = j * spacing  # Column position
            y = i * spacing  # Row position
            node_positions.append((x, y))
            node_ids.append(i * n_nodes_per_side + j)
    
    node_positions = np.array(node_positions)
    
    print(f"[INFO] Created {len(node_positions)} nodes in {n_nodes_per_side}x{n_nodes_per_side} grid")
    print(f"[INFO] Spacing: {spacing} cm between nodes")
    print(f"[INFO] Total grid size: {spacing * 3:.1f} cm x {spacing * 3:.1f} cm")
    
    return node_positions, node_ids

def visualize_mesh(node_positions, node_ids, detection_radius=0.5, save_path=None):
    """
    Visualize the 4x4 node mesh with spherical detection areas
    
    Args:
        node_positions: Array of (x, y) positions
        node_ids: Array of node IDs
        detection_radius: Radius of circular detection area for each node in cm (default: 0.5 cm)
        save_path: Optional path to save the figure
    """
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Draw spherical detection areas first (behind nodes)
    for i, (x, y) in enumerate(node_positions):
        circle = plt.Circle((x, y), detection_radius, 
                           facecolor='lightblue', alpha=0.3, edgecolor='blue', 
                           linewidth=1.5, zorder=1)
        ax.add_patch(circle)
    
    # Plot nodes on top
    ax.scatter(node_positions[:, 0], node_positions[:, 1], 
               s=300, c='blue', marker='o', edgecolors='black', linewidths=2, zorder=3)
    
    # Label nodes
    for i, (x, y) in enumerate(node_positions):
        ax.text(x, y, f'N{i}', ha='center', va='center', 
                fontsize=11, fontweight='bold', color='white')
    
    # Draw grid lines
    x_coords = np.unique(node_positions[:, 0])
    y_coords = np.unique(node_positions[:, 1])
    
    for x in x_coords:
        ax.axvline(x, color='gray', linestyle='--', linewidth=0.5, alpha=0.3, zorder=0)
    for y in y_coords:
        ax.axhline(y, color='gray', linestyle='--', linewidth=0.5, alpha=0.3, zorder=0)
    
    ax.set_xlabel('X Position (cm)', fontsize=12)
    ax.set_ylabel('Y Position (cm)', fontsize=12)
    ax.set_title(f'4x4 Contact Node Mesh with Detection Areas\n(Spacing: 1.0 cm, Detection Radius: {detection_radius:.1f} cm)', 
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.2, zorder=0)
    ax.set_aspect('equal')
    
    # Set axis limits with some padding
    margin = 1.0
    ax.set_xlim([node_positions[:, 0].min() - margin, 
                 node_positions[:, 0].max() + margin])
    ax.set_ylim([node_positions[:, 1].min() - margin, 
                 node_positions[:, 1].max() + margin])
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"[INFO] Mesh visualization saved to {save_path}")
    
    plt.show()
    
    return fig

if __name__ == "__main__":
    # Create the 4x4 mesh with 1 cm spacing
    node_positions, node_ids = create_4x4_mesh(spacing=1.0)
    
    # Print node information
    print("\n[INFO] Node positions:")
    for i, (x, y) in enumerate(node_positions):
        print(f"  Node {i:2d}: ({x:.1f}, {y:.1f}) cm")
    
    # Visualize the mesh with spherical detection areas
    print("\n[INFO] Visualizing mesh with detection areas...")
    output_dir = os.path.join(os.path.dirname(__file__), '..')
    save_path = os.path.join(output_dir, '4x4_mesh_layout.png')
    visualize_mesh(node_positions, node_ids, detection_radius=0.5, save_path=save_path)
    
    print("\n[INFO] Mesh creation complete!")

