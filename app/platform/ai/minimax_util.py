"""MiniMax AI 工具类

提供统一的 MiniMax AI 接口调用能力，支持文本生成和图片识别任务。
配置通过环境变量或AI配置获取。
"""

import os
import json
from typing import Optional

import httpx

# 默认配置（环境变量作为备选）
DEFAULT_MODEL: str = "MiniMax-Text-01"
VISION_MODEL: str = "MiniMax-VL-01"
DEFAULT_BASE_URL: str = "https://api.minimax.chat/v1"


def _get_api_key() -> str:
    """获取API Key，优先从AI配置获取，其次从环境变量"""
    try:
        from app.core.ai_config import get_minimax_api_key
        return get_minimax_api_key()
    except Exception:
        pass
    return os.getenv("MINIMAX_API_KEY", "")


def _get_base_url() -> str:
    """获取Base URL"""
    try:
        from app.core.ai_config import get_minimax_base_url
        return get_minimax_base_url()
    except Exception:
        pass
    return os.getenv("MINIMAX_BASE_URL", DEFAULT_BASE_URL)


def _get_vision_model() -> str:
    """获取视觉模型"""
    try:
        from app.core.ai_config import get_vision_model
        return get_vision_model()
    except Exception:
        return VISION_MODEL


def _get_text_model() -> str:
    """获取文本模型"""
    try:
        from app.core.ai_config import get_text_model
        return get_text_model()
    except Exception:
        return "MiniMax-Text-01"


DEFAULT_BASE_URL = "https://api.minimaxi.com/v1"
DEFAULT_API_KEY = ""
DEFAULT_MODEL = "abab6.5s-chat"
VISION_MODEL = "MiniMax-VL-01"


class MinimaxAiUtil:
    """MiniMax AI 工具类

    提供文本生成接口封装，支持自定义 System Prompt 和 User Message。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """初始化 MiniMax AI 工具

        Args:
            api_key: MiniMax API Key，若不传则从AI配置或环境变量获取
            base_url: API 基础 URL，默认使用官方地址
            timeout: 请求超时时间（秒），默认 30 秒
        """
        self.api_key = api_key or _get_api_key()
        self.base_url = base_url or _get_base_url()
        self.timeout = timeout

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """调用 MiniMax AI 文本生成接口

        Args:
            system_prompt: 系统提示词，定义 AI 角色和行为规范
            user_message: 用户输入的消息内容
            model: 使用的模型名称，默认使用 MiniMax-Text-01
            temperature: 生成温度，控制随机性（0-1），默认 0.7
            max_tokens: 最大生成 token 数，默认 1024

        Returns:
            AI 返回的文本内容

        Raises:
            httpx.HTTPStatusError: HTTP 请求失败时抛出
            ValueError: API Key 未配置时抛出
        """
        if not self.api_key:
            raise ValueError("MiniMax API Key 未配置，请在AI配置设置页面配置API Key")

        url = f"{self.base_url}/text/chatcompletion_v2"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model or DEFAULT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()
            print(f"MiniMax API Response: {result}")
            # 解析 MiniMax 返回格式
            choices = result.get("choices", [])
            if choices and len(choices) > 0:
                choice = choices[0]
                # 格式: choices[0].message.content
                message = choice.get("message", {})
                content = message.get("content", "")
                if content:
                    return content
            return ""


class MinimaxVisionUtil(MinimaxAiUtil):
    """MiniMax 视觉理解工具类

    支持图片输入的多模态 AI 接口调用。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """初始化 MiniMax 视觉工具

        Args:
            api_key: MiniMax API Key，若不传则从AI配置或环境变量获取
            base_url: API 基础 URL
            timeout: 请求超时时间（秒），默认 60 秒
        """
        super().__init__(api_key, base_url, timeout)

    def _safe_print(self, msg):
        """安全打印，避免GBK编码问题"""
        try:
            print(msg)
        except Exception:
            print(repr(msg[:100]) if len(msg) > 100 else repr(msg))

    async def recognize_image(
        self,
        image_urls: list[str],
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        """调用 MiniMax VL 模型识别图片

        Args:
            image_urls: 图片 URL 列表（支持多张图片）
            prompt: 识别提示词，描述需要提取的信息
            model: 使用的视觉模型名称，默认使用 MiniMax-VL-01
            max_tokens: 最大返回 token 数，默认 1024

        Returns:
            AI 返回的文本内容（通常是 JSON 格式）
        """
        # 每次调用时动态获取配置（支持运行时更新配置）
        api_key = _get_api_key()
        base_url = _get_base_url()

        if not api_key:
            raise ValueError("MiniMax API Key 未配置，请在AI配置设置页面配置API Key")

        vision_model = model or _get_vision_model()

        # MiniMax 使用 OpenAI 兼容格式
        # base_url 格式: https://api.minimaxi.com/v1
        base = base_url.rstrip('/')
        url = f"{base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # 构建消息内容（OpenAI 兼容格式）
        content = [{"type": "text", "text": prompt}]

        # 添加图片（支持多张）- 本地文件转为base64
        for image_url in image_urls:
            if image_url.startswith('/'):
                # 本地文件路径，读取并转为base64
                import os
                from pathlib import Path

                # 获取后端根目录（使用resolve确保绝对路径）
                backend_dir = Path(__file__).resolve().parent.parent.parent.parent
                uploads_dir = backend_dir / "uploads"
                self._safe_print(f"[DEBUG] Backend dir: {backend_dir}")
                self._safe_print(f"[DEBUG] Uploads dir: {uploads_dir}")
                self._safe_print(f"[DEBUG] Image URL: {image_url}")

                # 去掉 /uploads/ 前缀
                relative_path = image_url.lstrip('/')
                if relative_path.startswith('uploads/'):
                    relative_path = relative_path[8:]
                file_path = uploads_dir / relative_path
                self._safe_print(f"[DEBUG] File path: {file_path}")

                if file_path.exists():
                    import base64
                    with open(file_path, "rb") as f:
                        img_data = f.read()
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        # 根据文件扩展名确定media_type
                        ext = file_path.suffix.lower()
                        if ext in ['.png']:
                            media_type = "image/png"
                        elif ext in ['.gif']:
                            media_type = "image/gif"
                        elif ext in ['.webp']:
                            media_type = "image/webp"
                        else:
                            media_type = "image/jpeg"
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{img_base64}"
                            }
                        })
                else:
                    # 文件不存在，使用URL
                    self._safe_print(f"File not found: {file_path}")
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    })
            else:
                # 外部URL
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                })

        payload = {
            "model": vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)

            # 如果失败，打印详细错误信息
            if response.status_code != 200:
                error_text = response.text
                self._safe_print(f"MiniMax API Error: {response.status_code}")
                self._safe_print(f"Response: {error_text[:500]}")
                self._safe_print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)[:1000]}")

            response.raise_for_status()

            result = response.json()
            # 解析 OpenAI 兼容格式返回
            choices = result.get("choices", [])
            if choices and len(choices) > 0:
                return choices[0].get("message", {}).get("content", "")
            return ""

    async def recognize_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> str:
        """调用 MiniMax 文本模型处理纯文本

        Args:
            prompt: 提示词
            model: 使用的模型名称，默认使用 MiniMax-Text-01
            max_tokens: 最大返回 token 数，默认 4096

        Returns:
            AI 返回的文本内容
        """
        # 每次调用时动态获取配置（支持运行时更新配置）
        api_key = _get_api_key()
        base_url = _get_base_url()

        if not api_key:
            raise ValueError("MiniMax API Key 未配置，请在AI配置设置页面配置API Key")

        # 使用文本模型
        text_model = model or _get_text_model()

        # MiniMax 使用 OpenAI 兼容格式
        base = base_url.rstrip('/')
        url = f"{base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": text_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code != 200:
                error_text = response.text
                self._safe_print(f"MiniMax API Error: {response.status_code}")
                self._safe_print(f"Response: {error_text[:500]}")

            response.raise_for_status()

            result = response.json()
            choices = result.get("choices", [])
            if choices and len(choices) > 0:
                return choices[0].get("message", {}).get("content", "")
            return ""


# 全局单例实例（延迟初始化）
_ai_util_instance: Optional[MinimaxAiUtil] = None
_vision_util_instance: Optional[MinimaxVisionUtil] = None


def get_ai_util() -> MinimaxAiUtil:
    """获取全局 AI 工具单例

    Returns:
        MinimaxAiUtil 实例
    """
    global _ai_util_instance
    if _ai_util_instance is None:
        _ai_util_instance = MinimaxAiUtil()
    return _ai_util_instance


def get_vision_util() -> MinimaxVisionUtil:
    """获取全局视觉理解工具单例

    Returns:
        MinimaxVisionUtil 实例
    """
    global _vision_util_instance
    if _vision_util_instance is None:
        _vision_util_instance = MinimaxVisionUtil()
    return _vision_util_instance