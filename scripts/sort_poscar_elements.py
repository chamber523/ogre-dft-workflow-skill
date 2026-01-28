#!/usr/bin/env python3
"""
Sort POSCAR files to group atoms by element type.

Converts: Nb Sn Nb Sn Nb Sn ... -> Nb Nb ... Sn Sn ...
Or:      Pb Se Pb Se Pb Se ... -> Pb Pb ... Se Se ...
"""

import os
import sys
from pymatgen.core import Structure
from pathlib import Path

def sort_poscar(input_file, output_file=None):
    """
    Read POSCAR and rewrite with atoms grouped by element.
    
    Args:
        input_file: Path to input POSCAR
        output_file: Path to output POSCAR (default: overwrite input)
    """
    if output_file is None:
        output_file = input_file
    
    # Read structure
    structure = Structure.from_file(input_file)
    
    # Sort by element (pymatgen automatically groups by species)
    structure = structure.get_sorted_structure()
    
    # Write sorted structure
    structure.to(filename=str(output_file), fmt='poscar')
    
    # Get element counts
    composition = structure.composition
    elements = [str(el) for el in composition.elements]
    counts = [int(composition[el]) for el in composition.elements]
    
    print(f"  {Path(input_file).name}: {' '.join(f'{el}{n}' for el, n in zip(elements, counts))}")
    
    return structure

def get_reference_calculations_dir():
    """Get the reference calculations directory."""
    # Get script directory
    script_dir = Path(__file__).parent.absolute()
    # Go up to workflow, then up to DFT, then to reference/calculations
    workflow_dir = script_dir.parent
    dft_dir = workflow_dir.parent
    calc_dir = dft_dir / "reference" / "calculations"
    return calc_dir

def main():
    # Get calculations directory
    calc_dir = get_reference_calculations_dir()
    
    print("Sorting POSCAR files by element...")
    print()
    
    for i in range(4):
        calc_name = f"calc_{i:04d}"
        poscar_path = calc_dir / calc_name / "POSCAR"
        
        if poscar_path.exists():
            sort_poscar(poscar_path)
        else:
            print(f"  Warning: {poscar_path} not found")
    
    print()
    print("All POSCAR files sorted successfully!")
    print("Each element is now grouped together.")

if __name__ == "__main__":
    main()
