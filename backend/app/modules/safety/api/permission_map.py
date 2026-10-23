"""Safety 模块的路由资源 → 权限码映射。

背景：safety 的 20 个子路由原本统一挂 `safety:module:read`，导致「只有模块只读码
的账号也能创建/删除/审批」。这里按「资源 + HTTP 方法」细分：

- GET/HEAD（以及语义等价的只读 POST）→ `<prefix>:read`
- 其余写动作 → `<prefix>:manage`

表是唯一权威：`safety/api/__init__.py` 用它生成依赖，registry 的绑定登记也用同一份
口径生成（见 `scripts/ci/gen_permission_bindings.py` 的 safety 分支）。
新增资源时必须同时补 registry 的 PermissionDef，否则导入期校验会报错。
"""

from typing import Final

# resource（URL 资源段）→ (只读码, 写码)
SAFETY_RESOURCE_CODES: Final[dict[str, tuple[str, str]]] = {
    "accidents": ("safety:accident:read", "safety:accident:manage"),
    "ai-workflow-configs": ("safety:ai-workflow-config:read", "safety:ai-workflow-config:manage"),
    "checks": ("safety:check:read", "safety:check:manage"),
    "contractors": ("safety:contractor:read", "safety:contractor:manage"),
    "daily-risk-reports": ("safety:daily-risk-report:read", "safety:daily-risk-report:manage"),
    "ehs-changes": ("safety:ehs-change:read", "safety:ehs-change:manage"),
    # 枚举字典 / 文件下载只有读动作，直接复用模块级只读码
    "enums": ("safety:module:read", "safety:module:read"),
    "feishu": ("safety:feishu:manage", "safety:feishu:manage"),
    "files": ("safety:module:read", "safety:module:read"),
    "hazard-identifications": ("safety:hazard-identification:read", "safety:hazard-identification:manage"),
    "hazards": ("safety:hazard:read", "safety:hazard:manage"),
    "knowledge-articles": ("safety:knowledge-article:read", "safety:knowledge-article:manage"),
    "knowledge-graph": ("safety:knowledge-graph:read", "safety:knowledge-graph:manage"),
    "oh-hazard-monitors": ("safety:oh-hazard-monitor:read", "safety:oh-hazard-monitor:manage"),
    "oh-health-exams": ("safety:oh-health-exam:read", "safety:oh-health-exam:manage"),
    "regulations": ("safety:regulation:read", "safety:regulation:manage"),
    "revisions": ("safety:regulation-revision:read", "safety:regulation-revision:manage"),
    "scheduled-tasks": ("safety:scheduled-task:read", "safety:scheduled-task:manage"),
    "special-operation-ledger": ("safety:special-operation-ledger:read", "safety:special-operation-ledger:manage"),
    "special-operation-permits": ("safety:special-operation-permit:read", "safety:special-operation-permit:manage"),
    "special-operation-personnel": (
        "safety:special-operation-personnel:read",
        "safety:special-operation-personnel:manage",
    ),
    "special-operation-reports": ("safety:special-operation-report:read", "safety:special-operation-report:manage"),
    "trainings": ("safety:training:read", "safety:training:manage"),
    "training-certificates": ("safety:training-certificate:read", "safety:training-certificate:manage"),
    "training-records": ("safety:training-record:read", "safety:training-record:manage"),
}

# 语义只读的 POST（导出 / 预览 / 解析查询）：按只读码校验
SAFETY_READ_ONLY_SUFFIXES: Final[tuple[str, ...]] = (
    "/export",
    "/export-pdf",
    "/parse-query",
    "/preview",
    "/preview-card",
    "/split-preview",
    "/ai-preview",
    "/download",
)

MODULE_PATH_SEGMENT: Final[str] = "/safety/"
FALLBACK_CODES: Final[tuple[str, str]] = ("safety:module:read", "safety:module:read")


def resolve_code(method: str, path: str) -> str:
    """按方法与路径解析该请求应检查的权限码（依赖与绑定生成脚本共用同一口径）。

    以 `/safety/` 段定位（而不是写死 `/api/v1` 前缀），避免 `API_V1_PREFIX`
    被改后资源段解析失败、整模块回落粗码。
    """
    marker = MODULE_PATH_SEGMENT
    idx = path.find(marker)
    relative = path[idx + len(marker) :].strip("/") if idx >= 0 else ""
    resource = relative.split("/")[0] if relative else ""
    read_code, write_code = SAFETY_RESOURCE_CODES.get(resource, FALLBACK_CODES)
    if method.upper() in ("GET", "HEAD", "OPTIONS"):
        return read_code
    if relative and ("/" + relative.rstrip("/")).endswith(SAFETY_READ_ONLY_SUFFIXES):
        return read_code
    return write_code
