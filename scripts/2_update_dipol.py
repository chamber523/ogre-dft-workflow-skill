#!/usr/bin/env python3
"""
DIPOL Update Script for DFT Calculations

This script calculates the mass-weighted center of mass for each structure
and updates the DIPOL tag in INCAR files accordingly.

Usage:
    python 2_update_dipol.py <calculations_directory> [options]

Options:
    --dry-run       : Show what would be changed without making changes
    --use-geom      : Use geometric center instead of mass-weighted center
    --verbose       : Show detailed output
    --force         : Overwrite existing DIPOL values without confirmation

Author: DFT Workflow Assistant
Last Updated: October 2025
"""

import os
import sys
import argparse
import re
from datetime import datetime
import numpy as np

try:
    from pymatgen.io.vasp.inputs import Poscar
except ImportError:
    print("❌ Error: pymatgen is required but not installed")
    print("Install with: pip install pymatgen")
    sys.exit(1)


def get_dipol(poscar_file, use_mass_weight=True):
    """
    Calculate DIPOL value from POSCAR file.
    
    Args:
        poscar_file (str): Path to POSCAR file
        use_mass_weight (bool): Use mass-weighted center (True) or geometric center (False)
    
    Returns:
        str: DIPOL value as space-separated coordinates
    """
    try:
        poscar = Poscar.from_file(poscar_file, check_for_POTCAR=False)
        structure = poscar.structure
        
        # Get fractional coordinates
        frac_coords = structure.frac_coords
        
        # Calculate weights
        if use_mass_weight:
            weights = [s.species.weight for s in structure]
        else:
            weights = np.ones(len(structure))
        
        # Calculate weighted center
        center = np.average(frac_coords, axis=0, weights=weights)
        
        # Format to 5 decimal places
        dipol = " ".join([f"{x:.5f}" for x in center])
        
        return dipol
    
    except Exception as e:
        raise Exception(f"Failed to calculate DIPOL from {poscar_file}: {str(e)}")


def update_incar_dipol(incar_path, dipol_value, force=False):
    """
    Update DIPOL value in INCAR file.
    
    Args:
        incar_path (str): Path to INCAR file
        dipol_value (str): New DIPOL value
        force (bool): Overwrite without confirmation
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Read INCAR file
        with open(incar_path, 'r') as f:
            lines = f.readlines()
        
        # Find and update DIPOL line (must match ^DIPOL exactly, not IDIPOL)
        updated = False
        for i, line in enumerate(lines):
            # Look for DIPOL line (not commented out, not IDIPOL or LDIPOL)
            if line.strip().startswith("DIPOL =") and not line.strip().startswith("#"):
                # Extract comment if present
                comment_part = ""
                if '#' in line:
                    comment_part = line[line.index('#'):]
                else:
                    comment_part = "   # Defining the location of the center of the dipole moment (center of mass)"
                
                # Check if it's a placeholder or needs update
                old_dipol = line.split('=')[1].split('#')[0].strip() if '=' in line else ""
                
                if not force and old_dipol and "PLACEHOLDER" not in old_dipol:
                    print(f"    ⚠️  DIPOL already set to: {old_dipol}")
                    print(f"    🔄 New value would be: {dipol_value}")
                    response = input("    ❓ Update anyway? (y/N): ").strip().lower()
                    if response not in ['y', 'yes']:
                        print("    ⏭️  Skipping update")
                        return False
                
                # Update the line
                lines[i] = f"DIPOL = {dipol_value}   {comment_part}\n"
                updated = True
                break
        
        if not updated:
            print(f"    ⚠️  Warning: DIPOL line not found in {incar_path}")
            print(f"    ➕ Adding DIPOL line to end of file")
            lines.append(f"DIPOL = {dipol_value}   # Defining the location of the center of the dipole moment (center of mass)\n")
            updated = True
        
        # Write updated INCAR
        with open(incar_path, 'w') as f:
            f.writelines(lines)
        
        return updated
    
    except Exception as e:
        print(f"    ❌ Error updating INCAR: {str(e)}")
        return False


def ensure_dipol_tags(incar_path):
    """
    Ensure IDIPOL and LDIPOL tags are present in INCAR.
    
    Args:
        incar_path (str): Path to INCAR file
    
    Returns:
        bool: True if tags were added/verified, False on error
    """
    try:
        with open(incar_path, 'r') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Check for required tags
        has_idipol = any('IDIPOL' in line and not line.strip().startswith('#') for line in lines)
        has_ldipol = any('LDIPOL' in line and not line.strip().startswith('#') for line in lines)
        
        # Add missing tags
        if not has_idipol:
            lines.append("IDIPOL = 3      # Calculates the dipole along the z-axis")
        
        if not has_ldipol:
            lines.append("LDIPOL = True   # Adding dipole corrections")
        
        # Write back if changes were made
        if not has_idipol or not has_ldipol:
            with open(incar_path, 'w') as f:
                f.write('\n'.join(lines))
            return True
        
        return True
    
    except Exception as e:
        print(f"    ❌ Error ensuring DIPOL tags: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Update DIPOL values in DFT calculation INCAR files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python 2_update_dipol.py ./calculations
    python 2_update_dipol.py ./calculations --dry-run
    python 2_update_dipol.py ./calculations --use-geom --verbose
    python 2_update_dipol.py ./calculations --force
        """
    )
    
    parser.add_argument("calculations_dir", 
                       help="Directory containing calculation subdirectories")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be changed without making changes")
    parser.add_argument("--use-geom", action="store_true",
                       help="Use geometric center instead of mass-weighted center")
    parser.add_argument("--verbose", action="store_true",
                       help="Show detailed output")
    parser.add_argument("--force", action="store_true",
                       help="Overwrite existing DIPOL values without confirmation")
    
    args = parser.parse_args()
    
    # Validate calculations directory
    if not os.path.isdir(args.calculations_dir):
        print(f"❌ Error: Calculations directory not found: {args.calculations_dir}")
        sys.exit(1)
    
    print("=" * 80)
    print("DIPOL UPDATE SCRIPT")
    print("=" * 80)
    print(f"📁 Calculations directory: {args.calculations_dir}")
    print(f"🧮 Center calculation: {'Geometric' if args.use_geom else 'Mass-weighted'}")
    print(f"🔍 Mode: {'DRY RUN' if args.dry_run else 'UPDATE'}")
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Find calculation directories
    calc_dirs = []
    for item in os.listdir(args.calculations_dir):
        item_path = os.path.join(args.calculations_dir, item)
        if os.path.isdir(item_path) and item.startswith('calc_'):
            calc_dirs.append(item_path)
    
    calc_dirs.sort()
    
    if not calc_dirs:
        print("❌ No calculation directories found (looking for calc_* directories)")
        sys.exit(1)
    
    print(f"📊 Found {len(calc_dirs)} calculation directories")
    print()
    
    # Initialize counters
    successful_updates = 0
    failed_updates = 0
    skipped_updates = 0
    
    # Process each calculation directory
    for calc_dir in calc_dirs:
        calc_name = os.path.basename(calc_dir)
        print(f"📂 Processing {calc_name}...")
        
        # Check for required files
        poscar_path = os.path.join(calc_dir, "POSCAR")
        incar_path = os.path.join(calc_dir, "INCAR")
        
        if not os.path.exists(poscar_path):
            print(f"  ❌ POSCAR not found, skipping")
            skipped_updates += 1
            continue
        
        if not os.path.exists(incar_path):
            print(f"  ❌ INCAR not found, skipping")
            skipped_updates += 1
            continue
        
        try:
            # Calculate DIPOL value
            dipol_value = get_dipol(poscar_path, use_mass_weight=not args.use_geom)
            
            if args.verbose:
                print(f"  🧮 Calculated DIPOL: {dipol_value}")
            
            if args.dry_run:
                print(f"  🔍 Would update DIPOL to: {dipol_value}")
                successful_updates += 1
            else:
                # Update INCAR file
                if update_incar_dipol(incar_path, dipol_value, args.force):
                    # Ensure IDIPOL and LDIPOL tags are present
                    if ensure_dipol_tags(incar_path):
                        print(f"  ✅ Updated DIPOL: {dipol_value}")
                        successful_updates += 1
                    else:
                        print(f"  ❌ Failed to ensure DIPOL tags")
                        failed_updates += 1
                else:
                    print(f"  ❌ Failed to update DIPOL")
                    failed_updates += 1
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            failed_updates += 1
    
    print()
    print("=" * 80)
    print("DIPOL UPDATE COMPLETE")
    print("=" * 80)
    print(f"✅ Successful updates: {successful_updates}")
    print(f"❌ Failed updates: {failed_updates}")
    print(f"⏭️  Skipped: {skipped_updates}")
    print(f"📊 Total processed: {len(calc_dirs)}")
    
    print("=" * 80)
    
    if failed_updates > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
