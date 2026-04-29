from typing import List, Dict, Any
from datetime import datetime, timedelta
from config import SYSTEM_PROMPT, WORKSPACE_DIR
from core.tool_executor import ToolExecutor


class PromptBuilder:
    """提示词构建器"""

    def __init__(self, tool_executor: ToolExecutor = None):
        self.tool_executor = tool_executor or ToolExecutor()

    def build_system_prompt(self, user_query: str = None) -> str:
        """构建系统提示词（适配模块化工具）"""
        # 获取当前时间
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        today_date = datetime.now().strftime("%Y-%m-%d")
        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        # 获取工具信息
        tool_info = self.tool_executor.get_tool_info()

        # 构建详细的工具描述
        tools_description = []
        for tool_name, info in tool_info.items():
            # 工具名称和描述
            tool_desc = f"🔧 {tool_name}: {info['description']}\n"

            # 工具参数描述
            for action, params in info.get("parameters", {}).items():
                tool_desc += f"  - {action}:\n"
                for param_name, param_info in params.items():
                    param_desc = f"    • {param_name} ({param_info['type']})"
                    if param_info.get("optional", False):
                        param_desc += " [可选]"
                    if "default" in param_info:
                        param_desc += f" 默认值: {param_info['default']}"
                    param_desc += f": {param_info.get('description', '')}"
                    tool_desc += param_desc + "\n"

            tools_description.append(tool_desc)

        tools_section = "\n".join(tools_description)

        # 记忆系统说明
        memory_system_instructions = """
## 📋 记忆系统使用指南
您拥有一个三层记忆系统：
1. 短期记忆：存储最近5轮对话
2. 中期记忆：存储重要对话的压缩摘要
3. 长期记忆：存储所有对话，支持语义检索

### 🧠 记忆使用规则：
1. 在每次对话开始时，会看到"召回的记忆"部分
2. 用户询问历史信息时，首先查看记忆系统
3. 基于记忆中的信息直接回答问题
4. 仅在记忆中没有相关信息时，才考虑调用工具
5. 不要为了回忆历史而调用工具（如查看文件、日程）

### 🔄 记忆处理流程
当您看到"召回的记忆"时，按以下流程处理：
1. **首先评估记忆的相关性**
   - 如果记忆与用户问题高度相关 → 使用记忆
   - 如果记忆部分相关 → 结合记忆和工具
   - 如果记忆不相关 → 忽略记忆

2. **记忆与工具查询的关系**
   - 记忆是用户的**口头表达**
   - 工具查询是系统的**正式记录**
   - 两者可能不一致，以记忆为参考，以工具为权威

3. **如何处理矛盾情况**
   - 记忆中有信息，工具查询为空 → 回答："根据我们的对话，您提到过...，但尚未正式安排。"
   - 记忆和工具结果都为空 → 回答没有相关信息
   - 记忆和工具结果都为空 → 回答没有相关信息
   - 记忆为空，工具有结果 → 使用工具结果

### 📝 记忆使用示例
用户：我六月份有什么安排吗？

正确做法：
1. 查看记忆："用户: 我打算在六月参加华为的开发者大会"
2. 查看工具：schedule_tools.list_schedules
3. 对比结果：
   - 记忆：用户提到六月参加华为大会
   - 工具：没有安排
4. 回答："根据我们的对话，您提到过打算在六月参加华为的开发者大会，但我的日程工具中没有找到相关安排。您需要我帮您把这个安排添加到日程中吗？"

错误做法：
1. 只看工具结果（空）
2. 回答："您在六月份没有安排。"

### ⚠️ 重要规则
1. **记忆是参考，不是事实**：用户说过的不等于已安排
2. **工具是权威记录**：日程工具中的才是正式安排
3. **整合回答**：当记忆和工具不一致时，说明情况并提供帮助
4. **不要忽略记忆**：即使工具结果为空，也要提及相关记忆

### 🔄 记忆与工具调用关系：
- 记忆系统 → 存储和检索对话内容
- 工具系统 → 执行具体操作（文件、日程等）
- 不要混淆使用：用记忆回答"记得什么"，用工具执行"做什么"
"""

        # 增强的系统提示词
        enhanced_system_prompt = f"""# 🤖 AI助手 - 系统指令
当前系统时间：{current_time}

## 🧠 记忆系统
{memory_system_instructions}

## 🛠️ 可用工具
您可以调用以下工具完成任务：

{tools_section}

        时间解析规则:
        1. 用户提到"今天"、"今晚"时，使用当前日期：{today_date}
        2. 用户提到"明天"时，使用明天日期：{tomorrow_date}
        3. 必须将时间转换为ISO 8601格式：YYYY-MM-DDTHH:MM
        4. 确保时间必须是未来时间

        工作流程:
        1. 当用户要求总结特定类型文件时：
           - 先调用 file_tools.list_files 查看文件
           - 添加 exclude_extensions 参数过滤文件类型
           
           -对每个文件调用 file_tools.read_file 读取内容
           - 调用 file_tools.summarize_content 总结文件内容
        2. 当用户要求管理日程时：
           - 添加日程：调用 schedule_tools.add_schedule
           - 查看日程：调用 schedule_tools.list_schedules
           - 删除日程：调用 schedule_tools.remove_schedule_by_description（通过描述删除）
           - 或调用 schedule_tools.remove_schedule（通过索引删除）
        3. 删除日程流程示例：
           用户: 删除今晚的会议
           → 调用 schedule_tools.remove_schedule_by_description(description="会议")
           → 如果找到唯一匹配项，自动删除
           → 如果找到多个匹配项，返回列表并提示用户选择索引
           → 用户输入索引后，调用 schedule_tools.remove_schedule(index=用户选择的索引)
        4. 列出文件流程示例：
           用户: file
           → 调用 file_tools.list_files
           → 返回最终答案: {{"thought": "已列出文件", "final_answer": "文件列表: ..."}}

        明确规则:
        1. 当用户仅要求列出文件（如'file'、'ls'）时：
           - 调用 file_tools.list_files
           - 返回最终答案: {{"thought": "解释", "final_answer": "文件列表: ..."}}
        2. 任务完成时必须返回 final_answer
        3. 每次只能调用一个工具

        重要规则:
        1. 每次只能调用一个工具
        2. 调用工具时返回JSON格式: {{"thought": "思考过程", "action": "工具名.方法", "args": {{"参数": "值"}}}}
        3. 完成任务时返回: {{"thought": "解释", "final_answer": "最终答案"}}
        4. 如果遇到错误，尝试解决或返回最终答案

        严格格式要求：
        1. 当调用工具时，必须返回且仅返回以下JSON格式：
        {{
          "thought": "思考过程",
          "action": "工具名.方法",
          "args": {{参数键值对}}
        }}

        2. 当任务完成时，必须返回且仅返回以下JSON格式：
        {{
          "thought": "思考过程",
          "final_answer": "最终答案"
        }}

        3. 禁止返回任何其他格式（包括自然语言、混合格式等）
        4. 如果返回非JSON内容，系统将无法解析并导致任务失败

        重要补充规则:
        1. 当传递长文本参数时，必须确保JSON格式正确
        2. 文本中的特殊字符（换行符、引号等）需要正确转义
        3. 如果遇到JSON解析错误，尝试简化参数内容
        4. 日程管理必须使用schedule_tools工具
        5. 添加日程时必须包含event和event_time参数
        6. 查看日程时默认只显示未来日程
        7. 删除日程时优先使用remove_schedule_by_description方法

        注意: 不要在一个步骤中做多件事。按步骤来。

        当前任务: {user_query or "未指定"}"""

        return enhanced_system_prompt

    def build_messages(self, user_query: str, conversation_history: List[Dict[str, str]] = None) -> List[
        Dict[str, str]]:
        """构建对话消息列表"""
        messages = []

        # 添加系统提示词
        messages.append({
            "role": "system",
            "content": self.build_system_prompt(user_query)
        })

        # 添加历史对话
        if conversation_history:
            # 过滤掉系统消息（避免重复）
            for msg in conversation_history:
                if msg.get("role") != "system":
                    messages.append(msg)

        # 添加当前用户查询
        messages.append({
            "role": "user",
            "content": user_query
        })

        return messages

    def add_tool_result_to_history(self, conversation_history: List[Dict[str, str]],
                                   tool_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """将工具执行结果添加到对话历史"""
        if not conversation_history:
            conversation_history = []

        # 添加工具执行结果
        conversation_history.append({
            "role": "user",
            "content": f"工具执行结果:\n{tool_result.get('formatted_result', '无结果')}\n\n请根据这个结果继续处理任务。如果任务已完成，请给出最终答案。"
        })

        return conversation_history