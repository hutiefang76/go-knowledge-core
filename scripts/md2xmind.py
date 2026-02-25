#!/usr/bin/env python3
"""
Markdown to XMind content.json converter

用法:
    python scripts/md2xmind.py [input.md] [output.json]

默认:
    input:  knowledge.md
    output: xmind_source/content.json
"""

import json
import re
import uuid
import sys
from pathlib import Path
from datetime import datetime


def generate_id():
    """生成XMind兼容的ID"""
    return str(uuid.uuid4())


def update_metadata(md_content: str) -> str:
    """更新Markdown中的版本号和时间"""
    # 更新时间
    today = datetime.now().strftime('%Y-%m-%d')
    md_content = re.sub(
        r'(\*\*更新时间\*\*:\s*)\d{4}-\d{2}-\d{2}',
        f'\\g<1>{today}',
        md_content
    )

    # 更新版本号 (v1.0 -> v1.1, v1.9 -> v1.10, etc.)
    def increment_version(match):
        prefix = match.group(1)
        major = int(match.group(2))
        minor = int(match.group(3))
        minor += 1
        return f'{prefix}v{major}.{minor}'

    md_content = re.sub(
        r'(\*\*版本\*\*:\s*)v(\d+)\.(\d+)',
        increment_version,
        md_content
    )

    return md_content


def parse_markdown(md_content: str) -> dict:
    """解析Markdown为树形结构"""
    lines = md_content.split('\n')

    root = {
        'id': generate_id(),
        'class': 'topic',
        'title': 'Untitled',
        'structureClass': 'org.xmind.ui.map.clockwise',
        'children': {'attached': []}
    }

    # 栈: (level, node)
    stack = [(0, root)]
    current_code_block = None
    current_table = None  # 当前正在解析的表格
    code_fence_pattern = re.compile(r'^```')
    skip_metadata = True  # 跳过开头的元数据块

    def add_node_to_parent(node, level):
        """将节点添加到正确的父节点"""
        while len(stack) > 1 and stack[-1][0] >= level:
            stack.pop()
        _, parent = stack[-1]
        if 'children' not in parent:
            parent['children'] = {'attached': []}
        parent['children']['attached'].append(node)
        return node

    def create_node(title):
        """创建一个新节点"""
        return {
            'id': generate_id(),
            'title': title,
            'titleUnedited': False
        }

    i = 0
    while i < len(lines):
        line = lines[i]

        # 跳过开头的元数据块（以 > 开头的 blockquote 或 ---）
        if skip_metadata:
            if line.strip().startswith('>') or line.strip() == '---' or not line.strip():
                i += 1
                continue
            else:
                skip_metadata = False  # 遇到非元数据行，停止跳过

        # 处理代码块
        if code_fence_pattern.match(line.strip()):
            if current_code_block is None:
                # 开始代码块
                current_code_block = [line]
            else:
                # 结束代码块
                current_code_block.append(line)
                code_content = '\n'.join(current_code_block)

                # 添加代码块作为当前节点的子节点
                _, parent = stack[-1]
                if 'children' not in parent:
                    parent['children'] = {'attached': []}

                code_node = create_node(code_content)
                parent['children']['attached'].append(code_node)
                current_code_block = None
            i += 1
            continue

        if current_code_block is not None:
            current_code_block.append(line)
            i += 1
            continue

        # 跳过空行
        if not line.strip():
            # 结束表格解析
            if current_table is not None:
                current_table = None
            i += 1
            continue

        # 解析表格
        if line.strip().startswith('|') and line.strip().endswith('|'):
            # 跳过分隔行 (|---|---|)
            if re.match(r'^\|[\s\-:|]+\|$', line.strip()):
                i += 1
                continue

            # 解析表格行
            cells = [cell.strip() for cell in line.strip().split('|')[1:-1]]

            if current_table is None:
                # 这是表头
                current_table = {'headers': cells, 'rows': []}
            else:
                # 这是数据行
                current_table['rows'].append(cells)

                # 将表格行作为节点添加（格式：列1: 值1 | 列2: 值2）
                if current_table['headers']:
                    row_content = ' | '.join([
                        f"{current_table['headers'][j]}: {cells[j]}"
                        if j < len(current_table['headers']) and current_table['headers'][j]
                        else cells[j]
                        for j in range(len(cells))
                    ])
                else:
                    row_content = ' | '.join(cells)

                # 添加为当前节点的子节点
                _, parent = stack[-1]
                if 'children' not in parent:
                    parent['children'] = {'attached': []}
                parent['children']['attached'].append(create_node(row_content))

            i += 1
            continue

        # 解析引用块 (> xxx) - 非元数据区域的引用
        quote_match = re.match(r'^>\s*(.+)$', line)
        if quote_match:
            quote_content = quote_match.group(1).strip()
            if quote_content:  # 非空引用
                # 添加为当前节点的子节点，带 📌 标记
                _, parent = stack[-1]
                if 'children' not in parent:
                    parent['children'] = {'attached': []}
                parent['children']['attached'].append(create_node(f"📌 {quote_content}"))
            i += 1
            continue

        # 解析标题 (# ## ### ####)
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()

            node = {
                'id': generate_id(),
                'title': title,
                'titleUnedited': False,
                'children': {'attached': []}
            }

            if level == 1:
                # 根标题
                root['title'] = title
            else:
                # 找到正确的父节点
                while len(stack) > 1 and stack[-1][0] >= level:
                    stack.pop()

                _, parent = stack[-1]
                if 'children' not in parent:
                    parent['children'] = {'attached': []}
                parent['children']['attached'].append(node)
                stack.append((level, node))

            # 重置表格状态
            current_table = None
            i += 1
            continue

        # 解析列表项 (- 或 *)
        list_match = re.match(r'^(\s*)([-*])\s+(.+)$', line)
        if list_match:
            indent = len(list_match.group(1))
            content = list_match.group(3).strip()

            # 计算列表层级 (每2空格一级，基础level=10)
            list_level = 10 + indent // 2

            node = create_node(content)

            # 找到正确的父节点
            while len(stack) > 1 and stack[-1][0] >= list_level:
                stack.pop()

            _, parent = stack[-1]
            if 'children' not in parent:
                parent['children'] = {'attached': []}
            parent['children']['attached'].append(node)
            stack.append((list_level, node))

            i += 1
            continue

        # 解析普通段落（非空、非特殊格式的行）
        # 排除只有特殊字符的行
        if line.strip() and not line.strip().startswith(('|', '>', '#', '-', '*', '`')):
            paragraph = line.strip()
            # 跳过纯格式行（如 **xxx**）或很短的格式标记
            if len(paragraph) > 3:
                _, parent = stack[-1]
                if 'children' not in parent:
                    parent['children'] = {'attached': []}
                parent['children']['attached'].append(create_node(paragraph))
            i += 1
            continue

        i += 1

    # 清理空的children
    def clean_empty_children(node):
        if 'children' in node:
            if not node['children'].get('attached'):
                del node['children']
            else:
                for child in node['children']['attached']:
                    clean_empty_children(child)

    clean_empty_children(root)
    return root


def create_xmind_content(root_topic: dict) -> list:
    """创建完整的XMind content.json结构"""
    return [{
        'id': generate_id(),
        'revisionId': str(uuid.uuid4()),
        'class': 'sheet',
        'rootTopic': root_topic,
        'title': root_topic['title'],
        'topicOverlapping': 'overlap',
        'extensions': [{
            'provider': 'org.xmind.ui.skeleton.structure.style',
            'content': {'centralTopic': 'org.xmind.ui.map.clockwise'}
        }],
        'theme': get_default_theme()
    }]


def get_default_theme() -> dict:
    """返回默认主题配置"""
    return {
        'map': {
            'id': generate_id(),
            'properties': {
                'svg:fill': '#ffffff',
                'multi-line-colors': '#FF6B6B #FF9F69 #97D3B6 #88E2D7 #6FD0F9 #E18BEE',
                'color-list': '#FF6B6B #FF9F69 #97D3B6 #88E2D7 #6FD0F9 #E18BEE',
                'line-tapered': 'none'
            }
        },
        'centralTopic': {
            'id': generate_id(),
            'properties': {
                'fo:font-family': 'NeverMind',
                'fo:font-size': '30pt',
                'fo:font-weight': '800',
                'svg:fill': '#000000',
                'shape-class': 'org.xmind.topicShape.roundedRect',
                'line-class': 'org.xmind.branchConnection.curve'
            }
        },
        'mainTopic': {
            'id': generate_id(),
            'properties': {
                'fo:font-family': 'NeverMind',
                'fo:font-size': '18pt',
                'fo:font-weight': '500',
                'shape-class': 'org.xmind.topicShape.roundedRect',
                'line-class': 'org.xmind.branchConnection.roundedElbow'
            }
        },
        'subTopic': {
            'id': generate_id(),
            'properties': {
                'fo:font-family': 'NeverMind',
                'fo:font-size': '14pt',
                'fo:font-weight': '400',
                'shape-class': 'org.xmind.topicShape.roundedRect',
                'line-class': 'org.xmind.branchConnection.roundedElbow'
            }
        }
    }


def json_to_markdown(content_json: list) -> str:
    """将content.json转换回Markdown"""
    if not content_json:
        return ''

    root_topic = content_json[0].get('rootTopic', {})
    lines = []

    def process_node(node, level=1, is_list=False):
        title = node.get('title', '')

        if level == 1:
            lines.append(f"# {title}")
        elif level <= 4 and not is_list:
            lines.append(f"\n{'#' * level} {title}")
        else:
            # 作为列表项
            indent = '  ' * max(0, level - 5)
            # 处理多行内容（代码块等）
            if '\n' in title:
                lines.append(f"{indent}- (代码块)")
                lines.append(title)
            else:
                lines.append(f"{indent}- {title}")

        children = node.get('children', {}).get('attached', [])

        # level==1时对一级子节点排序（按"第X部分"顺序，总结放最后）
        if level == 1 and children:
            def sort_key(child):
                t = child.get('title', '')
                if '第一部分' in t: return 1
                if '第二部分' in t: return 2
                if '第三部分' in t: return 3
                if '第四部分' in t: return 4
                if '第五部分' in t: return 5
                if '总结' in t: return 99
                return 50
            children = sorted(children, key=sort_key)

        for child in children:
            # 判断是否应该作为列表项
            child_children = child.get('children', {}).get('attached', [])
            next_is_list = level >= 4 or is_list or not child_children
            process_node(child, level + 1, next_is_list)

    process_node(root_topic)
    return '\n'.join(lines)


def main():
    project_dir = Path(__file__).parent.parent

    # 默认路径
    input_file = project_dir / 'knowledge.md'
    output_file = project_dir / 'xmind_source' / 'content.json'

    # 命令行参数
    if len(sys.argv) >= 2:
        input_file = Path(sys.argv[1])
    if len(sys.argv) >= 3:
        output_file = Path(sys.argv[2])

    # 特殊命令：从现有JSON生成MD
    if len(sys.argv) >= 2 and sys.argv[1] == '--reverse':
        json_file = project_dir / 'xmind_source' / 'content.json'
        md_file = project_dir / 'knowledge.md'

        with open(json_file, 'r', encoding='utf-8') as f:
            content = json.load(f)

        md_content = json_to_markdown(content)
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)

        print(f"✅ 已从 {json_file} 生成 {md_file}")
        return

    # 正常转换：MD -> JSON
    if not input_file.exists():
        print(f"❌ 输入文件不存在: {input_file}")
        print(f"   提示: 先运行 `python {sys.argv[0]} --reverse` 从现有JSON生成MD模板")
        sys.exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # 更新版本号和时间
    updated_md_content = update_metadata(md_content)
    if updated_md_content != md_content:
        with open(input_file, 'w', encoding='utf-8') as f:
            f.write(updated_md_content)
        # 提取新版本号用于显示
        version_match = re.search(r'\*\*版本\*\*:\s*(v[\d.]+)', updated_md_content)
        version = version_match.group(1) if version_match else 'unknown'
        print(f"📝 已更新版本号: {version}，时间: {datetime.now().strftime('%Y-%m-%d')}")
        md_content = updated_md_content

    root_topic = parse_markdown(md_content)
    content = create_xmind_content(root_topic)

    # 备份原文件
    if output_file.exists():
        backup_file = output_file.with_suffix('.json.bak')
        output_file.rename(backup_file)
        print(f"📦 已备份原文件到: {backup_file}")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

    print(f"✅ 转换完成: {input_file} -> {output_file}")
    print(f"   下一步: ./scripts/build_xmind.sh")


if __name__ == '__main__':
    main()
