#!/usr/bin/env python3
"""
Validates the architecture-contract.yaml file according to schema version 1.
"""

import sys
import os
import yaml

def validate_contract(filepath):
    if not os.path.exists(filepath):
        print(f"Contract file not found: {filepath}")
        sys.exit(1)

    try:
        with open(filepath, 'r') as f:
            contract = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Invalid YAML: {e}")
        sys.exit(1)

    errors = []

    if contract.get('schema_version') != 1:
        errors.append("schema_version must be 1")

    components = contract.get('components', [])
    for comp in components:
        if 'id' not in comp:
            errors.append("Component missing 'id'")
        if 'allowed_dependencies' not in comp:
            errors.append(f"Component {comp.get('id')} missing 'allowed_dependencies'")

    invariants = contract.get('invariants', [])
    for inv in invariants:
        if 'id' not in inv:
            errors.append("Invariant missing 'id'")
        if 'scope' not in inv:
            errors.append(f"Invariant {inv.get('id')} missing 'scope'")
        severity = inv.get('severity')
        if severity not in ['block', 'warn', 'info']:
            errors.append(f"Invariant {inv.get('id')} has invalid severity: {severity}")

    if errors:
        print("Validation FAILED:")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)
    else:
        print("Validation PASSED. Contract is valid.")
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate-contract.py <path/to/architecture-contract.yaml>")
        sys.exit(1)
    validate_contract(sys.argv[1])
