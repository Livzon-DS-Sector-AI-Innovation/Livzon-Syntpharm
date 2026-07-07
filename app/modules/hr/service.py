"""HR business workflows live here."""

import logging
from datetime import date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateException, NotFoundException
from app.modules.hr.models import (
    AnnualTrainingPlan,
    AnnualTrainingPlanItem,
    Candidate,
    Department,
    DepartureRecord,
    Employee,
    OffboardingRecord,
    OnboardingRecord,
    Team,
    TrainingLedger,
    TrainingLedgerPage,
    TrainingSession,
)
from app.modules.hr.repository import (
    AnnualTrainingPlanItemRepository,
    AnnualTrainingPlanRepository,
    CandidateRepository,
    DepartureRecordRepository,
    DepartmentRepository,
    EmployeeRepository,
    OffboardingRecordRepository,
    OnboardingRecordRepository,
    TeamRepository,
    TrainingLedgerRepository,
    TrainingLedgerPageRepository,
    TrainingSessionRepository,
)
from app.modules.hr.schemas import (
    AnnualTrainingPlanCreate,
    AnnualTrainingPlanItemBatchUpdate,
    AnnualTrainingPlanItemCreate,
    AnnualTrainingPlanUpdate,
    CandidateCreate,
    CandidateUpdate,
    DepartureRecordCreate,
    DepartureRecordUpdate,
    DepartmentCreate,
    DepartmentUpdate,
    EmployeeCreate,
    EmployeeUpdate,
    OffboardingRecordCreate,
    OffboardingRecordUpdate,
    OnboardingRecordCreate,
    OnboardingRecordUpdate,
    SyncStatusResponse,
    TeamCreate,
    TeamUpdate,
    TrainingLedgerCreate,
    TrainingLedgerUpdate,
    TrainingSessionCreate,
    TrainingSessionUpdate,
)
from app.platform.integrations.feishu import FeishuBitableSync
from app.platform.integrations.feishu.employee_datasource import (
    EmployeeBitableDataSource,
)
from app.platform.integrations.feishu.onboarding_datasource import (
    OnboardingBitableDataSource,
)
from app.platform.integrations.feishu.departure_datasource import (
    DepartureBitableDataSource,
)
from app.platform.integrations.feishu.candidate_datasource import (
    CandidateBitableDataSource,
)
from app.core.config import get_settings
from app.platform.ai.service import AiChatService

logger = logging.getLogger(__name__)

# ─── Feishu field mapping helpers ───

def _extract_text(value) -> str:
    """Extract text from Feishu array format or plain string."""
    if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
        return value[0].get("text", "")
    if isinstance(value, dict):
        if "text" in value:
            return value["text"]
        if "value" in value and isinstance(value["value"], list):
            inner = value["value"]
            if len(inner) > 0 and isinstance(inner[0], dict):
                return inner[0].get("text", "")
    if value is None:
        return ""
    return str(value)


def _extract_number(value) -> int | None:
    """Extract number from Feishu format."""
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, dict):
        if "value" in value and isinstance(value["value"], list) and len(value["value"]) > 0:
            return int(value["value"][0])
    return None


def _ms_to_date(value) -> date | None:
    """Convert Feishu millisecond timestamp to Python date."""
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value / 1000).date()
    return None


def _parse_feishu_record(record: dict) -> dict:
    """Convert a raw Feishu record into Employee constructor kwargs."""
    fields = record.get("fields", {})
    rid = record.get("record_id", "")
    updated_time = record.get("updated_time", "")

    def gt(key: str):
        return fields.get(key)

    data = {
        "feishu_record_id": rid,
        "employee_number": _extract_text(gt("工号")),
        "name": _extract_text(gt("姓名")),
        "domain_account": _extract_text(gt("域账号")),
        "department": gt("部门") or "",
        "team": gt("班组") or "",
        "position": _extract_text(gt("职位")),
        "job_category": gt("职类") or "",
        "level": gt("级别") or "",
        "qualifications": gt("职称／职业资格") if isinstance(gt("职称／职业资格"), list) else None,
        "qualification_type": gt("职称类型") or "",
        "gender": gt("性别") or "",
        "native_place": _extract_text(gt("籍贯")),
        "political_status": gt("政治面貌") or "",
        "marital_status": gt("婚姻状况") or "",
        "household_type": gt("户籍类型") or "",
        "status_category": gt("统计类别") or "",
        "birth_year": _extract_number(gt("年")),
        "birth_month": _extract_number(gt("月")),
        "birth_day": _extract_number(gt("日")),
        "age": _extract_number(gt("年龄")),
        "work_start_date": _ms_to_date(gt("参加工作时间")),
        "factory_entry_date": _ms_to_date(gt("进厂时间")),
        "livo_entry_date": _ms_to_date(gt("入丽珠时间")),
        "hire_date": _ms_to_date(gt("进厂时间")) or date.today(),
        "graduation_date": _ms_to_date(gt("毕业时间")),
        "work_years": _extract_number(gt("工作年限")),
        "factory_tenure": _extract_text(gt("厂龄")),
        "company_tenure": _extract_text(gt("司龄")),
        "education": gt("学历") or "",
        "classification": gt("分类") or "",
        "school": _extract_text(gt("毕业学校")),
        "major": _extract_text(gt("专业")),
        "id_card": _extract_text(gt("身份证号")),
        "id_card_expiry": _extract_text(gt("身份证到期日")),
        "id_card_address": _extract_text(gt("身份证地址|家庭地址")),
        "current_address": _extract_text(gt("现住址")),
        "contract_type": gt("合同期限") or "",
        "contract_start_date": _ms_to_date(gt("第一次合同起点时间")),
        "contract_end_date": _ms_to_date(gt("第一次合同终止时间")),
        "contract_start_2": _ms_to_date(gt("第二次合同起点时间")),
        "contract_end_2": _ms_to_date(gt("第二次合同终止时间")),
        "contract_start_3": _ms_to_date(gt("第三次合同起点时间")),
        "contract_end_3": _ms_to_date(gt("第三次合同终止时间")),
        "contract_start_4": _ms_to_date(gt("第四次合同起点时间")),
        "contract_end_4": _ms_to_date(gt("第四次合同终止时间")),
        "phone": _extract_text(gt("手机")),
        "email": _extract_text(gt("邮箱地址")),
        "emergency_contact_name": "",
        "emergency_contact_phone": _extract_text(gt("紧急联系人电话")),
        "emergency_contact_relation": _extract_text(gt("紧急联系人|关系")),
        "bank_account": _extract_text(gt("银行卡号")),
        "training_id": _extract_text(gt("培训档案编号")),
        "transfer_history": _extract_text(gt("异动（含曾经工作部门、岗位)")),
        "remarks": gt("备注") if isinstance(gt("备注"), list) else None,
        "status": "在职",
    }
    # Parse updated_time for sync tracking
    if updated_time:
        try:
            # Feishu returns ISO format string like "2024-01-15T08:30:00.000000Z"
            dt = datetime.fromisoformat(updated_time.replace("Z", "+00:00"))
            data["feishu_synced_at"] = dt.date()
        except Exception:
            data["feishu_synced_at"] = date.today()
    else:
        data["feishu_synced_at"] = date.today()

    # Remove empty strings for optional text fields to avoid overwriting existing data
    cleaned = {k: v for k, v in data.items() if v != "" or k in ("department", "name", "employee_number", "status", "position")}
    return cleaned


# ─── Services ───

class EmployeeService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = EmployeeRepository(session)
        self.feishu = FeishuBitableSync()
        self.bitable = EmployeeBitableDataSource()

    async def get_employee(self, employee_id: UUID) -> Employee:
        employee = await self.repo.get_by_id(employee_id)
        if not employee:
            raise NotFoundException("员工", str(employee_id))
        return employee

    async def get_employee_by_number(self, employee_number: str) -> Employee:
        employee = await self.repo.get_by_employee_number(employee_number)
        if not employee:
            # 旧厂未找到，尝试从新厂查询
            new_emp = await self.repo.get_new_employee_by_number(employee_number)
            if new_emp:
                return new_emp
            raise NotFoundException("员工", employee_number)
        return employee

    async def create_employee(self, data: EmployeeCreate) -> Employee:
        existing = await self.repo.get_by_employee_number(data.employee_number)
        if existing:
            raise DuplicateException("工号", data.employee_number)

        employee = Employee(**data.model_dump())
        employee.status = "在职"

        # 根据手机号获取飞书 open_id（非阻塞，失败仅记录日志）
        if data.phone:
            try:
                from app.platform.integrations.feishu.im import FeishuIM

                im = FeishuIM()
                # 飞书接口要求手机号带 +86 区号
                mobile = data.phone if data.phone.startswith("+") else f"+86{data.phone}"
                mapping = await im.batch_get_open_ids_by_mobile([mobile])
                open_id = mapping.get(mobile) or mapping.get(data.phone)
                if open_id:
                    employee.feishu_open_id = open_id
                    logger.info(
                        "Fetched feishu_open_id for employee %s: %s",
                        data.employee_number,
                        open_id,
                    )
            except Exception as e:
                logger.warning(
                    "Failed to fetch feishu open_id for phone %s: %s",
                    data.phone,
                    e,
                )

        result = await self.repo.create(employee)

        # Sync to Feishu
        rid = await self.bitable.create(self._to_bitable_fields(result))
        if rid:
            result.feishu_record_id = rid
            result.feishu_synced_at = date.today()
            await self.repo.update(result)

        return result

    async def approve_employee(self, employee_number: str) -> Employee:
        employee = await self.repo.get_by_employee_number(employee_number)
        if not employee:
            raise NotFoundException("员工", employee_number)
        if employee.status != "待审批":
            raise DuplicateException("审批", "该员工已审批完成")

        employee.status = "在职"
        result = await self.repo.update(employee)

        try:
            await self._sync_single_to_feishu(result)
        except Exception as e:
            logger.warning("Feishu sync failed for employee approved: %s", e)

        return result

    async def update_employee(self, employee_id: UUID, data: EmployeeUpdate) -> Employee:
        employee = await self.get_employee(employee_id)
        update_data = data.model_dump(exclude_unset=True)

        if "employee_number" in update_data:
            existing = await self.repo.get_by_employee_number(update_data["employee_number"])
            if existing and existing.id != employee_id:
                raise DuplicateException("工号", update_data["employee_number"])

        for field, value in update_data.items():
            setattr(employee, field, value)

        result = await self.repo.update(employee)

        try:
            await self._sync_single_to_feishu(result)
        except Exception as e:
            logger.warning("Feishu sync failed for employee updated: %s", e)

        return result

    async def delete_employee(self, employee_id: UUID) -> None:
        employee = await self.get_employee(employee_id)
        employee_number = employee.employee_number
        await self.repo.soft_delete(employee)

        try:
            if employee.feishu_record_id:
                await self.bitable.delete(employee.feishu_record_id)
            else:
                await self.feishu.sync_employee_deleted(employee_number)
        except Exception as e:
            logger.warning("Feishu sync failed for employee deleted: %s", e)

    async def list_employees(
        self,
        *,
        department: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Employee], int]:
        return await self.repo.list_employees(
            department=department,
            status=status,
            keyword=keyword,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def notify_training(self, payload) -> dict:
        """给受训人员发送飞书单聊消息。

        老厂员工直接读取 employees 表的 feishu_open_id；
        新厂员工从 employees_new 表查询，若缺少 feishu_open_id 则根据手机号实时获取。

        Args:
            payload: TrainingNotifyInput instance.
        """
        from app.platform.integrations.feishu.im import FeishuIM
        from sqlalchemy import text

        im = FeishuIM()
        is_new_factory = getattr(payload, "factory", None) == "new"

        # 1. 查询所有员工
        emp_list: list[Employee] = []
        missing_numbers: list[str] = []
        for emp_no in payload.employee_numbers:
            if is_new_factory:
                sql = text(
                    "SELECT * FROM hr.employees_new "
                    "WHERE employee_number = :eno AND is_deleted = false"
                )
                result = await self.repo.session.execute(sql, {"eno": emp_no})
                row = result.mappings().first()
                if row:
                    emp_list.append(Employee(**dict(row)))
                else:
                    missing_numbers.append(emp_no)
            else:
                emp = await self.repo.get_by_employee_number(emp_no)
                if emp:
                    emp_list.append(emp)
                else:
                    missing_numbers.append(emp_no)

        # 2. 对缺少 open_id 的员工，按手机号批量获取
        phones_to_fetch: list[str] = []
        phone_emp_map: dict[str, Employee] = {}
        for emp in emp_list:
            if not emp.feishu_open_id and emp.phone:
                mobile = emp.phone if emp.phone.startswith("+") else f"+86{emp.phone}"
                phones_to_fetch.append(mobile)
                phone_emp_map[mobile] = emp
                # 同时保留原始号码作为 fallback key
                if emp.phone not in phone_emp_map:
                    phone_emp_map[emp.phone] = emp

        if phones_to_fetch:
            try:
                open_id_mapping = await im.batch_get_open_ids_by_mobile(phones_to_fetch)
                for mobile, open_id in open_id_mapping.items():
                    emp = phone_emp_map.get(mobile)
                    if emp and open_id:
                        emp.feishu_open_id = open_id
                        logger.info(
                            "Fetched feishu_open_id for %s (%s): %s",
                            emp.name, emp.employee_number, open_id,
                        )
                        # 把获取到的 openid 持久化到数据库
                        try:
                            if is_new_factory:
                                update_sql = text(
                                    "UPDATE hr.employees_new SET feishu_open_id = :oid WHERE employee_number = :eno"
                                )
                            else:
                                update_sql = text(
                                    "UPDATE hr.employees SET feishu_open_id = :oid WHERE employee_number = :eno"
                                )
                            await self.repo.session.execute(
                                update_sql,
                                {"oid": open_id, "eno": emp.employee_number},
                            )
                        except Exception as db_err:
                            logger.warning(
                                "Failed to persist feishu_open_id for %s: %s",
                                emp.employee_number,
                                db_err,
                            )
                # 统一 flush，让 get_db 在请求结束时统一 commit
                await self.repo.session.flush()
            except Exception as e:
                logger.warning("Batch get open_id by mobile failed: %s", e)

        # 3. 组装消息内容
        time_str = ""
        if payload.training_time_start and payload.training_time_end:
            time_str = f"{payload.training_time_start} ~ {payload.training_time_end}"
        content_lines = [
            "【培训通知】",
            f"主题：{payload.subject}",
            f"时间：{payload.training_date} {time_str}",
            f"地点：{payload.location or '待定'}",
            f"培训师：{payload.trainer or '待定'}",
        ]
        if payload.content:
            content_lines.append(f"内容：{payload.content}")
        content_lines.append("请准时参加，自带笔记本笔，不得无故缺席。")
        content = "\n".join(content_lines)

        # 4. 逐条发送
        sent = 0
        failed = 0
        details: list[dict] = []
        for emp in emp_list:
            open_id = emp.feishu_open_id
            if not open_id:
                failed += 1
                reason = "数据库中缺少 feishu_open_id 且手机号未关联到飞书"
                if not emp.phone:
                    reason = "数据库中缺少 feishu_open_id 且无手机号"
                details.append(
                    {
                        "employee_number": emp.employee_number,
                        "name": emp.name,
                        "status": "failed",
                        "reason": reason,
                    }
                )
                continue

            try:
                await im.send_text_message(open_id, content)
                sent += 1
                details.append(
                    {
                        "employee_number": emp.employee_number,
                        "name": emp.name,
                        "status": "sent",
                    }
                )
            except Exception as e:
                failed += 1
                details.append(
                    {
                        "employee_number": emp.employee_number,
                        "name": emp.name,
                        "status": "failed",
                        "reason": str(e),
                    }
                )

        # 未找到的员工
        for emp_no in missing_numbers:
            failed += 1
            details.append(
                {
                    "employee_number": emp_no,
                    "name": "",
                    "status": "failed",
                    "reason": "未找到该员工",
                }
            )

        return {"sent": sent, "failed": failed, "details": details}

    # ─── Bi-directional sync ───

    async def sync_from_feishu(self) -> dict:
        """Pull all records from Feishu Bitable and upsert into local PG.

        Returns:
            {"created": N, "updated": N, "failed": N, "total": N}
        """
        # Use raw client to get original dicts instead of EmployeeRecord wrappers
        raw_records = await self.bitable.client.search_records(
            self.bitable.table_id,
            page_size=500,
        )
        stats = {"created": 0, "updated": 0, "failed": 0, "total": len(raw_records)}

        for rec in raw_records:
            try:
                parsed = _parse_feishu_record(rec)
                emp_no = parsed.get("employee_number")
                if not emp_no:
                    stats["failed"] += 1
                    continue

                await self.repo.upsert_by_employee_number(parsed)
                existing = await self.repo.get_by_employee_number(emp_no)
                if existing and existing.created_at and (datetime.utcnow() - existing.created_at.replace(tzinfo=None)).total_seconds() < 60:
                    stats["created"] += 1
                else:
                    stats["updated"] += 1
            except Exception as e:
                logger.error("Failed to sync Feishu record %s: %s", rec.get("record_id"), e)
                stats["failed"] += 1

        return stats

    async def sync_to_feishu(self, employee_id: UUID) -> str:
        """Force-sync a single employee to Feishu.

        Returns the Feishu record_id.
        """
        employee = await self.get_employee(employee_id)
        return await self._sync_single_to_feishu(employee)

    async def get_sync_status(self) -> SyncStatusResponse:
        local_total = await self.repo.count_total()
        synced_count = await self.repo.count_synced()
        unsynced_count = local_total - synced_count

        # Use local synced count as feishu_total proxy to avoid expensive
        # real-time Feishu API calls (fetching 500 records takes ~5s).
        # Data consistency is ensured by the sync process itself.
        feishu_total = synced_count

        return SyncStatusResponse(
            local_total=local_total,
            feishu_total=feishu_total,
            synced_count=synced_count,
            unsynced_count=unsynced_count,
            conflict_count=0,  # TODO: implement conflict detection
            last_sync_at=None,
        )

    # ─── Internal helpers ───

    async def _sync_single_to_feishu(self, employee: Employee) -> str:
        """Sync one employee to Feishu, creating or updating as needed."""
        fields = self._to_bitable_fields(employee)
        if employee.feishu_record_id:
            await self.bitable.update(employee.feishu_record_id, fields)
            return employee.feishu_record_id
        else:
            rid = await self.bitable.create(fields)
            employee.feishu_record_id = rid
            employee.feishu_synced_at = date.today()
            await self.repo.update(employee)
            return rid

    def _to_bitable_fields(self, employee: Employee) -> dict:
        """Convert Employee ORM object to Feishu Bitable field dict.

        Filters out empty values to avoid Feishu validation errors
        (especially for phone fields which reject empty strings).
        """
        from app.platform.integrations.feishu.bitable import _to_ms_timestamp

        # Build raw fields, keeping None/empty filtering for later
        raw: dict = {
            "姓名": employee.name,
            "工号": employee.employee_number,
            "部门": employee.department,
            "职位": employee.position,
            "手机": employee.phone,
            "邮箱地址": employee.email,
            "性别": employee.gender,
            "籍贯": employee.native_place,
            "政治面貌": employee.political_status,
            "婚姻状况": employee.marital_status,
            "学历": employee.education,
            "分类": employee.classification,
            "专业": employee.major,
            "身份证号": employee.id_card,
            "银行卡号": employee.bank_account,
            "培训档案编号": employee.training_id,
            "域账号": employee.domain_account,
            "班组": employee.team,
            "职类": employee.job_category,
            "级别": employee.level,
            "职称类型": employee.qualification_type,
            "户籍类型": employee.household_type,
            "统计类别": employee.status_category,
            "身份证到期日": employee.id_card_expiry,
            "合同期限": employee.contract_type,
            "身份证地址|家庭地址": employee.id_card_address,
            "现住址": employee.current_address,
            "紧急联系人电话": employee.emergency_contact_phone,
            "紧急联系人|关系": employee.emergency_contact_relation,
            "异动（含曾经工作部门、岗位)": employee.transfer_history,
        }
        # Filter out empty strings / None / empty lists
        fields = {k: v for k, v in raw.items() if v not in (None, "", [])}

        if employee.qualifications:
            fields["职称／职业资格"] = employee.qualifications
        if employee.remarks:
            fields["备注"] = employee.remarks

        # Dates
        if employee.work_start_date:
            fields["参加工作时间"] = _to_ms_timestamp(employee.work_start_date)
        if employee.factory_entry_date:
            fields["进厂时间"] = _to_ms_timestamp(employee.factory_entry_date)
        if employee.livo_entry_date:
            fields["入丽珠时间"] = _to_ms_timestamp(employee.livo_entry_date)
        if employee.graduation_date:
            fields["毕业时间"] = _to_ms_timestamp(employee.graduation_date)
        if employee.contract_start_date:
            fields["第一次合同起点时间"] = _to_ms_timestamp(employee.contract_start_date)
        if employee.contract_end_date:
            fields["第一次合同终止时间"] = _to_ms_timestamp(employee.contract_end_date)
        if employee.contract_start_2:
            fields["第二次合同起点时间"] = _to_ms_timestamp(employee.contract_start_2)
        if employee.contract_end_2:
            fields["第二次合同终止时间"] = _to_ms_timestamp(employee.contract_end_2)
        if employee.contract_start_3:
            fields["第三次合同起点时间"] = _to_ms_timestamp(employee.contract_start_3)
        if employee.contract_end_3:
            fields["第三次合同终止时间"] = _to_ms_timestamp(employee.contract_end_3)
        if employee.contract_start_4:
            fields["第四次合同起点时间"] = _to_ms_timestamp(employee.contract_start_4)
        if employee.contract_end_4:
            fields["第四次合同终止时间"] = _to_ms_timestamp(employee.contract_end_4)

        # Birth date
        if employee.birth_year:
            fields["年"] = employee.birth_year
        if employee.birth_month:
            fields["月"] = employee.birth_month
        if employee.birth_day:
            fields["日"] = employee.birth_day

        return fields


class DepartmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = DepartmentRepository(session)
        self.feishu = FeishuBitableSync()

    async def get_department(self, department_id: UUID) -> Department:
        department = await self.repo.get_by_id(department_id)
        if not department:
            raise NotFoundException("部门", str(department_id))
        return department

    async def create_department(self, data: DepartmentCreate) -> Department:
        existing = await self.repo.get_by_code(data.code)
        if existing:
            raise DuplicateException("部门编码", data.code)

        department = Department(**data.model_dump())
        result = await self.repo.create(department)

        try:
            await self.feishu.sync_department_created(result.__dict__)
        except Exception as e:
            logger.warning("Feishu sync failed for department created: %s", e)

        return result

    async def update_department(self, department_id: UUID, data: DepartmentUpdate) -> Department:
        department = await self.get_department(department_id)
        update_data = data.model_dump(exclude_unset=True)

        if "code" in update_data:
            existing = await self.repo.get_by_code(update_data["code"])
            if existing and existing.id != department_id:
                raise DuplicateException("部门编码", update_data["code"])

        for field, value in update_data.items():
            setattr(department, field, value)

        result = await self.repo.update(department)

        try:
            await self.feishu.sync_department_updated(result.__dict__)
        except Exception as e:
            logger.warning("Feishu sync failed for department updated: %s", e)

        return result

    async def delete_department(self, department_id: UUID) -> None:
        department = await self.get_department(department_id)
        code = department.code
        await self.repo.soft_delete(department)

        try:
            await self.feishu.sync_department_deleted(code)
        except Exception as e:
            logger.warning("Feishu sync failed for department deleted: %s", e)

    async def list_departments(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Department], int]:
        return await self.repo.list_departments(
            keyword=keyword,
            page=page,
            page_size=page_size,
        )


class TeamService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = TeamRepository(session)
        self.department_repo = DepartmentRepository(session)

    async def get_team(self, team_id: UUID) -> Team:
        team = await self.repo.get_by_id(team_id)
        if not team:
            raise NotFoundException("班组", str(team_id))
        return team

    async def create_team(self, data: TeamCreate) -> Team:
        department = await self.department_repo.get_by_id(data.department_id)
        if not department:
            raise NotFoundException("部门", str(data.department_id))

        team = Team(**data.model_dump())
        result = await self.repo.create(team)
        return result

    async def update_team(self, team_id: UUID, data: TeamUpdate) -> Team:
        team = await self.get_team(team_id)
        update_data = data.model_dump(exclude_unset=True)

        if "department_id" in update_data:
            department = await self.department_repo.get_by_id(update_data["department_id"])
            if not department:
                raise NotFoundException("部门", str(update_data["department_id"]))

        for field, value in update_data.items():
            setattr(team, field, value)

        result = await self.repo.update(team)
        return result

    async def delete_team(self, team_id: UUID) -> None:
        team = await self.get_team(team_id)
        await self.repo.soft_delete(team)

    async def list_teams(
        self,
        *,
        department_id: UUID | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Team], int]:
        return await self.repo.list_teams(
            department_id=department_id,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )


class OffboardingRecordService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = OffboardingRecordRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.feishu = FeishuBitableSync()

    async def get_record(self, record_id: UUID) -> OffboardingRecord:
        record = await self.repo.get_by_id(record_id)
        if not record:
            raise NotFoundException("离职记录", str(record_id))
        return record

    async def create_record(self, data: OffboardingRecordCreate) -> OffboardingRecord:
        employee = await self.employee_repo.get_by_id(data.employee_id)
        if not employee:
            raise NotFoundException("员工", str(data.employee_id))

        record = OffboardingRecord(**data.model_dump())
        record = await self.repo.create(record)

        # 自动将员工状态更新为离职
        employee.status = "离职"
        await self.employee_repo.update(employee)

        # 同步到飞书
        try:
            record_dict = {
                **record.__dict__,
                "employee": {
                    "name": employee.name,
                    "employee_number": employee.employee_number,
                },
            }
            await self.feishu.sync_offboarding_created(record_dict)
        except Exception as e:
            logger.warning("Feishu sync failed for offboarding created: %s", e)

        return record

    async def update_record(self, record_id: UUID, data: OffboardingRecordUpdate) -> OffboardingRecord:
        record = await self.get_record(record_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(record, field, value)

        result = await self.repo.update(record)

        try:
            await self.feishu.sync_offboarding_updated(result.__dict__)
        except Exception as e:
            logger.warning("Feishu sync failed for offboarding updated: %s", e)

        return result

    async def delete_record(self, record_id: UUID) -> None:
        record = await self.get_record(record_id)
        await self.repo.soft_delete(record)

    async def list_records(
        self,
        *,
        employee_id: UUID | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[OffboardingRecord], int]:
        return await self.repo.list_records(
            employee_id=employee_id,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )


class OnboardingRecordService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = OnboardingRecordRepository(session)
        self.bitable = OnboardingBitableDataSource()

    async def get_record(self, record_id: UUID) -> OnboardingRecord:
        record = await self.repo.get_by_id(record_id)
        if not record:
            raise NotFoundException("入职记录", str(record_id))
        return record

    async def list_records(
        self,
        *,
        department: str | None = None,
        position: str | None = None,
        is_employed: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "hire_date",
        sort_order: str = "desc",
    ) -> tuple[list[OnboardingRecord], int]:
        return await self.repo.list_records(
            department=department,
            position=position,
            is_employed=is_employed,
            keyword=keyword,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def sync_from_feishu(self) -> dict:
        """Pull all records from Feishu Bitable and upsert into local PG.

        Returns:
            {"created": N, "updated": N, "failed": N, "total": N}
        """
        raw_records = await self.bitable.client.search_records(
            self.bitable.table_id,
            page_size=500,
        )
        stats = {"created": 0, "updated": 0, "failed": 0, "total": len(raw_records)}

        for rec in raw_records:
            try:
                from app.platform.integrations.feishu.onboarding_datasource import (
                    OnboardingRecord as BitableOnboardingRecord,
                )

                parsed = BitableOnboardingRecord.from_api(rec)
                data = parsed.to_dict()
                data["feishu_synced_at"] = date.today()
                rid = data.get("feishu_record_id")
                if not rid:
                    stats["failed"] += 1
                    continue

                # Skip records with empty critical fields (blank rows in Bitable)
                if not data.get("name") or not data.get("department") or not data.get("hire_date"):
                    logger.debug("Skipping blank onboarding record: %s", rid)
                    continue

                await self.repo.upsert_by_feishu_record_id(data)
                existing = await self.repo.get_by_feishu_record_id(rid)
                if existing and existing.created_at and (
                    datetime.utcnow() - existing.created_at.replace(tzinfo=None)
                ).total_seconds() < 60:
                    stats["created"] += 1
                else:
                    stats["updated"] += 1
            except Exception as e:
                logger.error("Failed to sync onboarding record %s: %s", rec.get("record_id"), e)
                stats["failed"] += 1

        return stats

    async def get_sync_status(self) -> SyncStatusResponse:
        local_total = await self.repo.count_total()
        synced_count = await self.repo.count_synced()
        unsynced_count = local_total - synced_count
        feishu_total = synced_count

        return SyncStatusResponse(
            local_total=local_total,
            feishu_total=feishu_total,
            synced_count=synced_count,
            unsynced_count=unsynced_count,
            conflict_count=0,
            last_sync_at=None,
        )


class DepartureRecordService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = DepartureRecordRepository(session)
        self.bitable = DepartureBitableDataSource()

    async def get_record(self, record_id: UUID) -> DepartureRecord:
        record = await self.repo.get_by_id(record_id)
        if not record:
            raise NotFoundException("离职台账记录", str(record_id))
        return record

    async def list_records(
        self,
        *,
        department: str | None = None,
        offboarding_type: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "offboarding_date",
        sort_order: str = "desc",
    ) -> tuple[list[DepartureRecord], int]:
        return await self.repo.list_records(
            department=department,
            offboarding_type=offboarding_type,
            keyword=keyword,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def create_record(self, data: DepartureRecordCreate) -> DepartureRecord:
        record = DepartureRecord(**data.model_dump())
        return await self.repo.create(record)

    async def update_record(self, record_id: UUID, data: DepartureRecordUpdate) -> DepartureRecord:
        record = await self.get_record(record_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(record, field, value)
        return await self.repo.update(record)

    async def delete_record(self, record_id: UUID) -> None:
        record = await self.get_record(record_id)
        await self.repo.soft_delete(record)

    async def sync_from_feishu(self) -> dict:
        """Pull all records from Feishu Bitable and upsert into local PG.

        Returns:
            {"created": N, "updated": N, "failed": N, "total": N}
        """
        raw_records = await self.bitable.client.search_records(
            self.bitable.table_id,
            page_size=500,
        )
        stats = {"created": 0, "updated": 0, "failed": 0, "total": len(raw_records)}

        for rec in raw_records:
            try:
                from app.platform.integrations.feishu.departure_datasource import (
                    DepartureRecord as BitableDepartureRecord,
                )

                parsed = BitableDepartureRecord.from_api(rec)
                data = parsed.to_dict()
                data["feishu_synced_at"] = date.today()
                rid = data.get("feishu_record_id")
                if not rid:
                    stats["failed"] += 1
                    continue

                await self.repo.upsert_by_feishu_record_id(data)
                existing = await self.repo.get_by_feishu_record_id(rid)
                if existing and existing.created_at and (
                    datetime.utcnow() - existing.created_at.replace(tzinfo=None)
                ).total_seconds() < 60:
                    stats["created"] += 1
                else:
                    stats["updated"] += 1
            except Exception:
                logger.exception("Failed to sync departure record %s", rec.get("record_id"))
                stats["failed"] += 1

        return stats

    async def get_sync_status(self) -> SyncStatusResponse:
        local_total = await self.repo.count_total()
        synced_count = await self.repo.count_synced()
        unsynced_count = local_total - synced_count
        feishu_total = synced_count

        return SyncStatusResponse(
            local_total=local_total,
            feishu_total=feishu_total,
            synced_count=synced_count,
            unsynced_count=unsynced_count,
            conflict_count=0,
            last_sync_at=None,
        )


class TrainingLedgerService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = TrainingLedgerRepository(session)

    async def get_record(self, record_id: UUID) -> TrainingLedger:
        record = await self.repo.get_by_id(record_id)
        if not record:
            raise NotFoundException("培训台账记录", str(record_id))
        return record

    async def create_record(self, data: TrainingLedgerCreate) -> TrainingLedger:
        record = TrainingLedger(**data.model_dump())
        return await self.repo.create(record)

    async def update_record(
        self, record_id: UUID, data: TrainingLedgerUpdate
    ) -> TrainingLedger:
        record = await self.get_record(record_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(record, field, value)
        return await self.repo.update(record)

    async def delete_record(self, record_id: UUID) -> None:
        record = await self.get_record(record_id)
        await self.repo.soft_delete(record)

    async def list_records(
        self,
        *,
        employee_number: str | None = None,
        ledger_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "training_date",
        sort_order: str = "asc",
    ) -> tuple[list[TrainingLedger], int]:
        return await self.repo.list_records(
            employee_number=employee_number,
            ledger_type=ledger_type,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def create_from_notification(
        self,
        *,
        employee_number: str,
        training_date: date,
        training_subject: str,
        training_method: str | None,
        trainer: str | None,
        source_id: str | None = None,
    ) -> TrainingLedger | None:
        """当培训通知包含特定员工时，自动创建培训台账记录。"""
        if source_id:
            existing = await self.repo.get_by_source("notification", source_id)
            if existing:
                return existing

        record = TrainingLedger(
            employee_number=employee_number,
            training_date=training_date,
            training_subject=training_subject,
            training_method=training_method,
            trainer=trainer,
            source_type="notification",
            source_id=source_id,
        )
        return await self.repo.create(record)


class TrainingLedgerPageService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = TrainingLedgerPageRepository(session)

    async def list_pages(self) -> list[TrainingLedgerPage]:
        return await self.repo.list_pages()

    async def list_pages_with_department(self) -> list[tuple[TrainingLedgerPage, str | None, str | None]]:
        return await self.repo.list_pages_with_department()

    async def create_page(self, data) -> TrainingLedgerPage:
        existing = await self.repo.get_by_employee_number(data.employee_number, data.ledger_type)
        if existing:
            raise DuplicateException("培训台账页面", f"{data.employee_number}({data.ledger_type})")
        page = TrainingLedgerPage(**data.model_dump())
        return await self.repo.create(page)


class TrainingSessionService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = TrainingSessionRepository(session)

    async def get_session(self, session_id: UUID) -> TrainingSession:
        session_obj = await self.repo.get_by_id(session_id)
        if not session_obj:
            raise NotFoundException("培训记录", str(session_id))
        return session_obj

    async def create_session(self, data: TrainingSessionCreate) -> TrainingSession:
        session_obj = TrainingSession(**data.model_dump())
        return await self.repo.create(session_obj)

    async def update_session(
        self, session_id: UUID, data: TrainingSessionUpdate
    ) -> TrainingSession:
        session_obj = await self.get_session(session_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(session_obj, field, value)
        return await self.repo.update(session_obj)

    async def update_status(self, session_id: UUID, status: str) -> TrainingSession:
        session_obj = await self.get_session(session_id)
        session_obj.status = status
        return await self.repo.update(session_obj)

    async def link_select_task(self, session_id: UUID, token: str) -> TrainingSession:
        session_obj = await self.get_session(session_id)
        session_obj.select_task_token = token
        session_obj.status = "selecting"
        return await self.repo.update(session_obj)

    async def check_all_select_tasks_completed(self, session_id: UUID) -> bool:
        session_obj = await self.get_session(session_id)
        select_tasks = session_obj.select_tasks or []
        if not select_tasks:
            return False
        return all(task.get("status") == "submitted" for task in select_tasks)

    async def delete_session(self, session_id: UUID) -> None:
        session_obj = await self.get_session(session_id)
        await self.repo.soft_delete(session_obj)

    async def list_sessions(
        self,
        *,
        department: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "training_date",
        sort_order: str = "desc",
    ) -> tuple[list[TrainingSession], int]:
        return await self.repo.list_sessions(
            department=department,
            keyword=keyword,
            status=status,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def check_all_select_tasks_completed(self, session_id: UUID) -> bool:
        session_obj = await self.get_session(session_id)
        select_tasks = session_obj.select_tasks or []
        if not select_tasks:
            return False
        return all(task.get("status") == "submitted" for task in select_tasks)


class AnnualTrainingPlanService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AnnualTrainingPlanRepository(session)
        self.item_repo = AnnualTrainingPlanItemRepository(session)

    async def get_plan(self, plan_id: UUID) -> AnnualTrainingPlan:
        plan = await self.repo.get_by_id(plan_id)
        if not plan:
            raise NotFoundException("年度培训计划", str(plan_id))
        return plan

    async def create_plan(self, data: AnnualTrainingPlanCreate) -> AnnualTrainingPlan:
        existing = await self.repo.get_by_year_and_department(data.year, data.department)
        if existing:
            raise DuplicateException("年度培训计划", f"{data.year}年-{data.department}")
        plan = AnnualTrainingPlan(**data.model_dump())
        return await self.repo.create(plan)

    async def update_plan(self, plan_id: UUID, data: AnnualTrainingPlanUpdate) -> AnnualTrainingPlan:
        plan = await self.get_plan(plan_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(plan, field, value)
        return await self.repo.update(plan)

    async def delete_plan(self, plan_id: UUID) -> None:
        plan = await self.get_plan(plan_id)
        await self.repo.soft_delete(plan)

    async def list_plans(
        self,
        *,
        year: int | None = None,
        department: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[AnnualTrainingPlan], int]:
        return await self.repo.list_plans(
            year=year,
            department=department,
            page=page,
            page_size=page_size,
        )


class AnnualTrainingPlanItemService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AnnualTrainingPlanItemRepository(session)
        self.plan_repo = AnnualTrainingPlanRepository(session)

    async def list_items(self, plan_id: UUID) -> list[AnnualTrainingPlanItem]:
        return await self.repo.list_items(plan_id)

    async def batch_update_items(
        self, plan_id: UUID, data: AnnualTrainingPlanItemBatchUpdate
    ) -> list[AnnualTrainingPlanItem]:
        plan = await self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise NotFoundException("年度培训计划", str(plan_id))

        # 删除旧明细
        await self.repo.delete_by_plan_id(plan_id)

        # 创建新明细
        results: list[AnnualTrainingPlanItem] = []
        for idx, item_data in enumerate(data.items):
            item = AnnualTrainingPlanItem(
                plan_id=plan_id,
                sort_order=idx,
                **item_data.model_dump(exclude={"sort_order"}),
            )
            created = await self.repo.create(item)
            results.append(created)
        return results


class CandidateService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = CandidateRepository(session)
        self.bitable = CandidateBitableDataSource()
        settings = get_settings()
        self.ai_chat = AiChatService(
            api_key=settings.MOONSHOT_API_KEY or "",
            model=settings.AI_MODEL or "kimi-k2.5",
        )

    async def get_candidate(self, candidate_id: UUID) -> Candidate:
        candidate = await self.repo.get_by_id(candidate_id)
        if not candidate:
            raise NotFoundException("候选人", str(candidate_id))
        return candidate

    async def list_candidates(
        self,
        *,
        position: str | None = None,
        education: str | None = None,
        keyword: str | None = None,
        recommendation_level: str | None = None,
        sync_status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Candidate], int]:
        return await self.repo.list_candidates(
            position=position,
            education=education,
            keyword=keyword,
            recommendation_level=recommendation_level,
            sync_status=sync_status,
            page=page,
            page_size=page_size,
        )

    async def create_candidate(self, data: CandidateCreate) -> Candidate:
        candidate = Candidate(**data.model_dump())
        return await self.repo.create(candidate)

    async def parse_resume_preview(
        self, resume_bytes: bytes, position: str
    ) -> dict[str, str]:
        """Convert PDF to images and parse resume via vision-capable AI."""
        logger.info(
            "parse_resume_preview called: position=%s, pdf_size=%d bytes",
            position,
            len(resume_bytes),
        )
        images: list[bytes] = []
        try:
            import fitz

            doc = fitz.open(stream=resume_bytes, filetype="pdf")
            page_count = len(doc)
            logger.info("PDF opened: %d pages", page_count)
            for idx, page in enumerate(doc):
                if idx >= 5:
                    logger.warning(
                        "Resume PDF has more than 5 pages, only first 5 will be parsed"
                    )
                    break
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                logger.info(
                    "Page %d rendered: %dx%d, %d bytes",
                    idx + 1,
                    pix.width,
                    pix.height,
                    len(img_bytes),
                )
                images.append(img_bytes)
            doc.close()
        except Exception:
            logger.exception("Failed to convert uploaded PDF to images")
            return {
                "gender": "",
                "school": "",
                "education": "",
                "major": "",
                "match_report": "",
                "recommendation_level": "",
            }

        if not images:
            logger.warning("No images extracted from PDF")
            return {
                "gender": "",
                "school": "",
                "education": "",
                "major": "",
                "match_report": "",
                "recommendation_level": "",
            }

        logger.info(
            "Calling AI vision parser with %d images for position=%s",
            len(images),
            position,
        )
        try:
            result = await self.ai_chat.parse_resume_from_images(images, position)
            logger.info("AI parser result: %s", result)
            return result
        except Exception:
            logger.exception("Failed to parse resume images via AI")
            return {
                "gender": "",
                "school": "",
                "education": "",
                "major": "",
                "match_report": "",
                "recommendation_level": "",
            }

    async def create_candidate_with_resume(
        self,
        name: str,
        position: str,
        resume_bytes: bytes,
        filename: str,
        *,
        gender: str | None = None,
        school: str | None = None,
        education: str | None = None,
        major: str | None = None,
        match_report: str | None = None,
        recommendation_level: str | None = None,
    ) -> Candidate:
        """Create a candidate with resume upload and Feishu sync."""
        import os
        from typing import Any

        candidate = Candidate(
            name=name,
            position=position,
            gender=gender or None,
            school=school or None,
            education=education or None,
            major=major or None,
            match_report=match_report or None,
            recommendation_level=recommendation_level or None,
        )
        created = await self.repo.create(candidate)

        upload_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "uploads", "resumes"
        )
        upload_dir = os.path.abspath(upload_dir)
        os.makedirs(upload_dir, exist_ok=True)
        ext = os.path.splitext(filename)[1] or ".pdf"
        file_path = os.path.join(upload_dir, f"{created.id}{ext}")
        with open(file_path, "wb") as f:
            f.write(resume_bytes)
        created.resume_storage_path = file_path
        await self.repo.update(created)

        sync_error_parts: list[str] = []
        feishu_file: dict[str, Any] = {}

        try:
            feishu_file = await self.bitable.upload_resume(
                resume_bytes, filename or f"{name}.pdf"
            )
        except Exception as exc:
            logger.exception("Failed to upload resume to Feishu Drive")
            sync_error_parts.append(f"Drive upload failed: {exc}")

        try:
            fields: dict[str, Any] = {
                "候选人姓名": name,
                "应聘职位名称": position,
                "性别": gender or "",
                "学校名称": school or "",
                "学历": education or "",
                "专业": major or "",
                "候选人匹配度报告-AI.输出结果": match_report or "",
                "推荐等级": recommendation_level or "",
            }
            if feishu_file.get("file_token"):
                fields["简历 PDF"] = [
                    {
                        "file_token": feishu_file["file_token"],
                        "name": feishu_file.get(
                            "name", filename or f"{name}.pdf"
                        ),
                        "size": feishu_file.get("size", len(resume_bytes)),
                        "type": "application/pdf",
                    }
                ]
            record_id = await self.bitable.create(fields)
            created.feishu_record_id = record_id
            created.feishu_synced_at = date.today()
            created.feishu_sync_status = "synced"
            created.feishu_sync_error = None
            await self.repo.update(created)
        except Exception as exc:
            logger.exception("Failed to create candidate record in Feishu")
            sync_error_parts.append(f"Bitable create failed: {exc}")
            created.feishu_sync_status = "failed"
            created.feishu_sync_error = "; ".join(sync_error_parts) if sync_error_parts else str(exc)
            await self.repo.update(created)

        return created

    async def update_candidate(self, candidate_id: UUID, data: CandidateUpdate) -> Candidate:
        candidate = await self.get_candidate(candidate_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(candidate, field, value)
        updated = await self.repo.update(candidate)

        if candidate.feishu_record_id:
            feishu_field_map = {
                "position": "应聘职位名称",
                "gender": "性别",
                "school": "学校名称",
                "education": "学历",
                "major": "专业",
            }
            feishu_fields = {
                feishu_field_map[k]: v
                for k, v in update_data.items()
                if k in feishu_field_map and v is not None
            }
            if feishu_fields:
                try:
                    await self.bitable.update(candidate.feishu_record_id, feishu_fields)
                except Exception as exc:
                    logger.exception(
                        "Failed to sync candidate update to Feishu %s", candidate_id
                    )
                    updated.feishu_sync_status = "failed"
                    updated.feishu_sync_error = f"Update sync failed: {exc}"
                    await self.repo.update(updated)

        return updated

    async def update_recommendation_level(self, candidate_id: UUID, level: str) -> Candidate:
        candidate = await self.get_candidate(candidate_id)
        candidate.recommendation_level = level
        updated = await self.repo.update(candidate)

        if candidate.feishu_record_id:
            try:
                await self.bitable.update_recommendation_level(
                    candidate.feishu_record_id, level
                )
            except Exception as exc:
                logger.exception(
                    "Failed to sync recommendation level to Feishu for %s",
                    candidate_id,
                )
                updated.feishu_sync_status = "failed"
                updated.feishu_sync_error = f"Recommendation level sync failed: {exc}"
                await self.repo.update(updated)

        return updated

    async def sync_candidate_to_feishu(self, candidate_id: UUID) -> Candidate:
        """Retry syncing a candidate (and resume) to Feishu."""
        import os
        from typing import Any

        candidate = await self.get_candidate(candidate_id)

        if not candidate.resume_storage_path or not os.path.exists(candidate.resume_storage_path):
            raise RuntimeError("Local resume file not found, cannot sync to Feishu")

        with open(candidate.resume_storage_path, "rb") as f:
            resume_bytes = f.read()

        filename = os.path.basename(candidate.resume_storage_path)
        sync_error_parts: list[str] = []
        feishu_file: dict[str, Any] = {}

        try:
            feishu_file = await self.bitable.upload_resume(
                resume_bytes, filename or f"{candidate.name}.pdf"
            )
        except Exception as exc:
            logger.exception("Failed to upload resume to Feishu Drive during retry")
            sync_error_parts.append(f"Drive upload failed: {exc}")

        try:
            fields: dict[str, Any] = {
                "候选人姓名": candidate.name or "",
                "应聘职位名称": candidate.position or "",
                "性别": candidate.gender or "",
                "学校名称": candidate.school or "",
                "学历": candidate.education or "",
                "专业": candidate.major or "",
                "候选人匹配度报告-AI.输出结果": candidate.match_report or "",
                "推荐等级": candidate.recommendation_level or "",
            }
            if feishu_file.get("file_token"):
                fields["简历 PDF"] = [
                    {
                        "file_token": feishu_file["file_token"],
                        "name": feishu_file.get("name", filename or f"{candidate.name}.pdf"),
                        "size": feishu_file.get("size", len(resume_bytes)),
                        "type": "application/pdf",
                    }
                ]

            if candidate.feishu_record_id:
                await self.bitable.update(candidate.feishu_record_id, fields)
            else:
                record_id = await self.bitable.create(fields)
                candidate.feishu_record_id = record_id

            candidate.feishu_synced_at = date.today()
            candidate.feishu_sync_status = "synced"
            candidate.feishu_sync_error = None
            await self.repo.update(candidate)
        except Exception as exc:
            logger.exception("Failed to sync candidate record to Feishu during retry")
            sync_error_parts.append(f"Bitable write failed: {exc}")
            candidate.feishu_sync_status = "failed"
            candidate.feishu_sync_error = "; ".join(sync_error_parts) if sync_error_parts else str(exc)
            await self.repo.update(candidate)
            raise RuntimeError(candidate.feishu_sync_error) from exc

        return candidate

    async def delete_candidate(self, candidate_id: UUID) -> None:
        candidate = await self.get_candidate(candidate_id)
        await self.repo.soft_delete(candidate)

        if candidate.feishu_record_id:
            try:
                await self.bitable.delete(candidate.feishu_record_id)
            except Exception:
                logger.exception("Failed to delete candidate from Feishu %s", candidate_id)

    async def sync_from_feishu(self) -> dict:
        """Pull all candidate records from Feishu Bitable and upsert into local PG."""
        raw_records = await self.bitable.fetch_all(page_size=500)
        stats = {"created": 0, "updated": 0, "failed": 0, "total": len(raw_records)}

        for rec in raw_records:
            try:
                data = rec.to_dict()
                data["feishu_synced_at"] = date.today()
                rid = data.get("feishu_record_id")
                if not rid:
                    stats["failed"] += 1
                    continue

                await self.repo.upsert_by_feishu_record_id(data)
                existing = await self.repo.get_by_feishu_record_id(rid)
                if existing and existing.created_at and (
                    datetime.utcnow() - existing.created_at.replace(tzinfo=None)
                ).total_seconds() < 60:
                    stats["created"] += 1
                else:
                    stats["updated"] += 1

                if existing and rec.resume_attachments:
                    import os
                    has_local = (
                        existing.resume_storage_path
                        and os.path.exists(existing.resume_storage_path)
                    )
                    if not has_local:
                        await self._download_resume(existing, rec.resume_attachments[0])
            except Exception:
                logger.exception("Failed to sync candidate record %s", rec.record_id)
                stats["failed"] += 1

        return stats

    async def _download_resume(self, candidate: Candidate, attachment: dict) -> None:
        import os
        file_token = attachment.get("file_token")
        if not file_token:
            logger.warning("No file_token in attachment for candidate %s", candidate.id)
            return

        try:
            tmp_download_url = await self.bitable.get_resume_download_url(file_token)

            import httpx
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(tmp_download_url)
                response.raise_for_status()

            upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads", "resumes")
            upload_dir = os.path.abspath(upload_dir)
            os.makedirs(upload_dir, exist_ok=True)

            original_name = attachment.get("name", "")
            ext = os.path.splitext(original_name)[1] if original_name else ".pdf"
            if not ext:
                ext = ".pdf"
            file_path = os.path.join(upload_dir, f"{candidate.id}{ext}")
            with open(file_path, "wb") as f:
                f.write(response.content)

            candidate.resume_storage_path = file_path
            await self.repo.update(candidate)
            logger.info("Downloaded resume for candidate %s to %s", candidate.id, file_path)
        except Exception:
            logger.exception("Failed to download resume for candidate %s", candidate.id)

    async def get_sync_status(self) -> SyncStatusResponse:
        local_total = await self.repo.count_total()
        synced_count = await self.repo.count_synced()
        failed_count = await self.repo.count_failed_sync()
        pending_count = await self.repo.count_pending_sync()
        unsynced_count = local_total - synced_count
        feishu_total = synced_count

        return SyncStatusResponse(
            local_total=local_total,
            feishu_total=feishu_total,
            synced_count=synced_count,
            unsynced_count=unsynced_count,
            conflict_count=0,
            pending_count=pending_count,
            failed_count=failed_count,
            last_sync_at=None,
        )
