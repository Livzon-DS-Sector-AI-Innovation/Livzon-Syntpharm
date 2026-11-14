"""Identity 模块对外公开的 API。

其他模块只能通过本文件调用 identity 的内部实现，不得直接 import
`app.platform.identity.service`（AGENTS.md 模块所有权规则）。
"""

from app.platform.identity.service import _verify_feishu_callback_signature

__all__ = ["verify_feishu_callback_signature"]


def verify_feishu_callback_signature(
    *,
    encrypt_key: str | None,
    raw_body: bytes,
    timestamp: str | None,
    nonce: str | None,
    signature: str | None,
) -> bool:
    """校验飞书回调签名（HMAC-SHA256）。

    未配置 `encrypt_key` 时返回 `True`，由调用方的 verification token 校验兜底。
    """
    return _verify_feishu_callback_signature(
        encrypt_key=encrypt_key,
        raw_body=raw_body,
        timestamp=timestamp,
        nonce=nonce,
        signature=signature,
    )
