#!/bin/bash
# 运行所有示例代码
# 用法: ./scripts/run_all_examples.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=========================================="
echo "Go 多线程知识点 - 示例代码运行"
echo "=========================================="

# Part 2: Go基础
echo -e "\n>>> Part 2: Go语言基本的多线程使用"
for f in examples/part2_go_basics/*.go; do
    echo -e "\n--- 运行: $(basename $f) ---"
    go run "$f"
done

# Part 3: 线程安全
echo -e "\n>>> Part 3: 多线程问题和线程不安全"
for f in examples/part3_thread_safety/*.go; do
    echo -e "\n--- 运行: $(basename $f) ---"
    go run "$f"
done

# Part 4: 最佳实践
echo -e "\n>>> Part 4: Go语言并发最佳实践"
for f in examples/part4_best_practices/*.go; do
    echo -e "\n--- 运行: $(basename $f) ---"
    go run "$f"
done

# Part 5: 死锁
echo -e "\n>>> Part 5: 死锁问题及解决方案"
for f in examples/part5_deadlock/*.go; do
    echo -e "\n--- 运行: $(basename $f) ---"
    go run "$f"
done

echo -e "\n=========================================="
echo "所有示例运行完成!"
echo "=========================================="
