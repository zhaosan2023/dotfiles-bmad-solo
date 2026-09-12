#!/usr/bin/env python3
"""
Validates the task-state.yaml file according to schema version 1.
"""

import sys
import os
import yaml

VALID_CLAIM_STATUSES = ['verified', 'accepted', 'hypothesis', 'local-only', 'refuted', 'stale']

def validate_task_state(filepath):
    if not os.path.exists(filepath):
        print(f"Task state file not found: {filepath}")
        sys.exit(1)

    try:
        with open(filepath, 'r') as f:
            state = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Invalid YAML: {e}")
        sys.exit(1)

    errors = []

    if state.get('schema_version') != 1:
        errors.append("schema_version must be 1")

    claims = state.get('claims', [])
    for claim in claims:
        status = claim.get('status')
        if status not in VALID_CLAIM_STATUSES:
            errors.append(f"Claim {claim.get('id')} has invalid status: {status}")

    obligations = state.get('open_obligations', [])
    for obl in obligations:
        if 'verification_method' not in obl:
            errors.append(f"Obligation {obl.get('id')} missing 'verification_method'")

    if errors:
        print("Validation FAILED:")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)
    else:
        print("Validation PASSED. Task state is valid.")
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate-task-state.py <path/to/task-state.yaml>")
        sys.exit(1)
    validate_task_state(sys.argv[1])
