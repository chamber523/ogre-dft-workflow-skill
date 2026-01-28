#!/usr/bin/env python3
"""
NPY File Creation Script for DFT Calculations

This script creates NumPy arrays from extracted DFT energies,
suitable for further analysis and plotting.

Usage:
    python 5_create_npy.py <calculations_directory> [options]

Options:
    --csv-file FILE        : Use specific CSV file instead of auto-detection
    --output-name NAME     : Output filename (default: energies.npy)
    --fill-value VALUE     : Value for failed calculations (default: NaN)
    --energy-type TYPE     : Energy type: 'sigma0' or 'free' (default: sigma0)
    --verbose              : Show detailed output

Author: DFT Workflow Assistant
Last Updated: October 2025
"""

import os
import sys
import argparse
import re
from datetime import datetime
import glob

try:
    import numpy as np
except ImportError:
    print("❌ Error: numpy is required but not installed")
    print("Install with: pip install numpy")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("❌ Error: pandas is required but not installed")
    print("Install with: pip install pandas")
    sys.exit(1)


def extract_energy_from_outcar(outcar_path, energy_type='sigma0'):
    """
    Extract final energy from OUTCAR file.
    
    Args:
        outcar_path (str): Path to OUTCAR file
        energy_type (str): 'sigma0' for sigma->0 energy, 'free' for free energy
    
    Returns:
        float or None: Extracted energy in eV, None if extraction failed
    """
    try:
        if not os.path.exists(outcar_path):
            return None
        
        # Check if file is empty or too small
        if os.path.getsize(outcar_path) < 1000:  # Less than 1KB
            return None
        
        with open(outcar_path, 'r') as f:
            content = f.read()
        
        # Check if calculation completed successfully
        if "reached required accuracy" not in content:
            return None
        
        # Extract energy based on type
        if energy_type == 'sigma0':
            # Look for "energy(sigma->0)" - more accurate for single-point calculations
            pattern = r'energy\(sigma->0\)\s*=\s*([-+]?\d+\.\d+)'
            matches = re.findall(pattern, content)
            if matches:
                return float(matches[-1])  # Take the last occurrence
        
        # Fallback to free energy
        pattern = r'free  energy   TOTEN\s*=\s*([-+]?\d+\.\d+)\s*eV'
        matches = re.findall(pattern, content)
        if matches:
            return float(matches[-1])  # Take the last occurrence
        
        return None
    
    except Exception as e:
        return None


def find_latest_csv(directory):
    """
    Find the most recent energy CSV file in the directory.
    
    Args:
        directory (str): Directory to search
    
    Returns:
        str or None: Path to latest CSV file, None if not found
    """
    # Look for energy CSV files
    patterns = [
        'energies_*.csv',
        '*energies*.csv',
        '*_energies_*.csv'
    ]
    
    csv_files = []
    for pattern in patterns:
        csv_files.extend(glob.glob(os.path.join(directory, pattern)))
    
    if not csv_files:
        return None
    
    # Sort by modification time, most recent first
    csv_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    return csv_files[0]


def create_energies_array_from_csv(csv_file, fill_value=np.nan):
    """
    Create energies array from CSV file.
    
    Args:
        csv_file (str): Path to CSV file
        fill_value: Value to use for missing/failed calculations
    
    Returns:
        tuple: (energies_array, metadata_dict)
    """
    try:
        df = pd.read_csv(csv_file)
        
        # Ensure we have the required columns
        # Check for energy column (support multiple naming conventions)
        energy_col = None
        for col in ['Energy_eV', 'Energy_without_entropy_eV', 'Energy_sigma_0_eV']:
            if col in df.columns:
                energy_col = col
                break
        
        if energy_col is None:
            raise ValueError("CSV file must contain energy column (Energy_eV, Energy_without_entropy_eV, or Energy_sigma_0_eV)")
        
        # Sort by index if available
        if 'Index' in df.columns and df['Index'].notna().any():
            df = df.sort_values('Index')
            max_index = int(df['Index'].max())
            
            # Create array with proper size
            energies = np.full(max_index + 1, fill_value)
            
            # Fill in the energies
            for _, row in df.iterrows():
                if pd.notna(row['Index']) and pd.notna(row[energy_col]):
                    idx = int(row['Index'])
                    energies[idx] = row[energy_col]
        else:
            # No index column, just use the order in CSV
            energies = df[energy_col].fillna(fill_value).values
        
        # Create metadata
        valid_energies = energies[~np.isnan(energies)]
        metadata = {
            'total_calculations': len(energies),
            'successful_extractions': len(valid_energies),
            'failed_extractions': len(energies) - len(valid_energies),
            'min_energy': np.min(valid_energies) if len(valid_energies) > 0 else None,
            'max_energy': np.max(valid_energies) if len(valid_energies) > 0 else None,
            'mean_energy': np.mean(valid_energies) if len(valid_energies) > 0 else None,
            'std_energy': np.std(valid_energies) if len(valid_energies) > 0 else None,
            'creation_date': datetime.now().isoformat(),
            'source_csv': os.path.basename(csv_file)
        }
        
        return energies, metadata
    
    except Exception as e:
        raise Exception(f"Failed to process CSV file {csv_file}: {str(e)}")


def create_energies_array_direct(calc_dir, energy_type='sigma0', fill_value=np.nan):
    """
    Create energies array directly from calculation directories.
    
    Args:
        calc_dir (str): Calculations directory
        energy_type (str): Energy type to extract
        fill_value: Value to use for missing/failed calculations
    
    Returns:
        tuple: (energies_array, metadata_dict)
    """
    # Find calculation directories
    calc_dirs = []
    for item in os.listdir(calc_dir):
        item_path = os.path.join(calc_dir, item)
        if os.path.isdir(item_path) and item.startswith('calc_'):
            calc_dirs.append(item_path)
    
    if not calc_dirs:
        raise Exception("No calculation directories found")
    
    # Extract indices and energies
    calc_data = []
    for calc_path in calc_dirs:
        calc_name = os.path.basename(calc_path)
        
        # Extract index
        try:
            index = int(calc_name.split('_')[1])
        except:
            continue
        
        # Extract energy
        outcar_path = os.path.join(calc_path, 'OUTCAR')
        energy = extract_energy_from_outcar(outcar_path, energy_type)
        
        calc_data.append((index, energy))
    
    # Sort by index
    calc_data.sort(key=lambda x: x[0])
    
    # Create array
    if calc_data:
        max_index = max(calc_data, key=lambda x: x[0])[0]
        energies = np.full(max_index + 1, fill_value)
        
        successful = 0
        for index, energy in calc_data:
            if energy is not None:
                energies[index] = energy
                successful += 1
    else:
        energies = np.array([])
        successful = 0
    
    # Create metadata
    valid_energies = energies[~np.isnan(energies)]
    metadata = {
        'total_calculations': len(energies),
        'successful_extractions': successful,
        'failed_extractions': len(energies) - successful,
        'min_energy': np.min(valid_energies) if len(valid_energies) > 0 else None,
        'max_energy': np.max(valid_energies) if len(valid_energies) > 0 else None,
        'mean_energy': np.mean(valid_energies) if len(valid_energies) > 0 else None,
        'std_energy': np.std(valid_energies) if len(valid_energies) > 0 else None,
        'creation_date': datetime.now().isoformat(),
        'source': 'direct_extraction'
    }
    
    return energies, metadata


def main():
    parser = argparse.ArgumentParser(
        description="Create NumPy arrays from DFT calculation energies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python 5_create_npy.py ./calculations
    python 5_create_npy.py ./calculations --csv-file energies_20241027.csv
    python 5_create_npy.py ./calculations --output-name pes_energies.npy
    python 5_create_npy.py ./calculations --fill-value -999.0
        """
    )
    
    parser.add_argument("calculations_dir", 
                       help="Directory containing calculation subdirectories")
    parser.add_argument("--csv-file", 
                       help="Use specific CSV file instead of auto-detection")
    parser.add_argument("--output-name", default="energies.npy",
                       help="Output filename (default: energies.npy)")
    parser.add_argument("--fill-value", type=float, default=np.nan,
                       help="Value for failed calculations (default: NaN)")
    parser.add_argument("--energy-type", choices=['sigma0', 'free'], default='sigma0',
                       help="Energy type to extract (default: sigma0)")
    parser.add_argument("--verbose", action="store_true",
                       help="Show detailed output")
    
    args = parser.parse_args()
    
    # Validate calculations directory
    if not os.path.isdir(args.calculations_dir):
        print(f"❌ Error: Calculations directory not found: {args.calculations_dir}")
        sys.exit(1)
    
    print("=" * 80)
    print("NPY FILE CREATION SCRIPT")
    print("=" * 80)
    print(f"📁 Calculations directory: {args.calculations_dir}")
    print(f"📄 Output file: {args.output_name}")
    print(f"🔢 Fill value: {args.fill_value}")
    print(f"⚡ Energy type: {args.energy_type}")
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # Determine data source
        if args.csv_file:
            if not os.path.exists(args.csv_file):
                print(f"❌ Error: CSV file not found: {args.csv_file}")
                sys.exit(1)
            csv_file = args.csv_file
            print(f"📊 Using specified CSV file: {csv_file}")
        else:
            # Try to find latest CSV file
            csv_file = find_latest_csv(args.calculations_dir)
            if csv_file:
                print(f"📊 Found CSV file: {os.path.basename(csv_file)}")
            else:
                print("📊 No CSV file found, extracting directly from OUTCAR files")
        
        # Create energies array
        if csv_file and os.path.exists(csv_file):
            print("🔄 Creating array from CSV file...")
            energies, metadata = create_energies_array_from_csv(csv_file, args.fill_value)
        else:
            print("🔄 Creating array from direct extraction...")
            energies, metadata = create_energies_array_direct(
                args.calculations_dir, args.energy_type, args.fill_value
            )
        
        print()
        print("📊 Array Statistics:")
        print(f"   Shape: {energies.shape}")
        print(f"   Dtype: {energies.dtype}")
        print(f"   Total calculations: {metadata['total_calculations']}")
        print(f"   Successful extractions: {metadata['successful_extractions']}")
        print(f"   Failed extractions: {metadata['failed_extractions']}")
        
        if metadata['successful_extractions'] > 0:
            print()
            print("📈 Energy Statistics (eV):")
            print(f"   Min: {metadata['min_energy']:.6f}")
            print(f"   Max: {metadata['max_energy']:.6f}")
            print(f"   Mean: {metadata['mean_energy']:.6f}")
            print(f"   Std: {metadata['std_energy']:.6f}")
        
        # Save NPY file
        output_path = os.path.join(args.calculations_dir, args.output_name)
        np.save(output_path, energies)
        print()
        print(f"✅ Successfully saved: {output_path}")
        
        # Save metadata
        metadata_file = output_path.replace('.npy', '_metadata.txt')
        with open(metadata_file, 'w') as f:
            f.write("NPY File Metadata\\n")
            f.write("=" * 50 + "\\n")
            for key, value in metadata.items():
                f.write(f"{key}: {value}\\n")
        
        print(f"📄 Metadata saved: {metadata_file}")
        
        # Verify the file
        print()
        print("🔍 Verifying saved file...")
        try:
            loaded_energies = np.load(output_path)
            if np.array_equal(energies, loaded_energies, equal_nan=True):
                print("✅ File verification successful!")
            else:
                print("❌ File verification failed!")
                sys.exit(1)
        except Exception as e:
            print(f"❌ File verification error: {str(e)}")
            sys.exit(1)
        
        # Show sample data
        if args.verbose and len(energies) > 0:
            print()
            print("🔍 Sample data:")
            n_show = min(10, len(energies))
            for i in range(n_show):
                status = "✅" if not np.isnan(energies[i]) else "❌"
                print(f"   calc_{i:04d}: {energies[i]:.6f} eV {status}")
            
            if len(energies) > n_show:
                print(f"   ... and {len(energies) - n_show} more")
        
        print()
        print("💡 Usage examples:")
        print(f"   import numpy as np")
        print(f"   energies = np.load('{args.output_name}')")
        print(f"   print(f'Min energy: {{np.nanmin(energies):.6f}} eV')")
        print(f"   print(f'Max energy: {{np.nanmax(energies):.6f}} eV')")
        
        print("=" * 80)
        print("NPY FILE CREATION COMPLETE")
        print("=" * 80)
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
