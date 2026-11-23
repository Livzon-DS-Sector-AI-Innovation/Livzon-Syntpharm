"""DOCX 翻译 —— 引擎配置与常量。

单位白名单与中英单位映射是唯一数据源，translator 与 prompts 从这里导入。
平台部署配置（API key / base_url）不在此处理：翻译统一走 `app.core.llm` 的
全局 LLM 配置，模型与批次参数来自运行时配置（`core.module_settings`）。
"""

from dataclasses import dataclass

# 需原样保留的计量单位缩写集合
UNIT_WHITELIST: set[str] = {
    "kg",
    "g",
    "mg",
    "L",
    "mL",
    "μL",
    "mm",
    "cm",
    "m",
    "km",
    "nm",
    "μm",
    "°C",
    "°F",
    "%",
    "ppm",
    "ppb",
    "h",
    "hr",
    "min",
    "s",
    "sec",
    "Pa",
    "kPa",
    "MPa",
    "bar",
    "mbar",
}

# 中文单位名 → 英文缩写
UNIT_REVERSE_MAP: dict[str, str] = {
    "千克": "kg",
    "克": "g",
    "毫克": "mg",
    "升": "L",
    "毫升": "mL",
    "微升": "μL",
    "毫米": "mm",
    "厘米": "cm",
    "米": "m",
    "纳米": "nm",
    "微米": "μm",
    "摄氏度": "°C",
    "华氏度": "°F",
    "小时": "h",
    "分钟": "min",
    "秒": "s",
}

# 输出模式
MODE_BILINGUAL = "bilingual"
MODE_REPLACE = "replace"
MODE_BOTH = "both"
MODES: tuple[str, ...] = (MODE_BILINGUAL, MODE_REPLACE, MODE_BOTH)

# 翻译方向
SOURCE_LANGS: tuple[str, ...] = ("en", "zh")


@dataclass
class TranslateConfig:
    """一次翻译的运行参数（不含凭证）。"""

    source_lang: str = "en"
    target_lang: str = "zh"
    mode: str = MODE_BILINGUAL
    batch_size: int = 30
    max_tokens_per_batch: int = 12000
    temperature: float = 0.3

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.source_lang not in SOURCE_LANGS:
            errors.append(f"源语言不支持: {self.source_lang}")
        if self.target_lang not in SOURCE_LANGS:
            errors.append(f"目标语言不支持: {self.target_lang}")
        if self.source_lang == self.target_lang:
            errors.append("源语言与目标语言不能相同")
        if self.mode not in MODES:
            errors.append(f"输出模式不支持: {self.mode}")
        if not 5 <= self.batch_size <= 200:
            errors.append("每批段落数需在 5~200 之间")
        return errors

    def get_output_suffix(self) -> str:
        """输出文件名后缀：双语版 _bi / 译文版 _<target>。"""
        return "_bi" if self.mode == MODE_BILINGUAL else f"_{self.target_lang}"
