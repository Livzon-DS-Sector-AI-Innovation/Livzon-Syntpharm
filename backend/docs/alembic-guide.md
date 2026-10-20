# Alembic 迁移机制说明

本文讲清三件事：**Alembic 解决什么问题、它到底怎么工作、出问题怎么查**。

- 日常命令速查：[database-setup.md](database-setup.md)
- 操作流程：[development-guide.md](development-guide.md#数据库迁移操作)
- 命名/单模块/Orphan Table 等硬性规则的权威来源：[AGENTS.md](../AGENTS.md) 的「迁移规范」

## 目录

- [1. 它解决什么问题](#1-它解决什么问题)
- [2. 工作机制](#2-工作机制)
- [3. 本项目对 Alembic 的 5 处改造](#3-本项目对-alembic-的-5-处改造)
- [4. 版本号规范（项目铁律）](#4-版本号规范项目铁律)
- [5. 常见故障与原理对应](#5-常见故障与原理对应)
- [6. 日常操作速查](#6-日常操作速查)
- [7. 共享库（UAT）的团队约定](#7-共享库uat的团队约定)
- [8. 相关文件索引](#8-相关文件索引)

---

## 1. 它解决什么问题

### 1.1 没有它会发生什么

代码里的模型（`models.py`）和数据库里真实的表，是两份**互相不知道对方**的东西：

- 改了模型、没告诉数据库 → 运行时 `relation "xxx" does not exist` 或 `column does not exist`
- 改了数据库、没告诉代码 → 别人的环境行为和你不一样，且无法追溯
- 靠人肉发 SQL → 谁在什么时候改了哪张表，查不出来，也没法回退

本项目有 12 个业务模块、800+ 个模型、80+ 次结构变更、多人并行开发。人肉同步是不可能的。

### 1.2 Alembic 给出的答案

把"结构变更"变成**代码文件**：

- 每一次改结构 = 一个 `.py` 文件，可以 review、可以追溯、可以回退
- 数据库里存一个"进度标记"，一眼看出这个库停在哪一版

### 1.3 打个比方

| 角色 | 对应物 |
|---|---|
| 设计图纸 | `backend/app/**/models.py` 里的 SQLAlchemy 模型 |
| 盖好的房子 | PostgreSQL 里实际的 schema / 表 / 列 |
| 施工步骤单 | `backend/alembic/versions/NNNN_*.py` |
| 门牌上的进度 | `alembic_version` 表（只有一行：已施工到第几号） |
| `alembic upgrade head` | 照着施工单，一路干到最新一版 |

**核心心智模型**：Alembic 做的事就是"让图纸和房子始终一致"，而一致性靠人写的施工单保证，不是自动同步。

---

## 2. 工作机制

### 2.1 三个角色

| 角色 | 位置 | 作用 |
|---|---|---|
| 模型（图纸） | `backend/app/**/models.py`，继承 `app/shared/base_model.py` 的 `Base` | 描述"应该长什么样" |
| 迁移文件（施工单） | `backend/alembic/versions/NNNN_*.py` | 描述"从上一版到这版要做什么操作" |
| 版本表（进度） | `alembic_version`，建在默认 `search_path`（通常是 `public`） | 记录"库当前停在哪一版" |

### 2.2 关键：它不做"结构比对"

`alembic upgrade head` 的行为是：

1. 读出 `alembic_version` 当前值，比如 `0066_...`
2. 沿着 `down_revision` 链，找出「当前版本 → head」之间**还没执行过**的文件
3. 按顺序执行这些文件里的 `upgrade()` 函数

它**不会**去比对表结构、也不会猜你想要什么。文件里写什么就执行什么。

所以：
- 只改模型不写迁移 → 库纹丝不动 → 运行时报表/列不存在
- 迁移文件写错了 → 它就照着错的东西执行

`alembic revision --autogenerate` 只是**生成文件的助手**（把模型和库的差异草拟成代码），它是开发期工具，不是运行时行为。

### 2.3 版本链 = 一条单链表

每个迁移文件声明两个标识：

```python
revision: str = "0082_create_permission_schema"
down_revision: Union[str, None] = "0066_add_knowledge_article_document_fields"
```

- `revision` 是自己这一段的名字
- `down_revision` 指向上一段的 `revision`

首尾相接形成一条链，链尾叫 `head`。`alembic_version` 里存的是"当前插在链上的哪个位置"。

**关键限制**：`alembic_version` 只有一行。所以"链"必须是**单线的**。一旦出现两条并行的链，就有两个 `head`，Alembic 不知道该走哪条 → 报 `Multiple head revisions`。

### 2.4 版本号不是哈希

Alembic 默认用随机哈希当 revision ID（如 `3cb28d1e1ac7`）。本项目**明令禁止**，必须用顺序编号 `NNNN_描述`。原因：人要能一眼从文件名找到"哪一次改动建了这张表"。

---

## 3. 本项目对 Alembic 的 5 处改造

都在 `backend/alembic/env.py` 和 `backend/alembic.ini` 里。

### 3.1 汇总 12 个模块的模型

`env.py` 会遍历 `BUSINESS_MODULES`，逐个 `import app.modules.<module>.models`，再加上 `platform` / `core` 的模型，最后：

```python
target_metadata = Base.metadata
```

**推论**：新建模块或模型文件后，必须保证它能被 import 到（新模块要在 `app/shared/module_registry.py` 注册）。否则 Alembic 根本看不见这张表，autogenerate 会"漏生成"。

### 3.2 按 PostgreSQL schema 隔离

本项目按模块分 schema（`quality`、`safety`、`permission`……），所以配了三样东西：

| 配置 | 作用 |
|---|---|
| `include_schemas=True` + `include_name` / `include_object` 白名单 `PROJECT_SCHEMAS` | 只认自己定义的 schema，**不碰 `public`、`pg_catalog`、`information_schema`** |
| 环境变量 `ALEMBIC_TARGET_SCHEMA` | autogenerate 时只对指定 schema 生成差异 —— 这是"单模块原则"的落地手段 |
| `process_revision_directives` 钩子 | autogenerate 时自动在迁移头顶插入 `CREATE SCHEMA IF NOT EXISTS xxx`，新模块第一次建表不用手写建 schema |

注意 `ALEMBIC_TARGET_SCHEMA` **只影响 autogenerate**（生成哪些差异），不影响 `upgrade` 的执行。

### 3.3 偷偷换了数据库驱动

应用层用异步驱动（`DATABASE_URL` 是 `postgresql+asyncpg://`），但 Alembic 要**同步**驱动。`env.py` 会把 URL 里的 `postgresql+asyncpg://` 剥掉，重新拼成 `postgresql+pg8000://`：

```python
db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "")
sync_url = f"postgresql+pg8000://{quote_plus(parsed.username)}:...@{parsed.hostname}:{parsed.port or 5432}/{db_name}"
```

**推论**：不要奇怪为什么 Alembic 的连接方式和应用不一致；也不要指望它能用 asyncpg。

### 3.4 版本表自己建，而且字段放宽到 varchar(255)

`env.py` 在执行迁移前会先补一句：

```sql
CREATE TABLE IF NOT EXISTS alembic_version (version_num varchar(255) NOT NULL PRIMARY KEY)
```

为什么是 `255`？Alembic 官方默认是 `varchar(32)`，但本项目的 revision ID 是 `0082_create_permission_schema` 这种长名字（已超过 32 字符），**默认长度会截断版本号，导致链彻底对不上**。所以必须放宽。

### 3.5 命名规范用 CI 脚本强制

有两个脚本守着命名和范围规则（详见下一节）：

- `backend/scripts/ci/check_migration_numbers.py`
- `backend/scripts/ci/check_migration_scope.py`

**它们只在 CI/PR 时跑。** 本地手动 `alembic upgrade`、或在服务器上手动跑，全部绕过这两道门禁。

---

## 4. 版本号规范（项目铁律）

### 4.1 三条硬规则

1. **格式**：`NNNN_描述`（4 位数字 + 下划线 + 字母数字下划线），如 `0082_create_permission_schema`
2. **文件名前缀必须等于 revision 前缀**：文件叫 `0082_xxx.py`，里面 `revision` 就必须是 `0082_xxx`
3. **引用完整**：`down_revision` 必须指向一个真实存在的 `revision`；任意两个文件的 `NNNN` 全局唯一

### 4.2 谁来检查

| 脚本 | 检查范围 | 检查内容 |
|---|---|---|
| `backend/scripts/ci/check_migration_numbers.py` | 整个 versions 目录（跨文件） | 编号全局唯一、文件名前缀 == revision 前缀、每个 `down_revision` 都能解析到 |
| `backend/scripts/ci/check_migration_scope.py` | 单个迁移文件 | 命名合规 + **只能动一个 schema**（`0001_baseline_full_schema` 是唯一允许跨所有 schema 的例外） |

CI 自动执行，违反会导致 PR 无法合并。

### 4.3 为什么编号会"断档"

偶尔会看到编号不连续（比如有 `0066` 接着 `0082`）。这**本身不是错误**——不同分支各自带着自己那批迁移文件，本分支没合进别人的文件时就会出现空洞。

**但断档意味着链断了**：如果数据库的 `alembic_version` 指向一个你本地没有的文件，Alembic 会直接报 `Can't locate revision identified by 'xxx'`。这时候需要的是"把文件补齐"或"用 merge migration 收拢"，而不是改版本号。

### 4.4 两条链并存时怎么办

项目已有 merge migration 先例：

- `0060_merge_migration_heads.py`
- `0061_merge_0056_heads.py`

merge 迁移本身不含任何 DDL，只声明"把这两个 head 合成一个"：

```python
down_revision = ("0081_add_doc_gen_caches", "0083_create_dictionary_tables")
```

---

## 5. 常见故障与原理对应

### 5.1 报错对照表

| 现象 | 原理 | 处置 |
|---|---|---|
| `relation "xxx" does not exist` | 模型有表、但迁移没写或没执行 | 补迁移文件 → `upgrade head` |
| `Can't locate revision identified by 'xxx'` | 库里记的版本号，在你当前代码里找不到（切了分支 / 文件被删 / 重编号） | 把该迁移文件找回来；确认库状态正确后用 `alembic stamp <rev>` 只改进度标记 |
| `Multiple head revisions are present` | 两条并行的链，存在两个 head | 补一个 merge migration 收拢 |
| 迁移执行到一半报错 | 版本没推进，但前面几条 DDL 已生效 → 库处于"半成品"状态 | 人工核对已执行的 DDL，决定手工回补还是修文件后重跑 |
| autogenerate 生成了别的模块的表 | 没设 `ALEMBIC_TARGET_SCHEMA` | 删掉文件，加环境变量重新生成 |

### 5.2 危险操作：目标版本不在当前 head 的后代链上

```bash
alembic upgrade 0082_create_permission_schema   # 库当前在 0081_xxx 时
```

Alembic 发现目标不是当前版本的"后代"，**会先 downgrade 到两人的共同祖先，再 upgrade 上去**。也就是说，它会**倒着执行中间那批迁移的 `downgrade()`**——把别人的施工拆掉。

在共享库上这么干，等于拿别人的表结构开玩笑。

**记法**：`upgrade` 不等于"只往上走"。要升到某个特定版本前，先 `alembic current` + `alembic heads` 确认目标确实在当前链的后方。

### 5.3 关于 downgrade 的实际情况

`backend/alembic/versions/` 下**每个迁移都写了 `downgrade()` 实现**（当前分支 62 个文件无一为空实现）。

但"写了"不等于"能安全回退"：

- 简单建表 → `op.drop_table(...)`，可回退
- 改列类型 / 重命名 / 数据回填 → 逆操作往往是粗略的，可能丢数据
- 破坏性操作（删表、删列）→ 回退只能建回空表，数据回不来

**结论**：`downgrade` 仅用于本地开发的快速纠错，不要当生产回滚手段。

---

## 6. 日常操作速查

### 6.1 命令

```bash
# 看库当前停在哪一版
uv run alembic current

# 看代码侧有几个 head（正常应只有 1 个）
uv run alembic heads

# 看完整迁移历史
uv run alembic history

# 升到最新版
uv run alembic upgrade head

# 生成新迁移（务必限定模块 schema）
ALEMBIC_TARGET_SCHEMA=permission uv run alembic revision --autogenerate -m "create permission schema"

# 不连库、只输出 DDL（离线模式，用于审查生成的 SQL）
uv run alembic upgrade 0082:0083 --sql
```

### 6.2 在本机直接跑的两个前置条件

1. `app/core/config.py` 的 `check()` 会无条件校验 `FEISHU__PLATFORM__APP_ID`、`FEISHU__PLATFORM__APP_SECRET`、`FRONTEND_URL`，缺任何一个直接启动失败（值可以是 dummy）
2. `DATABASE_URL` 指向哪个库，迁移就打在哪个库上

**日常更推荐走容器**（环境变量齐全）：

```bash
docker compose -f docker-compose.local-dev.yml --env-file .env.local run --rm migrate
```

### 6.3 改模型的标准流程

1. 拉最新代码 → `upgrade head`（先和别人的改动对齐）
2. 改模型
3. `ALEMBIC_TARGET_SCHEMA=<schema>` + `revision --autogenerate`
4. **人工审查生成的文件**：autogenerate 检测不到数据回填、列重命名、破坏性操作
5. 模型和迁移必须在**同一个 PR**

---

## 7. 共享库（UAT）的团队约定

UAT 是多人共用的库，而 `alembic_version` 只有一行 → 谁先跑谁的版本号生效。

### 7.1 危险在哪

- 你的迁移链和库里的版本号对不上 → 报错，或更糟
- 两条链并存 → 双 head，收不拢
- 强行 `upgrade` 到非后代版本 → 把别人的迁移倒着执行掉

### 7.2 落库前必做

1. `select version_num from alembic_version;` 看库实际停在哪
2. `alembic heads` 看代码侧有几个 head，确认库里的版本号在你的链上
3. 备份（`pg_dump`）
4. 通知同事

### 7.3 推荐流程

不要在共享库上做开发试验。要测自己的分支，走一次性集成分支：

从目标分支（如 `origin/uat`）拉一个临时分支 → 合入自己的开发分支 → 在临时分支里补 merge migration 解掉双 head → 推送 → 备份 + 通知后落库。

---

## 8. 相关文件索引

| 文件 | 说明 |
|---|---|
| `backend/alembic.ini` | Alembic 基础配置（脚本位置、日志） |
| `backend/alembic/env.py` | 运行时环境：模型汇总、schema 白名单、驱动替换、版本表创建 |
| `backend/alembic/script.py.mako` | 新迁移文件的模板 |
| `backend/alembic/versions/` | 全部迁移文件 |
| `backend/scripts/ci/check_migration_numbers.py` | 跨文件编号检查 |
| `backend/scripts/ci/check_migration_scope.py` | 单文件命名 + 单模块 schema 检查 |
| `backend/app/shared/module_registry.py` | `BUSINESS_MODULES` / `BUSINESS_SCHEMAS`，决定哪些模块的模型会被汇总 |
| `backend/app/shared/base_model.py` | `Base` 与 `BaseModel` |

## 9. 与本项目其他文档的关系

- **本文**：原理、机制、故障的"为什么"
- [database-setup.md](database-setup.md)：命令速查、建库步骤
- [development-guide.md](development-guide.md#数据库迁移操作)：开发流程中的迁移操作
- [AGENTS.md](../AGENTS.md)：命名的强制规则、模型与迁移必须同 PR、Orphan Table 处理规则
