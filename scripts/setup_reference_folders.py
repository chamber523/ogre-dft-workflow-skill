#!/usr/bin/env python3
"""
Reference Folder Setup Script for DFT Calculations

This script creates calculation directories in the reference folder
with the correct ordering for energies.npy extraction.

Reference Calculations for Interface Energy:
--------------------------------------------
These 4 calculations are needed to compute interface adhesion energy:

calc_0000: E1 = Film slab energy
  - POSCAR: POSCAR_film_slab
  - Single film slab

calc_0001: E2 = Substrate slab energy  
  - POSCAR: POSCAR_sub_slab
  - Single substrate slab

calc_0002: E3 = Film double slab energy
  - POSCAR: POSCAR_film_double_slab
  - Double film slab (for surface energy correction)

calc_0003: E4 = Substrate double slab energy
  - POSCAR: POSCAR_sub_double_slab
  - Double substrate slab (for surface energy correction)

Interface Energy Formula:
-------------------------
E_interface = E_total - (E1 + E2) + 0.5*(E3 + E4)

Where:
  E_total = Total interface energy (from PES/zdist)
  E1, E2 = Single slab energies
  E3, E4 = Double slab energies (surface correction)

Usage:
    python setup_reference_folders.py [reference_directory] [options]

Options:
    --templates-dir DIR    : Directory containing templates (default: ../templates)
    --dry-run             : Preview without creating directories
    --verbose             : Show detailed output

Author: DFT Workflow Assistant
Last Updated: October 2025
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# Reference file mapping
REFERENCE_FILES = {
    'E1_film': 'POSCAR_film_slab',
    'E2_substrate': 'POSCAR_sub_slab',
    'E3_film_double_slab': 'POSCAR_film_double_slab',
    'E4_substrate_double_slab': 'POSCAR_sub_double_slab'
}

# Directory mapping (index: description)
DIRECTORY_MAPPING = {
    0: 'E1_film',
    1: 'E2_substrate',
    2: 'E3_film_double_slab',
    3: 'E4_substrate_double_slab'
}


def get_script_directory():
    """Get the directory where this script is located."""
    return os.path.dirname(os.path.abspath(__file__))


def find_reference_directory():
    """Find the reference directory relative to the workflow directory."""
    script_dir = get_script_directory()
    workflow_dir = os.path.dirname(script_dir)
    dft_dir = os.path.dirname(workflow_dir)
    reference_dir = os.path.join(dft_dir, 'reference')
    return reference_dir


def setup_reference_calculations(reference_dir, templates_dir, dry_run=False, verbose=False):
    """
    Setup reference calculation directories with correct ordering.
    
    Args:
        reference_dir (str): Reference directory path
        templates_dir (str): Templates directory path
        dry_run (bool): Preview without creating directories
        verbose (bool): Show detailed output
    """
    # Validate reference directory
    if not os.path.isdir(reference_dir):
        raise Exception(f"Reference directory not found: {reference_dir}")
    
    # Validate poscars directory
    poscars_dir = os.path.join(reference_dir, 'poscars')
    if not os.path.isdir(poscars_dir):
        raise Exception(f"POSCARs directory not found: {poscars_dir}")
    
    # Validate templates directory
    if not os.path.isdir(templates_dir):
        raise Exception(f"Templates directory not found: {templates_dir}")
    
    # Check required template files
    required_templates = ['POTCAR', 'INCAR_template', 'KPOINTS_template', 'job_template.slurm']
    for template_file in required_templates:
        template_path = os.path.join(templates_dir, template_file)
        if not os.path.exists(template_path):
            raise Exception(f"Required template file not found: {template_path}")
    
    # Create calculations directory
    calculations_dir = os.path.join(reference_dir, 'calculations')
    
    if not dry_run:
        os.makedirs(calculations_dir, exist_ok=True)
    
    if verbose:
        print(f"📁 Calculations directory: {calculations_dir}")
        if dry_run:
            print("   (dry-run mode: directories will not be created)")
    
    # Setup each reference calculation
    successful_setups = 0
    failed_setups = 0
    
    for index, key in DIRECTORY_MAPPING.items():
        calc_name = f"calc_{index:04d}"
        calc_path = os.path.join(calculations_dir, calc_name)
        
        # Get POSCAR filename
        poscar_filename = REFERENCE_FILES[key]
        poscar_path = os.path.join(poscars_dir, poscar_filename)
        
        if not os.path.exists(poscar_path):
            print(f"⚠️  Warning: POSCAR not found: {poscar_filename}")
            failed_setups += 1
            continue
        
        if verbose:
            print(f"\n📁 Setting up {calc_name} ({key})...")
            print(f"   POSCAR: {poscar_filename}")
        
        if not dry_run:
            # Create calculation directory
            os.makedirs(calc_path, exist_ok=True)
            
            # Copy POSCAR
            shutil.copy2(poscar_path, os.path.join(calc_path, 'POSCAR'))
            
            # Copy POTCAR
            potcar_source = os.path.join(templates_dir, 'POTCAR')
            shutil.copy2(potcar_source, os.path.join(calc_path, 'POTCAR'))
            
            # Copy KPOINTS (from template)
            kpoints_source = os.path.join(templates_dir, 'KPOINTS_template')
            shutil.copy2(kpoints_source, os.path.join(calc_path, 'KPOINTS'))
            
            # Copy INCAR (from template)
            incar_source = os.path.join(templates_dir, 'INCAR_template')
            shutil.copy2(incar_source, os.path.join(calc_path, 'INCAR'))
            
            # Copy job.slurm (from template)
            job_source = os.path.join(templates_dir, 'job_template.slurm')
            shutil.copy2(job_source, os.path.join(calc_path, 'job.slurm'))
        
        successful_setups += 1
        
        if verbose:
            print(f"   ✅ {calc_name} setup complete")
    
    return successful_setups, failed_setups


def main():
    parser = argparse.ArgumentParser(
        description="Setup reference calculation directories with correct ordering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python setup_reference_folders.py
    python setup_reference_folders.py /path/to/reference
    python setup_reference_folders.py --templates-dir /path/to/templates
    python setup_reference_folders.py --dry-run --verbose
        """
    )
    
    parser.add_argument("reference_dir", nargs='?', default=None,
                       help="Reference directory (default: auto-detect)")
    parser.add_argument("--templates-dir", default=None,
                       help="Templates directory (default: ../templates)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview without creating directories")
    parser.add_argument("--verbose", action="store_true",
                       help="Show detailed output")
    
    args = parser.parse_args()
    
    # Determine reference directory
    if args.reference_dir:
        reference_dir = os.path.abspath(args.reference_dir)
    else:
        reference_dir = find_reference_directory()
    
    # Determine templates directory
    if args.templates_dir:
        templates_dir = os.path.abspath(args.templates_dir)
    else:
        script_dir = get_script_directory()
        workflow_dir = os.path.dirname(script_dir)
        templates_dir = os.path.join(workflow_dir, 'templates')
    
    print("=" * 80)
    print("REFERENCE FOLDER SETUP SCRIPT")
    print("=" * 80)
    print(f"📁 Reference directory: {reference_dir}")
    print(f"📁 Templates directory: {templates_dir}")
    if args.dry_run:
        print("🔍 Mode: DRY-RUN (preview only)")
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Display directory mapping
    print("\n📋 Directory Mapping:")
    print("   calc_0000 -> E1 = Film slab energy (POSCAR_film_slab)")
    print("   calc_0001 -> E2 = Substrate slab energy (POSCAR_sub_slab)")
    print("   calc_0002 -> E3 = Film double slab energy (POSCAR_film_double_slab)")
    print("   calc_0003 -> E4 = Substrate double slab energy (POSCAR_sub_double_slab)")
    print("\n💡 This ordering ensures energies.npy is structured as: [E1, E2, E3, E4]")
    print("\n📐 Interface Energy Formula:")
    print("   E_interface = E_total - (E1 + E2) + 0.5*(E3 + E4)")
    print()
    
    try:
        successful, failed = setup_reference_calculations(
            reference_dir, templates_dir, args.dry_run, args.verbose
        )
        
        print()
        print("=" * 80)
        print("SETUP SUMMARY")
        print("=" * 80)
        print(f"✅ Successful setups: {successful}")
        if failed > 0:
            print(f"❌ Failed setups: {failed}")
        
        if args.dry_run:
            print("\n💡 This was a dry-run. Use without --dry-run to create directories.")
        else:
            print(f"\n✅ Reference calculations directory created: {os.path.join(reference_dir, 'calculations')}")
            print("\n💡 Next steps:")
            print("   1. Run sort_poscar_elements.py to sort POSCAR elements (if needed)")
            print("   2. Run 2_update_dipol.py to update DIPOL values")
            print("   3. Run 3_submit_jobs.sh to submit calculations")
            print("   4. After completion, extract energies to create energies.npy")
            print("   5. Use energies.npy with interface energy formula:")
            print("      E_interface = E_total - (E1 + E2) + 0.5*(E3 + E4)")
        
        print("=" * 80)
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

