#!/bin/bash

# DFT Calculation Setup Script
# Usage: ./1_setup_calculations.sh <calculation_type> <poscars_directory> [reference_directory]
# calculation_type: "pes" or "zdist"
# poscars_directory: Directory containing POSCAR files
# reference_directory: Directory containing reference POTCAR, KPOINTS, INCAR, job.slurm (optional)

set -e  # Exit on any error

# Configuration - MODIFY THESE PATHS FOR YOUR SYSTEM
# Get script directory to set relative paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKFLOW_DIR="$(dirname "$SCRIPT_DIR")"
DEFAULT_POTCAR_PATH="$WORKFLOW_DIR/templates/POTCAR"
DEFAULT_KPOINTS_PATH="$WORKFLOW_DIR/templates/KPOINTS_template"
DEFAULT_INCAR_PATH="$WORKFLOW_DIR/templates/INCAR_template"
DEFAULT_JOB_PATH="$WORKFLOW_DIR/templates/job_template.slurm"

# Function to display usage
usage() {
    echo "=============================================================================="
    echo "DFT CALCULATION SETUP SCRIPT"
    echo "=============================================================================="
    echo "Usage: $0 <calculation_type> <poscars_directory> [reference_directory]"
    echo ""
    echo "Arguments:"
    echo "  calculation_type    : 'pes' or 'zdist'"
    echo "  poscars_directory   : Directory containing POSCAR files"
    echo "  reference_directory : Directory with reference files (optional)"
    echo ""
    echo "Reference files needed:"
    echo "  - POTCAR (pseudopotential file)"
    echo "  - KPOINTS (k-point sampling)"
    echo "  - INCAR (calculation parameters)"
    echo "  - job.slurm (SLURM job script)"
    echo ""
    echo "Examples:"
    echo "  $0 pes ./poscars"
    echo "  $0 zdist ./poscars /path/to/reference"
    echo "=============================================================================="
    exit 1
}

# Check arguments
if [ $# -lt 2 ] || [ $# -gt 3 ]; then
    usage
fi

CALC_TYPE="$1"
POSCARS_DIR="$2"
REF_DIR="${3:-}"

# Validate calculation type
if [ "$CALC_TYPE" != "pes" ] && [ "$CALC_TYPE" != "zdist" ]; then
    echo "❌ Error: calculation_type must be 'pes' or 'zdist'"
    usage
fi

# Validate poscars directory
if [ ! -d "$POSCARS_DIR" ]; then
    echo "❌ Error: POSCARS directory not found: $POSCARS_DIR"
    exit 1
fi

echo "=============================================================================="
echo "DFT CALCULATION SETUP - $(echo $CALC_TYPE | tr '[:lower:]' '[:upper:]')"
echo "=============================================================================="
echo "📁 POSCARS directory: $POSCARS_DIR"
echo "📁 Reference directory: ${REF_DIR:-'Using defaults'}"
echo "🕐 Setup started: $(date)"
echo "=============================================================================="

# Set reference file paths
if [ -n "$REF_DIR" ]; then
    POTCAR_SOURCE="$REF_DIR/POTCAR"
    KPOINTS_SOURCE="$REF_DIR/KPOINTS"
    INCAR_SOURCE="$REF_DIR/INCAR"
    JOB_SOURCE="$REF_DIR/job.slurm"
else
    POTCAR_SOURCE="$DEFAULT_POTCAR_PATH"
    KPOINTS_SOURCE="$DEFAULT_KPOINTS_PATH"
    INCAR_SOURCE="$DEFAULT_INCAR_PATH"
    JOB_SOURCE="$DEFAULT_JOB_PATH"
fi

# Verify reference files exist
echo "🔍 Checking reference files..."
for file_path in "$POTCAR_SOURCE" "$KPOINTS_SOURCE" "$INCAR_SOURCE" "$JOB_SOURCE"; do
    if [ ! -f "$file_path" ]; then
        echo "❌ Error: Reference file not found: $file_path"
        exit 1
    fi
    echo "  ✅ Found: $(basename "$file_path")"
done

# Create calculations directory inside the parent of the POSCARS directory
# e.g., if POSCARS_DIR=/path/to/zdist/poscars → CALC_DIR=/path/to/zdist/calculations
CALC_DIR="$(dirname "$POSCARS_DIR")/calculations"
mkdir -p "$CALC_DIR"
echo "Created calculations directory: $CALC_DIR"

# Count POSCAR files
poscar_count=$(find "$POSCARS_DIR" -name "POSCAR*" -type f | wc -l)
echo "📊 Found $poscar_count POSCAR files"

if [ $poscar_count -eq 0 ]; then
    echo "❌ Error: No POSCAR files found in $POSCARS_DIR"
    exit 1
fi

# Setup calculations
echo ""
echo "🚀 Setting up calculation directories..."
echo ""

successful_setups=0
failed_setups=0

# Process each POSCAR file
for poscar_file in "$POSCARS_DIR"/POSCAR*; do
    if [ ! -f "$poscar_file" ]; then
        continue
    fi
    
    # Extract index from filename
    basename_poscar=$(basename -- "$poscar_file")
    if [[ "$basename_poscar" =~ POSCAR_([0-9]+) ]]; then
        index="${BASH_REMATCH[1]}"
        # Convert to decimal to handle octal issue with leading zeros
        index=$((10#$index))
        calc_name=$(printf "calc_%04d" "$index")
    elif [[ "$basename_poscar" == "POSCAR" ]]; then
        calc_name="calc_0000"
    else
        echo "⚠️  Warning: Skipping file with unexpected name: $basename_poscar"
        continue
    fi
    
    calc_path="$CALC_DIR/$calc_name"
    
    echo "📁 Setting up $calc_name..."
    
    # Create calculation directory
    if ! mkdir -p "$calc_path"; then
        echo "  Failed to create directory: $calc_path"
        failed_setups=$((failed_setups + 1))
        continue
    fi
    
    # Copy POSCAR
    if ! cp "$poscar_file" "$calc_path/POSCAR"; then
        echo "  Failed to copy POSCAR"
        failed_setups=$((failed_setups + 1))
        continue
    fi
    
    # Copy POTCAR
    if ! cp "$POTCAR_SOURCE" "$calc_path/POTCAR"; then
        echo "  Failed to copy POTCAR"
        failed_setups=$((failed_setups + 1))
        continue
    fi
    
    # Copy KPOINTS
    if ! cp "$KPOINTS_SOURCE" "$calc_path/KPOINTS"; then
        echo "  Failed to copy KPOINTS"
        failed_setups=$((failed_setups + 1))
        continue
    fi
    
    # Copy INCAR (will be updated later with correct DIPOL)
    if ! cp "$INCAR_SOURCE" "$calc_path/INCAR"; then
        echo "  Failed to copy INCAR"
        failed_setups=$((failed_setups + 1))
        continue
    fi
    
    # Copy job.slurm
    if ! cp "$JOB_SOURCE" "$calc_path/job.slurm"; then
        echo "  Failed to copy job.slurm"
        failed_setups=$((failed_setups + 1))
        continue
    fi
    
    # Create README for this calculation
    cat > "$calc_path/README.txt" << EOF
DFT Calculation Directory: $calc_name
=====================================
Calculation Type: $CALC_TYPE
Setup Date: $(date)
POSCAR Source: $poscar_file

Files Status:
✅ POSCAR   - Copied from poscars (this calculation's structure)
✅ POTCAR   - Copied from templates
✅ KPOINTS  - Copied from templates
✅ INCAR    - Copied from templates (DIPOL needs update)
✅ job.slurm- Copied from templates

Next Steps:
1. ⚠️  Update DIPOL value in INCAR using update_dipol.py
2. Submit job using: sbatch job.slurm
3. Monitor completion
4. Extract energy from OUTCAR

Notes:
- DIPOL value is placeholder and must be calculated
- Check all parameters before submission
- Ensure proper module loading in job.slurm
EOF
    
    echo "  Setup complete"
    successful_setups=$((successful_setups + 1))
done

echo ""
echo "=============================================================================="
echo "SETUP COMPLETE"
echo "=============================================================================="
echo "Successfully set up: $successful_setups calculations"
echo "Failed setups: $failed_setups calculations"
echo ""

if [ $successful_setups -gt 0 ]; then
    echo "Next steps:"
    echo "   1. Update DIPOL values:"
    echo "      python scripts/2_update_dipol.py $CALC_DIR"
    echo ""
    echo "   2. Submit jobs:"
    echo "      ./scripts/3_submit_jobs.sh $CALC_DIR"
    echo ""
    echo "   3. Extract energies (after completion):"
    echo "      python scripts/extract_energies_simple.py"
fi

echo "=============================================================================="
