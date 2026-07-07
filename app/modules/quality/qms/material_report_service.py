"""原料报告单 Service"""

import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qms.material_report_models import ReportStatus
from app.modules.quality.qms.material_report_repository import (
    MaterialReportRepository,
    MaterialReportItemRepository,
    ReportTemplateRepository,
    ReportImageRepository,
)
from app.modules.quality.qms.material_report_schemas import (
    ReportCreate,
    ReportUpdate,
    ReportItemsBatchSave,
    TemplateCreate,
    TemplateUpdate,
)
from app.modules.quality.word_generator import generate_report_bytes


class MaterialReportService:
    """报告单服务"""

    # AI识别提示词
    SYSTEM_PROMPT_REPORT_IMAGE = """你是一个专业的质量报告单数据提取助手。请仔细分析上传的图片图片，并从中提取出质量报告单相关的数据。

请提取以下信息并以JSON格式返回：
- 检测项目/指标名称
- 检测结果/数值
- 单位
- 检测方法
- 判定结论（合格/不合格）

请确保返回的是有效的JSON格式，不要包含任何额外的解释或说明。

返回格式示例：
{
    "items": [
        {
            "name": "检测项目名称",
            "value": "检测结果",
            "unit": "单位",
            "method": "检测方法",
            "conclusion": "合格/不合格"
        }
    ]
}"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.report_repo = MaterialReportRepository(session)
        self.item_repo = MaterialReportItemRepository(session)
        self.image_repo = ReportImageRepository(session)

    async def create_report(self, data: ReportCreate) -> dict:
        """创建报告单"""
        # 生成报告单编号
        report_no = await self.report_repo.get_next_report_no()

        # 创建报告单
        report_data = data.model_dump()
        report_data["report_no"] = report_no
        report_data["status"] = ReportStatus.DRAFT

        report = await self.report_repo.create(report_data)
        return report

    async def get_report(self, report_id: UUID) -> Optional[dict]:
        """获取报告单详情"""
        report = await self.report_repo.get_by_id(report_id)
        if not report:
            return None

        # 转换为字典格式
        result = {
            "id": str(report.id),
            "report_no": report.report_no,
            "template_id": str(report.template_id) if report.template_id else None,
            "report_title": report.report_title,
            "report_date": report.report_date.isoformat() if report.report_date else None,
            "static_data": report.static_data or {},
            "status": report.status,
            "generated_file_url": report.generated_file_url,
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat() if report.updated_at else None,
            "items": [],
        }

        # 添加模板信息
        if report.template:
            result["template"] = {
                "id": str(report.template.id),
                "template_name": report.template.template_name,
                "template_file_url": report.template.template_file_url,
                "field_mapping": report.template.field_mapping or {},
                "table_fields": report.template.table_fields or {},
            }

        # 添加明细数据
        if report.items:
            # 按行分组
            rows_dict = {}
            for item in report.items:
                row_idx = item.row_index
                if row_idx not in rows_dict:
                    rows_dict[row_idx] = {"row_index": row_idx}
                rows_dict[row_idx][item.field_key] = item.field_value

            result["items"] = list(rows_dict.values())

        return result

    async def update_report(self, report_id: UUID, data: ReportUpdate) -> Optional[dict]:
        """更新报告单"""
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_report(report_id)

        report = await self.report_repo.update(report_id, update_data)
        if not report:
            return None

        return await self.get_report(report_id)

    async def delete_report(self, report_id: UUID) -> bool:
        """删除报告单"""
        return await self.report_repo.delete(report_id)

    async def list_reports(
        self,
        template_id: Optional[UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """获取报告单列表"""
        # 解析日期
        start_dt = None
        end_dt = None
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

        reports, total = await self.report_repo.list_with_filter(
            template_id=template_id,
            status=status,
            start_date=start_dt,
            end_date=end_dt,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

        result = []
        for report in reports:
            item = {
                "id": str(report.id),
                "report_no": report.report_no,
                "template_id": str(report.template_id) if report.template_id else None,
                "template_name": report.template.template_name if report.template else None,
                "report_title": report.report_title,
                "report_date": report.report_date.isoformat() if report.report_date else None,
                "status": report.status,
                "created_at": report.created_at.isoformat(),
            }
            result.append(item)

        return result, total

    async def save_items(
        self, report_id: UUID, data: ReportItemsBatchSave
    ) -> list[dict]:
        """批量保存明细数据"""
        items_data = [item.model_dump() for item in data.items]
        items = await self.item_repo.batch_create(report_id, items_data)

        return [
            {
                "row_index": item.row_index,
                "field_key": item.field_key,
                "field_value": item.field_value,
            }
            for item in items
        ]

    async def generate_report(self, report_id: UUID) -> bytes:
        """生成报告单Word文件"""
        report = await self.report_repo.get_by_id(report_id)
        if not report:
            raise ValueError(f"报告单不存在: {report_id}")

        if not report.template:
            raise ValueError("报告单未关联模板")

        # 获取模板文件路径
        template_path = report.template.template_file_url
        if not template_path.startswith("/"):
            template_path = f"uploads/{template_path}"

        # 准备静态数据
        static_data = report.static_data or {}
        static_data["report_no"] = report.report_no
        static_data["report_title"] = report.report_title
        static_data["report_date"] = (
            report.report_date.isoformat() if report.report_date else ""
        )

        # 准备表格数据
        table_data = []
        if report.items:
            # 按行分组
            rows_dict = {}
            for item in report.items:
                row_idx = item.row_index
                if row_idx not in rows_dict:
                    rows_dict[row_idx] = {}
                rows_dict[row_idx][item.field_key] = item.field_value

            table_data = list(rows_dict.values())

        # 生成Word文档
        content = generate_report_bytes(template_path, static_data, table_data)

        # 更新生成文件路径
        output_path = f"reports/{report.report_no}.docx"
        await self.report_repo.update(
            report_id, {"generated_file_url": output_path}
        )

        return content

    async def submit_report(self, report_id: UUID) -> dict:
        """提交报告单"""
        report = await self.report_repo.update(
            report_id, {"status": ReportStatus.COMPLETED}
        )
        if not report:
            raise ValueError(f"报告单不存在: {report_id}")

        return await self.get_report(report_id)

    async def get_statistics(self) -> dict:
        """获取统计数据"""
        return await self.report_repo.get_statistics()

    async def upload_image_and_recognize(
        self,
        report_id: UUID,
        file,
        field_key: Optional[str] = None,
        row_index: Optional[int] = None,
    ) -> dict:
        """上传图片并进行AI识别"""
        import json
        import re

        from app.core.storage import save_upload_file
        from app.platform.ai.minimax_util import get_vision_util

        # 1. 保存上传的图片
        file_url = await save_upload_file(file, sub_dir="report-images")
        full_url = f"/uploads/{file_url}" if not file_url.startswith("/") else file_url

        # 2. 调用AI识别
        vision_util = get_vision_util()
        ai_response = None
        parsed_result = None

        try:
            ai_response = await vision_util.recognize_image(
                image_urls=[full_url],
                prompt=self.SYSTEM_PROMPT_REPORT_IMAGE,
            )

            # 解析AI响应
            def safe_print(msg):
                """安全打印，避免编码问题"""
                try:
                    print(msg)
                except Exception:
                    print(repr(msg[:100]) if len(msg) > 100 else repr(msg))

            safe_print(f"[DEBUG] AI响应长度: {len(ai_response)}")

            try:
                # 尝试直接解析JSON
                parsed_result = json.loads(ai_response)
            except json.JSONDecodeError:
                # 如果直接解析失败，清理思考过程标签后提取JSON
                safe_print("[DEBUG] 直接解析失败，尝试清理思考标签...")
                clean_response = ai_response
                while '<think>' in clean_response and '' in clean_response:
                    clean_response = re.sub(r'<think>[\s\S]*?', '', clean_response)
                clean_response = clean_response.strip()

                # 查找JSON代码块
                json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', clean_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # 尝试直接在清理后的文本中找JSON对象
                    json_match = re.search(r'\{[\s\S]*\}', clean_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = clean_response

                try:
                    parsed_result = json.loads(json_str)
                except json.JSONDecodeError:
                    parsed_result = {"items": [], "error": "解析失败"}

        except Exception as e:
            safe_print(f"[ERROR] AI识别异常: {e}")
            parsed_result = {"items": [], "error": str(e)}

        # 3. 保存图片记录到数据库
        image_data = {
            "report_id": report_id,
            "row_index": row_index,
            "field_key": field_key,
            "image_url": file_url,
            "ai_result": parsed_result,
        }
        image_record = await self.image_repo.create(image_data)

        # 4. 如果提供了field_key，自动填充到明细
        if field_key and row_index is not None and parsed_result and "items" in parsed_result:
            items = parsed_result["items"]
            if items:
                # 取第一个识别的项目作为值
                first_item = items[0]
                field_value = first_item.get("value", "") or first_item.get("name", "")
                if field_value:
                    await self.item_repo.create({
                        "row_index": row_index,
                        "field_key": field_key,
                        "field_value": field_value,
                    })

        return {
            "id": image_record.id,
            "image_url": file_url,
            "ai_result": parsed_result,
            "field_key": field_key,
            "row_index": row_index,
        }

    async def get_report_images(self, report_id: UUID) -> list[dict]:
        """获取报告单的所有图片记录"""
        images = await self.image_repo.get_by_report_id(report_id)

        return [
            {
                "id": image.id,
                "report_id": str(image.report_id),
                "row_index": image.row_index,
                "field_key": image.field_key,
                "image_url": image.image_url,
                "ai_result": image.ai_result,
                "created_at": image.created_at.isoformat() if image.created_at else None,
            }
            for image in images
        ]


class ReportTemplateService:
    """报告单模板服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.template_repo = ReportTemplateRepository(session)

    async def create_template(
        self, data: TemplateCreate, file_url: str
    ) -> dict:
        """创建模板"""
        template_data = data.model_dump()
        template_data["template_file_url"] = file_url

        template = await self.template_repo.create(template_data)

        return {
            "id": str(template.id),
            "template_name": template.template_name,
            "template_file_url": template.template_file_url,
            "template_description": template.template_description,
            "field_mapping": template.field_mapping or {},
            "table_fields": template.table_fields or {},
            "is_active": template.is_active,
            "created_at": template.created_at.isoformat(),
        }

    async def get_template(self, template_id: UUID) -> Optional[dict]:
        """获取模板详情"""
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            return None

        return {
            "id": str(template.id),
            "template_name": template.template_name,
            "template_file_url": template.template_file_url,
            "template_description": template.template_description,
            "field_mapping": template.field_mapping or {},
            "table_fields": template.table_fields or {},
            "is_active": template.is_active,
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        }

    async def update_template(
        self, template_id: UUID, data: TemplateUpdate
    ) -> Optional[dict]:
        """更新模板"""
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_template(template_id)

        template = await self.template_repo.update(template_id, update_data)
        if not template:
            return None

        return await self.get_template(template_id)

    async def delete_template(self, template_id: UUID) -> bool:
        """删除模板"""
        return await self.template_repo.delete(template_id)

    async def list_templates(
        self,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """获取模板列表"""
        templates, total = await self.template_repo.list_all(
            is_active=is_active,
            page=page,
            page_size=page_size,
        )

        result = []
        for template in templates:
            item = {
                "id": str(template.id),
                "template_name": template.template_name,
                "template_description": template.template_description,
                "is_active": template.is_active,
                "created_at": template.created_at.isoformat(),
            }
            result.append(item)

        return result, total

    async def parse_template(self, template_id: UUID) -> Optional[dict]:
        """解析模板获取字段配置"""
        from app.modules.quality.word_generator import get_template_fields

        template = await self.template_repo.get_by_id(template_id)
        if not template:
            return None

        template_path = template.template_file_url
        if not template_path.startswith("/"):
            template_path = f"uploads/{template_path}"

        fields = get_template_fields(template_path)

        return {
            "template_id": str(template.id),
            "template_name": template.template_name,
            "field_mapping": fields.get("static", {}),
            "table_fields": fields.get("table"),
        }