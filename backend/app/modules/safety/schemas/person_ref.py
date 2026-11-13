"""人员引用契约 — 台账中「系统用户」的统一展示模型。

台账里的人员字段有两种来源：
- 新数据：落库 ``identity.users`` 的 UUID + 姓名快照；
- 历史数据（Bitable / Excel 导入）：只有姓名，UUID 为空。

服务端读取时做一次批量解析：姓名唯一命中（或同名多人但部门消歧唯一）即视为已关联，
返回该用户 UUID 并补充头像与部门；同名多人无法消歧、或查无此人时只保留姓名，
走首字母色块 + 「待确认」标记。
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class PersonRef(BaseModel):
    """人员引用（只含展示所需字段，不返回手机号 / 邮箱等敏感信息）。"""

    id: uuid.UUID | None = Field(
        None, description="已确认关联的系统用户 UUID（姓名唯一匹配时由服务端解析给出，可能尚未落库）"
    )
    name: str | None = Field(None, description="姓名（优先取台账姓名快照）")
    avatar_url: str | None = Field(None, description="头像 URL（服务端已按 avatar_thumb → avatar_url 归一）")
    department: str | None = Field(None, description="部门")
    pending: bool = Field(False, description="姓名无法唯一解析（同名多人或查无此人），前端显示「待确认」")
