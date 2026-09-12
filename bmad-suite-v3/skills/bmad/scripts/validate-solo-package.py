#!/usr/bin/env python3
"""
BMAD-Solo Package Integrity Validator

Checks that:
1. Every procedure referenced in capability-map.md actually exists.
2. All mode reference files exist.
3. No hard dependency on _bmad/scripts/ exists in any procedure.
"""

import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)  # skills/bmad/
REFERENCES_DIR = os.path.join(SKILL_ROOT, "references")
PROCEDURES_DIR = os.path.join(REFERENCES_DIR, "procedures")

EXPECTED_MODES = [
    "mode-product.md",
    "mode-architect.md",
    "mode-developer.md",
    "mode-reviewer.md",
    "mode-operator.md",
]

FORBIDDEN_PATTERNS = [
    r"_bmad/scripts/",
    r"render_skill\.py",
    r"resolve_customization\.py",
    r"customize\.toml",
    r"bmm/config\.yaml",
]

errors = []
warnings = []


def check_mode_references():
    """Verify all mode reference files exist."""
    for mode in EXPECTED_MODES:
        path = os.path.join(REFERENCES_DIR, mode)
        if not os.path.isfile(path):
            errors.append(f"Missing mode reference: {mode}")
        else:
            print(f"  [✔] {mode}")


def check_capability_map():
    """Verify every procedure in capability-map.md exists."""
    cap_map = os.path.join(REFERENCES_DIR, "capability-map.md")
    if not os.path.isfile(cap_map):
        errors.append("Missing capability-map.md")
        return

    with open(cap_map, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract procedure paths from markdown table cells
    procedure_refs = re.findall(r"procedures/[\w-]+\.md", content)

    for ref in procedure_refs:
        full_path = os.path.join(REFERENCES_DIR, ref)
        if os.path.isfile(full_path):
            print(f"  [✔] {ref}")
        else:
            # Check if it's in the "Planned" section
            planned_section = content.split("## Planned")
            if len(planned_section) > 1:
                # Check if ref appears after "Planned" header
                active_section = planned_section[0]
                if ref in active_section:
                    errors.append(f"Active capability references missing procedure: {ref}")
                else:
                    print(f"  [~] {ref} (planned, not yet created)")
            else:
                errors.append(f"Capability references missing procedure: {ref}")


def check_forbidden_dependencies():
    """Verify no procedure has hard dependencies on _bmad/scripts."""
    if not os.path.isdir(PROCEDURES_DIR):
        errors.append(f"Procedures directory not found: {PROCEDURES_DIR}")
        return

    for filename in os.listdir(PROCEDURES_DIR):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(PROCEDURES_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        for pattern in FORBIDDEN_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                errors.append(
                    f"{filename} contains forbidden dependency: {matches[0]}"
                )

    print(f"  [✔] No forbidden dependencies in {len(os.listdir(PROCEDURES_DIR))} procedures")


def check_skill_md():
    """Verify SKILL.md exists and has proper frontmatter."""
    skill_md = os.path.join(SKILL_ROOT, "SKILL.md")
    if not os.path.isfile(skill_md):
        errors.append("Missing SKILL.md")
        return

    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        warnings.append("SKILL.md missing YAML frontmatter")
    if "name: bmad-solo" not in content:
        warnings.append("SKILL.md missing 'name: bmad-solo' in frontmatter")
    if len(content) < 500:
        warnings.append("SKILL.md seems too short for a complete router")

    print(f"  [✔] SKILL.md ({len(content)} bytes)")


def main():
    print("=" * 60)
    print("BMAD-Solo Package Integrity Validator")
    print("=" * 60)

    print("\n1. Checking SKILL.md...")
    check_skill_md()

    print("\n2. Checking mode references...")
    check_mode_references()

    print("\n3. Checking capability map procedures...")
    check_capability_map()

    print("\n4. Checking for forbidden dependencies...")
    check_forbidden_dependencies()

    print("\n" + "=" * 60)

    if warnings:
        print(f"\n⚠ {len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")

    if errors:
        print(f"\n✘ {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        print("\nValidation FAILED.")
        sys.exit(1)
    else:
        print("\n✔ All checks passed. Package is self-contained.")
        sys.exit(0)


if __name__ == "__main__":
    main()
