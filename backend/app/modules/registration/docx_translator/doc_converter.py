"""DOCX 翻译 —— .doc/.wps → .docx 转换。

移植自 docx-translator/scripts/doc_converter.py，仅保留 LibreOffice 转换：
原 PDF/OCR 分支依赖硬编码的第三方 OCR 地址与 token，平台内不允许，已移除。
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

CONVERT_SUFFIXES = (".doc", ".wps")


class ConversionUnavailableError(RuntimeError):
    """服务器缺少 LibreOffice，消息可直接回显给用户。"""


class ConversionFailedError(RuntimeError):
    """调用 soffice 失败。"""


class DocConverter:
    """使用 soffice 命令行把 .doc/.wps 转成 .docx。"""

    def __init__(self) -> None:
        self._soffice_path = self._find_soffice()

    @staticmethod
    def _find_soffice() -> str:
        candidates = ["soffice", "/usr/bin/soffice", "/usr/lib/libreoffice/program/soffice"]
        for cmd in candidates:
            try:
                result = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=5)
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                continue
            if result.returncode == 0:
                return cmd
        return ""

    def is_available(self) -> bool:
        return bool(self._soffice_path)

    def convert(self, doc_path: str, work_dir: str | None = None) -> str:
        """转成 .docx 并返回路径；临时目录由调用方负责清理（work_dir 为空时自建）。"""
        src = Path(doc_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"文件不存在: {src.name}")
        if not self.is_available():
            raise ConversionUnavailableError("服务器未安装 LibreOffice，暂不支持 .doc 文件，请另存为 .docx 后重新上传")

        out_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="docx_translator_"))
        out_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                self._soffice_path,
                "--headless",
                "--convert-to",
                "docx",
                "--outdir",
                str(out_dir),
                str(src),
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            logger.error(
                "soffice convert failed: exit=%s stderr=%s",
                result.returncode,
                result.stderr.strip()[:300],
                extra={"biz_module": "registration"},
            )
            raise ConversionFailedError("文档格式转换失败，请确认文件未损坏后重试")

        converted = out_dir / f"{src.stem}.docx"
        if not converted.exists():
            found = sorted(out_dir.glob("*.docx"))
            if not found:
                raise ConversionFailedError("文档格式转换失败：未生成 .docx 文件")
            converted = found[0]

        final_path = out_dir / "converted.docx"
        if converted.resolve() != final_path.resolve():
            shutil.move(str(converted), str(final_path))
        return str(final_path)

    def cleanup(self, temp_path: str) -> None:
        """删除转换产生的临时目录（幂等）。"""
        if not temp_path:
            return
        shutil.rmtree(Path(temp_path).parent, ignore_errors=True)


__all__ = ["CONVERT_SUFFIXES", "ConversionFailedError", "ConversionUnavailableError", "DocConverter"]
