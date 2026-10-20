#!/usr/bin/env python3
"""Inject require_permission into HR + Production API endpoint functions.

Usage:
    uv run python scripts/ci/inject_permissions_hr_prod.py [--dry-run]
"""

import ast
import os
import re
import sys

BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# Permission mapping: for each file, map (method, path_suffix) -> permission_code
# ============================================================

PERMISSION_MAP = {}
with open(os.path.join(BACKEND, "app/platform/permission/registry.py")) as f:
    for line in f:
        m = re.search(r'ApiBindingDef\("([^"]+)",\s*"([A-Z]+)",\s*"([^"]+)"\)', line)
        if m:
            code, method, path = m.group(1), m.group(2), m.group(3)
            if code.startswith("hr:") or code.startswith("production:"):
                PERMISSION_MAP[(method, path)] = code

print(f"Loaded {len(PERMISSION_MAP)} permission bindings")


# ============================================================
# Files to inject and their prefix mapping
# ============================================================

FILES_CONFIG = [
    # (rel_path, prefix_parts)
    ("app/modules/hr/api.py", ["api/v1/hr"]),
    ("app/modules/hr/analysis_api.py", ["api/v1/hr", "turnover-analysis"]),
    ("app/modules/hr/ai_exam/api.py", ["api/v1/hr", "ai-exam"]),
    ("app/modules/production/api.py", ["api/v1/production"]),
    ("app/modules/production/product/api.py", ["api/v1/production"]),
    ("app/modules/production/product/output_api.py", ["api/v1/production"]),
    ("app/modules/production/product/sync_config_api.py", ["api/v1/production"]),
    ("app/modules/production/pressure/api.py", ["api/v1/production"]),
]


def build_full_path(prefix_parts, route_path):
    """Build full API path from prefix and route path."""
    full_parts = prefix_parts + [route_path.lstrip("/")]
    return "/" + "/".join(p for p in full_parts if p)


def find_permission(method, full_path):
    """Find permission code from registry bindings."""
    return PERMISSION_MAP.get((method, full_path))


def has_permission_injection(source, func_node):
    """Check if a function already has require_permission injection."""
    # Get the function's source lines
    lines = source.split("\n")
    # Check function parameters for ctx with require_permission
    start = func_node.lineno - 1
    end = func_node.body[0].lineno if func_node.body else start + 20
    func_text = "\n".join(lines[start:min(end, len(lines))])
    return "require_permission" in func_text


def get_indent(line):
    """Get indentation of a line."""
    return len(line) - len(line.lstrip())


def get_non_default_params(params_text):
    """Extract non-default parameter names from function signature."""
    # Parse parameter list
    non_defaults = []
    current_param = ""
    paren_depth = 0
    for char in params_text + ",":
        if char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
        elif char == "," and paren_depth == 0:
            param = current_param.strip()
            if param and "=" not in param:
                # No default value
                name = param.split(":")[0].strip()
                if name and name not in ("self", "*"):
                    non_defaults.append(name)
            current_param = ""
        else:
            current_param += char
    return non_defaults


def inject_into_file(filepath, prefix_parts, dry_run=False):
    """Inject require_permission into all endpoints in a file."""
    with open(filepath) as f:
        source = f.read()

    lines = source.split("\n")
    tree = ast.parse(source)

    # Find all endpoint functions that need injection
    injections = []  # (line_no, permission_code, insert_after_line)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    if dec.func.attr in ("get", "post", "put", "delete", "patch"):
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            method = dec.func.attr.upper()
                            route_path = dec.args[0].value
                            if route_path == "/":
                                break
                            full_path = build_full_path(prefix_parts, route_path)
                            perm = find_permission(method, full_path)
                            if perm and not has_permission_injection(source, node):
                                injections.append((node.lineno, perm, method, route_path))
                        break

    if not injections:
        print(f"  No injections needed for {filepath}")
        return

    # Sort from bottom to top to avoid line number drift
    injections.sort(key=lambda x: -x[0])

    for func_lineno, perm, method, route_path in injections:
        func_lineno = func_lineno - 1  # 0-indexed

        # Find function signature lines
        # Start from the decorator or function def line
        sig_start = func_lineno
        sig_end = func_lineno

        # Expand to include multi-line signature
        paren_count = 0
        in_paren = False
        for i in range(func_lineno, min(func_lineno + 20, len(lines))):
            line = lines[i]
            paren_count += line.count("(") - line.count(")")
            if "(" in line:
                in_paren = True
            if in_paren and paren_count == 0:
                sig_end = i
                break
            if ":" in line and paren_count <= 0 and in_paren:
                sig_end = i
                break

        # Get the signature text
        sig_lines = lines[sig_start:sig_end + 1]
        sig_text = "\n".join(sig_lines)

        # Check if it's a single-line signature
        is_single_line = len(sig_lines) == 1

        # Extract the function name and parameters
        # Find the opening paren after "def "
        def_idx = sig_text.index("def ")
        open_paren = sig_text.index("(", def_idx)
        close_paren = sig_text.rindex(")")

        if is_single_line:
            # Single-line: async def func(params) -> Any:
            func_prefix = sig_text[:open_paren + 1]
            params_part = sig_text[open_paren + 1:close_paren]
            suffix = sig_text[close_paren:]

            # Parse parameters
            params = [p.strip() for p in params_part.split(",") if p.strip()]
            non_defaults = get_non_default_params(params_part)

            # Insert ctx after the last non-default param
            insert_idx = len(non_defaults) if non_defaults else 0

            new_params = params[:insert_idx] + [
                f"ctx: PermissionContext = Depends(require_permission(\"{perm}\"))"
            ] + params[insert_idx:]

            new_sig = func_prefix + ", ".join(new_params) + suffix
            lines[sig_start] = new_sig
        else:
            # Multi-line signature: need to find where to insert ctx
            base_indent = get_indent(lines[sig_start])
            ctx_line = " " * (base_indent + 4) + f"ctx: PermissionContext = Depends(require_permission(\"{perm}\")),"

            # Collect all parameters from all lines
            all_params = []
            param_line_indices = []
            for i in range(sig_start, sig_end + 1):
                line = lines[i]
                stripped = line.strip()
                if stripped.startswith("def ") or stripped.startswith("async def "):
                    # Extract parameters after "("
                    if "(" in stripped:
                        p = stripped[stripped.index("(")+1:]
                        if p.strip():
                            all_params.extend([x.strip() for x in p.split(",") if x.strip()])
                    param_line_indices.append(i)
                elif stripped.startswith(")") or stripped.startswith("->"):
                    # End of params
                    pass
                else:
                    # Parameter line
                    p = stripped.rstrip(",")
                    if p.strip():
                        all_params.append(p.strip())
                    param_line_indices.append(i)

            # Determine non-default params
            non_default_names = []
            for p in all_params:
                if "=" not in p and p.strip() not in ("self", "*"):
                    name = p.split(":")[0].strip()
                    non_default_names.append(name)

            # Find where to insert ctx: after last non-default param
            default_params_start = len(non_default_names)

            # Map non-default names back to line indices
            # Find which line contains param number default_params_start
            # Simple approach: insert ctx after the line that contains the last non-default param
            param_count = 0
            target_line = param_line_indices[-1] if param_line_indices else sig_start

            for pi, p in enumerate(all_params):
                name = p.split(":")[0].strip() if ":" in p else p
                if name in non_default_names:
                    if param_count == len(non_default_names) - 1:
                        # This is the last non-default param
                        for j in range(sig_start, sig_end + 1):
                            line = lines[j].strip()
                            if name in line or p.split(":")[0].strip() in line:
                                target_line = j
                                break
                        break
                    param_count += 1

            # Insert ctx_line after target_line
            lines.insert(target_line + 1, ctx_line)
            sig_end += 1  # adjust for insertion

    # Check if import is needed
    has_import = any("from app.core.deps import PermissionContext, require_permission" in l for l in lines)
    if not has_import:
        # Check for existing deps import
        for i, line in enumerate(lines):
            if "from app.core.deps import" in line:
                if "CurrentUser" in line and "PermissionContext" not in line:
                    lines[i] = line.replace("CurrentUser", "CurrentUser, PermissionContext, require_permission")
                    break
                elif "PermissionContext" not in line:
                    lines[i] = line.rstrip() + ", PermissionContext, require_permission\n"
                    break
        else:
            # Add new import after the last existing import
            last_import = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("from ") or line.strip().startswith("import "):
                    last_import = i
            lines.insert(last_import + 1, "")
            lines.insert(last_import + 2, "from app.core.deps import PermissionContext, require_permission")

    result = "\n".join(lines)

    if dry_run:
        print(f"  [DRY RUN] Would modify {filepath}: {len(injections)} injections")
    else:
        with open(filepath, "w") as f:
            f.write(result)
        print(f"  Injected {filepath}: {len(injections)} endpoints")


def main():
    dry_run = "--dry-run" in sys.argv

    for rel_path, prefix_parts in FILES_CONFIG:
        filepath = os.path.join(BACKEND, rel_path)
        if not os.path.exists(filepath):
            print(f"  SKIP (not found): {filepath}")
            continue
        try:
            inject_into_file(filepath, prefix_parts, dry_run)
        except Exception as e:
            print(f"  ERROR {filepath}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()