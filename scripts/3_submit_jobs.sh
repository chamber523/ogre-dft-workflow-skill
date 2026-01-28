#!/bin/bash

# DFT Job Submission Script
# Usage: ./3_submit_jobs.sh <calculations_directory> [start_index] [end_index] [options]

set -e  # Exit on any error

# Function to display usage
usage() {
    echo "=============================================================================="
    echo "DFT JOB SUBMISSION SCRIPT"
    echo "=============================================================================="
    echo "Usage: $0 <calculations_directory> [start_index] [end_index] [options]"
    echo ""
    echo "Arguments:"
    echo "  calculations_directory : Directory containing calc_* subdirectories"
    echo "  start_index           : Starting calculation index (default: 0)"
    echo "  end_index             : Ending calculation index (default: all)"
    echo ""
    echo "Options:"
    echo "  --dry-run             : Show what would be submitted without submitting"
    echo "  --delay SECONDS       : Delay between submissions (default: 1)"
    echo "  --batch-size N        : Submit in batches of N jobs (default: all)"
    echo "  --check-dipol         : Verify DIPOL values before submission"
    echo ""
    echo "Examples:"
    echo "  $0 ./calculations                    # Submit all jobs"
    echo "  $0 ./calculations 0 99               # Submit jobs 0-99"
    echo "  $0 ./calculations --dry-run          # Preview submission"
    echo "  $0 ./calculations --delay 2          # 2 second delay between jobs"
    echo "  $0 ./calculations --batch-size 50    # Submit in batches of 50"
    echo "=============================================================================="
    exit 1
}

# Parse arguments
CALC_DIR=""
START_INDEX=""
END_INDEX=""
DRY_RUN=false
DELAY=1
BATCH_SIZE=""
CHECK_DIPOL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --delay)
            DELAY="$2"
            shift 2
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --check-dipol)
            CHECK_DIPOL=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            if [ -z "$CALC_DIR" ]; then
                CALC_DIR="$1"
            elif [ -z "$START_INDEX" ]; then
                START_INDEX="$1"
            elif [ -z "$END_INDEX" ]; then
                END_INDEX="$1"
            else
                echo "❌ Error: Too many arguments"
                usage
            fi
            shift
            ;;
    esac
done

# Validate required arguments
if [ -z "$CALC_DIR" ]; then
    echo "❌ Error: calculations_directory is required"
    usage
fi

if [ ! -d "$CALC_DIR" ]; then
    echo "❌ Error: Calculations directory not found: $CALC_DIR"
    exit 1
fi

echo "=============================================================================="
echo "DFT JOB SUBMISSION"
echo "=============================================================================="
echo "📁 Calculations directory: $CALC_DIR"
echo "🔢 Index range: ${START_INDEX:-'all'} to ${END_INDEX:-'all'}"
echo "🔍 Mode: $([ "$DRY_RUN" = true ] && echo 'DRY RUN' || echo 'SUBMIT')"
echo "⏱️  Delay between jobs: ${DELAY}s"
echo "📦 Batch size: ${BATCH_SIZE:-'unlimited'}"
echo "🔍 Check DIPOL: $([ "$CHECK_DIPOL" = true ] && echo 'yes' || echo 'no')"
echo "🕐 Started: $(date)"
echo "=============================================================================="

# Find calculation directories
calc_dirs=()
for item in "$CALC_DIR"/calc_*; do
    if [ -d "$item" ]; then
        calc_name=$(basename "$item")
        # Extract index from calc_XXXX
        if [[ "$calc_name" =~ calc_([0-9]+) ]]; then
            index="${BASH_REMATCH[1]}"
            # Remove leading zeros for comparison
            index_num=$((10#$index))
            
            # Check if within range
            if [ -n "$START_INDEX" ] && [ $index_num -lt $((10#$START_INDEX)) ]; then
                continue
            fi
            if [ -n "$END_INDEX" ] && [ $index_num -gt $((10#$END_INDEX)) ]; then
                continue
            fi
            
            calc_dirs+=("$item")
        fi
    fi
done

# Sort directories
IFS=$'\n' calc_dirs=($(sort <<<"${calc_dirs[*]}"))
unset IFS

if [ ${#calc_dirs[@]} -eq 0 ]; then
    echo "❌ No calculation directories found in range"
    exit 1
fi

echo "Found ${#calc_dirs[@]} calculation directories to process"
echo ""

# Initialize counters
successful_submissions=0
failed_submissions=0
skipped_submissions=0
batch_count=0

# Function to check DIPOL value
check_dipol_value() {
    local incar_file="$1"
    if [ ! -f "$incar_file" ]; then
        return 1
    fi
    
    # Check if DIPOL line exists and is not placeholder
    if grep -q "DIPOL.*PLACEHOLDER" "$incar_file" 2>/dev/null; then
        return 1
    fi
    
    # Check if DIPOL line exists with actual values
    if grep -q "DIPOL.*[0-9]" "$incar_file" 2>/dev/null; then
        return 0
    fi
    
    return 1
}

echo "🚀 Processing calculations..."
echo ""

# Process each calculation directory
for calc_dir in "${calc_dirs[@]}"; do
    calc_name=$(basename "$calc_dir")
    echo "📤 Processing $calc_name..."
    
    # Check required files
    if [ ! -f "$calc_dir/POSCAR" ]; then
        echo "  ❌ POSCAR not found, skipping"
        skipped_submissions=$((skipped_submissions + 1))
        continue
    fi
    
    if [ ! -f "$calc_dir/INCAR" ]; then
        echo "  ❌ INCAR not found, skipping"
        skipped_submissions=$((skipped_submissions + 1))
        continue
    fi
    
    if [ ! -f "$calc_dir/KPOINTS" ]; then
        echo "  ❌ KPOINTS not found, skipping"
        skipped_submissions=$((skipped_submissions + 1))
        continue
    fi
    
    if [ ! -f "$calc_dir/POTCAR" ]; then
        echo "  ❌ POTCAR not found, skipping"
        skipped_submissions=$((skipped_submissions + 1))
        continue
    fi
    
    if [ ! -f "$calc_dir/job.slurm" ]; then
        echo "  ❌ job.slurm not found, skipping"
        skipped_submissions=$((skipped_submissions + 1))
        continue
    fi
    
    # Check DIPOL if requested
    if [ "$CHECK_DIPOL" = true ]; then
        if ! check_dipol_value "$calc_dir/INCAR"; then
            echo "  ⚠️  DIPOL value not set or is placeholder, skipping"
            echo "  💡 Run: python scripts/2_update_dipol.py $CALC_DIR"
            skipped_submissions=$((skipped_submissions + 1))
            continue
        fi
    fi
    
    # Check if already running or completed
    if [ -f "$calc_dir/OUTCAR" ]; then
        # Check if calculation completed successfully
        if grep -q "reached required accuracy" "$calc_dir/OUTCAR" 2>/dev/null; then
            echo "  ✅ Already completed, skipping"
            skipped_submissions=$((skipped_submissions + 1))
            continue
        fi
    fi
    
    # Check if job is currently running
    if [ -f "$calc_dir/job.slurm" ]; then
        # Look for slurm output files
        if ls "$calc_dir"/slurm-*.out >/dev/null 2>&1; then
            # Check if any jobs are still running
            job_running=false
            for slurm_file in "$calc_dir"/slurm-*.out; do
                if [ -f "$slurm_file" ]; then
                    job_id=$(basename "$slurm_file" | sed 's/slurm-\([0-9]*\)\.out/\1/')
                    if squeue -j "$job_id" >/dev/null 2>&1; then
                        job_running=true
                        break
                    fi
                fi
            done
            
            if [ "$job_running" = true ]; then
                echo "  🏃 Job already running, skipping"
                skipped_submissions=$((skipped_submissions + 1))
                continue
            fi
        fi
    fi
    
    if [ "$DRY_RUN" = true ]; then
        echo "  🔍 Would submit job"
        successful_submissions=$((successful_submissions + 1))
    else
        # Change to calculation directory and submit
        cd "$calc_dir" || continue
        
        # Clean up previous run files
        rm -f OUTCAR OSZICAR vasprun.xml EIGENVAL DOSCAR IBZKPT PCDAT REPORT XDATCAR slurm-*.out
        
        # Submit job and capture job ID
        if job_output=$(sbatch job.slurm 2>&1); then
            job_id=$(echo "$job_output" | grep -o '[0-9]\+' | head -1)
            echo "  Submitted successfully - Job ID: $job_id"
            successful_submissions=$((successful_submissions + 1))
        else
            echo "  Submission failed: $job_output"
            failed_submissions=$((failed_submissions + 1))
        fi
        
        # Return to original directory
        cd - >/dev/null
        
        # Apply delay between submissions
        if [ $DELAY -gt 0 ] && [ $successful_submissions -lt ${#calc_dirs[@]} ]; then
            sleep $DELAY
        fi
    fi
    
    # Check batch size limit
    if [ -n "$BATCH_SIZE" ]; then
        batch_count=$((batch_count + 1))
        if [ $batch_count -ge $BATCH_SIZE ]; then
            echo ""
            echo "📦 Batch limit reached ($BATCH_SIZE jobs). Stopping here."
            echo "💡 To submit more, run again with different start index."
            break
        fi
    fi
done

echo ""
echo "=============================================================================="
echo "SUBMISSION COMPLETE"
echo "=============================================================================="
echo "✅ Successfully submitted: $successful_submissions"
echo "Failed submissions: $failed_submissions"
echo "Skipped: $skipped_submissions"
echo "Total processed: ${#calc_dirs[@]}"

if [ $successful_submissions -gt 0 ] && [ "$DRY_RUN" = false ]; then
    echo ""
    echo "📋 Monitor job status with:"
    echo "   squeue -u \$USER"
    echo ""
    echo "📊 After completion, extract energies with:"
    echo "   python scripts/4_extract_energies.py $CALC_DIR"
fi

echo "=============================================================================="

# Exit with error code if any submissions failed
if [ $failed_submissions -gt 0 ]; then
    exit 1
fi
