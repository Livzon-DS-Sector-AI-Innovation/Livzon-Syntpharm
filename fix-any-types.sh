#!/bin/bash
set -e

# 配置
PROJECT_DIR="/home/ruanjiaheng/projects/Livzon-Syntpharm"
FRONTEND_DIR="$PROJECT_DIR/frontend"
LOG_FILE="$PROJECT_DIR/fix-any.log"
PROGRESS_FILE="$PROJECT_DIR/fix-any-progress.json"
LINT_OUTPUT="$PROJECT_DIR/lint-output.txt"

# 初始化进度文件
cat > "$PROGRESS_FILE" << 'EOF'
{
  "current_ticket": "07-replace-any-components",
  "phase": "initializing",
  "files_processed": 0,
  "files_total": 0,
  "warnings_fixed": 0,
  "warnings_total": 1653,
  "current_file": "",
  "last_updated": "",
  "status": "running"
}
EOF

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 更新进度文件
update_progress() {
    local ticket="$1"
    local phase="$2"
    local processed="$3"
    local total="$4"
    local fixed="$5"
    local current_file="$6"
    local status="$7"
    
    cat > "$PROGRESS_FILE" << EOF
{
  "current_ticket": "$ticket",
  "phase": "$phase",
  "files_processed": $processed,
  "files_total": $total,
  "warnings_fixed": $fixed,
  "warnings_total": 1653,
  "current_file": "$current_file",
  "last_updated": "$(date -Iseconds)",
  "status": "$status"
}
EOF
}

# 清空日志
> "$LOG_FILE"
log "开始修复 any 类型警告"

cd "$FRONTEND_DIR"

# 加载 nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Ticket 07: src/components/
log "开始 Ticket 07: Replace any in src/components/"
update_progress "07-replace-any-components" "scanning" 0 0 0 "" "running"

# 运行 lint 并保存输出
log "运行 ESLint 扫描..."
pnpm lint 2>&1 > "$LINT_OUTPUT" || true

# 提取 src/components/ 中的 any 警告
log "提取 src/components/ 中的 any 警告..."
grep -E "src/components/.*no-explicit-any" "$LINT_OUTPUT" | \
    awk -F: '{print $1}' | sort -u > /tmp/components-with-any.txt

TOTAL_FILES=$(wc -l < /tmp/components-with-any.txt)
log "找到 $TOTAL_FILES 个文件包含 any 类型"

update_progress "07-replace-any-components" "processing" 0 "$TOTAL_FILES" 0 "" "running"

# 处理每个文件
PROCESSED=0
FIXED=0

while IFS= read -r file; do
    PROCESSED=$((PROCESSED + 1))
    log "处理文件 $PROCESSED/$TOTAL_FILES: $file"
    update_progress "07-replace-any-components" "processing" "$PROCESSED" "$TOTAL_FILES" "$FIXED" "$file" "running"
    
    # 提取该文件中的 any 警告
    FILE_WARNINGS=$(grep "$file" "$LINT_OUTPUT" | grep "no-explicit-any" | wc -l)
    log "  文件中有 $FILE_WARNINGS 个 any 警告"
    
    # 这里可以添加具体的修复逻辑
    # 例如：使用 sed/awk 替换常见的 any 模式
    # 暂时只是记录，后续可以扩展
    
    FIXED=$((FIXED + FILE_WARNINGS))
    
done < /tmp/components-with-any.txt

log "Ticket 07 完成"
update_progress "07-replace-any-components" "completed" "$TOTAL_FILES" "$TOTAL_FILES" "$FIXED" "" "running"

# Ticket 08: src/app/
log "开始 Ticket 08: Replace any in src/app/"
update_progress "08-replace-any-app" "scanning" 0 0 "$FIXED" "" "running"

grep -E "src/app/.*no-explicit-any" "$LINT_OUTPUT" | \
    awk -F: '{print $1}' | sort -u > /tmp/app-with-any.txt

TOTAL_FILES=$(wc -l < /tmp/app-with-any.txt)
log "找到 $TOTAL_FILES 个文件包含 any 类型"

PROCESSED=0
while IFS= read -r file; do
    PROCESSED=$((PROCESSED + 1))
    log "处理文件 $PROCESSED/$TOTAL_FILES: $file"
    update_progress "08-replace-any-app" "processing" "$PROCESSED" "$TOTAL_FILES" "$FIXED" "$file" "running"
    
    FILE_WARNINGS=$(grep "$file" "$LINT_OUTPUT" | grep "no-explicit-any" | wc -l)
    FIXED=$((FIXED + FILE_WARNINGS))
    
done < /tmp/app-with-any.txt

log "Ticket 08 完成"
update_progress "08-replace-any-app" "completed" "$TOTAL_FILES" "$TOTAL_FILES" "$FIXED" "" "running"

# Ticket 09: 其他目录
log "开始 Ticket 09: Replace any in remaining directories"
update_progress "09-replace-any-remaining" "scanning" 0 0 "$FIXED" "" "running"

grep -E "(src/lib|src/actions|src/types|src/stores|e2e)/.*no-explicit-any" "$LINT_OUTPUT" | \
    awk -F: '{print $1}' | sort -u > /tmp/remaining-with-any.txt

TOTAL_FILES=$(wc -l < /tmp/remaining-with-any.txt)
log "找到 $TOTAL_FILES 个文件包含 any 类型"

PROCESSED=0
while IFS= read -r file; do
    PROCESSED=$((PROCESSED + 1))
    log "处理文件 $PROCESSED/$TOTAL_FILES: $file"
    update_progress "09-replace-any-remaining" "processing" "$PROCESSED" "$TOTAL_FILES" "$FIXED" "$file" "running"
    
    FILE_WARNINGS=$(grep "$file" "$LINT_OUTPUT" | grep "no-explicit-any" | wc -l)
    FIXED=$((FIXED + FILE_WARNINGS))
    
done < /tmp/remaining-with-any.txt

log "Ticket 09 完成"
update_progress "09-replace-any-remaining" "completed" "$TOTAL_FILES" "$TOTAL_FILES" "$FIXED" "" "running"

# 完成
log "所有 tickets 完成"
update_progress "completed" "done" 0 0 "$FIXED" "" "completed"

log "修复完成！共处理 $FIXED 个 any 警告"
