"""DOCX 翻译 —— 翻译引擎。

移植自 docx-translator/scripts/translator.py，改动点：
- LLM 调用统一走平台 `app.core.llm.llm_client`（异步），不再持有 API key / base_url；
- 去掉 openai SDK、tqdm、线程池与 print，改为 logging + asyncio 串行批次；
- 保留批次切分、[ID:xxx] 协议解析、术语注入、单位/空格后处理、失败批次重试。
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from collections.abc import Callable

from app.core.llm import llm_client
from app.core.llm.exceptions import LLMError

from .config import UNIT_REVERSE_MAP as CN_TO_EN_UNIT
from .config import TranslateConfig
from .engine_models import TextUnit, TranslationBatch, TranslationResult
from .glossary import Glossary

logger = logging.getLogger(__name__)

_ID_LINE = re.compile(r"^\s*[-*]*\s*\[ID:\s*([a-zA-Z0-9_]+)\]\s+(.*)$")
_ID_PREFIX = re.compile(r"^\s*[-*]*\s*\[ID:\s*\w+\]")


class TranslationEngineError(Exception):
    """整批翻译失败（重试用尽）。"""


class Translator:
    """批量翻译引擎：一个实例对应一个文件的翻译过程。"""

    _max_batch_retries = 3
    _request_retries = 3
    _batch_delay = (0.5, 2.0)
    _retry_delay = (2.0, 5.0)

    def __init__(self, config: TranslateConfig, glossary: Glossary | None = None) -> None:
        self.config = config
        self.glossary = glossary or Glossary()

    # ── 提示词 ────────────────────────────────────────────────

    def _build_system_prompt(self, batch_terms: dict[str, str] | None = None) -> str:
        """构建系统提示词；batch_terms 为本批次命中的术语 {源词: 目标词}。"""
        tgt_lang = "中文" if self.config.target_lang == "zh" else "英文"
        prompt = f"""你是一名专业的制药领域翻译专家，精通原料药GMP、药品注册申报资料（CTD/DMF）、中国药典、ICH指南、USP/EP、FDA、EMA及质量控制领域的规范用语。请将以下文本翻译成{tgt_lang}。

翻译要求：
1. 保持原文的段落结构，每段以 [ID:xxx] 开头
2. 返回结果中每段也必须以对应的 [ID:xxx] 开头，随后紧跟一个空格，然后是译文
3. 如果某段只有数字、符号或空白，保持原样
4. 表格内的文本要准确翻译，保持专业术语一致性
5. 不要添加额外解释、不要添加总结，只返回翻译后的文本
6. 确保每个 [ID:xxx] 都有对应的译文行，不要遗漏
7. 【强制全译】无论源文本包含何种语言（英文、西班牙语、葡萄牙语、法文、德文、日文等），除术语表规定的保留外，一律翻译为{tgt_lang}。公司名称、地址、人名、机构名称等专有名词也必须翻译（音译或意译），绝对不允许保留任何非{tgt_lang}原文。
8. 【术语强制】术语表中的英文翻译不得替换为同义词或近义表达，也不得将缩写展开为全称。全称可以压缩为缩写。大小写由语法和上下文决定。
9. 【缩写优先】术语表提供的缩写形式（如 PQS、WFI、HVAC、LDPE、QA、QC 等），优先使用缩写而非全称拼写。
10. 【GMP文体规范】翻译目标为英文时，必须符合ICH英文文字格式规范：行为优先于主语（如"经QA放行后方可发运"→"Release shall be granted by QA before shipment"），大量使用被动语态和短主句（如shall be transported、must be verified），使用granted/released/verified/confirmed等正式批准/验证动词，主谓倒装或省略主语，每句简洁不堆砌从句。
11. 【格式强制】严禁使用 markdown 格式（如列表符号 - 或 *）。严禁将 [ID:xxx] 和译文分成两行，必须在一行内完成。
12. 【单位绝对保护】纯计量单位缩写（如 kg, g, mg, μg, L, mL, μL, mm, cm, m, km, nm, μm, °C, °F, %, ppm, ppb, h, hr, min, s, sec, Pa, kPa, MPa, bar, mbar 等）必须原样保留，不得翻译、改写、重复或添加任何额外字符。单位与数字之间的空格必须严格遵循原文格式。
13. 【空格保护】译文必须保留原文中的空格、制表符和换行格式，不得压缩多个连续空格为单个空格。
14. 【空格规范】英文单词之间的空格必须为单个半角空格（U+0020），严禁在英文字母之间插入额外空格。中文汉字之间不需要空格。
"""
        if batch_terms:
            prompt += "\n【术语对照表】以下术语不可替换为同义词，缩写优先使用：\n"
            for src, tgt in sorted(batch_terms.items()):
                prompt += f"  {src} → {tgt}\n"
        return prompt

    def _build_user_prompt(self, batch: TranslationBatch) -> str:
        combined = batch.prepare_combined_text()
        return f"请翻译以下文本：\n\n{combined}\n\n请确保每段都以 [ID:xxx] 开头返回译文："

    def _extract_batch_terms(self, batch: TranslationBatch) -> dict[str, str]:
        """取出本批次实际命中的术语，避免把整表塞进 prompt。"""
        if not self.glossary.is_loaded():
            return {}

        def _match(term: str, text: str) -> bool:
            if all(ord(c) < 128 for c in term):
                pattern = r"(?<![a-zA-Z])" + re.escape(term) + r"(?![a-zA-Z])"
                if re.search(pattern, text, re.IGNORECASE):
                    return True
                if len(term) >= 5:
                    for suffix in ("ed", "ing", "s", "es"):
                        variant = term + suffix
                        variant_pattern = r"(?<![a-zA-Z])" + re.escape(variant) + r"(?![a-zA-Z])"
                        if re.search(variant_pattern, text, re.IGNORECASE):
                            return True
                return False
            return term in text

        all_terms = self.glossary.get_terms()
        hit: dict[str, str] = {}
        for unit in batch.units:
            for src, tgt in all_terms.items():
                if src in hit or tgt in hit:
                    continue
                matched_src = _match(src, unit.text)
                matched_tgt = _match(tgt, unit.text)
                if not (matched_src or matched_tgt):
                    continue
                if self.config.source_lang == "en" and self.config.target_lang == "zh":
                    key = tgt if matched_tgt else src
                    val = src if matched_tgt else tgt
                    hit[key] = val
                else:
                    hit[src] = tgt
        return hit

    # ── LLM 调用 ──────────────────────────────────────────────

    async def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """调用平台 LLM 客户端；空响应/异常按指数退避重试。"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        last_error: Exception | None = None
        for attempt in range(self._request_retries):
            try:
                content = await llm_client.chat(
                    messages=messages,
                    response_format=None,
                    temperature=self.config.temperature,
                    max_tokens=16384,
                )
                if not content or not content.strip():
                    raise LLMError("LLM 返回空内容")
                return content
            except Exception as e:  # noqa: BLE001 - 需覆盖 SDK/HTTP/业务异常并统一重试
                last_error = e
                logger.warning(
                    "docx translation LLM call failed (%d/%d): %s",
                    attempt + 1,
                    self._request_retries,
                    type(e).__name__,
                    extra={"biz_module": "registration"},
                )
                if attempt < self._request_retries - 1:
                    delay = 2**attempt + random.uniform(0, 1)
                    await asyncio.sleep(delay)

        raise TranslationEngineError(f"LLM 调用失败（已重试 {self._request_retries} 次）: {last_error}") from last_error

    # ── 解析与后处理 ──────────────────────────────────────────

    def _parse_response(self, response_text: str, batch: TranslationBatch) -> dict[str, str]:
        """解析 [ID:xxx] 译文映射，容忍 markdown 列表符与续行。"""
        results: dict[str, str] = {}
        last_unit_id: str | None = None
        for raw_line in response_text.split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            match = _ID_LINE.match(line)
            if match:
                unit_id = match.group(1)
                results[unit_id] = match.group(2).strip()
                last_unit_id = unit_id
            elif last_unit_id is not None and not _ID_PREFIX.match(line):
                results[last_unit_id] = results[last_unit_id] + "\n" + raw_line.rstrip()

        non_empty_ids = {u.id for u in batch.units if not u.is_empty}
        missing = non_empty_ids - set(results.keys())
        if missing:
            logger.warning(
                "docx translation batch %d missing %d/%d translations",
                batch.batch_id,
                len(missing),
                len(non_empty_ids),
                extra={"biz_module": "registration"},
            )
        return results

    def _post_process_translation(self, original: str, translated: str) -> str:
        """修复单位重复、英文字母间多余空格，并强制套用术语表。"""
        if not translated:
            return translated

        for cn_name, unit_abbr in CN_TO_EN_UNIT.items():
            pattern = re.escape(cn_name) + r"\s*\(?" + re.escape(unit_abbr) + r"\)?\s*" + re.escape(unit_abbr)
            translated = re.sub(pattern, unit_abbr, translated, flags=re.IGNORECASE)

        def _fix_letter_spacing(m: re.Match[str]) -> str:
            letters = m.group(0).split()
            if len(letters) >= 3 and all(len(ch) == 1 for ch in letters):
                return "".join(letters)
            return m.group(0)

        translated = re.sub(r"(?:\b[a-zA-Z]\b\s+){3,}", _fix_letter_spacing, translated)

        if self.glossary.is_loaded() and self.config.source_lang == "en" and self.config.target_lang == "zh":
            en_to_zh: dict[str, str] = {}
            for zh_src, en_tgt in self.glossary.get_terms().items():
                en_to_zh.setdefault(en_tgt.lower(), zh_src)

            for en_term, zh_correct in en_to_zh.items():
                if not re.search(r"(?<![a-zA-Z])" + re.escape(en_term) + r"(?![a-zA-Z])", original, re.IGNORECASE):
                    continue
                for other_en, other_zh in en_to_zh.items():
                    if other_zh == zh_correct or other_zh not in translated:
                        continue
                    if not re.search(r"(?<![a-zA-Z])" + re.escape(other_en) + r"(?![a-zA-Z])", original, re.IGNORECASE):
                        translated = translated.replace(other_zh, zh_correct)

        return translated

    # ── 翻译 ──────────────────────────────────────────────────

    async def translate_batch(self, batch: TranslationBatch) -> list[TranslationResult]:
        batch_terms = self._extract_batch_terms(batch)
        system_prompt = self._build_system_prompt(batch_terms=batch_terms or None)
        user_prompt = self._build_user_prompt(batch)
        response_text = await self._call_api(system_prompt, user_prompt)
        parsed = self._parse_response(response_text, batch)

        results: list[TranslationResult] = []
        for unit in batch.units:
            if unit.is_empty:
                results.append(
                    TranslationResult(unit_id=unit.id, original_text=unit.text, translated_text="", success=True)
                )
                continue
            translated = parsed.get(unit.id, "")
            if translated:
                translated = self._post_process_translation(unit.text, translated)
            if not translated:
                results.append(
                    TranslationResult(
                        unit_id=unit.id,
                        original_text=unit.text,
                        translated_text="",
                        success=False,
                        error_message="LLM 返回中未找到对应译文",
                    )
                )
            else:
                results.append(
                    TranslationResult(
                        unit_id=unit.id,
                        original_text=unit.text,
                        translated_text=translated,
                        success=True,
                    )
                )
        return results

    async def translate_all(
        self,
        units: list[TextUnit],
        on_batch_done: Callable[[int, int], None] | None = None,
    ) -> list[TranslationResult]:
        """串行翻译全部单元；失败批次在多轮重试后仍失败则标记该批段落失败。"""
        batches = self._split_into_batches(units)
        logger.info(
            "docx translation start: %d units / %d batches",
            len(units),
            len(batches),
            extra={"biz_module": "registration"},
        )

        all_results: list[TranslationResult] = []
        failed: list[tuple[TranslationBatch, str]] = []

        for index, batch in enumerate(batches, start=1):
            try:
                all_results.extend(await self.translate_batch(batch))
            except Exception as e:  # noqa: BLE001 - 批次失败不中断整体，记录后重试
                logger.warning(
                    "docx translation batch %d failed: %s",
                    batch.batch_id,
                    type(e).__name__,
                    extra={"biz_module": "registration", "batch_id": batch.batch_id},
                )
                failed.append((batch, str(e)))
            if on_batch_done is not None:
                on_batch_done(index, len(batches))
            if index < len(batches):
                await asyncio.sleep(random.uniform(*self._batch_delay))

        if failed:
            results_map = {r.unit_id: r for r in all_results}
            current_failed = failed
            round_no = 0
            while current_failed and round_no < self._max_batch_retries:
                round_no += 1
                next_failed: list[tuple[TranslationBatch, str]] = []
                for batch, _err in current_failed:
                    await asyncio.sleep(random.uniform(*self._retry_delay))
                    try:
                        for r in await self.translate_batch(batch):
                            results_map[r.unit_id] = r
                    except Exception as e2:  # noqa: BLE001 - 重试失败继续记录
                        next_failed.append((batch, str(e2)))
                current_failed = next_failed

            for batch, error in current_failed:
                for unit in batch.units:
                    results_map[unit.id] = TranslationResult(
                        unit_id=unit.id,
                        original_text=unit.text,
                        translated_text="",
                        success=False,
                        error_message=f"批次 {batch.batch_id} 最终失败: {error}",
                    )
            all_results = list(results_map.values())

        return all_results

    def _split_into_batches(self, units: list[TextUnit]) -> list[TranslationBatch]:
        """按「每批段落数 + 估算 token 上限」切分批次。"""

        def estimate_tokens(text: str) -> int:
            cn_count = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
            other_count = len(text) - cn_count
            return int(cn_count + other_count * 0.75)

        batches: list[TranslationBatch] = []
        current: list[TextUnit] = []
        current_tokens = 0
        batch_id = 0

        for unit in units:
            unit_tokens = estimate_tokens(unit.text) + 20
            if (
                len(current) >= self.config.batch_size
                or current_tokens + unit_tokens > self.config.max_tokens_per_batch
            ):
                if current:
                    batch_id += 1
                    batches.append(TranslationBatch(batch_id=batch_id, units=current))
                current = [unit]
                current_tokens = unit_tokens
            else:
                current.append(unit)
                current_tokens += unit_tokens

        if current:
            batch_id += 1
            batches.append(TranslationBatch(batch_id=batch_id, units=current))
        return batches


def build_translator(config: TranslateConfig, glossary: Glossary | None = None) -> Translator:
    return Translator(config=config, glossary=glossary)


__all__ = ["TranslationEngineError", "Translator", "build_translator"]
