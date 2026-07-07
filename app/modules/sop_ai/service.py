"""SOP AI 模块业务逻辑层

包含校验服务、AI 辅助校验功能。
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sop_ai.algorithm import DuplicateChecker
from app.modules.sop_ai.models import (
    SopAiCheckMain,
    SopAiCheckProblem,
    CheckStatus,
    CheckType,
    ProblemType,
    RiskLevel,
    HandleStatus,
)
from app.modules.sop_ai.repository import (
    SopAiConfigRepository,
    SopAiCheckMainRepository,
    SopAiCheckProblemRepository,
)

logger = logging.getLogger(__name__)


# AI 提示词模板
SYSTEM_PROMPT_CONFLICT = """你是一位专业的 GMP 药品质量合规专家。请分析以下文件内容，检测是否存在参数冲突或不一致的问题。

需要检测的常见问题：
1. 工艺参数前后不一致（如温度、时间、压力等）
2. 检测方法与标准不一致
3. 物料规格与配方不一致
4. 关键参数缺失或错误

请以 JSON 格式返回结果：
{
    "conflicts": [
        {
            "location": "位置描述",
            "description": "问题描述",
            "risk_level": "high/medium/low",
            "suggestion": "整改建议"
        }
    ]
}"""

SYSTEM_PROMPT_COMPLIANCE = """你是一位专业的 GMP 药品质量合规专家。请根据《中国药典》和《药品生产质量管理规范》检测以下文件内容是否符合法规要求。

需要检测的要点：
1. 文件格式和编号是否符合要求
2. 内容是否完整（包含必要的章节）
3. 关键术语使用是否规范
4. 记录要求是否符合规范

请以 JSON 格式返回结果：
{
    "issues": [
        {
            "location": "位置描述",
            "description": "问题描述",
            "risk_level": "high/medium/low",
            "suggestion": "整改建议"
        }
    ]
}"""


class SopAiCheckService:
    """SOP AI 校验服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.config_repo = SopAiConfigRepository(session)
        self.main_repo = SopAiCheckMainRepository(session)
        self.problem_repo = SopAiCheckProblemRepository(session)

    async def _init_default_config(self):
        """初始化默认配置"""
        default_configs = {
            "simhash_threshold": "3",
            "chunk_size": "500",
            "overlap_size": "80",
            "ai_enabled": "true",
            "conflict_check_enabled": "true",
            "compliance_check_enabled": "true",
        }

        for key, value in default_configs.items():
            await self.config_repo.upsert(key, value, f"系统初始化: {key}")

    async def _get_config(self, key: str, default: str = "") -> str:
        """获取配置"""
        config = await self.config_repo.get_by_key(key)
        return config.config_value if config else default

    async def single_check(
        self,
        file_path: str,
        file_name: str,
        check_type: str = "single",
        operator: Optional[str] = None,
    ) -> dict:
        """单文件预审

        Args:
            file_path: 文件路径
            file_name: 文件名
            check_type: 校验类型
            operator: 操作人

        Returns:
            校验结果
        """
        # 创建校验记录
        file_type = self._get_file_type(file_name)
        main_record = await self.main_repo.create(
            file_name=file_name,
            file_type=file_type,
            check_type=check_type,
            operator=operator,
        )

        # 解析文件
        from app.modules.sop_ai.algorithm import FileParser

        parser = FileParser()
        try:
            text = parser.parse(file_path)
        except Exception as e:
            logger.error(f"文件解析失败: {file_path}, error: {e}")
            await self.main_repo.update_status(
                main_record.id,
                CheckStatus.FAILED,
                f"文件解析失败: {str(e)}",
            )
            return {
                "task_id": main_record.id,
                "status": "failed",
                "message": f"文件解析失败: {str(e)}",
            }

        # 更新状态为运行中
        await self.main_repo.update_status(
            main_record.id,
            CheckStatus.RUNNING,
            "正在校验...",
        )

        # 执行校验
        problems = await self._check_content(
            main_record.id,
            text,
            operator,
        )

        # 更新结果
        risk_counts = {
            "high": sum(1 for p in problems if p.get("risk_level") == "high"),
            "medium": sum(1 for p in problems if p.get("risk_level") == "medium"),
            "low": sum(1 for p in problems if p.get("risk_level") == "low"),
        }

        result_summary = f"发现问题 {len(problems)} 个（高: {risk_counts['high']}, 中: {risk_counts['medium']}, 低: {risk_counts['low']}）"

        await self.main_repo.update_result(
            main_record.id,
            result_summary,
            total_problems=len(problems),
            risk_high=risk_counts["high"],
            risk_medium=risk_counts["medium"],
            risk_low=risk_counts["low"],
        )

        # 更新状态为完成
        await self.main_repo.update_status(
            main_record.id,
            CheckStatus.COMPLETED,
            result_summary,
        )

        return {
            "task_id": main_record.id,
            "status": "completed",
            "result": {
                "total_problems": len(problems),
                "risk_high": risk_counts["high"],
                "risk_medium": risk_counts["medium"],
                "risk_low": risk_counts["low"],
                "problems": problems,
            },
        }

    async def batch_check(
        self,
        file_paths: list[str],
        check_type: str = "batch",
        operator: Optional[str] = None,
    ) -> dict:
        """批量巡检

        Args:
            file_paths: 文件路径列表
            check_type: 校验类型
            operator: 操作人

        Returns:
            校验结果
        """
        from app.modules.sop_ai.algorithm import FileParser

        parser = FileParser()
        all_problems = []
        file_results = []

        for file_path in file_paths:
            file_name = file_path.split("/")[-1].split("\\")[-1]

            # 创建校验记录
            file_type = self._get_file_type(file_name)
            main_record = await self.main_repo.create(
                file_name=file_name,
                file_type=file_type,
                check_type=check_type,
                operator=operator,
            )

            # 解析文件
            try:
                text = parser.parse(file_path)
            except Exception as e:
                logger.error(f"文件解析失败: {file_path}, error: {e}")
                await self.main_repo.update_status(
                    main_record.id,
                    CheckStatus.FAILED,
                    f"文件解析失败: {str(e)}",
                )
                file_results.append({
                    "file_path": file_path,
                    "status": "failed",
                    "message": str(e),
                })
                continue

            # 执行校验
            problems = await self._check_content(
                main_record.id,
                text,
                operator,
            )

            # 更新结果
            risk_counts = {
                "high": sum(1 for p in problems if p.get("risk_level") == "high"),
                "medium": sum(1 for p in problems if p.get("risk_level") == "medium"),
                "low": sum(1 for p in problems if p.get("risk_level") == "low"),
            }

            result_summary = f"发现问题 {len(problems)} 个"

            await self.main_repo.update_result(
                main_record.id,
                result_summary,
                total_problems=len(problems),
                risk_high=risk_counts["high"],
                risk_medium=risk_counts["medium"],
                risk_low=risk_counts["low"],
            )

            await self.main_repo.update_status(
                main_record.id,
                CheckStatus.COMPLETED,
                result_summary,
            )

            file_results.append({
                "file_path": file_path,
                "status": "completed",
                "task_id": main_record.id,
                "total_problems": len(problems),
                "risk_high": risk_counts["high"],
                "risk_medium": risk_counts["medium"],
                "risk_low": risk_counts["low"],
            })

            all_problems.extend(problems)

        return {
            "task_id": f"batch_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "status": "completed",
            "result": {
                "total_files": len(file_paths),
                "total_problems": len(all_problems),
                "file_results": file_results,
            },
        }

    async def _check_content(
        self,
        main_id: str,
        text: str,
        operator: Optional[str] = None,
    ) -> list[dict]:
        """检查文件内容

        Args:
            main_id: 校验主记录ID
            text: 文件文本
            operator: 操作人

        Returns:
            问题列表
        """
        problems = []

        # 获取配置
        threshold = int(await self._get_config("simhash_threshold", "3"))
        ai_enabled = await self._get_config("ai_enabled", "true") == "true"
        conflict_enabled = await self._get_config("conflict_check_enabled", "true") == "true"
        compliance_enabled = await self._get_config("compliance_check_enabled", "true") == "true"

        # 1. SimHash 查重（与数据库已有记录比对）
        from app.modules.sop_ai.algorithm import DuplicateChecker

        checker = DuplicateChecker(threshold)
        existing_records = await self._get_existing_fingerprints()

        if existing_records:
            duplicates = checker.find_duplicates(text, existing_records)
            for dup in duplicates:
                problem = {
                    "main_id": main_id,
                    "problem_type": ProblemType.DUPLICATE,
                    "risk_level": RiskLevel.HIGH,
                    "location": "全文",
                    "description": f"与已有文件重复度高: {dup.get('similarity', 0)*100:.1f}%",
                    "source_file": dup.get("identifier"),
                    "suggestion": "请确认是否为同一文件的更新版本",
                    "operator": operator,
                }
                problems.append(problem)

        # 2. AI 冲突检测
        if ai_enabled and conflict_enabled:
            conflicts = await self._ai_conflict_check(text)
            problems.extend(conflicts)

        # 3. AI 合规检测
        if ai_enabled and compliance_enabled:
            compliance_issues = await self._ai_compliance_check(text)
            problems.extend(compliance_issues)

        # 保存问题到数据库
        if problems:
            await self.problem_repo.create_batch(problems)

        return problems

    async def _get_existing_fingerprints(self) -> list[tuple[str, str]]:
        """获取已有文件的指纹列表

        Returns:
            [(文本, 标识), ...]
        """
        # 获取已完成校验的记录
        records, _ = await self.main_repo.list(
            status=CheckStatus.COMPLETED,
            page=1,
            page_size=100,
        )

        # 实际应该存储指纹，这里简化为返回空列表
        # 生产环境需要存储 SimHash 指纹到数据库
        return []

    async def _ai_conflict_check(self, text: str) -> list[dict]:
        """AI 冲突检测

        Args:
            text: 文件文本

        Returns:
            冲突问题列表
        """
        try:
            from app.platform.ai.minimax_util import get_ai_util

            ai_util = get_ai_util()

            # 提取关键参数
            params = self._extract_params(text)

            if not params:
                return []

            # 调用 AI 检测
            user_message = f"请分析以下参数是否存在冲突：\n{json.dumps(params, ensure_ascii=False, indent=2)}"

            result = ai_util.chat(
                system_prompt=SYSTEM_PROMPT_CONFLICT,
                user_message=user_message,
            )

            # 解析结果
            return self._parse_ai_result(result, ProblemType.CONFLICT)

        except Exception as e:
            logger.error(f"AI 冲突检测失败: {e}")
            return []

    async def _ai_compliance_check(self, text: str) -> list[dict]:
        """AI 合规检测

        Args:
            text: 文件文本

        Returns:
            合规问题列表
        """
        try:
            from app.platform.ai.minimax_util import get_ai_util

            ai_util = get_ai_util()

            # 截取前 2000 字符（AI 输入限制）
            truncated_text = text[:2000]

            user_message = f"请检测以下文件内容是否符合 GMP 要求：\n{truncated_text}"

            result = ai_util.chat(
                system_prompt=SYSTEM_PROMPT_COMPLIANCE,
                user_message=user_message,
            )

            # 解析结果
            return self._parse_ai_result(result, ProblemType.COMPLIANCE)

        except Exception as e:
            logger.error(f"AI 合规检测失败: {e}")
            return []

    def _extract_params(self, text: str) -> dict:
        """提取关键参数

        从文本中提取温度、时间、压力等关键参数。
        """
        params = {}

        # 提取温度
        temps = re.findall(r'(\d+(?:\.\d+)?)\s*[°℃C]', text)
        if temps:
            params["temperatures"] = temps[:10]

        # ��取��间
        times = re.findall(r'(\d+(?:\.\d+)?)\s*(?:分钟|小时|h|min)', text)
        if times:
            params["times"] = times[:10]

        # 提取压力
        pressures = re.findall(r'(\d+(?:\.\d+)?)\s*(?:MPa|帕|kPa)', text)
        if pressures:
            params["pressures"] = pressures[:10]

        return params

    def _parse_ai_result(self, result: str, problem_type: ProblemType) -> list[dict]:
        """解析 AI 返回结果

        Args:
            result: AI 返回的 JSON 字符串
            problem_type: 问题类型

        Returns:
            问题列表
        """
        problems = []

        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                data = json.loads(json_match.group())

                if problem_type == ProblemType.CONFLICT:
                    items = data.get("conflicts", [])
                else:
                    items = data.get("issues", [])

                for item in items:
                    risk = item.get("risk_level", "low")
                    problems.append({
                        "problem_type": problem_type,
                        "risk_level": (
                            RiskLevel.HIGH
                            if risk == "high"
                            else RiskLevel.MEDIUM
                            if risk == "medium"
                            else RiskLevel.LOW
                        ),
                        "location": item.get("location", ""),
                        "description": item.get("description", ""),
                        "suggestion": item.get("suggestion", ""),
                    })
        except Exception as e:
            logger.error(f"解析 AI 结果失败: {e}")

        return problems

    def _get_file_type(self, file_name: str) -> str:
        """获取文件类型"""
        ext = file_name.split(".")[-1].lower()
        if ext in {"doc", "docx"}:
            return "docx"
        elif ext == "pdf":
            return "pdf"
        return "txt"

    async def get_record(
        self,
        id: str,
    ) -> Optional[SopAiCheckMain]:
        """获取校验记录"""
        return await self.main_repo.get_by_id(id)

    async def get_record_detail(
        self,
        id: str,
    ) -> Optional[dict]:
        """获取校验记录详情"""
        main_record = await self.main_repo.get_by_id(id)
        if not main_record:
            return None

        problems = await self.problem_repo.get_by_main_id(id)

        return {
            "id": main_record.id,
            "file_code": main_record.file_code,
            "file_name": main_record.file_name,
            "file_type": main_record.file_type,
            "check_type": main_record.check_type,
            "status": main_record.status,
            "result_summary": main_record.result_summary,
            "total_problems": main_record.total_problems,
            "risk_high": main_record.risk_high,
            "risk_medium": main_record.risk_medium,
            "risk_low": main_record.risk_low,
            "operator": main_record.operator,
            "created_at": main_record.created_at,
            "updated_at": main_record.updated_at,
            "problems": [
                {
                    "id": p.id,
                    "problem_type": p.problem_type,
                    "risk_level": p.risk_level,
                    "location": p.location,
                    "description": p.description,
                    "source_file": p.source_file,
                    "suggestion": p.suggestion,
                    "handle_status": p.handle_status,
                    "ignore_reason": p.ignore_reason,
                    "operator": p.operator,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                }
                for p in problems
            ],
        }

    async def list_records(
        self,
        status: Optional[str] = None,
        file_code: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[SopAiCheckMain], int]:
        """查询校验记录列表"""
        return await self.main_repo.list(
            status=status,
            file_code=file_code,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )

    async def handle_problem(
        self,
        problem_id: str,
        handle_status: str,
        ignore_reason: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> Optional[SopAiCheckProblem]:
        """处理问题"""
        status = HandleStatus(handle_status)
        return await self.problem_repo.update_handle_status(
            problem_id,
            status,
            ignore_reason,
            operator,
        )

    async def get_config(self, config_key: str) -> str:
        """获取配置值"""
        config = await self.config_repo.get_by_key(config_key)
        return config.config_value if config else ""

    async def set_config(
        self,
        config_key: str,
        config_value: str,
        description: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> dict:
        """设置配置"""
        config = await self.config_repo.upsert(
            config_key,
            config_value,
            description,
            operator,
        )
        return {
            "id": config.id,
            "config_key": config.config_key,
            "config_value": config.config_value,
            "description": config.description,
        }

    async def list_config(self) -> list[dict]:
        """获取所有配置"""
        configs = await self.config_repo.get_all()
        return [
            {
                "id": c.id,
                "config_key": c.config_key,
                "config_value": c.config_value,
                "description": c.description,
                "operator": c.operator,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in configs
        ]