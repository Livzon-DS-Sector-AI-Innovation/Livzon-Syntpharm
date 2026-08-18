# 常用命令

## 数据库迁移

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
uv run alembic downgrade -1
```

## 代码验证

完成代码修改后至少运行：

```bash
uv run ruff check .
uv run mypy app tests
uv run pytest
```

## 迁移验证

如果修改了 Alembic：

```bash
uv run alembic heads
```

## 应用启动验证

如果修改了应用启动、路由或依赖注入：

```bash
uv run python -c "from app.main import app; print(app.title)"
```

## 测试

```bash
uv run pytest                                    # 全量
uv run pytest tests/modules/<module>/            # 单模块
uv run pytest tests/modules/<module>/ -k "test_name"  # 单个用例
```

## 类型生成

如果后端 API 发生变化，前端必须重新生成类型：

```bash
# 使用根目录 CI 脚本（推荐，一次性完成导出 + 生成 + 漂移检查）
bash scripts/ci.sh openapi

# 或分步执行：
# 1. 在 backend 目录导出最新 spec
cd ../backend && uv run python scripts/ci/export_openapi.py

# 2. 在 frontend 目录重新生成类型
cd ../frontend && pnpm generate:api
```

CI 会检查生成的类型是否与后端同步，不同步的 PR 无法合并。
