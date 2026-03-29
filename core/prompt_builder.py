import json
from typing import List, Dict, Any
from config import SYSTEM_PROMPT, WORKSPACE_DIR
from core.tool_executor import ToolExecutor


class PromptBuilder:

    def __init__(self, tool_executor: ToolExecutor = None):
        self.tool_executor = tool_executor or ToolExecutor()
    def build_system_prompt(self, user_query: str = None) -> str:
        """构建系统提示词"""
        # 获取工具信息
        tool_info = self.tool_executor.get_tool_info()
        tools_description = []
        for tool_name, info in tool_info["tools"].items():
            params_desc = []
            for param_name, param_info in info["parameters"].items():
                param_desc = f"    - {param_name} ({param_info['type']})"
                if param_info.get("optional", False):
                    param_desc += f" [可选]"
                if "default" in param_info:
                    param_desc += f" 默认值: {param_info['default']}"
                param_desc += f": {param_info['description']}"
                params_desc.append(param_desc)

            tools_description.append(f"{tool_name}: {info['description']}")
            if params_desc:
                tools_description.append("\n".join(params_desc))
            tools_description.append("") 

        tools_section = "\n".join(tools_description)
        enhanced_system_prompt = f"""你是一个AI助手，可以操作文件。你有以下能力:

    {tools_section}

    工作流程:
    1. 当用户要求总结文件时，先调用 list_files 查看有哪些文件
    2. 对每个文件调用 read_file 读取内容
    3. 调用 summarize_content 总结文件内容
    4. 最后生成综合报告

    重要规则:
    1. 每次只能调用一个工具
    2. 调用工具时返回JSON格式: {{"thought": "解释", "action": "工具名", "args": {{"参数": "值"}}}}
    3. 完成任务时返回: {{"thought": "解释", "final_answer": "最终答案"}}
    4. 如果遇到错误，尝试解决或返回最终答案
    重要补充规则:
    1. 当传递长文本参数时，必须确保JSON格式正确
    2. 文本中的特殊字符（换行符、引号等）需要正确转义
    3. 如果遇到JSON解析错误，尝试简化参数内容
    4. 文件内容总结必须使用summarize_content工具

    注意: 不要在一个步骤中做多件事。按步骤来。

    当前任务: {user_query or "未指定"}"""

        return enhanced_system_prompt

    def build_messages(self, user_query: str, conversation_history: List[Dict[str, str]] = None) -> List[
        Dict[str, str]]:
        """构建对话消息列表"""
        messages = []

        messages.append({
            "role": "system",
            "content": self.build_system_prompt(user_query)
        })

        if conversation_history:
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
