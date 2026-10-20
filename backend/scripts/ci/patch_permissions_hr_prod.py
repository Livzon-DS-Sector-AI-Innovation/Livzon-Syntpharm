#!/usr/bin/env python3
"""Patch registry.py with HR + Production permissions, bindings, and labels."""

import os
import subprocess
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REGISTRY = os.path.join(BACKEND, "app/platform/permission/registry.py")
GEN_SCRIPT = os.path.join(BACKEND, "scripts/ci/generate_permissions_hr_prod.py")

def run_generator():
    """Run the permission generation script and parse output sections."""
    result = subprocess.run(
        [sys.executable, GEN_SCRIPT],
        capture_output=True, text=True, cwd=BACKEND
    )
    output = result.stdout
    
    sections = {
        "hr_perms": [],
        "prod_perms": [],
        "bindings": [],
        "labels": [],
    }
    
    current = None
    for line in output.split("\n"):
        if line.startswith("# ========== HR_PERMISSIONS"):
            current = "hr_perms"
            continue
        elif line.startswith("# ========== PRODUCTION_PERMISSIONS"):
            current = "prod_perms"
            continue
        elif line.startswith("# ========== HR + PRODUCTION API BINDINGS"):
            current = "bindings"
            continue
        elif line.startswith("# ========== HR + PRODUCTION RESOURCE LABELS"):
            current = "labels"
            continue
        elif line.startswith("# =========="):
            current = None
            continue
        elif line.startswith("# Total routes"):
            continue
        
        if current and line.strip():
            sections[current].append(line)
    
    return sections

def patch_registry(sections):
    """Insert generated sections into registry.py."""
    with open(REGISTRY) as f:
        lines = f.readlines()
    
    hr_perms_text = "\n".join(sections["hr_perms"])
    prod_perms_text = "\n".join(sections["prod_perms"])
    bindings_text = "\n".join(sections["bindings"])
    labels_text = "\n".join(sections["labels"])
    
    new_lines = []
    
    # ── Step 1: Insert HR_PERMISSIONS after QUALITY_PERMISSIONS ──
    in_quality_perms = False
    quality_done = False
    for line in lines:
        if quality_done:
            new_lines.append(line)
            continue
        
        if line.strip().startswith("QUALITY_PERMISSIONS: tuple"):
            in_quality_perms = True
            new_lines.append(line)
        elif in_quality_perms and line.rstrip() == ")":
            # End of QUALITY_PERMISSIONS - insert HR and Production perms
            new_lines.append(line)
            new_lines.append("\n")
            new_lines.append(hr_perms_text + "\n")
            new_lines.append("\n")
            new_lines.append(prod_perms_text + "\n")
            in_quality_perms = False
            quality_done = True
        else:
            new_lines.append(line)
    
    lines = new_lines
    
    # ── Step 2: Add HR + Production to ALL_PERMISSIONS ──
    new_lines = []
    for line in lines:
        if "+ QUALITY_PERMISSIONS" in line and "ALL_PERMISSIONS" not in line:
            line = line.replace("+ QUALITY_PERMISSIONS", "+ QUALITY_PERMISSIONS + HR_PERMISSIONS + PRODUCTION_PERMISSIONS")
        new_lines.append(line)
    lines = new_lines
    
    # ── Step 3: Insert API bindings after quality bindings (before closing ) of API_BINDINGS) ──
    new_lines = []
    in_api_bindings = False
    bindings_inserted = False
    for i, line in enumerate(lines):
        if line.strip().startswith("API_BINDINGS: tuple"):
            in_api_bindings = True
            new_lines.append(line)
        elif in_api_bindings and not bindings_inserted:
            # Look ahead: if next non-empty line after this is just ")", we're at end of bindings
            rest = [l.strip() for l in lines[i+1:i+5]]
            if line.rstrip() == ")" and not bindings_inserted:
                # Actually we want to insert BEFORE the closing )
                # So go back one position
                pass
            # Find the line that is just ")" preceded by quality bindings
            # We know the last quality binding ends with a quality: prefix
            stripped = line.strip()
            next_stripped = lines[i+1].strip() if i+1 < len(lines) else ""
            next_next_stripped = lines[i+2].strip() if i+2 < len(lines) else ""
            
            if stripped == ")" and not bindings_inserted:
                # Insert bindings before this closing paren - but we need to go back
                # Find the last binding line and insert after it
                new_lines.append("\n")
                new_lines.append(bindings_text + "\n")
                new_lines.append(line)
                bindings_inserted = True
                in_api_bindings = False
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    lines = new_lines
    
    # ── Step 4: Insert RESOURCE_LABELS ──
    new_lines = []
    in_labels = False
    labels_done = False
    for line in lines:
        if labels_done:
            new_lines.append(line)
            continue
        
        if line.strip().startswith("RESOURCE_LABELS"):
            in_labels = True
            new_lines.append(line)
        elif in_labels and line.rstrip() == "}" and not labels_done:
            # End of RESOURCE_LABELS - insert new labels before closing }
            new_lines.append(labels_text + "\n")
            new_lines.append(line)
            in_labels = False
            labels_done = True
        else:
            new_lines.append(line)
    
    lines = new_lines
    
    # ── Step 5: Update ENFORCE_READY_MODULES ──
    new_lines = []
    for line in lines:
        if "ENFORCE_READY_MODULES: tuple[str, ...]" in line:
            # Add hr and production to the list
            if '"quality")' in line:
                line = line.replace('"quality")', '"quality", "hr", "production")')
        new_lines.append(line)
    
    # Write back
    with open(REGISTRY, "w") as f:
        f.writelines(new_lines)
    
    print("Registry patched successfully.")

def verify():
    """Verify the patched registry imports correctly."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("registry", REGISTRY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print(f"ALL_PERMISSIONS: {len(mod.ALL_PERMISSIONS)}")
    print(f"API_BINDINGS: {len(mod.API_BINDINGS)}")
    print(f"ENFORCE_READY_MODULES: {mod.ENFORCE_READY_MODULES}")


if __name__ == "__main__":
    # Backup first
    import shutil
    backup = REGISTRY + ".bak-hr-prod"
    shutil.copy2(REGISTRY, backup)
    print(f"Backup saved to {backup}")
    
    sections = run_generator()
    print(f"HR perms: {len(sections['hr_perms'])} lines")
    print(f"Prod perms: {len(sections['prod_perms'])} lines")
    print(f"Bindings: {len(sections['bindings'])} lines")
    print(f"Labels: {len(sections['labels'])} lines")
    
    patch_registry(sections)
    verify()