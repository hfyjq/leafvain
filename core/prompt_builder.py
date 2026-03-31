import json
from typing import List, Dict, Any
from config import SYSTEM_PROMPT, WORKSPACE_DIR
from core.tool_executor import ToolExecutor

class PromptBuilder:
    """提示词构建器"""

    def __init__(self, tool_executor: ToolExecutor = None):
        self.tool_executor = tool_executor or ToolExecutor()

    def build_system_prompt(self, user_query: str = None) -> str:
        """构建系统提示词（适配模块化工具）"""
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

        # 增强的系统提示词
        enhanced_system_prompt = f"""你是一个AI助手，可以调用以下工具完成任务:

{tools_section}

工作流程:
1. 当用户要求总结文件时，先调用 file_tools.list_files 查看有哪些文件
2. 对每个文件调用 file_tools.read_file 读取内容
3. 调用 file_tools.summarize_content 总结文件内容
4. 最后生成综合报告

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
4. 文件内容总结必须使用file_tools.summarize_content工具
5. 当文件超过10KB时，必须使用file_tools.summarize_large_file工具
6. 禁止对大文件直接调用read_file+summarize_content组合

注意: 不要在一个步骤中做多件事。按步骤来。

当前任务: {user_query or "未指定"}"""

        return enhanced_system_prompt

    # 其他方法保持不变...

    def build_messages(self, user_query: str, conversation_history: List[Dict[str, str]] = None) -> List[
        Dict[str, str]]:
        """构建对话消息列表"""
        messages = []

        # 添加系统提示词
        messages.append({
            "role": "system",
            "content": self.build_system_prompt(user_query)
        })


        if conversation_history:
            # 过滤掉系统消息（避免重复）
            for msg in conversation_history:
                if msg.get("role") != "system":
                    messages.append(msg)
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
        conversation_history.append({
            "role": "user",
            "content": f"工具执行结果:\n{tool_result.get('formatted_result', '无结果')}\n\n请根据这个结果继续处理任务。如果任务已完成，请给出最终答案。"
        })

        return conversation_history
