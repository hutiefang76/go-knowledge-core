#!/bin/bash
# 打包xmind文件脚本
# 用法: ./scripts/build_xmind.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
XMIND_SOURCE="$PROJECT_DIR/xmind_source"
OUTPUT_FILE="$PROJECT_DIR/Go多线程知识点.xmind"

cd "$XMIND_SOURCE"
rm -f "$OUTPUT_FILE"
zip -r "$OUTPUT_FILE" . -x "*.bak" -x ".DS_Store"

echo "XMind文件已生成: $OUTPUT_FILE"
