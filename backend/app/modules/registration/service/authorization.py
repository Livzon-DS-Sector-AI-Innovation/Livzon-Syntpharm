"""Registration business workflows live here."""

import io
import logging
import uuid
import zipfile
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.config import get_settings
from app.core.exceptions import AppException, BadRequestException, NotFoundException
from app.modules.registration.models import (
    AuthorizationLetter,
    AuthorizationLetterTrail,
    Drug,
    SupplementaryReply,
)
from app.modules.registration.repository import (
    AuthorizationLetterRepository,
    SupplementaryReplyRepository,
)
from app.modules.registration.schemas import (
    AuthorizationLetterCreate,
    AuthorizationLetterFilterOptions,
    AuthorizationLetterListItem,
    AuthorizationLetterResponse,
    AuthorizationLetterTrailItem,
    ProductInfo,
    SupplementaryReplyListItem,
    SupplementaryReplyResponse,
)
from app.platform.identity.models import User

logger = logging.getLogger(__name__)

# 固定原料药企业
API_COMPANY = "珠海保税区丽珠合成制药有限公司"

# MinIO 存储模块名与对象前缀
_STORAGE_MODULE = "registration"
_OBJECT_PREFIX = "authorization_letters"

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOC_MEDIA_TYPE = "application/msword"

# 内置授权书模板目录（模板随代码发布，属静态资源，不进 MinIO）
BUILTIN_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "assets" / "authorization_templates"

# 内置模板变体 -> 文件名；新增语种时在此登记并放入对应 docx
BUILTIN_TEMPLATES: dict[str, str] = {
    "zh": "zh.docx",
}

# 内置模板占位符 -> AuthorizationLetterCreate 字段名
BUILTIN_PLACEHOLDER_FIELDS: dict[str, str] = {
    "{产品名称}": "product_name",
    "{登记号}": "registration_number",
    "{制剂单位}": "preparation_unit",
    "{制剂名称}": "preparation_name",
    "{给药途径}": "administration_route",
}

# 品种登记号对照表
REGISTRATION_NUMBERS: dict[str, str] = {
    "阿魏酸钠": "Y20190001800",
    "艾普拉唑": "Y20190009784",
    "艾普拉唑钠": "Y20170001429",
    "奥美拉唑钠": "Y20190006673",
    "丙氨酰谷氨酰胺": "Y20190002584",
    "布南色林": "Y20210001289",
    "丹曲林钠": "Y20170001099",
    "丁苯酞": "Y20170001569",
    "厄贝沙坦": "Y20190001962",
    "更昔洛韦": "Y20190008005",
    "枸酸铋钾 (干品)": "Y20200001089",
    "枸橼酸铋钾 (湿品)": "Y20190003316",
    "枸橼酸铋雷尼替丁 (1:1)": "Y20190005110",
    "枸橼酸铋雷尼替丁 (1:1.1)": "Y20190001948",
    "桂利嗪": "Y20190007743",
    "酒石酸托特罗定": "Y20190001881",
    "卡维地洛": "Y20190001959",
    "磷酸川芎嗪": "Y20190007731",
    "硫酸钾": "Y20230000325",
    "硫酸头孢匹罗": "Y20190002699",
    "氯雷他定": "Y20190008122",
    "马来酸氟伏沙明": "Y20170001958",
    "马来酸茚达特罗": "Y20220000555",
    "舒巴坦钠": "Y20190001952",
    "他唑巴坦": "Y20190003875",
    "头孢地嗪钠": "Y20190001846",
    "头孢呋辛钠": "Y20190009596",
    "头孢曲松钠": "Y20190009444",
    "头孢他啶/碳酸钠": "Y20190006854",
    "头孢他啶": "Y20190007742",
    "无水碳酸钠": "Y20190006967",
    "盐酸哌罗匹隆 (新工艺)": "Y20220000720",
    "盐酸哌罗匹隆": "Y20190006883",
    "盐酸头孢吡肟": "Y20190001951",
    "盐酸伊托必利": "Y20190001876",
    "阿立哌唑": "Y20230000505",
    "盐酸鲁拉西酮": "Y20230001106",
    "棕榈酸帕利哌酮": "Y20240000016",
}


def _get_upload_dir() -> Path:
    """获取上传/生成文件存储目录"""
    settings = get_settings()
    upload_dir_setting = getattr(settings, "UPLOAD_DIR", "uploads")
    base = Path(upload_dir_setting)
    upload_dir = base / "authorization_letters"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _is_docx_format(data: bytes) -> bool:
    """检测文件是否为 DOCX 格式（ZIP 压缩包）"""
    return data[:4] == b"PK"


def generate_authorization_letter_bytes(
    template_data: bytes,
    replacements: list[tuple[str, str]],
    *,
    strict: bool = False,
) -> bytes:
    """
    对模板执行文本替换。支持 .docx 格式（实际是 ZIP 压缩包）。

    Args:
        template_data: 模板文件二进制内容
        replacements: 替换规则列表 [(原文本，新文本), ...]
        strict: 是否严格模式（内置模板启用，占位符未命中即报错）

    Returns:
        替换后的文件二进制内容
    """
    if not _is_docx_format(template_data):
        # 如果不是 DOCX 格式，尝试旧的二进制替换方式
        return _binary_replace(template_data, replacements)

    # DOCX 格式：使用 XML 文本替换
    return _docx_replace(template_data, replacements, strict=strict)


def _docx_replace(
    template_data: bytes,
    replacements: list[tuple[str, str]],
    *,
    strict: bool = False,
) -> bytes:
    """对 DOCX 文件执行 XML 文本替换。

    strict=True（内置模板场景）时，任一占位符未命中即视为模板损坏并报错；
    strict=False（用户自定义模板）时，未命中仅记录告警，保持原有宽松行为。
    """
    replacement_dict = {old: new for old, new in replacements}

    with zipfile.ZipFile(io.BytesIO(template_data), "r") as z:
        # 读取所有文件
        files = {}
        for name in z.namelist():
            files[name] = z.read(name)

        # 处理 document.xml
        if "word/document.xml" in files:
            try:
                doc_xml = files["word/document.xml"].decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError("模板文件编码错误：DOCX 文档包含非 UTF-8 编码的内容")

            missed: list[str] = []
            for old_text, new_text in replacement_dict.items():
                if old_text in doc_xml:
                    doc_xml = doc_xml.replace(old_text, new_text)
                    logger.info(f"替换：'{old_text}' -> '{new_text}'")
                else:
                    missed.append(old_text)
                    logger.warning(f"未找到文本：'{old_text}'")

            if missed and strict:
                raise AppException(
                    status_code=500,
                    message=f"内置模板缺少占位符：{'、'.join(missed)}，请联系管理员检查模板文件",
                )

            files["word/document.xml"] = doc_xml.encode("utf-8")

        # 创建新的 docx 文件
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as out_z:
            for name, content in files.items():
                out_z.writestr(name, content)

        return output.getvalue()


def _binary_replace(
    template_data: bytes,
    replacements: list[tuple[str, str]],
) -> bytes:
    """对 .doc 模板执行二进制等长替换（旧方式）"""
    data = bytearray(template_data)

    for old_text, new_text in replacements:
        old_bytes = old_text.encode("utf-16le")
        new_bytes = new_text.encode("utf-16le")

        if len(old_bytes) != len(new_bytes):
            raise ValueError(
                f"长度不匹配：'{old_text}' ({len(old_text)}字，{len(old_bytes)}字节) ->"
                f" '{new_text}' ({len(new_text)}字，{len(new_bytes)}字节)"
            )

        pos = 0
        while True:
            pos = data.find(old_bytes, pos)
            if pos == -1:
                break
            data[pos : pos + len(old_bytes)] = new_bytes
            pos += 1

    return bytes(data)


def get_builtin_template(variant: str) -> tuple[bytes, str]:
    """加载内置授权书模板。

    Returns:
        (模板二进制内容, 模板文件名)

    Raises:
        BadRequestException: 变体不存在或模板文件未发布
    """
    file_name = BUILTIN_TEMPLATES.get(variant)
    if file_name is None:
        raise BadRequestException(f"未知的模板版本：{variant}")
    template_path = BUILTIN_TEMPLATE_DIR / file_name
    if not template_path.exists():
        raise BadRequestException(f"模板版本 {variant} 尚未内置，请上传自定义模板")
    return template_path.read_bytes(), file_name


def _object_media_type(object_key: str) -> str:
    return DOC_MEDIA_TYPE if object_key.lower().endswith(".doc") else DOCX_MEDIA_TYPE


class AuthorizationLetterService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AuthorizationLetterRepository(session)

    def _to_response(self, obj: AuthorizationLetter) -> AuthorizationLetterResponse:
        return AuthorizationLetterResponse.model_validate(obj)

    def _to_list_item(
        self, obj: AuthorizationLetter, names: dict[UUID, str] | None = None
    ) -> AuthorizationLetterListItem:
        item = AuthorizationLetterListItem.model_validate(obj)
        item.created_by_name = names.get(obj.created_by) if names and obj.created_by else None
        return item

    async def _resolve_user_names(self, user_ids: set[UUID]) -> dict[UUID, str]:
        """批量解析操作人姓名（与注册项目页同一模式）"""
        if not user_ids:
            return {}
        result = await self.session.execute(select(User).where(User.id.in_(user_ids)))
        return {u.id: u.name for u in result.scalars().all()}

    @staticmethod
    def _trail_to_item(obj: AuthorizationLetterTrail, names: dict[UUID, str]) -> AuthorizationLetterTrailItem:
        item = AuthorizationLetterTrailItem.model_validate(obj)
        item.created_by_name = names.get(obj.created_by) if obj.created_by else None
        return item

    @staticmethod
    def get_product_list() -> list[ProductInfo]:
        """获取品种登记号对照表"""
        return [
            ProductInfo(product_name=name, registration_number=number)
            for name, number in sorted(REGISTRATION_NUMBERS.items())
        ]

    @staticmethod
    def get_registration_number(product_name: str) -> str | None:
        """根据品种名称获取登记号"""
        return REGISTRATION_NUMBERS.get(product_name)

    @staticmethod
    def get_builtin_template_variants() -> list[str]:
        """返回已内置（文件实际存在）的模板变体列表"""
        return [v for v, name in BUILTIN_TEMPLATES.items() if (BUILTIN_TEMPLATE_DIR / name).exists()]

    async def generate_letter(
        self,
        data: AuthorizationLetterCreate,
        template_data: bytes | None = None,
        template_file_name: str | None = None,
        template_variant: str = "zh",
        template_placeholders: dict[str, str] | None = None,
        operator_id: UUID | None = None,
    ) -> AuthorizationLetterResponse:
        """
        生成授权书。

        Args:
            data: 生成请求数据
            template_data: 自定义模板文件二进制内容；None 时使用内置模板
            template_file_name: 自定义模板文件名
            template_variant: 内置模板版本（zh=中文），仅未上传自定义模板时生效
            template_placeholders: 自定义模板的手动替换规则 {原文本：新文本}
            operator_id: 操作人ID（写入 created_by 与生成留痕）
        """
        use_builtin = template_data is None
        if use_builtin:
            template_bytes, builtin_name = get_builtin_template(template_variant)
            # 内置模板：按占位符映射自动替换，无等长限制
            replacements = [
                (placeholder, getattr(data, field_name))
                for placeholder, field_name in BUILTIN_PLACEHOLDER_FIELDS.items()
            ]
            template_file_name = builtin_name
            template_file_key = f"builtin:{template_variant}"
        else:
            if not template_placeholders:
                raise BadRequestException("使用自定义模板时必须提供替换规则")
            assert template_data is not None  # noqa: S101  # use_builtin=False 时必然已上传
            template_bytes = template_data
            replacements = list(template_placeholders.items())
            template_file_key = ""

        # 执行替换
        try:
            output_data = generate_authorization_letter_bytes(template_bytes, replacements, strict=use_builtin)
        except ValueError as exc:
            raise BadRequestException(str(exc)) from exc

        if not storage.is_enabled():
            raise AppException(status_code=503, message="对象存储未启用，无法保存生成的授权书")

        # 保存生成文件与自定义模板到 MinIO
        file_id = uuid.uuid4().hex[:12]
        is_docx = _is_docx_format(output_data)
        ext = ".docx" if is_docx else ".doc"
        output_file_key = f"{_OBJECT_PREFIX}/{file_id}{ext}"
        output_file_name = f"授权书-{data.product_name}-{data.preparation_unit}{ext}"
        storage.upload_object(
            _STORAGE_MODULE, output_file_key, output_data, len(output_data), _object_media_type(output_file_key)
        )

        if not use_builtin:
            template_ext = ".docx" if _is_docx_format(template_bytes) else ".doc"
            template_file_key = f"{_OBJECT_PREFIX}/{file_id}_template{template_ext}"
            storage.upload_object(
                _STORAGE_MODULE,
                template_file_key,
                template_bytes,
                len(template_bytes),
                _object_media_type(template_file_key),
            )

        # 创建数据库记录
        letter = AuthorizationLetter(
            api_company=API_COMPANY,
            product_name=data.product_name,
            registration_number=data.registration_number,
            preparation_unit=data.preparation_unit,
            preparation_name=data.preparation_name,
            administration_route=data.administration_route,
            template_file_key=template_file_key,
            template_file_name=template_file_name,
            output_file_key=output_file_key,
            output_file_name=output_file_name,
            remarks=data.remarks,
            created_by=operator_id,
        )
        created = await self.repo.create(letter)

        # 写入「生成」留痕（含模板版本）
        if use_builtin:
            template_desc = f"内置模板（{template_variant}）"
        else:
            template_desc = f"自定义模板「{template_file_name}」"
        await self.repo.add_trail(
            letter_id=created.id,
            action="generate",
            detail=f"使用{template_desc}生成授权书",
            created_by=operator_id,
        )
        return self._to_response(created)

    async def get_letter(self, letter_id: UUID) -> AuthorizationLetterResponse:
        """获取单条授权书记录"""
        letter = await self.repo.get_by_id(letter_id)
        if not letter:
            raise NotFoundException("授权书记录", str(letter_id))
        return self._to_response(letter)

    async def list_letters(
        self,
        *,
        keyword: str | None = None,
        product_name: str | None = None,
        year: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AuthorizationLetterListItem], int]:
        """查询授权书列表（关键词/品种/年份可叠加，AND 关系）"""
        letters, total = await self.repo.list_letters(
            keyword=keyword,
            product_name=product_name,
            year=year,
            page=page,
            page_size=page_size,
        )
        names = await self._resolve_user_names({x.created_by for x in letters if x.created_by})
        return [self._to_list_item(letter, names) for letter in letters], total

    async def get_filter_options(self) -> AuthorizationLetterFilterOptions:
        """筛选下拉选项：品种 = 品种主数据(原料药) ∪ 已有记录品种；年份按生成时间降序"""
        drugs_result = await self.session.execute(
            select(Drug.name).where(Drug.is_deleted.is_(False), Drug.type == "原料药")
        )
        master_names = set(drugs_result.scalars().all())
        record_names = set(await self.repo.list_distinct_products())
        products = sorted(master_names | record_names)
        years = await self.repo.list_years()
        return AuthorizationLetterFilterOptions(products=products, years=years)

    async def record_download(self, letter_id: UUID, operator_id: UUID | None = None) -> AuthorizationLetter:
        """写入「下载」留痕并返回记录（供下载端点调用）"""
        letter = await self.repo.get_by_id(letter_id)
        if not letter:
            raise NotFoundException("授权书记录", str(letter_id))
        await self.repo.add_trail(
            letter_id=letter.id,
            action="download",
            detail=f"下载授权书文件：{letter.output_file_name}",
            created_by=operator_id,
        )
        return letter

    async def list_trails(self, letter_id: UUID) -> list[AuthorizationLetterTrailItem]:
        """授权书留痕时间线（新→旧倒序）"""
        letter = await self.repo.get_by_id(letter_id)
        if not letter:
            raise NotFoundException("授权书记录", str(letter_id))
        trails = await self.repo.list_trails(letter_id)
        names = await self._resolve_user_names({t.created_by for t in trails if t.created_by})
        return [self._trail_to_item(t, names) for t in trails]

    async def delete_letter(self, letter_id: UUID) -> None:
        """删除授权书记录（软删除），并清理对象存储中的文件"""
        letter = await self.repo.get_by_id(letter_id)
        if not letter:
            raise NotFoundException("授权书记录", str(letter_id))
        await self.repo.soft_delete(letter)

        for key in (letter.output_file_key, letter.template_file_key):
            # 内置模板是代码内置静态资源，跳过；历史本地文件无法经 MinIO 删除，仅尝试并忽略失败
            if not key or key.startswith("builtin:"):
                continue
            try:
                if storage.is_enabled():
                    storage.delete_object(_STORAGE_MODULE, key)
            except Exception:
                logger.warning("清理授权书文件失败: key=%s", key, exc_info=True)

    def load_output_file(self, letter: AuthorizationLetter) -> tuple[bytes, str]:
        """读取生成文件内容与媒体类型。

        优先从 MinIO 读取；兼容迁移前写入本地磁盘的历史记录。
        """
        if storage.is_enabled():
            found = storage.get_object(_STORAGE_MODULE, letter.output_file_key)
            if found is not None:
                return found[0], _object_media_type(letter.output_file_key)

        # 历史记录兼容：旧版本 output_file_key 为本地文件名（如 abc123.doc）
        legacy_path = _get_upload_dir() / Path(letter.output_file_key).name
        if legacy_path.exists():
            return legacy_path.read_bytes(), _object_media_type(letter.output_file_key)

        raise NotFoundException("授权书文件")


# ─── 发补回复 ────────────────────────────────────────────


def _get_reply_upload_dir() -> Path:
    """获取发补回复文件存储目录"""
    settings = get_settings()
    upload_dir_setting = getattr(settings, "UPLOAD_DIR", "uploads")
    base = Path(upload_dir_setting)
    upload_dir = base / "supplementary_replies"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


class SupplementaryReplyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SupplementaryReplyRepository(session)

    def _to_response(self, obj: SupplementaryReply) -> SupplementaryReplyResponse:
        return SupplementaryReplyResponse.model_validate(obj)

    def _to_list_item(self, obj: SupplementaryReply) -> SupplementaryReplyListItem:
        return SupplementaryReplyListItem.model_validate(obj)

    async def generate_reply(
        self,
        notice_data: bytes,
        notice_file_name: str,
        template_data: bytes | None = None,
        template_file_name: str | None = None,
        drug_name_override: str | None = None,
        registration_number_override: str | None = None,
        acceptance_number_override: str | None = None,
        company_name_override: str | None = None,
        remarks: str | None = None,
    ) -> SupplementaryReplyResponse:
        """
        生成发补回复文档。

        流程：解析 PDF → 提取药品信息和问题 → 生成 Word → 保存记录
        """
        from app.modules.registration.reply_generator import (
            generate_reply_document,
            parse_cde_notice,
        )

        # 1. 解析 CDE 通知函 PDF
        parsed = parse_cde_notice(notice_data)
        metadata = parsed["metadata"]
        questions = parsed["questions"]

        # 2. 合并药品信息（用户手动输入优先于 PDF 提取）
        drug_info = {
            "drug_name": drug_name_override or metadata.get("drug_name", "未知药品"),
            "registration_number": registration_number_override or metadata.get("registration_number", ""),
            "acceptance_number": acceptance_number_override or metadata.get("acceptance_number", ""),
            "company_name": company_name_override or metadata.get("company_name", API_COMPANY),
            "doc_type": "补充资料",
            "application_type": "首次登记",
            "contact": "魏永红",
            "phone": "0756-8686208",
            "address": "中国，广东省，珠海市，珠海保税区联峰路22号",
            "zipcode": "519030",
            "related_no": "/",
            "email": "lzsyntpharmzhucebu@livzon.cn",
        }

        # 3. 生成 Word 文档
        output_data = generate_reply_document(drug_info, questions)

        # 4. 保存文件
        file_id = uuid.uuid4().hex[:12]
        output_file_name = f"发补回复-{drug_info['drug_name']}.docx"
        upload_dir = _get_reply_upload_dir()

        # 保存通知函
        notice_path = upload_dir / f"{file_id}_notice.pdf"
        notice_path.write_bytes(notice_data)

        # 保存模板（如有）
        template_key = None
        if template_data:
            template_path = upload_dir / f"{file_id}_template.docx"
            template_path.write_bytes(template_data)
            template_key = f"{file_id}_template.docx"

        # 保存生成的文档
        output_path = upload_dir / f"{file_id}.docx"
        output_path.write_bytes(output_data)

        # 5. 创建数据库记录
        reply = SupplementaryReply(
            drug_name=drug_info["drug_name"],
            registration_number=drug_info["registration_number"],
            acceptance_number=drug_info["acceptance_number"],
            company_name=drug_info["company_name"],
            notice_file_key=f"{file_id}_notice.pdf",
            notice_file_name=notice_file_name,
            template_file_key=template_key,
            template_file_name=template_file_name,
            output_file_key=f"{file_id}.docx",
            output_file_name=output_file_name,
            question_count=len(questions),
            remarks=remarks,
        )
        created = await self.repo.create(reply)
        return self._to_response(created)

    async def get_reply(self, reply_id: UUID) -> SupplementaryReplyResponse:
        """获取单条发补回复记录"""
        reply = await self.repo.get_by_id(reply_id)
        if not reply:
            raise NotFoundException("发补回复记录", str(reply_id))
        return self._to_response(reply)

    async def list_replies(
        self,
        *,
        drug_name: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SupplementaryReplyListItem], int]:
        """查询发补回复列表"""
        replies, total = await self.repo.list_replies(
            drug_name=drug_name,
            page=page,
            page_size=page_size,
        )
        return [self._to_list_item(r) for r in replies], total

    async def delete_reply(self, reply_id: UUID) -> None:
        """删除发补回复记录（软删除）"""
        reply = await self.repo.get_by_id(reply_id)
        if not reply:
            raise NotFoundException("发补回复记录", str(reply_id))
        await self.repo.soft_delete(reply)

    def get_output_file_path(self, reply: SupplementaryReply) -> Path:
        """获取生成文件路径"""
        return _get_reply_upload_dir() / reply.output_file_key
