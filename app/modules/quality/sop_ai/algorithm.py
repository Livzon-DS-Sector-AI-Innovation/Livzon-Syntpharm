"""SOP AI 模块核心算法

包含 SimHash 查重算法和文件解析功能。
"""

import hashlib
import re
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SimHash:
    """SimHash 指纹计算

    使用 64 位指纹，通过汉明距离计算文本相似度。
    默认阈值：距离 <= 3 表示相似（相似度 > 95%）
    """

    # 分片参数
    CHUNK_SIZE = 500  # 每片字符数
    OVERLAP_SIZE = 80  # 重叠字符数

    # SimHash 参数
    FINGERPRINT_BITS = 64  # 指纹位数
    DEFAULT_THRESHOLD = 3  # 默认汉明距离阈值

    def __init__(self, threshold: int = DEFAULT_THRESHOLD):
        """初始化 SimHash

        Args:
            threshold: 汉明距离阈值，默认 3
        """
        self.threshold = threshold

    def _tokenize(self, text: str) -> list[str]:
        """分词

        将文本分成词语列表。
        """
        # 简单中文分词：按标点和空格分割
        tokens = re.split(r'[,，。.！!？?；;：:\s\n\r\t]+', text)
        # 过滤空字符串
        tokens = [t for t in tokens if t and len(t) > 1]
        return tokens

    def _hash_feature(self, feature: str) -> int:
        """计算特征的哈希值

        使用 MD5 生成 64 位整数。
        """
        md5_hash = hashlib.md5(feature.encode("utf-8")).hexdigest()
        return int(md5_hash, 16)

    def _compute_fingerprint(self, text: str) -> int:
        """计算 SimHash 指纹

        步骤：
        1. 分词
        2. 计算每个词的哈希
        3. 按位累加
        4. 转成 64 位
        """
        tokens = self._tokenize(text)
        if not tokens:
            return 0

        # 初始化 64 位向量
        v = [0] * self.FINGERPRINT_BITS

        # 对每个词计算哈希并累加
        for token in tokens:
            hash_val = self._hash_feature(token)
            for i in range(self.FINGERPRINT_BITS):
                # 检查第 i 位
                if hash_val & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1

        # 转成 64 位整数
        fingerprint = 0
        for i in range(self.FINGERPRINT_BITS):
            if v[i] > 0:
                fingerprint |= (1 << i)

        return fingerprint

    def compute(self, text: str) -> int:
        """计算文本的 SimHash 指纹

        Args:
            text: 输入文本

        Returns:
            64 位整数指纹
        """
        if not text or not text.strip():
            return 0
        return self._compute_fingerprint(text.strip())

    def _hamming_distance(self, hash1: int, hash2: int) -> int:
        """计算汉明距离

        Args:
            hash1: 指纹 1
            hash2: 指纹 2

        Returns:
            汉明距离
        """
        xor = hash1 ^ hash2
        distance = 0
        while xor:
            distance += 1
            xor &= xor - 1
        return distance

    def is_similar(self, hash1: int, hash2: int) -> bool:
        """判断两个指纹是否相似

        Args:
            hash1: 指纹 1
            hash2: 指纹 2

        Returns:
            是否相似
        """
        if hash1 == 0 or hash2 == 0:
            return False
        distance = self._hamming_distance(hash1, hash2)
        return distance <= self.threshold

    def compute_text_similarity(self, text1: str, text2: str) -> dict:
        """计算两个文本的相似度

        Args:
            text1: 文本 1
            text2: 文本 2

        Returns:
            包含指纹和相似度信息的字典
        """
        hash1 = self.compute(text1)
        hash2 = self.compute(text2)

        if hash1 == 0 or hash2 == 0:
            return {
                "hash1": hex(hash1),
                "hash2": hex(hash2),
                "hamming_distance": -1,
                "is_similar": False,
                "similarity": 0.0,
            }

        distance = self._hamming_distance(hash1, hash2)
        # 相似度 = 1 - (距离 / 64)
        similarity = max(0.0, 1.0 - distance / self.FINGERPRINT_BITS)

        return {
            "hash1": hex(hash1),
            "hash2": hex(hash2),
            "hamming_distance": distance,
            "is_similar": distance <= self.threshold,
            "similarity": similarity,
        }


class FileParser:
    """文件解析器

    支持 .doc/.docx/.pdf 文件的文本提取。
    """

    # 支持的文件类型
    SUPPORTED_EXTENSIONS = {".doc", ".docx", ".pdf", ".txt"}

    def __init__(self):
        self.supported_extensions = self.SUPPORTED_EXTENSIONS

    def is_supported(self, file_path: str) -> bool:
        """检查文件是否支持

        Args:
            file_path: 文件路径

        Returns:
            是否支持
        """
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions

    def parse(self, file_path: str) -> str:
        """解析文件

        Args:
            file_path: 文件路径

        Returns:
            提取的纯文本

        Raises:
            ValueError: 不支持的文件类型
            IOError: 文件读取失败
        """
        path = Path(file_path)

        if not path.exists():
            raise IOError(f"文件不存在: {file_path}")

        ext = path.suffix.lower()

        if ext not in self.supported_extensions:
            raise ValueError(f"不支持的文件类型: {ext}")

        # 根据扩展名选择解析方法
        if ext == ".txt":
            return self._parse_txt(file_path)
        elif ext in {".doc", ".docx"}:
            return self._parse_word(file_path)
        elif ext == ".pdf":
            return self._parse_pdf(file_path)

        return ""

    def _parse_txt(self, file_path: str) -> str:
        """解析纯文本文件"""
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return self._clean_text(text)

    def _parse_word(self, file_path: str) -> str:
        """解析 Word 文档

        使用 python-docx 和 pywin32（仅 Windows）解析 .doc/.docx 文件。
        实际生产环境需要安装相应库。
        """
        try:
            # 尝试使用 python-docx 解析 .docx
            if file_path.endswith(".docx"):
                return self._parse_docx(file_path)
            else:
                # .doc 文件需要 pywin32，这里简单返回
                logger.warning(f"暂不支持 .doc 格式，建议转换为 .docx: {file_path}")
                return ""
        except ImportError:
            logger.warning(f"缺少解析库，跳过文件: {file_path}")
            return ""
        except Exception as e:
            logger.error(f"解析 Word 文件失败: {file_path}, error: {e}")
            return ""

    def _parse_docx(self, file_path: str) -> str:
        """解析 .docx 文件"""
        try:
            from docx import Document

            doc = Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)
            return self._clean_text(text)
        except ImportError:
            logger.warning("python-docx 未安装")
            return ""
        except Exception as e:
            logger.error(f"解析 docx 失败: {e}")
            return ""

    def _parse_pdf(self, file_path: str) -> str:
        """解析 PDF 文件"""
        try:
            import PyPDF2

            text_parts = []
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text_parts.append(page.extract_text())
            text = "\n".join(text_parts)
            return self._clean_text(text)
        except ImportError:
            logger.warning("PyPDF2 未安装")
            return ""
        except Exception as e:
            logger.error(f"解析 PDF 失败: {e}")
            return ""

    def _clean_text(self, text: str) -> str:
        """清理文本

        去除页眉页脚、特殊字符等。
        """
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text)
        # 去除常见页眉页脚标记
        text = re.sub(r'第\s*\d+\s*页', '', text)
        text = re.sub(r'页眉|页脚', '', text, flags=re.IGNORECASE)
        # 去除特殊控制字符
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
        # 去除首尾空白
        text = text.strip()
        return text


class DuplicateChecker:
    """重复文件检查器

    使用 SimHash 进行文件查重。
    """

    def __init__(self, threshold: int = 3):
        self.simhash = SimHash(threshold)
        self.file_parser = FileParser()

    def compute_fingerprint(self, text: str) -> int:
        """计算文本指纹"""
        return self.simhash.compute(text)

    def check_duplicate(
        self,
        text1: str,
        text2: str,
    ) -> dict:
        """检查两个文本是否重复"""
        return self.simhash.compute_text_similarity(text1, text2)

    def check_file_duplicate(
        self,
        file_path1: str,
        file_path2: str,
    ) -> dict:
        """检查两个文件是否重复

        Args:
            file_path1: 文件 1 路径
            file_path2: 文件 2 路径

        Returns:
            相似度结果
        """
        # 解析文件
        text1 = self.file_parser.parse(file_path1)
        text2 = self.file_parser.parse(file_path2)

        if not text1 or not text2:
            return {
                "is_duplicate": False,
                "reason": "文件解析失败或内容为空",
            }

        return self.simhash.compute_text_similarity(text1, text2)

    def find_duplicates(
        self,
        target_text: str,
        reference_texts: list[tuple[str, str]],
    ) -> list[dict]:
        """在参考文本列表中查找重复

        Args:
            target_text: 目标文本
            reference_texts: 参考文本列表 [(文本, 标识), ...]

        Returns:
            重复的参考文本列表
        """
        target_hash = self.simhash.compute(target_text)
        duplicates = []

        for ref_text, identifier in reference_texts:
            ref_hash = self.simhash.compute(ref_text)
            if self.simhash.is_similar(target_hash, ref_hash):
                similarity = self.simhash.compute_text_similarity(target_text, ref_text)
                duplicates.append({
                    "identifier": identifier,
                    "hamming_distance": similarity["hamming_distance"],
                    "similarity": similarity["similarity"],
                })

        return duplicates


# 全局单例
_default_checker: Optional[DuplicateChecker] = None


def get_duplicate_checker(threshold: int = 3) -> DuplicateChecker:
    """获取重复检查器单例"""
    global _default_checker
    if _default_checker is None:
        _default_checker = DuplicateChecker(threshold)
    return _default_checker