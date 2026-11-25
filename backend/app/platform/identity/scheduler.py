"""Identity module scheduled tasks."""

import asyncio
import logging

logger = logging.getLogger(__name__)

stop_member_sync_flag = asyncio.Event()


async def member_sync_loop() -> None:
    """飞书成员全量同步（已停用）。

    #219 起账号改为「首次登录按需创建 + 授权时预建」，人员目录由
    ``hr.employee_profiles`` 承担，`identity.users` 不再是人员主数据。
    保留函数与 main.py 的注册点，回滚时从 git 历史恢复原实现即可。

    恢复方式：`git log -p -- app/platform/identity/scheduler.py` 取本函数历史版本。
    """
    logger.warning("飞书成员全量同步已停用（#219：账号改为首登按需创建），跳过启动")
    return
