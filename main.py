import json
import os
import sys
import re
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.notification_service import NotificationService
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import WORKSPACE_DIR, ZHIPU_API_KEY, MAX_EXECUTION_STEPS, BASE_DIR
from core.api_client import APIClientFactory
from core.prompt_builder import PromptBuilder
from core.tool_executor import ToolExecutor

import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# 确保首先加载config模块
import config
print(f"✅ 已加载配置文件: {config.__file__}")
# 在 robust_parse_model_response 函数中添加预处理
def robust_parse_model_response(response: str) -> Dict[str, Any]:
    """健壮的模型响应解析，处理各种JSON格式问题"""
    response = response.replace('%', '%%')
    if not response or not isinstance(response, str):
        return {
            "thought": "收到空响应",
            "final_answer": "大模型返回了空响应，请重试。"
        }

    response = response.strip()
    print(f"🔍 原始响应 (前500字符): {response[:500]}{'...' if len(response) > 500 else ''}")

    # 预处理：转义所有控制字符
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

    # 方法2: 尝试修复JSON（增强版）
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

        if not response.strip().startswith('{'):
            # 尝试添加缺失的大括号
            fixed = '{' + response + '}'
            try:
                parsed = json.loads(fixed)
                if isinstance(parsed, dict):
                    return parsed
            except:
                pass
        # 新增修复3: 处理属性名缺少双引号的情况
        fixed = re.sub(r'(\{|\s)(\w+):', r'\1"\2":', fixed)

        # 新增修复4: 处理单引号问题
        fixed = fixed.replace("'", '"')

        # 新增修复5: 处理多余逗号
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)


        parsed = json.loads(fixed)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError) as e:
        print(f"⚠️ JSON修复失败: {e}")

    # 方法3: 手动提取字段（保持不变）
    try:
        result = {}

        # 提取thought
        thought_match = re.search(r'"thought"\s*:\s*"([^"]*)"', response, re.DOTALL)
        if thought_match:
            result["thought"] = thought_match.group(1)

        # 提取action
        action_match = re.search(r'"action"\s*:\s*"([^"]*)"', response)
        if action_match:
            result["action"] = action_match.group(1)

        # 提取final_answer
        answer_match = re.search(r'"final_answer"\s*:\s*"([^"]*)"', response, re.DOTALL)
        if answer_match:
            result["final_answer"] = answer_match.group(1)

        # 提取args
        if "action" in result:
            # 查找args部分
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

    # 方法4: 如果是简单的自然语言响应（保持不变）
    if len(response) < 1000 and not response.startswith('{'):
        return {
            "thought": "模型返回了自然语言响应",
            "final_answer": response
        }

    # 最后手段: 返回错误（保持不变）
    return {
        "thought": "无法解析响应格式",
        "final_answer": f"模型返回了难以解析的响应。原始内容:\n\n{response[:1000]}"
    }


def check_workspace():
    """检查工作区配置和文件"""
    print("\n🔍 工作区诊断:")
    print(f"工作区路径: {WORKSPACE_DIR.resolve()}")
    print(f"是否存在: {WORKSPACE_DIR.exists()}")

    if WORKSPACE_DIR.exists():
        print("\n📂 工作区内容:")
        for item in WORKSPACE_DIR.iterdir():
            if item.is_file():
                print(f"  - {item.name} (大小: {item.stat().st_size}字节)")
            elif item.is_dir():
                print(f"  - 📁 {item.name}/")

        # 检查PDF文件是否存在
        pdf_files = list(WORKSPACE_DIR.glob("*.pdf"))
        print(f"\n🔎 找到PDF文件: {len(pdf_files)}个")
        for pdf in pdf_files:
            print(f"  - {pdf.name}")
    else:
        print("⚠️ 工作区目录不存在")


def main():
    # 添加工作目录检查
    print(f"🖥️ 当前工作目录: {os.getcwd()}")
    print(f"📁 项目根目录: {BASE_DIR}")

    # 如果工作目录不是项目根目录，切换到项目根目录
    if Path(os.getcwd()) != BASE_DIR:
        print(f"⚠️ 工作目录不是项目根目录，正在切换...")
        os.chdir(BASE_DIR)
        print(f"✅ 新工作目录: {os.getcwd()}")

    # 验证工作区路径
    print(f"🔍 工作区验证:")
    print(f"配置路径: {WORKSPACE_DIR}")
    print(f"绝对路径: {WORKSPACE_DIR.resolve()}")
    print(f"是否存在: {WORKSPACE_DIR.exists()}")

    # 如果工作区不存在则创建
    if not WORKSPACE_DIR.exists():
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        print(f"✅ 已创建工作区: {WORKSPACE_DIR}")

    # ...后续初始化代码...


def process_query_safely(user_query: str, api_client, tool_executor, prompt_builder, context: dict) -> None:
    """安全处理用户查询，包含完整的错误处理和上下文管理"""
    print(f"\n🔍 处理查询: {user_query}")
    print("-" * 50)

    # 检查上下文状态
    if context.get("awaiting_index_selection"):
        try:
            index = int(user_query)
            # 执行删除操作
            tool_result = tool_executor.execute(
                "schedule_tools.remove_schedule",
                {"index": index}
            )

            # 清除上下文
            context.pop("awaiting_index_selection", None)

            # 处理结果
            if tool_result["success"]:
                print(f"✅ 日程删除成功: {tool_result.get('message', '')}")
            else:
                print(f"❌ 删除失败: {tool_result.get('error', '未知错误')}")
            return
        except ValueError:
            print("⚠️ 请输入有效的索引数字")
            return

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

                # 安全记录参数
                try:
                    args_str = json.dumps(args, ensure_ascii=False)
                    if len(args_str) > 100:
                        print("参数: " + args_str[:100] + "...")
                    else:
                        print(f"参数: {args_str}")
                except:
                    print("⚠️ 无法序列化参数")
                try:
                    args_str = json.dumps(args, ensure_ascii=False)
                    if len(args_str) > 100:
                        print("参数: " + args_str[:100] + "...")
                    else:
                        print(f"参数: {args_str}")
                except Exception as e:
                    print(f"⚠️ 参数序列化失败: {str(e)}")
                # 安全执行工具
                try:
                    tool_result = tool_executor.execute(action, args)
                except Exception as e:
                    print(f"❌ 工具执行出错: {str(e)}")
                    # 添加到对话历史
                    conversation_history.append({
                        "role": "user",
                        "content": f"工具执行出错: {str(e)}\n\n请根据这个错误继续处理任务。"
                    })
                    continue

                # 处理工具结果
                if tool_result["success"]:
                    # 安全格式化工具结果
                    try:
                        formatted_result = tool_executor.format_tool_result(action, tool_result)
                    except Exception as e:
                        print(f"⚠️ 格式化结果失败: {str(e)}")
                        formatted_result = str(tool_result)

                    print("✅ 工具执行成功")
                    print(formatted_result)

                    # 检查是否是最终答案（列表文件）
                    if action == "file_tools.list_files" and tool_result.get("is_final_answer", False):
                        print("\n" + "=" * 50)
                        print("✅ 任务完成!")
                        print("=" * 50)
                        print("\n📋 最终报告:")
                        print(formatted_result)
                        return  # 直接结束任务

                    # 处理多匹配情况（日程删除）
                    if action == "schedule_tools.remove_schedule_by_description" and "matches" in tool_result:
                        # 设置上下文状态
                        context["awaiting_index_selection"] = True

                        # 显示匹配列表
                        print("\n🔍 找到多个匹配的日程:")
                        for match in tool_result["matches"]:
                            print(f"  [{match['index']}] {match['event']} @ {match['event_time']}")
                        print("📝 请输入要删除的日程索引（例如: 0）")
                        return  # 结束当前处理，等待用户输入

                    # 添加到对话历史
                    conversation_history = prompt_builder.add_tool_result_to_history(
                        conversation_history,
                        {"formatted_result": formatted_result}
                    )

                    # 获取结果预览
                    if isinstance(formatted_result, str) and len(formatted_result) > 200:
                        print(f"📄 结果预览: {formatted_result[:200]}...")
                    elif formatted_result:
                        print(f"📄 结果预览: {formatted_result}")

                    # 将结果添加到对话历史
                    conversation_history.append({
                        "role": "user",
                        "content": f"工具执行结果:\n{formatted_result}\n\n请根据这个结果继续处理任务。如果任务已完成，请给出最终答案。"
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
            traceback.print_exc()
            break

    if step >= MAX_EXECUTION_STEPS:
        print(f"\n⚠️ 达到最大步骤限制 ({MAX_EXECUTION_STEPS})")


def main():
    """主函数"""
    print("=" * 60)
    print("🤖 AI文件助手 - 健壮版本")
    print("=" * 60)
    tool_executor = ToolExecutor()
    prompt_builder = PromptBuilder(tool_executor)

    notification_service = NotificationService(tool_executor)
    notification_service.start()
    print("🔔 通知服务已启动")
    print("✅ 所有组件初始化完成!")
    print(f"✅ 工具执行器初始化完成，加载工具: {', '.join(tool_executor.get_tool_info().keys())}")
    # 检查API密钥
    if not ZHIPU_API_KEY or ZHIPU_API_KEY == "your_actual_api_key_here":
        print("❌ 请先在 .env 文件中设置 ZHIPU_API_KEY")
        api_key = input("请输入智谱AI API密钥: ").strip()
        if api_key:
            os.environ["ZHIPU_API_KEY"] = api_key
        else:
            print("程序退出")
            return

    notification_service = None
    context = {}  # 全局上下文字典

    try:
        # 初始化组件
        print("🔧 初始化组件...")
        api_client = APIClientFactory.create_client("zhipu")
        tool_executor = ToolExecutor()
        prompt_builder = PromptBuilder(tool_executor)

        # 启动通知服务
        notification_service = NotificationService(tool_executor)
        notification_service.start()
        print("🔔 通知服务已启动")

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

                # 在 main.py 的交互循环部分添加
                if user_input.lower() in ['tools', 'tl']:
                    tool_info = tool_executor.get_tool_info()
                    print("\n🛠️ 可用工具:")
                    for name, info in tool_info.items():
                        print(f"  - {name}: {info['description']}")
                        for action, params in info.get("parameters", {}).items():
                            print(f"    • {action}:")
                            for param, details in params.items():
                                param_desc = f"      {param} ({details['type']})"
                                if details.get("optional", False):
                                    param_desc += " [可选]"
                                if "default" in details:
                                    param_desc += f" 默认值: {details['default']}"
                                print(param_desc)
                    continue

                # 在main.py的交互循环中添加
                if user_input.lower() in ['diagnose', 'diag']:
                    check_workspace()
                    continue

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 再见!")
                    break
                # 在交互命令中添加
                if user_input.lower() in ['config', 'cfg']:
                    from config import WORKSPACE_DIR, ALLOWED_EXTENSIONS
                    print("\n⚙️ 系统配置:")
                    print(f"工作区路径: {WORKSPACE_DIR}")
                    print(f"绝对路径: {WORKSPACE_DIR.resolve()}")
                    print(f"允许的文件扩展名: {', '.join(ALLOWED_EXTENSIONS)}")
                    # 检查路径是否存在
                    print(f"工作区存在: {WORKSPACE_DIR.exists()}")
                    if WORKSPACE_DIR.exists():
                        print(f"工作区是目录: {WORKSPACE_DIR.is_dir()}")
                    continue


                if user_input.lower() in ['schedules', 'sch']:
                    result = tool_executor.execute("schedule_tools.list_schedules", {})
                    if result.get("success"):
                        print("\n📅 当前日程:")
                        for s in result.get("schedules", []):
                            print(f"  - [{s['index']}] {s['event']} @ {s['event_time']}")
                    else:
                        print(f"❌ 获取日程失败: {result.get('error', '未知错误')}")
                    continue

                if user_input.lower() in ['help', '?']:
                    print("\n📋 可用命令:")
                    print("  help, ?      - 显示帮助")
                    print("  files, ls    - 列出文件")
                    print("  quit, exit, q - 退出")
                    print("  tools, tl    - 列出可用工具")
                    print("  config, cfg  - 查看系统配置")
                    print("  diagnose, diag - 诊断工作区")
                    print("  schedules, sch - 查看当前日程")
                    continue

                if user_input.lower() in ['files', 'ls']:
                    result = tool_executor.execute("file_tools.list_files", {})
                    print(f"\n{result.get('formatted_result', '无结果')}")
                    continue

                # 处理用户查询
                process_query_safely(user_input, api_client, tool_executor, prompt_builder, context)

            except KeyboardInterrupt:
                print("\n\n⏹️ 操作被用户中断")
                break
            except Exception as e:
                print(f"❌ 错误: {e}")

    except Exception as e:
        print(f"❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 确保通知服务停止
        if notification_service:
            notification_service.stop()
            print("🔕 通知服务已停止")

if __name__ == "__main__":
    main()
