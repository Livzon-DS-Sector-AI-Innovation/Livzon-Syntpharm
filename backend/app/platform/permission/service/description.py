"""权限码中文词表与说明生成（权限树 / 权限目录展示用）。

集中维护三样东西，供权限树、权限目录、说明句共用，避免各界面重复维护映射：

- 模块中文名：``MODULE_LABELS`` / ``module_label()``
- 资源中文名：``build_resource_label()``（手写 → 反推 → 资源码三级兜底）
- 动作短词与语义句：``ACTION_LABELS`` / ``ACTION_PHRASES``

registry 的 ``RESOURCE_LABELS`` 存在两种键写法：裸资源码（``"user"``）与
「模块:资源码」（``"quality:capa"``）。查找必须先试带模块前缀的键、再回退裸键，
否则带前缀的中文名永远查不到——这是权限树资源节点大面积显示英文资源码的根因。

本模块只做展示推导，不参与权限判定，也不写库。
"""

import re
from collections import Counter
from functools import cache

from app.platform.permission.registry import (
    ALL_PERMISSIONS,
    PLATFORM_DOMAIN_LABEL,
    RESOURCE_LABELS,
    PermissionDef,
)
from app.shared.module_registry import BUSINESS_MODULES

_PLATFORM_MODULE = "platform"

# 动作短词：权限目录「动作」列展示用（与下面的语义句子是不同粒度，不复用）
ACTION_LABELS: dict[str, str] = {
    "read": "查看",
    "create": "新增",
    "update": "修改",
    "delete": "删除",
    "manage": "管理",
    "submit": "提交",
    "approve": "审核",
    "reject": "驳回",
    "export": "导出",
    "import": "导入",
    "sync": "同步",
    "cancel": "取消",
    "execute": "执行",
    "generate": "生成",
}

# 动作语义句：权限说明里用一句话讲清这个动作能做什么。
# 覆盖 registry 中实际出现的全部动作：read / create / update / delete / manage /
# submit / approve / reject / export / import / sync / cancel / execute / generate
ACTION_PHRASES: dict[str, str] = {
    "read": "可查看列表与详情",
    "create": "可新增",
    "update": "可修改",
    "delete": "可删除",
    "manage": "可执行全部管理操作（含新增、修改、删除）",
    "submit": "可提交流转",
    "approve": "可审核通过",
    "reject": "可驳回",
    "export": "可导出数据",
    "import": "可导入数据",
    "sync": "可触发同步",
    "cancel": "可取消",
    "execute": "可执行操作",
    "generate": "可生成",
}

MODULE_LABELS: dict[str, str] = {module.code: module.name for module in BUSINESS_MODULES}
MODULE_LABELS[_PLATFORM_MODULE] = PLATFORM_DOMAIN_LABEL

# 权限名多为「查看事故」「管理事故」，剥掉动作前缀即可得到资源中文名。
# 用于 RESOURCE_LABELS 未登记的资源，避免说明与节点标题里出现英文资源码。
_ACTION_NAME_PREFIXES: tuple[str, ...] = (
    "查看",
    "新增",
    "修改",
    "删除",
    "管理",
    "提交",
    "审核",
    "驳回",
    "导出",
    "导入",
    "同步",
    "取消",
    "执行",
    "生成",
    "访问",
)

# 另一类命名是「CAPA管理 - 查看」，破折号前本身就是资源名
_DASH_RE = re.compile(r"\s+-\s+")

# 「管理事故（创建/修改/删除/审批）」这类名称把动作清单塞在括号里，资源名里不需要重复
_ACTION_NOTE_RE = re.compile(r"[（(][^）)]*[/、][^）)]*[）)]\s*$")


def _group_definitions() -> dict[tuple[str, str], tuple[PermissionDef, ...]]:
    grouped: dict[tuple[str, str], list[PermissionDef]] = {}
    for definition in ALL_PERMISSIONS:
        grouped.setdefault((definition.module, definition.resource), []).append(definition)
    return {key: tuple(value) for key, value in grouped.items()}


_DEFINITIONS_BY_KEY: dict[tuple[str, str], tuple[PermissionDef, ...]] = _group_definitions()


def resource_definitions(module: str, resource: str) -> tuple[PermissionDef, ...]:
    """同一模块同一资源下的全部权限定义（资源中文名反推的输入）。"""
    return _DEFINITIONS_BY_KEY.get((module, resource), ())


def module_label(module_code: str) -> str:
    """模块中文名，未登记时回退模块码。"""
    return MODULE_LABELS.get(module_code, module_code)


def action_label(action: str) -> str:
    """动作短词，未登记时回退原值。"""
    return ACTION_LABELS.get(action, action)


@cache
def _derived_resource_label(definition: PermissionDef) -> str:
    """不看注册表、只从权限名推导资源中文名（反推兜底用）。"""
    name = definition.name
    if _DASH_RE.search(name):
        return _ACTION_NOTE_RE.sub("", _DASH_RE.split(name, maxsplit=1)[0]).strip()
    label = name
    for prefix in _ACTION_NAME_PREFIXES:
        if label.startswith(prefix) and len(label) > len(prefix):
            label = label[len(prefix) :]
            break
    return _ACTION_NOTE_RE.sub("", label).strip()


@cache
def build_resource_label(module: str, resource: str, definitions: tuple[PermissionDef, ...] = ()) -> str:
    """资源中文名的唯一出口：手写优先 → 权限名反推众数 → 资源码兜底。

    反推对同资源下多个权限定义各算一次（「查看事故」「管理事故」都得「事故」），
    取众数；票数并列时按长度、再按字典序排序，保证结果稳定可复现。
    """
    registered = RESOURCE_LABELS.get(f"{module}:{resource}") or RESOURCE_LABELS.get(resource)
    if registered:
        return registered

    pool = definitions or resource_definitions(module, resource)
    candidates = [label for label in (_derived_resource_label(definition) for definition in pool) if label]
    if not candidates:
        return resource

    votes = Counter(candidates)
    return min(votes.items(), key=lambda item: (-item[1], len(item[0]), item[0]))[0]


@cache
def build_permission_summary(definition: PermissionDef) -> str:
    """生成一句中文说明，如「安全管理 · 事故 — 可查看列表与详情」。

    ``PermissionDef`` 是 frozen dataclass（可哈希），结果按定义缓存，树渲染时无重复拼接开销。
    资源段与上面资源节点标题共用 ``build_resource_label``，保证两处名字永远一致。
    """
    label = module_label(definition.module)
    phrase = ACTION_PHRASES.get(definition.action, f"可执行 {definition.action} 操作")
    # 注册表里没有同资源的其它定义时（如测试构造的临时定义），退回用这条定义自身反推
    pool = resource_definitions(definition.module, definition.resource) or (definition,)
    resource = build_resource_label(definition.module, definition.resource, pool)
    # 模块准入类权限的资源段与模块名重复；反推失败时也省略，避免说明里冒出英文资源码
    if not resource or resource == definition.resource or resource in label:
        return f"{label} — {phrase}"
    return f"{label} · {resource} — {phrase}"
