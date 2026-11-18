# mypy: ignore-errors
"""授权书生成：内置模板加载、占位符替换与存储交互的测试。

外部依赖处理：
- MinIO 通过 monkeypatch mock，不连接真实对象存储；
- 数据库使用全局 db_session fixture（savepoint 隔离，回滚清理）。
"""

from __future__ import annotations

import io
import zipfile
from datetime import date

import pytest
from docx import Document
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, BadRequestException
from app.modules.registration.schemas.authorization import AuthorizationLetterCreate
from app.modules.registration.service import authorization as authz
from app.modules.registration.service.authorization import (
    BUILTIN_PLACEHOLDER_FIELDS,
    AuthorizationLetterService,
    _docx_replace,
    generate_authorization_letter_bytes,
    get_builtin_template,
)

FORM_DATA = AuthorizationLetterCreate(
    product_name="头孢曲松钠",
    registration_number="Y20190009444",
    preparation_unit="国药集团致君（深圳）制药有限公司",
    preparation_name="注射用头孢曲松钠",
    administration_route="注射",
    remarks=None,
)


def _build_docx(paragraphs: list[str]) -> bytes:
    """构造最小 docx 用于测试。"""
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _docx_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return z.read("word/document.xml").decode("utf-8")


@pytest.fixture
def mock_storage(monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes]:
    """Mock MinIO 存储，返回已上传对象的字典 {object_key: data}。"""
    objects: dict[str, bytes] = {}
    monkeypatch.setattr(authz.storage, "is_enabled", lambda: True)
    monkeypatch.setattr(
        authz.storage,
        "upload_object",
        lambda module, key, data, length, content_type="application/octet-stream": objects.setdefault(key, data),
    )
    monkeypatch.setattr(authz.storage, "get_object", lambda module, key: (objects[key], "") if key in objects else None)
    monkeypatch.setattr(authz.storage, "delete_object", lambda module, key: objects.pop(key, None))
    return objects


# ── 内置模板加载 ─────────────────────────────────────────


def test_builtin_template_loads_zh():
    data, name = get_builtin_template("zh")
    assert name == "zh.docx"
    assert data[:4] == b"PK\x03\x04"
    # 所有约定占位符必须在模板中完整存在（未被 Word 拆 run）
    xml = _docx_text(data)
    for placeholder in BUILTIN_PLACEHOLDER_FIELDS:
        assert placeholder in xml, f"内置模板缺少占位符 {placeholder}"


def test_builtin_template_unknown_variant():
    with pytest.raises(BadRequestException):
        get_builtin_template("xx")


# ── 替换逻辑 ─────────────────────────────────────────────


def test_docx_replace_strict_raises_on_missing_placeholder():
    template = _build_docx(["只有{产品名称}，没有其他占位符"])
    with pytest.raises(AppException) as exc_info:
        _docx_replace(template, [("{产品名称}", "A"), ("{不存在的占位符}", "B")], strict=True)
    assert exc_info.value.status_code == 500


def test_docx_replace_non_strict_tolerates_missing_placeholder():
    template = _build_docx(["只有{产品名称}"])
    out = _docx_replace(template, [("{产品名称}", "A"), ("{不存在}", "B")], strict=False)
    assert "A" in _docx_text(out)


def test_docx_replace_allows_different_lengths():
    """docx 替换不受等长限制（区别于旧 .doc 二进制替换）。"""
    template = _build_docx(["单位为{制剂单位}。"])
    out = generate_authorization_letter_bytes(template, [("{制剂单位}", "一家名字特别特别长的制药有限公司")])
    text = _docx_text(out)
    assert "一家名字特别特别长的制药有限公司" in text
    assert "{制剂单位}" not in text


# ── 生成流程（DB + mock MinIO） ──────────────────────────


async def test_generate_letter_with_builtin_template(db_session: AsyncSession, mock_storage):
    service = AuthorizationLetterService(db_session)
    letter = await service.generate_letter(FORM_DATA)

    assert letter.product_name == FORM_DATA.product_name
    assert letter.output_file_name.endswith(".docx")

    # 生成文件已入 mock MinIO，模板标记为内置
    key = next(k for k in mock_storage if not k.endswith("_template.docx") and "_template" not in k)
    output = mock_storage[key]
    text = _docx_text(output)
    for placeholder in BUILTIN_PLACEHOLDER_FIELDS:
        assert placeholder not in text, f"生成文件仍残留占位符 {placeholder}"
    assert FORM_DATA.preparation_unit in text
    assert FORM_DATA.registration_number in text

    # 内置模板不上传模板文件
    assert not any("_template" in k for k in mock_storage)


async def test_generate_letter_custom_template_uploads_both(db_session: AsyncSession, mock_storage):
    service = AuthorizationLetterService(db_session)
    template = _build_docx(["单位：XX公司"])
    letter = await service.generate_letter(
        FORM_DATA,
        template_data=template,
        template_file_name="自定义模板.docx",
        template_placeholders={"XX公司": FORM_DATA.preparation_unit},
    )
    assert letter.template_file_name == "自定义模板.docx"
    assert any("_template" in k for k in mock_storage)


async def test_generate_letter_custom_template_requires_replacements(db_session: AsyncSession, mock_storage):
    service = AuthorizationLetterService(db_session)
    template = _build_docx(["单位：XX公司"])
    with pytest.raises(BadRequestException):
        await service.generate_letter(FORM_DATA, template_data=template, template_file_name="t.docx")


async def test_generate_letter_storage_disabled(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(authz.storage, "is_enabled", lambda: False)
    service = AuthorizationLetterService(db_session)
    with pytest.raises(AppException) as exc_info:
        await service.generate_letter(FORM_DATA)
    assert exc_info.value.status_code == 503


async def test_delete_letter_cleans_storage_but_keeps_builtin(db_session: AsyncSession, mock_storage):
    service = AuthorizationLetterService(db_session)
    letter = await service.generate_letter(FORM_DATA)
    output_keys = list(mock_storage)
    assert output_keys, "前置条件：生成应产生存储对象"

    await service.delete_letter(letter.id)

    # 内置模板键为 builtin:zh，本就不在对象存储中；生成文件应已清理
    assert not any(k in mock_storage for k in output_keys)
    assert await service.repo.get_by_id(letter.id) is None  # 软删除后不可见


# ── 留痕（生成/下载，只增不删） ──────────────────────────


async def _generate_via_api(auth_client, **overrides):
    payload = {
        "product_name": "头孢曲松钠",
        "registration_number": "Y20190009444",
        "preparation_unit": "国药集团致君（深圳）制药有限公司",
        "preparation_name": "注射用头孢曲松钠",
        "administration_route": "注射",
        "template_variant": "zh",
        **overrides,
    }
    resp = await auth_client.post("/api/v1/registration/authorization-letters/generate", data=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


async def test_generate_writes_trail_with_operator_and_template(auth_client, mock_storage):
    letter = await _generate_via_api(auth_client)

    resp = await auth_client.get(f"/api/v1/registration/authorization-letters/{letter['id']}/trails")
    assert resp.status_code == 200
    trails = resp.json()["data"]
    assert len(trails) == 1
    trail = trails[0]
    assert trail["action"] == "generate"
    assert "内置模板（zh）" in trail["detail"]
    assert trail["created_by_name"] == "Test User"

    # 列表项带生成人（表格「XX 生成」行）
    list_resp = await auth_client.get("/api/v1/registration/authorization-letters")
    item = next(x for x in list_resp.json()["data"] if x["id"] == letter["id"])
    assert item["created_by_name"] == "Test User"


async def test_download_writes_trail(auth_client, mock_storage):
    letter = await _generate_via_api(auth_client)

    resp = await auth_client.get(f"/api/v1/registration/authorization-letters/{letter['id']}/download")
    assert resp.status_code == 200

    trails = (await auth_client.get(f"/api/v1/registration/authorization-letters/{letter['id']}/trails")).json()["data"]
    assert [t["action"] for t in trails] == ["download", "generate"]  # 新→旧倒序
    assert "下载授权书文件" in trails[0]["detail"]
    assert trails[0]["created_by_name"] == "Test User"


async def test_download_unknown_letter_no_trail(auth_client, mock_storage):
    import uuid as _uuid

    missing = _uuid.uuid4()
    resp = await auth_client.get(f"/api/v1/registration/authorization-letters/{missing}/download")
    assert resp.status_code == 404


# ── 组合筛选与下拉选项 ──────────────────────────────────


async def test_keyword_and_year_and_product_filters_combine(auth_client, mock_storage):
    letter = await _generate_via_api(auth_client)
    await _generate_via_api(
        auth_client,
        product_name="丁苯酞",
        registration_number="Y20170001569",
        preparation_unit="恒瑞医药",
        preparation_name="丁苯酞注射液",
    )

    # 关键词命中登记号
    resp = await auth_client.get("/api/v1/registration/authorization-letters", params={"keyword": "9444"})
    ids = [x["id"] for x in resp.json()["data"]]
    assert letter["id"] in ids

    # 关键词命中制剂单位 + 品种叠加（AND）
    resp = await auth_client.get(
        "/api/v1/registration/authorization-letters",
        params={"keyword": "恒瑞", "product_name": "丁苯酞"},
    )
    data = resp.json()["data"]
    assert len([x for x in data if x["product_name"] == "丁苯酞" and "恒瑞" in x["preparation_unit"]]) == len(data)
    assert any("恒瑞" in x["preparation_unit"] for x in data)

    # 年份筛选（两条都是今年生成）
    this_year = date.today().year
    resp = await auth_client.get("/api/v1/registration/authorization-letters", params={"year": this_year})
    assert any(x["id"] == letter["id"] for x in resp.json()["data"])
    resp = await auth_client.get("/api/v1/registration/authorization-letters", params={"year": this_year - 30})
    assert all(x["id"] != letter["id"] for x in resp.json()["data"])


async def test_filter_options_union_and_year_desc(auth_client, mock_storage):
    await _generate_via_api(auth_client)

    resp = await auth_client.get("/api/v1/registration/authorization-letters/filter-options")
    assert resp.status_code == 200
    options = resp.json()["data"]
    # 品种：已有记录品种必在选项中（主数据当前只有测试数据，做并集兜底）
    assert "头孢曲松钠" in options["products"]
    # 年份：降序且含今年
    years = options["years"]
    assert years == sorted(years, reverse=True)
    assert date.today().year in years
