FROM python:3.12-slim-bookworm

WORKDIR /app

# Remove all existing Debian sources and use Chinese mirror
RUN rm -f /etc/apt/sources.list /etc/apt/sources.list.d/* && \
    echo "deb https://mirrors.ustc.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.ustc.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.ustc.edu.cn/debian-security/ bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# Install system dependencies required for OpenCV and PaddleOCR
RUN apt-get update && apt-get install -y \
    curl \
    fontconfig \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    poppler-utils \
    libreoffice \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    fonts-liberation \
    fonts-crosextra-carlito \
    fonts-crosextra-caladea \
    && rm -rf /var/lib/apt/lists/*

# 字体必须与 Dockerfile.worker 保持一致：上传后的页图由 backend 进程生成
# （core.jobs），渲染在 worker 里做，两边字体不同会导致「预览和成片画面不一样」；
# 没有 CJK 字体时中文页图会整屏方块。
# fonts-liberation / carlito / caladea 负责**拉丁**字体的度量兼容（Arial / Times New
# Roman / Calibri / Cambria）。缺它们时这些族名落到更宽的 DejaVu，文本框提前折行：
# 实测 53 页项目中标题 "…Company Organization Chart" 折成两行压住下方方框。

# Install uv package manager (use Alibaba PyPI mirror for speed)
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ uv==0.12.2

ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV UV_EXTRA_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV UV_PYTHON=/usr/local/bin/python3

# Copy and install Python dependencies
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# Playwright Chromium 浏览器（regulatory_tracker 每日同步需要）
# --with-deps 安装运行 Chromium 所需的系统库（libatk、libnss3 等）
RUN .venv/bin/playwright install --with-deps chromium

# Copy application code
COPY . .

# 字体别名：把「微软雅黑 / 宋体 / 思源黑体」等 PPT 常用字体映射到 Noto CJK。
# 不映射时 fontconfig 会把它们判给无中文字形的 DejaVu，再逐字形回退到 Noto，
# 中西文度量不一致 → 页图文字重叠、表格跑位（归因见 docs/ppt-video-font-attribution.md）。
# 与 Dockerfile.worker 用同一份配置，改配置时同步递增 render.RENDERER_KEY 的 FONT_PROFILE。
COPY assets/fontconfig/69-ppt-font-alias.conf /etc/fonts/conf.d/69-ppt-font-alias.conf
RUN fc-cache -f && \
    for name in "微软雅黑" "Microsoft YaHei" "宋体" "SimSun" "思源黑体 CN"; do \
        hit="$(fc-match -f '%{family}' "$name")"; \
        case "$hit" in \
            *Noto*) ;; \
            *) echo "字体别名未生效：$name -> $hit"; exit 1 ;; \
        esac; \
    done && \
    for pair in "Arial=Liberation Sans" "Times New Roman=Liberation Serif" "Calibri=Carlito"; do \
        src="${pair%%=*}"; want="${pair#*=}"; \
        hit="$(fc-match -f '%{family}' "$src")"; \
        [ "$hit" = "$want" ] || { echo "拉丁字体度量兼容未生效：$src -> $hit（期望 $want）"; exit 1; }; \
    done

EXPOSE 8000


# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/live || exit 1

CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
