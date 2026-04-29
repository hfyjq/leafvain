# create_skill.py
# !/usr/bin/env python3
"""
Skill创建向导
帮助开发者快速创建符合规范的Skill
"""
import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# 添加到系统路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def create_skill_wizard():
    """Skill创建向导"""
    print("=" * 60)
    print("🛠️  Skill创建向导")
    print("=" * 60)
    print("此向导将帮助您创建一个符合规范的Skill。\n")

    # 步骤1: 获取技能基本信息
    print("📋 步骤1: 基本信息")
    print("-" * 30)

    skill_name = input("技能名称（中文，如：文件操作）: ").strip()
    while not skill_name:
        print("❌ 技能名称不能为空")
        skill_name = input("技能名称（中文，如：文件操作）: ").strip()

    # 自动生成技能ID
    skill_id = input(f"技能ID（英文小写，建议: {_to_snake_case(skill_name)}）: ").strip()
    if not skill_id:
        skill_id = _to_snake_case(skill_name)

    # 验证技能ID格式
    if not re.match(r'^[a-z][a-z0-9_]*$', skill_id):
        print(f"❌ 技能ID格式错误，只能包含小写字母、数字和下划线，且以字母开头")
        skill_id = _to_snake_case(skill_name)
        print(f"  已自动生成: {skill_id}")

    description = input("技能描述（简要说明功能）: ").strip()
    if not description:
        description = f"{skill_name}技能，提供相关功能。"

    author = input("开发者名称（可选）: ").strip() or "匿名开发者"

    # 步骤2: 技能分类和标签
    print(f"\n📋 步骤2: 分类和标签")
    print("-" * 30)

    default_categories = ["工具"]
    categories_input = input(f"技能分类（用逗号分隔，默认: {', '.join(default_categories)}）: ").strip()
    categories = [c.strip() for c in categories_input.split(',')] if categories_input else default_categories

    tags_input = input("技能标签（用逗号分隔，用于匹配用户查询，如：文件,文档,管理）: ").strip()
    tags = [t.strip() for t in tags_input.split(',')] if tags_input else []

    # 自动添加一些常用标签
    if not tags:
        tags = [skill_id]
        print(f"  已自动添加标签: {tags[0]}")

    # 步骤3: 技能图标
    print(f"\n📋 步骤3: 图标")
    print("-" * 30)

    icons = {
        "文件": "📁", "文档": "📄", "搜索": "🔍", "计算": "🧮",
        "天气": "🌤️", "日程": "📅", "网络": "🌐", "工具": "🛠️",
        "设置": "⚙️", "帮助": "❓", "安全": "🔒", "开发": "💻",
    }

    print("可用图标:")
    for name, icon in icons.items():
        print(f"  {icon} {name}", end="  ")
    print()

    icon = input("选择图标（输入图标或表情）: ").strip() or "🛠️"

    # 步骤4: 功能定义
    print(f"\n📋 步骤4: 功能定义")
    print("-" * 30)

    functions = []
    add_more = True

    while add_more:
        print(f"\n定义功能 #{len(functions) + 1}:")

        func_name = input("  功能名称（英文，如：list_files）: ").strip()
        if not func_name:
            print("  ❌ 功能名称不能为空")
            continue

        func_desc = input("  功能描述（简要说明）: ").strip()
        if not func_desc:
            func_desc = f"执行{func_name}功能"

        # 询问参数
        params = []
        add_params = True

        while add_params:
            param_name = input("    参数名称（英文，如：directory_path，回车跳过）: ").strip()
            if not param_name:
                add_params = False
                break

            param_type = input(f"    参数类型（如：str, int, bool，默认: str）: ").strip() or "str"
            param_desc = input(f"    参数描述: ").strip()

            is_optional = input(f"    是否可选？(y/N): ").strip().lower() == 'y'
            default_value = None
            if is_optional:
                default_input = input(f"    默认值（直接回车表示None）: ").strip()
                default_value = default_input if default_input else None

            params.append({
                "name": param_name,
                "type": param_type,
                "description": param_desc,
                "optional": is_optional,
                "default": default_value
            })

            add_more_params = input("    添加更多参数？(y/N): ").strip().lower() == 'y'
            if not add_more_params:
                add_params = False

        functions.append({
            "name": func_name,
            "description": func_desc,
            "params": params
        })

        add_more = input("  添加更多功能？(y/N): ").strip().lower() == 'y'

    # 步骤5: 示例对话
    print(f"\n📋 步骤5: 示例对话")
    print("-" * 30)

    examples = []
    add_examples = True

    while add_examples and len(examples) < 5:  # 最多5个示例
        print(f"\n示例 #{len(examples) + 1}:")

        user_query = input("  用户查询（如：列出所有文件）: ").strip()
        if not user_query:
            break

        assistant_response = input("  AI回复（简要说明如何调用）: ").strip()
        if not assistant_response:
            assistant_response = f"我将调用{skill_name}技能来处理。"

        # 关联功能
        if functions:
            print("  可关联的功能:")
            for i, func in enumerate(functions, 1):
                print(f"    {i}. {func['name']}: {func['description']}")

            func_idx = input(f"  关联的功能编号（1-{len(functions)}，回车跳过）: ").strip()
            if func_idx.isdigit() and 1 <= int(func_idx) <= len(functions):
                func_name = functions[int(func_idx) - 1]['name']
            else:
                func_name = functions[0]['name'] if functions else "example_function"
        else:
            func_name = "example_function"

        examples.append({
            "user": user_query,
            "assistant": assistant_response,
            "function": func_name
        })

        if len(examples) < 5:
            add_examples = input("  添加更多示例？(y/N): ").strip().lower() == 'y'
        else:
            print("  ℹ️ 已达到最大示例数量（5个）")
            add_examples = False

    # 步骤6: 确认信息
    print(f"\n📋 步骤6: 确认信息")
    print("-" * 30)

    print(f"\n🔧 技能信息:")
    print(f"  名称: {skill_name}")
    print(f"  ID: {skill_id}")
    print(f"  版本: 1.0.0")
    print(f"  描述: {description}")
    print(f"  开发者: {author}")
    print(f"  分类: {', '.join(categories)}")
    print(f"  标签: {', '.join(tags)}")
    print(f"  图标: {icon}")

    print(f"\n🛠️ 功能 ({len(functions)} 个):")
    for i, func in enumerate(functions, 1):
        print(f"  {i}. {func['name']}: {func['description']}")
        if func['params']:
            for param in func['params']:
                optional = " (可选)" if param['optional'] else ""
                default = f" 默认值: {param['default']}" if param['default'] is not None else ""
                print(f"    参数: {param['name']} ({param['type']}){optional}{default}")

    print(f"\n💬 示例 ({len(examples)} 个):")
    for i, ex in enumerate(examples, 1):
        print(f"  {i}. 用户: {ex['user']}")
        print(f"     AI: {ex['assistant']}")

    confirm = input(f"\n确认创建技能？(y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 已取消")
        return

    # 步骤7: 创建技能文件
    print(f"\n📁 步骤7: 创建文件")
    print("-" * 30)

    # 生成类名
    class_name = _to_pascal_case(skill_id) + "Skill"

    # 读取模板
    template_path = BASE_DIR / "skills" / "template_skill.py"
    if not template_path.exists():
        print(f"❌ 模板文件不存在: {template_path}")
        return

    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # 替换模板内容
    replacements = {
        "TemplateSkill": class_name,
        '"template"': json.dumps(skill_id, ensure_ascii=False),
        '"技能模板"': json.dumps(skill_name, ensure_ascii=False),
        '"1.0.0"': json.dumps("1.0.0", ensure_ascii=False),
        '"这是一个技能模板，描述了技能的功能和用途。"': json.dumps(description, ensure_ascii=False),
        '"开发者名称"': json.dumps(author, ensure_ascii=False),
        '["工具", "示例"]': json.dumps(categories, ensure_ascii=False),
        '["模板", "示例"]': json.dumps(tags, ensure_ascii=False),
        '"🛠️"': json.dumps(icon, ensure_ascii=False),
    }

    for old, new in replacements.items():
        template_content = template_content.replace(old, new)

    # 生成功能方法代码
    functions_code = "\n    # ========== 功能方法 ==========\n"

    for func in functions:
        func_name = func['name']
        func_desc = func['description']
        params = func['params']

        # 生成参数列表
        param_list = []
        for param in params:
            param_str = f"{param['name']}: {param['type']}"
            if param['optional'] and param['default'] is not None:
                param_str += f" = {_format_default_value(param['default'], param['type'])}"
            elif param['optional']:
                param_str += f" = None"
            param_list.append(param_str)

        param_str = ", ".join(['self'] + param_list) if param_list else 'self'

        # 生成函数文档
        docstring = f'        """\n        {func_desc}\n        \n        Args:\n'

        for param in params:
            optional = " (可选)" if param['optional'] else ""
            default = f"，默认值: {param['default']}" if param['default'] is not None else ""
            docstring += f"            {param['name']}: {param['description']}{optional}{default}\n"

        docstring += """        
        Returns:
            包含执行结果的字典
        """ + '        """'

        # 生成函数体
        function_body = f"""    def func_{func_name}({param_str}) -> Dict[str, Any]:
{docstring}
        # TODO: 实现功能逻辑
        try:
            # 你的代码在这里

            return {{
                "success": True,
                "data": "功能实现待完成",
                "message": "{func_desc}",
                "formatted_result": f"✅ {{'{func_desc}'}} 功能待实现",
                "is_final_answer": True,
            }}

        except Exception as e:
            return {{
                "success": False,
                "error": f"执行失败: {{str(e)}}",
                "formatted_result": f"❌ {{'{func_desc}'}} 失败: {{str(e)}}"
            }}
"""

        functions_code += "\n" + function_body

    # 在模板中插入功能方法
    # 找到示例功能的位置，替换为生成的功能
    template_content = template_content.replace(
        "    # ========== 功能方法示例 ==========",
        functions_code
    )

    # 移除示例功能
    template_content = re.sub(
        r'    def func_example_function.*?"""\n.*?\n    def func_another_function',
        '    def func_another_function',
        template_content,
        flags=re.DOTALL
    )

    # 写入技能文件
    skill_dir = BASE_DIR / "skills"
    skill_dir.mkdir(exist_ok=True)

    skill_file = skill_dir / f"{skill_id}_skill.py"

    if skill_file.exists():
        overwrite = input(f"文件 {skill_file.name} 已存在，是否覆盖？(y/N): ").strip().lower()
        if overwrite != 'y':
            print("❌ 已取消")
            return

    with open(skill_file, 'w', encoding='utf-8') as f:
        f.write(template_content)

    print(f"✅ 技能文件创建成功: {skill_file}")

    # 创建测试文件
    test_content = f'''#!/usr/bin/env python3
"""
测试 {skill_name} 技能
"""
import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def test_{skill_id}_skill():
    """测试{skill_name}技能"""
    print("🧪 测试{skill_name}技能")

    try:
        from skills.{skill_id}_skill import {class_name}

        # 创建技能实例
        skill = {class_name}()

        print(f"✅ 技能名称: {{skill.name}}")
        print(f"   版本: v{{skill.version}}")
        print(f"   描述: {{skill.description}}")

        # 测试功能
        print(f"\\n🔧 测试功能...")

        # 测试每个功能
        functions = skill.get_functions()
        for func in functions:
            func_name = func["name"]
            print(f"  🧪 测试功能: {{func_name}}")

            try:
                # 构建测试参数
                test_args = {{}}
                params = func.get("parameters", {{}})

                for param_name, param_info in params.items():
                    if not param_info.get("optional", False):
                        # 为必填参数提供测试值
                        param_type = param_info.get("type", "str")
                        if param_type == "int":
                            test_args[param_name] = 1
                        elif param_type == "bool":
                            test_args[param_name] = True
                        else:
                            test_args[param_name] = "测试值"

                # 执行功能
                result = skill.execute(func_name, **test_args)

                if result.get("success", False):
                    print(f"    ✅ 成功")
                    if "formatted_result" in result:
                        print(f"      结果: {{result['formatted_result'][:100]}}...")
                else:
                    print(f"    ❌ 失败: {{result.get('error', '未知错误')}}")

            except Exception as e:
                print(f"    ❌ 异常: {{e}}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {{e}}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_{skill_id}_skill()
    sys.exit(0 if success else 1)
'''

    test_file = skill_dir / f"test_{skill_id}.py"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)

    print(f"✅ 测试文件创建成功: {test_file}")

    # 创建README文件
    readme_content = f'''# {skill_name} 技能文档

## 基本信息
- **技能ID**: {skill_id}
- **名称**: {skill_name}
- **版本**: 1.0.0
- **开发者**: {author}
- **创建时间**: {datetime.now().strftime('%Y-%m-%d')}

## 功能描述
{description}

## 功能列表
{f"### 共 {len(functions)} 个功能" if functions else "暂无功能定义"}

{f"".join([f"### {i + 1}. {func['name']}\n{func['description']}\n\n" for i, func in enumerate(functions)]) if functions else ""}

## 使用示例
{f"".join([f"### 示例 {i + 1}\n- 用户: {ex['user']}\n- AI: {ex['assistant']}\n\n" for i, ex in enumerate(examples)]) if examples else "暂无使用示例"}

## 开发说明
1. 技能文件: `{skill_id}_skill.py`
2. 测试文件: `test_{skill_id}.py`
3. 主类: `{class_name}`

## 后续步骤
1. 实现所有功能方法
2. 完善错误处理
3. 添加更多测试用例
4. 优化用户体验
'''

    readme_file = skill_dir / f"README_{skill_id.upper()}.md"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print(f"✅ 文档文件创建成功: {readme_file}")

    print(f"\n🎉 技能创建完成！")
    print(f"\n📋 下一步：")
    print(f"  1. 编辑文件: {skill_file}")
    print(f"  2. 实现功能方法（查找TODO注释）")
    print(f"  3. 运行测试: python {test_file}")
    print(f"  4. 重启主程序加载新技能")


def _to_snake_case(text: str) -> str:
    """转换为蛇形命名"""
    # 移除特殊字符，只保留字母数字和空格
    text = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff\s]', '', text)
    # 中文转拼音（简化处理）
    text = re.sub(r'[\u4e00-\u9fff]', '_', text)
    # 转换为小写，用下划线替换空格
    text = text.lower().strip().replace(' ', '_')
    # 移除多余下划线
    text = re.sub(r'_+', '_', text)
    # 确保以字母开头
    if text and not text[0].isalpha():
        text = 'skill_' + text
    return text or 'new_skill'


def _to_pascal_case(text: str) -> str:
    """转换为帕斯卡命名"""
    snake = _to_snake_case(text)
    return ''.join(word.title() for word in snake.split('_'))


def _format_default_value(value: Any, type_hint: str) -> str:
    """格式化默认值"""
    if value is None:
        return "None"

    if type_hint == "str":
        return f'"{value}"'
    elif type_hint == "bool":
        return "True" if str(value).lower() in ["true", "1", "yes"] else "False"
    elif type_hint == "int":
        try:
            return str(int(value))
        except:
            return "0"
    else:
        return str(value)


if __name__ == "__main__":
    create_skill_wizard()