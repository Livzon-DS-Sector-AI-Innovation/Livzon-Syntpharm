#!/usr/bin/env python3
"""Generate HR + Production permission codes and API bindings for registry.py."""

import ast
import re
import os
import sys
from collections import OrderedDict

BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# Route extraction
# ============================================================


def extract_routes(filepath, prefix_parts):
    """Extract (method, path_suffix, func_name, line) from a Python API file."""
    routes = []
    if not os.path.exists(filepath):
        return routes
    with open(filepath) as f:
        source = f.read()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    if dec.func.attr in ("get", "post", "put", "delete", "patch"):
                        method = dec.func.attr.upper()
                        if dec.args:
                            arg = dec.args[0]
                            if isinstance(arg, ast.Constant):
                                path = arg.value
                                # skip factory endpoints
                                if path == "/":
                                    continue
                                # build full path
                                full_parts = prefix_parts + [path.lstrip("/")]
                                full_path = "/" + "/".join(p for p in full_parts if p)
                                routes.append((method, full_path, node.name, node.lineno))
                                break
    return routes


# ============================================================
# Resource/Action mapping
# ============================================================


def classify_route(method, full_path):
    """Classify a route into (module, resource, action)."""
    # Normalize path (remove double slashes) and strip /api/v1/ prefix
    rel = full_path.replace("//", "/").replace("/api/v1/", "").lstrip("/")

    # Determine module
    if rel.startswith("hr/"):
        module = "hr"
        rel = rel[3:]  # remove "hr/"
    elif rel.startswith("production/"):
        module = "production"
        rel = rel[11:]  # remove "production/"
    else:
        return None, None, None

    parts = rel.strip("/").split("/")
    if not parts:
        return module, None, None

    # Determine resource from first path segment(s)
    resource = parts[0]

    # Special handling for resource prefixes
    if resource == "new":
        # /hr/new/employees, /hr/new/onboarding-records, etc.
        if len(parts) >= 2:
            resource = f"new-{parts[1]}"
            rest = parts[2:]
        else:
            rest = []
    elif resource == "pressure":
        # /production/pressure/...
        if len(parts) >= 2:
            resource = f"pressure-{parts[1]}"
            rest = parts[2:]
        else:
            resource = "pressure"
            rest = []
    # Handle AI exam
    elif resource == "ai-exam" and module == "hr":
        resource = "ai-exam"
        rest = parts[1:]
    # Handle product-* under production
    elif resource == "product-output" and module == "production":
        resource = "product-output"
        rest = parts[1:]
    elif resource == "product-sync-config" and module == "production":
        resource = "product-sync-config"
        rest = parts[1:]
    elif resource == "products" and module == "production":
        resource = "products"
        rest = parts[1:]
    # Handle pressure sub-resources that have more nesting
    elif resource.startswith("pressure-"):
        rest = parts[1:]
    else:
        rest = parts[1:]

    # Determine action
    action = _determine_action(method, rest, resource, module)
    return module, resource, action


def _determine_action(method, rest, resource, module):
    """Determine action from method and remaining path parts."""
    tail = "_".join(rest) if rest else ""

    # Export patterns
    if "export" in tail:
        return "export"
    # Import patterns
    if "import" in tail:
        return "import"
    # Sync patterns
    if "sync" in tail or "push" in tail or "pull" in tail:
        if "preview" in tail:
            return "read"
        if "undo" in tail:
            return "update"
        return "sync"
    # Approve/submit patterns
    if "approve" in tail or "submit" in tail or "recommendation-level" in tail:
        return "update"
    # Status change
    if "status" in tail:
        return "update"
    # Calculate
    if "calculate" in tail:
        return "read"
    # Check unique
    if "check-unique" in tail:
        return "read"
    # Read-all / batch patterns (destructive ones = delete)
    if "batch-delete" in tail:
        return "delete"
    if "batch" in tail and method == "PUT":
        return "update"
    # AI exam specific
    if tail == "generate" and resource == "ai-exam":
        return "generate"
    if tail == "export" and resource == "ai-exam":
        return "export"
    # Send patterns
    if "send" in tail or "generate" in tail:
        return "create"
    # Dashboard / stats / summary / count / review
    if any(k in tail for k in ("dashboard", "stats", "summary", "batch-count", "annual-review", "result")):
        return "read"
    # Settings / templates
    if any(k in tail for k in ("settings", "template")):
        if method == "GET":
            return "read"
        else:
            return "update"
    # Webhook
    if "webhook" in tail:
        return "create"
    # Sync-to-feishu, sync-from-feishu
    if "sync" in resource.lower():
        pass  # fall through to method-based

    # Parse preview
    if "parse" in tail or "preview" in tail:
        return "read"
    # OCR
    if "ocr" in tail:
        if method == "POST":
            return "create"
        return "read"

    # Undo
    if "undo" in tail:
        return "delete"

    # Standard CRUD by method
    if method == "GET":
        return "read"
    elif method == "POST":
        return "create"
    elif method == "PUT":
        return "update"
    elif method == "DELETE":
        return "delete"
    elif method == "PATCH":
        return "update"

    return "read"


# ============================================================
# Generate registry entries
# ============================================================


def generate_permissions(module, resource_actions):
    """Generate PermissionDef entries."""
    lines = []
    for resource, actions in sorted(resource_actions.items()):
        for action in sorted(actions):
            code = f"{module}:{resource}:{action}"
            cn_resource = _resource_label(resource, module)
            cn_action = _action_label(action)
            lines.append(
                f'    PermissionDef("{code}", "{cn_resource} - {cn_action}", "{module}", "{resource}", "{action}"),'
            )
    return lines


def generate_bindings(all_routes):
    """Generate ApiBindingDef entries."""
    lines = []
    for method, path, module, resource, action in all_routes:
        lines.append(f'    ApiBindingDef("{module}:{resource}:{action}", "{method}", "{path}"),')
    return lines


def generate_resource_labels(module, resource_actions):
    """Generate RESOURCE_LABELS entries."""
    lines = []
    for resource in sorted(resource_actions.keys()):
        code = f"{module}:{resource}"
        label = _resource_label(resource, module)
        lines.append(f'    "{code}": "{label}",')
    return lines


def _resource_label(resource, module):
    """Chinese label for a resource."""
    labels = {
        "employees": "员工管理",
        "departments": "部门管理",
        "teams": "班组管理",
        "offboarding-records": "离岗记录",
        "onboarding-records": "入职记录",
        "departure-records": "离职记录",
        "training-ledgers": "培训台账",
        "training-sessions": "培训课程",
        "training-specialists": "培训专员",
        "training-teams": "培训班组",
        "training-select-tasks": "培训选课",
        "annual-training-plans": "年度培训计划",
        "candidates": "候选人管理",
        "prejob-training-templates": "岗前培训模板",
        "system-settings": "系统设置",
        "turnover-analysis": "流失率分析",
        "ai-exam": "AI出题",
        "training-notifications": "培训通知",
        "training-notification": "培训通知",
        "training-sign-in-sheet": "培训签到表",
        "training-evaluation": "培训评估",
        "onboarding-evaluation": "上岗评估",
        "new-employees": "新员工",
        "new-onboarding-records": "新入职记录",
        "new-departure-records": "新离职记录",
        "new-offboarding-records": "新离岗记录",
        "new-departments": "新部门",
        "webhook": "飞书回调",
        # Production
        "batches": "生产批次",
        "materials": "批次物料",
        "plans": "生产计划",
        "tasks": "生产任务",
        "process-specs": "工艺规程",
        "steps": "工艺步骤",
        "parameters": "工艺参数",
        "records": "生产记录",
        "balance": "物料平衡",
        "products": "产品定义",
        "product-output": "产量记录",
        "product-sync-config": "同步配置",
        "pressure-dashboard": "压差仪表盘",
        "pressure-point-mappings": "压差点位映射",
        "pressure-records": "压差记录",
        "pressure-audit": "压差审核",
        "pressure-ocr-tasks": "压差OCR任务",
        "pressure-data-master": "压差数据管理",
        "pressure-notifications": "压差通知",
    }
    return labels.get(resource, resource.replace("-", " ").title())


def _action_label(action):
    """Chinese label for an action."""
    labels = {
        "create": "新增",
        "read": "查看",
        "update": "编辑",
        "delete": "删除",
        "export": "导出",
        "import": "导入",
        "sync": "同步",
        "generate": "生成",
        "manage": "管理",
    }
    return labels.get(action, action)


# ============================================================
# Main
# ============================================================

HR_FILES = [
    ("app/modules/hr/api.py", ["api/v1/hr"]),
    ("app/modules/hr/analysis_api.py", ["api/v1/hr", "turnover-analysis"]),
    ("app/modules/hr/ai_exam/api.py", ["api/v1/hr", "ai-exam"]),
]

PROD_FILES = [
    ("app/modules/production/api.py", ["api/v1/production"]),
    ("app/modules/production/product/api.py", ["api/v1/production"]),
    ("app/modules/production/product/output_api.py", ["api/v1/production"]),
    ("app/modules/production/product/sync_config_api.py", ["api/v1/production"]),
    ("app/modules/production/pressure/api.py", ["api/v1/production"]),
]


def main():
    all_routes = []
    module_resources = {"hr": set(), "production": set()}
    resource_actions = {"hr": {}, "production": {}}

    for module_name, files in [("hr", HR_FILES), ("production", PROD_FILES)]:
        for rel_path, prefix_parts in files:
            filepath = os.path.join(BACKEND, rel_path)
            routes = extract_routes(filepath, prefix_parts)
            for method, path, func_name, line in routes:
                mod, resource, action = classify_route(method, path)
                if mod and resource and action:
                    all_routes.append((method, path, mod, resource, action))
                    module_resources[mod].add(resource)
                    if resource not in resource_actions[mod]:
                        resource_actions[mod][resource] = set()
                    resource_actions[mod][resource].add(action)

    # Print stats
    print(f"# Total routes: {len(all_routes)}")
    print(
        f"# HR: {sum(1 for r in all_routes if r[2] == 'hr')} routes, "
        f"{len(resource_actions['hr'])} resources, "
        f"{sum(len(v) for v in resource_actions['hr'].values())} permission codes"
    )
    print(
        f"# Production: {sum(1 for r in all_routes if r[2] == 'production')} routes, "
        f"{len(resource_actions['production'])} resources, "
        f"{sum(len(v) for v in resource_actions['production'].values())} permission codes"
    )
    print()

    # Generate output
    for module in ["hr", "production"]:
        print(f"# ========== {module.upper()}_PERMISSIONS ==========")
        perms = generate_permissions(module, resource_actions[module])
        print(f"{module.upper()}_PERMISSIONS: tuple[PermissionDef, ...] = (")
        for line in perms:
            print(line)
        print(")")
        print()

    print("# ========== HR + PRODUCTION API BINDINGS ==========")
    bindings = generate_bindings(all_routes)
    for line in bindings:
        print(line)
    print()

    print("# ========== HR + PRODUCTION RESOURCE LABELS ==========")
    for module in ["hr", "production"]:
        labels = generate_resource_labels(module, resource_actions[module])
        for line in labels:
            print(line)


if __name__ == "__main__":
    main()
