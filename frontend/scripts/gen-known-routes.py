#!/usr/bin/env python3
"""生成「已知页面路径清单」→ src/lib/navigation/known-routes.ts

用途：菜单管理里保存自定义菜单时，判断路径是否有对应页面（没有就提示"点开会是 404"）。
原因：Next 运行时枚举不出全部路由，只能靠构建期扫描 app 目录得到静态清单。

用法（在 frontend 目录下）：

    python3 scripts/gen-known-routes.py

新增页面后重新跑一次即可（清单文件会整体重写）。
"""

from __future__ import annotations

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
APP_DIR = os.path.join(PROJECT_ROOT, "src", "app")
OUT_FILE = os.path.join(PROJECT_ROOT, "src", "lib", "navigation", "known-routes.ts")


def collect_routes() -> list[str]:
    routes: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(APP_DIR):
        if "page.tsx" not in filenames:
            continue
        rel = os.path.relpath(dirpath, APP_DIR)
        parts = [part for part in rel.split(os.sep) if part != "."]
        # 路由组 (dashboard) / (mobile) 不影响 URL，去掉
        parts = [p for p in parts if not (p.startswith("(") and p.endswith(")"))]
        route = "/" + "/".join(parts)
        routes.append(route.rstrip("/") or "/")
    return sorted(set(routes))


def to_pattern(route: str) -> str:
    """动态段 [id] → [^/]+，用于正则匹配。"""
    return re.sub(r"\[[^\]]+\]", "[^/]+", route)


def render(static_routes: list[str], dynamic_patterns: list[str]) -> str:
    out: list[str] = [
        "/**",
        " * 已知页面路径清单（由 scripts/gen-known-routes.py 扫描 app 目录下的 page.tsx 生成，勿手改）。",
        " *",
        " * 用途：菜单管理里保存自定义菜单时，提示「该路径没有对应页面，点开会是 404」。",
        " * 为什么需要：Next 运行时枚举不出全部路由，只能靠这份构建期清单校验。",
        " *",
        " * 重新生成：cd frontend && python3 scripts/gen-known-routes.py",
        " */",
        "",
        "/** 静态路径（精确匹配） */",
        "export const KNOWN_STATIC_ROUTES: readonly string[] = [",
    ]
    out += [f"  '{route}'," for route in static_routes]
    out += [
        "]",
        "",
        "/** 动态路径模板（参数段已转成正则片段，按正则匹配） */",
        "export const KNOWN_DYNAMIC_ROUTE_PATTERNS: readonly string[] = [",
    ]
    out += [f"  '{pattern}'," for pattern in dynamic_patterns]
    out += [
        "]",
        "",
        "/** 该路径是否有对应页面（忽略 query 与结尾斜杠；外链一律视为有效，不参与校验） */",
        "export function isKnownRoute(path: string): boolean {",
        "  if (!path.startsWith('/')) return true",
        "  const clean = path.split('?')[0].replace(/\\/+$/, '') || '/'",
        "  if (KNOWN_STATIC_ROUTES.includes(clean)) return true",
        "  return KNOWN_DYNAMIC_ROUTE_PATTERNS.some((pattern) => new RegExp(`^${pattern}$`).test(clean))",
        "}",
        "",
    ]
    return "\n".join(out)


def main() -> None:
    routes = collect_routes()
    static_routes = [route for route in routes if "[" not in route]
    dynamic_patterns = sorted({to_pattern(route) for route in routes if "[" in route})

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as handle:
        handle.write(render(static_routes, dynamic_patterns))

    print(f"静态路径 {len(static_routes)} 条，动态模板 {len(dynamic_patterns)} 条 → {OUT_FILE}")


if __name__ == "__main__":
    main()
