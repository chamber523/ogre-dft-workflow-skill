#!/usr/bin/env python3
"""
Energy extraction script - extracts energies from OUTCAR files
Automatically detects number of calculations and saves to CSV
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
import re
from datetime import datetime

def extract_energy_from_outcar(outcar_path):
    """
    Extract the final single-point energy from OUTCAR file
    
    Args:
        outcar_path (str): Path to OUTCAR file
    
    Returns:
        dict: Dictionary containing energy information
    """
    result = {
        'energy_without_entropy': None,
        'energy_sigma_0': None,
        'converged': False,
        'electronic_steps': 0,
        'ionic_steps': 0,
        'total_cpu_time': None,
        'error': None
    }
    
    try:
        if not os.path.exists(outcar_path):
            result['error'] = 'OUTCAR not found'
            return result
        
        with open(outcar_path, 'r') as f:
            content = f.read()
        
        # Check convergence
        if 'reached required accuracy' in content:
            result['converged'] = True
        
        # Check if calculation completed successfully
        if 'Total CPU time used' in content:
            cpu_match = re.search(r'Total CPU time used \(sec\):\s*([\d\.]+)', content)
            if cpu_match:
                result['total_cpu_time'] = float(cpu_match.group(1))
        
        # Extract final energies
        # Energy without entropy (most commonly used)
        energy_matches = re.findall(r'energy  without entropy\s*=\s*([-\d\.]+)', content)
        if energy_matches:
            result['energy_without_entropy'] = float(energy_matches[-1])
        
        # Energy at sigma->0
        sigma_matches = re.findall(r'energy\(sigma->0\)\s*=\s*([-\d\.]+)', content)
        if sigma_matches:
            result['energy_sigma_0'] = float(sigma_matches[-1])
        
        # Count electronic and ionic steps
        result['electronic_steps'] = len(re.findall(r'DAV:', content))
        result['ionic_steps'] = len(re.findall(r'POSITION\s+TOTAL-FORCE', content))
        
    except Exception as e:
        result['error'] = str(e)
    
    return result

def main():
    """Main function to extract energies and create Excel file"""
    
    base_dir = Path("calculations")
    results = []
    
    # Dynamically find calculation directories
    calc_dirs = sorted([d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith('calc_')])
    
    print("=" * 80)
    print("ENERGY EXTRACTION")
    print("=" * 80)
    print(f"Extracting single-point energies from {len(calc_dirs)} calculations...")
    print(f"Base directory: {base_dir.absolute()}")
    print(f"Analysis time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Process each calculation
    for calc_dir in calc_dirs:
        calc_name = calc_dir.name
        outcar_path = calc_dir / "OUTCAR"
        
        print(f"Processing {calc_name}...", end=" ")
        
        # Extract energy information
        energy_info = extract_energy_from_outcar(str(outcar_path))
        
        # Extract index from calc_name
        try:
            calc_index = int(calc_name.split('_')[1])
        except:
            calc_index = None
        
        # Prepare result dictionary
        result = {
            'Calculation': calc_name,
            'Index': calc_index,
            'Energy_without_entropy_eV': energy_info['energy_without_entropy'],
            'Energy_sigma_0_eV': energy_info['energy_sigma_0'],
            'Converged': energy_info['converged'],
            'Electronic_steps': energy_info['electronic_steps'],
            'Ionic_steps': energy_info['ionic_steps'],
            'CPU_time_sec': energy_info['total_cpu_time'],
            'Status': 'Success' if energy_info['energy_without_entropy'] is not None else 'Failed',
            'Error': energy_info['error']
        }
        
        results.append(result)
        
        # Print status
        if energy_info['energy_without_entropy'] is not None:
            print(f"✅ Energy: {energy_info['energy_without_entropy']:.6f} eV (Converged: {energy_info['converged']})")
        else:
            print(f"❌ {energy_info['error']}")
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Calculate statistics
    successful_calcs = df[df['Status'] == 'Success']
    failed_calcs = df[df['Status'] == 'Failed']
    
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total calculations processed: {len(df)}")
    print(f"Successful calculations: {len(successful_calcs)}")
    print(f"Failed calculations: {len(failed_calcs)}")
    print(f"Success rate: {len(successful_calcs)/len(df)*100:.1f}%")
    
    if len(successful_calcs) > 0:
        energies = successful_calcs['Energy_without_entropy_eV'].dropna()
        cpu_times = successful_calcs['CPU_time_sec'].dropna()
        
        print(f"\nEnergy Statistics (eV):")
        print(f"  Mean energy: {energies.mean():.6f}")
        print(f"  Min energy:  {energies.min():.6f} (index {energies.idxmin()})")
        print(f"  Max energy:  {energies.max():.6f} (index {energies.idxmax()})")
        print(f"  Std dev:     {energies.std():.6f}")
        print(f"  Range:       {energies.max() - energies.min():.6f}")
        
        if len(cpu_times) > 0:
            print(f"\nComputational Statistics:")
            print(f"  Mean CPU time: {cpu_times.mean():.1f} seconds")
            print(f"  Total CPU time: {cpu_times.sum():.1f} seconds ({cpu_times.sum()/3600:.1f} hours)")
    
    # Save to files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_filename = f"energies_{timestamp}.xlsx"
    csv_filename = f"energies_{timestamp}.csv"
    
    # Try Excel first, fallback to CSV
    try:
        with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
            # Main results sheet
            df.to_excel(writer, sheet_name='All_Energies', index=False)
            
            # Summary statistics sheet
            if len(successful_calcs) > 0:
                summary_data = {
                    'Statistic': ['Total Calculations', 'Successful', 'Failed', 'Success Rate (%)', 
                                 'Mean Energy (eV)', 'Min Energy (eV)', 'Max Energy (eV)', 
                                 'Std Dev (eV)', 'Energy Range (eV)', 'Total CPU Hours'],
                    'Value': [len(df), len(successful_calcs), len(failed_calcs),
                             len(successful_calcs)/len(df)*100,
                             energies.mean(), energies.min(), energies.max(), 
                             energies.std(), energies.max() - energies.min(),
                             cpu_times.sum()/3600 if len(cpu_times) > 0 else 0]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Failed calculations sheet
            if len(failed_calcs) > 0:
                failed_calcs.to_excel(writer, sheet_name='Failed_Calculations', index=False)
        
        print(f"\n✅ Results saved to: {excel_filename}")
        
    except ImportError:
        # Fallback to CSV if Excel modules not available
        print(f"\n⚠️  Excel modules not available, saving to CSV instead...")
        df.to_csv(csv_filename, index=False)
        print(f"✅ Results saved to: {csv_filename}")
        
        # Also save summary statistics
        if len(successful_calcs) > 0:
            summary_data = {
                'Statistic': ['Total Calculations', 'Successful', 'Failed', 'Success Rate (%)', 
                             'Mean Energy (eV)', 'Min Energy (eV)', 'Max Energy (eV)', 
                             'Std Dev (eV)', 'Energy Range (eV)', 'Total CPU Hours'],
                'Value': [len(df), len(successful_calcs), len(failed_calcs),
                         len(successful_calcs)/len(df)*100,
                         energies.mean(), energies.min(), energies.max(), 
                         energies.std(), energies.max() - energies.min(),
                         cpu_times.sum()/3600 if len(cpu_times) > 0 else 0]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_filename = f"summary_{timestamp}.csv"
            summary_df.to_csv(summary_filename, index=False)
            print(f"✅ Summary saved to: {summary_filename}")
    
    print(f"📊 Complete dataset contains {len(df)} calculations")
    
    # Show failed calculations if any
    if len(failed_calcs) > 0:
        print(f"\n⚠️  Failed calculations ({len(failed_calcs)}):")
        for _, row in failed_calcs.iterrows():
            print(f"  {row['Calculation']}: {row['Error']}")
    
    # Check which need to be resubmitted (not converged)
    not_converged = df[~df['Converged'] & (df['Status'] == 'Success')]
    if len(not_converged) > 0:
        print(f"\n⚠️  Calculations with energy but NOT converged ({len(not_converged)}):")
        for _, row in not_converged.iterrows():
            print(f"  {row['Calculation']} - Energy: {row['Energy_without_entropy_eV']:.6f} eV")
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    
    return df

if __name__ == "__main__":
    main()

