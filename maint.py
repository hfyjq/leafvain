# quick_fix_main.py
#!/usr/bin/env python3
"""
快速修复主程序
解决AI返回action格式不正确的问题
"""
import os
import sys
import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 添加到系统路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# 导入配置
try:
    import config
    WORKSPACE_DIR = config.WORKSPACE_DIR
    MAX_EXECUTION_STEPS = getattr(config, 'MAX_EXECUTION_STEPS', 3)
    ZHIPU_API_KEY = config.ZHIPU_API_KEY
except ImportError as e:
    print(f"❌ 导入配置失败: {e}")
    sys.exit(1)

# 导入核心模块
from core.skill_manager import SkillManager
from core.skill_matcher import SkillMatcher
from core.skill_executor import SkillExecutor
from core.api_client import APIClientFactory

# 导入我们的JSON解析器
from json_parser import robust_parse_model_response, fix_ai_args


def build_strict_system_prompt(skill_manager: SkillManager, user_query: str) -> str:
    """严格的系统提示，明确要求完整的技能调用格式"""
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M")
    
    prompt = f"""# 🤖 AI助手
当前时间: {current_time}

## 📋 重要规则
你必须返回JSON格式，且action必须是完整的技能调用格式。

## 🎯 响应格式
调用技能时，必须返回：
json
{{
"thought": "思考过程",
"action": "skill.<技能ID>.<功能名>",
"args": {{}}
}}
注意：**action必须以"skill."开头**，后跟技能ID和功能名，用点号分隔。

## 🛠️ 可用技能
"""

    for skill_id, skill in skill_manager.get_all_skills().items():
        prompt += f"\n### {skill.icon} {skill.name} (ID: {skill_id})\n"

        functions = skill.get_functions()
        if functions:
            for func in functions:
                func_name = func['name']
                func_desc = func.get('description', '').strip()
                prompt += f"- {func_name}: {func_desc[:80]}...\n"

    # 特别强调格式
    prompt += f"""
## ⚠️ 特别注意
你必须返回完整的技能调用格式，如：
- ✅ 正确: "skill.file_enhanced.list_files"
- ✅ 正确: "skill.schedule.add_schedule"
- ❌ 错误: "list_files"
- ❌ 错误: "file_enhanced.list_files"
- ❌ 错误: "add_schedule"

必须包含完整的"skill."前缀。

## 🎯 当前任务
用户查询: "{user_query}"

请分析需求，返回正确的JSON，包含完整的skill.开头的action。
"""

    return prompt


def fix_action_format(action: str, matched_skill: Dict[str, Any] = None) -> str:
    """修复action格式"""
    if not action:
        return action

    # 如果已经是正确的格式
    if action.startswith("skill."):
        return action

    # 尝试修复常见的格式问题
    if "." in action:
        # 类似 "file_enhanced.list_files" 的格式
        if not action.startswith("skill."):
            return "skill." + action
    else:
        # 只有功能名，如 "list_files"
        if matched_skill and "skill_id" in matched_skill:
            skill_id = matched_skill["skill_id"]
            return f"skill.{skill_id}.{action}"

    return action


def process_query_quick_fix(user_query: str, api_client, skill_executor: SkillExecutor,
                            skill_matcher: SkillMatcher, context: Dict[str, Any]) -> None:
    """快速修复的查询处理"""
    print(f"\n🔍 查询: {user_query}")
    print("-" * 50)

    # 技能匹配
    matches = skill_matcher.match_skills(user_query, context)
    matched_skill = matches[0] if matches else None

    if matched_skill:
        print(f"🤔 匹配技能: {matched_skill['skill'].name} (ID: {matched_skill['skill_id']})")

    # 构建系统提示
    skill_manager = skill_executor.skill_manager
    system_prompt = build_strict_system_prompt(skill_manager, user_query)

    # 对话
    conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]

    for step in range(1, MAX_EXECUTION_STEPS + 1):
        print(f"\n🔄 步骤 {step}/{MAX_EXECUTION_STEPS}")

        try:
            # 调用AI
            print("🤔 AI思考中...")
            response = api_client.chat_completion(
                messages=conversation,
                temperature=0.1,
                max_tokens=1000
            )

            # 解析响应
            parsed = robust_parse_model_response(response)

            # 确保是字典
            if not isinstance(parsed, dict):
                parsed = {"thought": "解析失败", "final_answer": "无法解析AI响应"}

            thought = parsed.get("thought", "")
            if thought and thought != "解析失败":
                print(f"📝 AI思考: {thought[:100]}..." if len(thought) > 100 else f"📝 AI思考: {thought}")

            # 检查最终答案
            if "final_answer" in parsed and parsed["final_answer"]:
                print(f"\n✅ 最终答案:\n{parsed['final_answer']}")
                return

            # 执行技能
            if "action" in parsed and parsed["action"]:
                action = parsed["action"]
                args = parsed.get("args", {})

                print(f"⚙️ AI返回动作: {action}")

                # 修复action格式
                fixed_action = fix_action_format(action, matched_skill)
                if fixed_action != action:
                    print(f"  🔧 修复为: {fixed_action}")
                    action = fixed_action

                # 确保action格式正确
                if not action.startswith("skill."):
                    print(f"❌ 无效的action格式: {action}")
                    print(f"   期望格式: skill.<技能ID>.<功能名>")
                    return

                # 修复参数
                fixed_args = fix_ai_args(args, action)

                # 执行技能
                result = skill_executor.execute(action, fixed_args)

                # 调试：打印结果结构
                print(f"🔍 结果结构: {list(result.keys())}")

                # 初始化变量
                friendly = ""
                is_final = False
                actual_result = result

                # 如果有raw_result，使用它
                if 'raw_result' in result and isinstance(result['raw_result'], dict):
                    actual_result = result['raw_result']

                # 检查技能是否执行成功
                if result.get("success", False):
                    # 检查是否是最终结果
                    is_final = actual_result.get("is_final_answer", False)
                    if not is_final:
                        is_final = "files" in actual_result or "schedules" in actual_result or "formatted_result" in actual_result

                    # 获取友好消息
                    friendly = actual_result.get("friendly_message", "")
                    if not friendly:
                        friendly = actual_result.get("formatted_result", "")
                    if not friendly and actual_result.get("success", False):
                        friendly = "操作成功"
                else:
                    # 技能执行失败
                    is_final = True
                    friendly = actual_result.get("error", "未知错误")
                    if not friendly:
                        friendly = f"操作失败: {actual_result}"

                print(f"🔍 最终友好消息: {friendly[:200]}..." if len(friendly) > 200 else f"🔍 最终友好消息: {friendly}")

                if result.get("success", False):
                    # 检查是否是最终结果
                    # 技能明确标记为最终答案
                    is_final = result.get("is_final_answer", False)
                    # 或者有特定的数据结构
                    if not is_final:
                        is_final = "files" in result or "schedules" in result or "formatted_result" in result
                    # 并且技能执行成功
                    if is_final and not result.get("success", False):
                        is_final = False

                    # 总是获取友好消息
                    friendly = result.get("friendly_message", "")
                    if not friendly:
                        friendly = result.get("formatted_result", "")
                    if not friendly and result.get("success", False):
                        friendly = "操作成功"

                    if is_final:
                        # 最终结果，结束
                        print(f"\n✅ 任务完成!\n")
                        if friendly:
                            print(friendly)
                        return
                    else:
                        # 中间结果，继续
                        print(f"📄 结果: {friendly[:200]}..." if len(friendly) > 200 else f"📄 结果: {friendly}")

                        conversation.append({
                            "role": "assistant",
                            "content": response
                        })

                        conversation.append({
                            "role": "user",
                            "content": f"结果: {friendly}\n请继续处理。"
                        })
                else:
                    error = result.get("error", "未知错误")
                    print(f"❌ 执行失败: {error}")
                    return
            else:
                print("⚠️ AI没有返回可执行的动作")
                print(f"  解析结果: {parsed}")
                return

        except Exception as e:
            print(f"❌ 步骤 {step} 出错: {e}")
            traceback.print_exc()
            return

    print("\n⚠️ 达到最大步骤限制")


def main():
    """主函数"""
    print("=" * 60)
    print("🤖 AI助手 - 快速修复版")
    print("=" * 60)

    # 检查API密钥
    if not ZHIPU_API_KEY or ZHIPU_API_KEY == "your_actual_api_key_here":
        print("❌ 请设置API密钥")
        return

    # 初始化
    print("\n🔧 初始化...")
    try:
        skill_manager = SkillManager("skills")
        skill_manager.load_skills()

        if not skill_manager.skills:
            print("❌ 没有加载到技能")
            return

        skill_matcher = SkillMatcher(skill_manager)
        skill_executor = SkillExecutor(skill_manager)

        print(f"✅ 加载技能: {len(skill_manager.skills)} 个")
        for skill_id, skill in skill_manager.skills.items():
            print(f"  - {skill.icon} {skill.name} v{skill.version}")

    except Exception as e:
        print(f"❌ 技能系统初始化失败: {e}")
        traceback.print_exc()
        return

    # API客户端
    try:
        api_client = APIClientFactory.create_client("zhipu")
        print("✅ AI客户端初始化成功")
    except Exception as e:
        print(f"❌ AI客户端初始化失败: {e}")
        return

    # 交互
    context = {}
    print(f"\n💬 系统已就绪!")
    print("   输入 'quit' 退出, 'test' 运行测试")
    print("-" * 50)

    while True:
        try:
            query = input("\n👤 你: ").strip()

            if not query:
                continue

            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 再见!")
                break

            if query.lower() in ['test']:
                print("\n🧪 运行测试...")
                test_queries = [
                    "工作区有哪些文件",
                    "列出工作区所有文件",
                    "查看日程安排",
                ]

                for test_query in test_queries:
                    print(f"\n测试: {test_query}")
                    process_query_quick_fix(test_query, api_client, skill_executor, skill_matcher, {})
                continue

            # 处理查询
            process_query_quick_fix(query, api_client, skill_executor, skill_matcher, context)

        except KeyboardInterrupt:
            print("\n👋 再见!")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    main()