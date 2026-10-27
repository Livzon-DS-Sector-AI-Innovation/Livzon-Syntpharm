"""Fernet encryption for API keys.

写入（``encrypt_api_key``）为 fail-closed：``ENCRYPTION_KEY`` 未配置时直接报错，
禁止把 API key 明文落库。读取（``decrypt_api_key``）在无密钥时按明文原样返回，
只为兼容配置密钥之前写入的历史数据；配置密钥后应重新保存一次配置以便加密回写。
"""

import logging

from cryptography.fernet import Fernet, InvalidToken

from .exceptions import LLMConfigError

logger = logging.getLogger(__name__)
_missing_key_warned = False

_MISSING_KEY_WRITE_MSG = (
    "ENCRYPTION_KEY 未配置，拒绝将 API key 明文写入数据库。请在部署环境配置合法的 Fernet key（44 位 base64）后重试"
)


def _get_fernet(required: bool) -> Fernet | None:
    """取得 Fernet 实例。

    ``required=True``（写入路径）时无密钥直接抛 ``LLMConfigError``；
    ``required=False``（读取路径）时返回 None，由调用方按历史明文兼容处理。
    """
    global _missing_key_warned

    from app.core.config import get_settings

    key = get_settings().ENCRYPTION_KEY
    if not key:
        if required:
            raise LLMConfigError(_MISSING_KEY_WRITE_MSG)
        if not _missing_key_warned:
            logger.warning("ENCRYPTION_KEY 未配置：按明文读取历史 LLM 配置（仅兼容旧数据，新配置无法保存）")
            _missing_key_warned = True
        return None
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        raise LLMConfigError(f"Invalid ENCRYPTION_KEY: {e}")


def encrypt_api_key(plain_key: str) -> str:
    """Encrypt API key. Raises when ENCRYPTION_KEY is not configured."""
    fernet = _get_fernet(required=True)
    assert fernet is not None  # required=True 时必定返回实例
    return fernet.encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt API key. Returns as-is when encryption key is not configured (legacy plaintext)."""
    fernet = _get_fernet(required=False)
    if not fernet:
        return encrypted_key
    try:
        return fernet.decrypt(encrypted_key.encode()).decode()
    except InvalidToken:
        raise LLMConfigError("Failed to decrypt API key - invalid encryption key or corrupted data")


def mask_api_key(api_key: str) -> str:
    """Mask API key for display (show first 10 chars + ****)."""
    if not api_key or len(api_key) <= 10:
        return "****"
    return f"{api_key[:10]}****"
