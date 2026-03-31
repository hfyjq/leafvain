import json
import os
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import WORKSPACE_DIR, ZHIPU_API_KEY, MAX_EXECUTION_STEPS
from core.api_client import APIClientFactory
from core.prompt_builder import PromptBuilder
from core.tool_executor import ToolExecutor


def robust_parse_model_response(response: str) -> Dict[str, Any]:
    """健壮的模型响应解析，处理各种JSON格式问题"""
    if not response or not isinstance(response, str):
        return {
            "thought": "收到空响应",
            "final_answer": "大模型返回了空响应，请重试。"
        }

    response = response.strip()
    print(f"🔍 原始响应 (前500字符): {response[:500]}{'...' if len(response) > 500 else ''}")

    sanitized = re.sub(
        r'[\x00-\x1F\x7F-\x9F]',
        lambda m: f'\\u{ord(m.group(0)):04x}',
        response
    )

    # 方法1: 尝试直接解析
    try:
        parsed = json.loads(sanitized)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 方法2: 尝试修复JSON
    try:
        fixed = sanitized
        # 修复1: 确保字符串被正确引用
        pattern = r'(?<=": )([^"{}\[\],]+)(?=,|\})'

        def replace_match(match):
            value = match.group(1)
            if not (value.startswith('"') and value.endswith('"')):
                return json.dumps(value)
            return value

        fixed = re.sub(pattern, replace_match, fixed)

        # 修复2: 处理content字段中的JSON
        content_pattern = r'"content"\s*:\s*"(\{.*?\})"'

        def fix_content(match):
            content = match.group(1)
            content = content.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            return f'"content": "{content}"'

        fixed = re.sub(content_pattern, fix_content, fixed, flags=re.DOTALL)

        parsed = json.loads(fixed)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError) as e:
        print(f"⚠️ JSON修复失败: {e}")

    # ...（原有方法3和方法4保持不变）...

    # 方法3: 手动提取字段
    try:
        result = {}

        thought_match = re.search(r'"thought"\s*:\s*"([^"]*)"', response, re.DOTALL)
        if thought_match:
            result["thought"] = thought_match.group(1)

        action_match = re.search(r'"action"\s*:\s*"([^"]*)"', response)
        if action_match:
            result["action"] = action_match.group(1)

        answer_match = re.search(r'"final_answer"\s*:\s*"([^"]*)"', response, re.DOTALL)
        if answer_match:
            result["final_answer"] = answer_match.group(1)

        if "action" in result:
            args_start = response.find('"args"')
            if args_start != -1:
                # 从args开始找到匹配的}
                brace_count = 0
                args_end = -1

                for i in range(args_start, len(response)):
                    if response[i] == '{':
                        brace_count += 1
                    elif response[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            args_end = i
                            break

                if args_end != -1:
                    args_str = response[args_start:args_end + 1]
                    # 提取JSON部分
                    args_json_match = re.search(r'(\{.*\})', args_str, re.DOTALL)
                    if args_json_match:
                        try:
                            args = json.loads(args_json_match.group(1))
                            result["args"] = args
                        except:
                            # 如果解析失败，尝试手动提取
                            args = {}
                            # 提取key-value对
                            pairs = re.findall(r'"(\w+)"\s*:\s*"([^"]*)"', args_str)
                            for key, value in pairs:
                                args[key] = value
                            result["args"] = args

        if result:
            return result
    except Exception as e:
        print(f"⚠️ 手动提取失败: {e}")

    # 方法4: 如果是简单的自然语言响应
    if len(response) < 1000 and not response.startswith('{'):
        return {
            "thought": "模型返回了自然语言响应",
            "final_answer": response
        }

    # 最后手段: 返回错误
    return {
        "thought": "无法解析响应格式",
        "final_answer": f"模型返回了难以解析的响应。原始内容:\n\n{response[:1000]}"
    }


def process_query_safely(user_query: str, api_client, tool_executor, prompt_builder) -> None:
    """安全处理用户查询，包含完整的错误处理"""
    print(f"\n🔍 处理查询: {user_query}")
    print("-" * 50)

    # 初始化对话历史
    conversation_history = []

    # 构建初始消息
    messages = prompt_builder.build_messages(user_query, conversation_history)
    conversation_history.extend(messages)

    # 执行步骤循环
    for step in range(1, MAX_EXECUTION_STEPS + 1):
        print(f"\n🔄 步骤 {step}/{MAX_EXECUTION_STEPS}")

        try:
            # 调用大模型
            print("🤔 AI思考中...")
            model_response = api_client.chat_completion(
                messages=conversation_history,
                temperature=0.1,
                max_tokens=2000
            )

            # 解析响应
            parsed = robust_parse_model_response(model_response)

            thought = parsed.get("thought", "")
            if thought:
                print(f"📝 AI思考: {thought}")

            # 添加到历史
            conversation_history.append({
                "role": "assistant",
                "content": model_response
            })

            # 检查是否是最终答案
            if "final_answer" in parsed and parsed["final_answer"]:
                print("\n" + "=" * 50)
                print("✅ 任务完成!")
                print("=" * 50)
                print(f"\n📋 最终报告:\n{parsed['final_answer']}")
                print("\n" + "=" * 50)
                return

            # 执行工具
            if "action" in parsed and parsed["action"]:
                action = parsed["action"]
                args = parsed.get("args", {})

                print(f"⚙️ 执行工具: {action}")

                # 记录参数
                if args:
                    args_preview = json.dumps(args, ensure_ascii=False)[:100]
                    print(f"参数: {args_preview}{'...' if len(json.dumps(args)) > 100 else ''}")

                # 执行工具
                tool_result = tool_executor.execute(action, args)

                if tool_result["success"]:
                    print(f"✅ 工具执行成功")

                    # 获取结果预览
                    formatted_result = tool_result.get('formatted_result', '')
                    if formatted_result:
                        preview = formatted_result[:200]
                        if len(formatted_result) > 200:
                            preview += "..."
                        print(f"📄 结果预览: {preview}")

                    # 将结果添加到对话历史
                    conversation_history.append({
                        "role": "user",
                        "content": f"工具执行结果:\n{tool_result.get('formatted_result', '无结果')}\n\n请根据这个结果继续处理任务。如果任务已完成，请给出最终答案。"
                    })
                else:
                    error_msg = tool_result.get('error', '未知错误')
                    print(f"❌ 工具执行失败: {error_msg}")

                    # 将错误信息也添加到对话历史
                    conversation_history.append({
                        "role": "user",
                        "content": f"工具执行失败: {error_msg}\n\n请根据这个错误继续处理任务。如果无法继续，请给出最终答案。"
                    })
            else:
                print("⚠️ 模型响应格式不正确")
                # 尝试从原始响应中提取信息
                if "无法" in model_response or "失败" in model_response:
                    print("📋 模型似乎遇到了问题，返回原始响应:")
                    print(model_response[:500])
                break

        except Exception as e:
            print(f"❌ 步骤 {step} 出错: {e}")
            import traceback
            traceback.print_exc()
            break

    if step >= MAX_EXECUTION_STEPS:
        print(f"\n⚠️ 达到最大步骤限制 ({MAX_EXECUTION_STEPS})")


def main():
    """主函数"""
    print("=" * 60)
    print("🤖 AI文件助手 - 健壮版本")
    print("=" * 60)

    # 检查API密钥
    if not ZHIPU_API_KEY or ZHIPU_API_KEY == "your_actual_api_key_here":
        print("❌ 请先在 .env 文件中设置 ZHIPU_API_KEY")
        api_key = input("请输入智谱AI API密钥: ").strip()
        if api_key:
            os.environ["ZHIPU_API_KEY"] = api_key
        else:
            print("程序退出")
            return

    try:
        # 初始化组件
        print("🔧 初始化组件...")
        api_client = APIClientFactory.create_client("zhipu")
        tool_executor = ToolExecutor()
        prompt_builder = PromptBuilder(tool_executor)

        print("✅ 所有组件初始化完成!")

        # 交互模式
        print("\n💬 交互模式已启动")
        print("输入 'quit' 退出")
        print("-" * 50)

        while True:
            try:
                user_input = input("\n👤 你: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 再见!")
                    break

                if user_input.lower() in ['help', '?']:
                    print("\n📋 可用命令:")
                    print("  help, ?      - 显示帮助")
                    print("  files, ls    - 列出文件")
                    print("  quit, exit, q - 退出")
                    continue

                if user_input.lower() in ['files', 'ls']:
                    result = tool_executor.execute("list_files", {})
                    print(f"\n{result.get('formatted_result', '无结果')}")
                    continue
                process_query_safely(user_input, api_client, tool_executor, prompt_builder)

            except KeyboardInterrupt:
                print("\n\n⏹️ 操作被用户中断")
                break
            except Exception as e:
                print(f"❌ 错误: {e}")

    except Exception as e:
        print(f"❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
