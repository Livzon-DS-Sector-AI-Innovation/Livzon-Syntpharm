import logging
import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # dazah-backend/


def _get_env_file() -> str:
    """根据 APP_ENV 选择 .env 文件；缺省环境文件不存在时回退到 .env。"""
    app_env = os.getenv("APP_ENV", "development")
    env_path = _PROJECT_ROOT / f".env.{app_env}"
    if not env_path.exists():
        env_path = _PROJECT_ROOT / ".env"
    env_file = str(env_path)
    logging.getLogger(__name__).debug("Loading environment variables from: %s", env_file)
    return env_file


# ============================================================================
# Feishu Configuration Models
# ============================================================================

class FeishuAppCredentials(BaseModel):
    """Reusable model for a Feishu app's bot credentials."""
    app_id: str = ""
    app_secret: str = ""


class FeishuPlatformConfig(BaseModel):
    """Platform app — SSO, org sync, IM, and shared Bitable access."""
    app_id: str = ""
    app_secret: str = ""
    redirect_uri: str = ""
    scopes: str = "contact:contact.base:readonly contact:user.base:readonly"
    ws_enabled: bool = True
    bot_name: str = ""
    # Org sync
    sync_root_dept_id: str = ""
    sync_member_dept_id: str = ""
    # Department chat targets
    equipment_dept_id: str = ""
    equipment_chat_id: str = "oc_ba1a54a70a0d611315f29581621c50b5"
    safety_chat_id: str = ""


class FeishuHRBitableConfig(BaseModel):
    """HR module Bitable tables (uses platform app credentials)."""
    app_token: str = ""
    employee_table_id: str = ""
    department_table_id: str = ""
    offboarding_table_id: str = ""
    onboarding_table_id: str = ""
    departure_table_id: str = ""
    approval_table_id: str = ""
    candidate_app_token: str = ""
    candidate_table_id: str = ""


class FeishuSafetyConfig(BaseModel):
    """Safety module — independent Feishu app + hazard Bitable."""
    credentials: FeishuAppCredentials = Field(default_factory=FeishuAppCredentials)
    bitable_app_token: str = ""
    hazard_table_id: str = ""


class FeishuEquipmentConfig(BaseModel):
    """Equipment module — independent Feishu app for bot interaction."""
    credentials: FeishuAppCredentials = Field(default_factory=FeishuAppCredentials)
    ws_enabled: bool = True


class FeishuVehicleConfig(BaseModel):
    """Vehicle module — independent Feishu app + vehicle request Bitable."""
    credentials: FeishuAppCredentials = Field(default_factory=FeishuAppCredentials)
    bitable_request_app_token: str = ""
    bitable_request_table_id: str = ""


class FeishuTrainingConfig(BaseModel):
    """Training module — independent Feishu app + training-related Bitables."""
    credentials: FeishuAppCredentials = Field(default_factory=FeishuAppCredentials)
    bitable_material_bom_app_token: str = ""
    bitable_material_bom_table_id: str = ""
    bitable_training_notification_app_token: str = ""
    bitable_training_notification_table_id: str = ""


class FeishuProductConfig(BaseModel):
    """Product module Bitable (uses platform app credentials)."""
    bitable_app_token: str = ""
    bitable_table_id: str = ""


class FeishuAIQueryConfig(BaseModel):
    """AI-powered Bitable query settings."""
    tables: str = ""  # JSON: {"别名": {"app_token": "...", "table_id": "...", "filterable_fields": [...]}}
    max_rows: int = 200


class FeishuSettings(BaseModel):
    """Top-level Feishu configuration — all modules grouped."""
    platform: FeishuPlatformConfig = Field(default_factory=FeishuPlatformConfig)
    hr_bitable: FeishuHRBitableConfig = Field(default_factory=FeishuHRBitableConfig)
    safety: FeishuSafetyConfig = Field(default_factory=FeishuSafetyConfig)
    equipment: FeishuEquipmentConfig = Field(default_factory=FeishuEquipmentConfig)
    vehicle: FeishuVehicleConfig = Field(default_factory=FeishuVehicleConfig)
    training: FeishuTrainingConfig = Field(default_factory=FeishuTrainingConfig)
    product: FeishuProductConfig = Field(default_factory=FeishuProductConfig)
    ai_query: FeishuAIQueryConfig = Field(default_factory=FeishuAIQueryConfig)
    aily_app_id: str = ""


# ============================================================================
# Main Settings
# ============================================================================

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",  # Enables nested model env var mapping
        extra="ignore",
    )

    # App
    APP_NAME: str = "dazah-backend"
    APP_ENV: str = "development"
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def coerce_debug_bool(cls, v):
        """兼容 VS Code 等注入的非布尔值（如 DEBUG=release）。"""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            if v.lower() in ("true", "1", "yes"):
                return True
            return False
        return bool(v)

    SECRET_KEY: str = "change-me-in-production"
    ENCRYPTION_KEY: str | None = None

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dazah"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Upload
    UPLOAD_DIR: str = "./uploads"
    
    # AI
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_VISION_MODEL: str = "gpt-4o"

    # Audit
    AUDIT_RETENTION_DAYS: int = 7

    # Feishu / Lark — all modules grouped
    feishu: FeishuSettings = Field(default_factory=FeishuSettings)

    FRONTEND_URL: str = ""

    # Upload
    MAX_UPLOAD_SIZE_MB: int = 50

    # MinIO / S3-compatible object storage
    MINIO_ENABLED: bool = False
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_PREFIX: str = "dazah"
    MINIO_SECURE: bool = False

    # JWT
    JWT_EXPIRE_SECONDS: int = 86400  # 24 hours

    # AI — HR 离职分析
    MOONSHOT_API_KEY: str = ""

    # Regulatory Tracker — 定时同步
    CRAWLER_HEADLESS: str = "true"
    CRAWLER_BROWSERS_PATH: str = ""

    # Research — EDBO 服务
    EDBO_SERVICE_URL: str = "http://edbo-service:8000"

    # Storage
    STORAGE_ROOT: str = "./storage"

    # LLM (AI 解析配置)
    LLM_API_KEY: str | None = None
    LLM_BASE_URL: str | None = "https://api.deepseek.com"
    LLM_MODEL: str | None = "deepseek-chat"

    # MCP — AI Agent 认证
    MCP_AGENT_API_KEYS: str = ""

    # API
    API_V1_PREFIX: str = "/api/v1"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    def check(self) -> None:
        """启动时校验关键配置，避免漏配导致运行时异常。"""
        missing: list[str] = []
        if not self.SECRET_KEY:
            missing.append("SECRET_KEY")
        if not self.feishu.platform.app_id:
            missing.append("FEISHU__PLATFORM__APP_ID")
        if not self.feishu.platform.app_secret:
            missing.append("FEISHU__PLATFORM__APP_SECRET")
        if not self.feishu.platform.redirect_uri:
            missing.append("FEISHU__PLATFORM__REDIRECT_URI")
        if not self.FRONTEND_URL:
            missing.append("FRONTEND_URL")
        if missing:
            raise RuntimeError(
                "以下 .env 配置项缺失或无效，请检查:\n  " + "\n  ".join(missing),
            )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.check()
    return settings
