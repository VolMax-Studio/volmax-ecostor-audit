#!/usr/bin/env python3
import os
import sys
import argparse
import random
import numpy as np

# Enforce a fixed random seed for reproducibility
def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)

def generate_requirements(base_dir):
    requirements = [
        "pandas>=2.0.0",
        "numpy>=1.20.0",
        "openpyxl>=3.0.0",
        "matplotlib>=3.5.0",
        "scipy>=1.7.0"
    ]
    req_path = os.path.join(base_dir, "requirements.txt")
    with open(req_path, "w") as f:
        f.write("\n".join(requirements) + "\n")
    print(f"Generated requirements.txt at {req_path}")

def main():
    parser = argparse.ArgumentParser(description="P10 Audit Replication Pipeline for ECO STOR BESS")
    parser.add_argument("--l1-only", action="store_true", help="Run only Level 1 Data Integrity check and stop")
    args = parser.parse_args()
    
    set_seed(42)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("--- Starting ECO STOR Bollingstedt BESS Audit Reproduction Pipeline ---")
    generate_requirements(base_dir)
    
    # 1. Level 1 Data Integrity
    print("\n--- Running Level 1 (Data Integrity) Validation ---")
    from schema_validation import run_l1_validation
    run_l1_validation(base_dir)
    
    if args.l1_only:
        print("\nHalted at Level 1 Gate (as requested by --l1-only).")
        sys.exit(0)
        
    # 2. Downstream analysis
    print("\n--- Running Level 2 & 3 Claims Verification ---")
    try:
        import verify_claims
        verify_claims.main()
    except Exception as e:
        print(f"\nError running verify_claims.py: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
