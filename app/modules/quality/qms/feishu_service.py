"""飞书服务模块 - 提供飞书API调用功能"""

import httpx
from typing import Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.platform.database import async_session_factory
import logging

logger = logging.getLogger(__name__)


async def get_feishu_config_from_db() -> Optional[Dict[str, str]]:
    """从数据库获取飞书机器人配置"""
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT app_id, app_secret, is_enabled 
                FROM qms.qms_deviation_feishu_bot_config 
                WHERE is_deleted = FALSE AND is_enabled = TRUE
                LIMIT 1
            """)
        )
        row = result.fetchone()
        if row:
            return {
                "app_id": row[0],
                "app_secret": row[1],
            }
        return None


class FeishuService:
    """飞书服务类"""
    
    BASE_URL = "https://open.feishu.cn/open-apis"
    
    def __init__(self, app_id: Optional[str] = None, app_secret: Optional[str] = None):
        self.app_id = app_id
        self.app_secret = app_secret
        self._tenant_access_token: Optional[str] = None
    
    async def _ensure_config(self):
        """确保配置已加载"""
        if not self.app_id and not self.app_secret:
            config = await get_feishu_config_from_db()
            if config:
                self.app_id = config.get("app_id")
                self.app_secret = config.get("app_secret")
    
    async def get_tenant_access_token(self) -> Optional[str]:
        """获取 tenant_access_token"""
        await self._ensure_config()
        
        if not self.app_id or not self.app_secret:
            logger.warning("飞书App配置不完整，无法获取token")
            return None
            
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
                    json={
                        "app_id": self.app_id,
                        "app_secret": self.app_secret
                    }
                )
                data = response.json()
                if data.get("code") == 0:
                    self._tenant_access_token = data.get("tenant_access_token")
                    return self._tenant_access_token
                else:
                    logger.error(f"获取飞书token失败: {data}")
                    return None
        except Exception as e:
            logger.error(f"获取飞书token异常: {e}")
            return None
    
    async def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        token = await self.get_tenant_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def get_user_by_mobile(self, mobile: str, country_code: str = "86") -> Optional[Dict[str, Any]]:
        """
        根据手机号查询用户信息
        
        Args:
            mobile: 手机号
            country_code: 国家码，默认86（中国）
            
        Returns:
            用户信息字典，包含 open_id, name, en_name 等
        """
        await self._ensure_config()
        
        if not self.app_id:
            logger.warning("飞书App未配置")
            return None
            
        try:
            headers = await self._get_headers()
            if not headers.get("Authorization"):
                return None
                
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/contact/v3/users/batch_get_id",
                    headers=headers,
                    json={
                        "mobiles": [mobile],
                        "user_id_type": "open_id"
                    }
                )
                data = response.json()
                logger.info(f"飞书手机号查询响应: {data}")
                
                if data.get("code") == 0:
                    users = data.get("data", {}).get("user_list", [])
                    if users and len(users) > 0:
                        user = users[0]
                        if user.get("user_id"):
                            # 根据 open_id 获取详细信息（包含姓名）
                            user_info = await self.get_user_info(user.get("user_id"))
                            if user_info:
                                return user_info
                            else:
                                # 如果获取详细信息失败，至少返回 open_id
                                return {
                                    "open_id": user.get("user_id"),
                                    "name": "",
                                    "mobile": mobile,
                                }
                        elif user.get("code") == 99991663:
                            logger.warning(f"手机号 {mobile} 未找到对应用户")
                        else:
                            logger.warning(f"手机号 {mobile} 查询结果: {user}")
                    return None
                else:
                    logger.error(f"飞书API错误: {data}")
                    return None
                    
        except Exception as e:
            logger.error(f"根据手机号查询用户异常: {e}")
            return None
    
    async def get_user_info(self, open_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户详细信息
        
        Args:
            open_id: 用户open_id
            
        Returns:
            用户信息字典
        """
        await self._ensure_config()
        
        if not self.app_id:
            return None
            
        try:
            headers = await self._get_headers()
            if not headers.get("Authorization"):
                return None
                
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.BASE_URL}/contact/v3/users/{open_id}",
                    headers=headers,
                    params={"user_id_type": "open_id"}
                )
                data = response.json()
                
                if data.get("code") == 0:
                    user = data.get("data", {}).get("user", {})
                    return {
                        "open_id": user.get("open_id"),
                        "name": user.get("name", ""),
                        "en_name": user.get("en_name", ""),
                        "email": user.get("email", ""),
                        "mobile": user.get("mobile", ""),
                        "department_ids": user.get("department_ids", []),
                    }
                else:
                    logger.error(f"获取用户信息失败: {data}")
                    return None
                    
        except Exception as e:
            logger.error(f"获取用户信息异常: {e}")
            return None
    
    async def send_message(self, open_id: str, msg_type: str = "text", content: Any = None) -> bool:
        """
        发送消息给用户
        
        Args:
            open_id: 用户open_id
            msg_type: 消息类型 (text, post, card等)
            content: 消息内容
            
        Returns:
            是否发送成功
        """
        await self._ensure_config()
        
        if not self.app_id:
            logger.warning("飞书App未配置，无法发送消息")
            return False
            
        try:
            headers = await self._get_headers()
            if not headers.get("Authorization"):
                return False
                
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.BASE_URL}/im/v1/messages",
                    headers=headers,
                    params={"receive_id_type": "open_id"},
                    json={
                        "receive_id": open_id,
                        "msg_type": msg_type,
                        "content": content if isinstance(content, str) else str(content)
                    }
                )
                data = response.json()
                
                if data.get("code") == 0:
                    return True
                else:
                    logger.error(f"发送消息失败: {data}")
                    return False
                    
        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            return False


# 全局单例（不清除，每次调用时重新从数据库读取配置）
_feishu_service: Optional[FeishuService] = None


def get_feishu_service() -> FeishuService:
    """获取飞书服务实例"""
    global _feishu_service
    if _feishu_service is None:
        _feishu_service = FeishuService()
    return _feishu_service