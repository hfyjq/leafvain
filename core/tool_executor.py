import json
from typing import Dict, Any, Optional

from tools.file_tools import FileTools
from core.tool_loader import ToolLoader
from core.safety_checker import SafetyChecker


class ToolExecutor:
    """工具执行器（适配模块化）"""

    def __init__(self, tools_dir="tools"):
        self.tool_loader = ToolLoader(tools_dir)  # 传递目录参数
        self.safety_checker = SafetyChecker()
        self.tools = self.tool_loader.get_tool_info()
        print(f"✅ 工具执行器初始化完成，加载工具: {', '.join(self.tools.keys())}")

    def get_tool_info(self) -> Dict[str, Any]:
        """获取工具信息（用于提示词构建）"""
        return self.tools

    def execute(self, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        # 解析工具名和操作名（格式：工具名.操作名）
        if '.' not in action:
            return {
                "success": False,
                "error": f"无效的操作格式: {action}，应为 '工具名.操作名'"
            }

        tool_name, action_name = action.split('.', 1)

        # 安全检查
        if not SafetyChecker.validate_tool_params(tool_name, action_name, args):
            return {
                "success": False,
                "error": "参数安全检查失败"
            }

        # 将 action_name 作为参数传递
        return self.tool_loader.execute_tool(
            tool_name,
            {"action": action_name, **args}
        )
    def _validate_arguments(self, action: str, args: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证和清理参数"""
        validated = {}

        for key, value in args.items():
            if isinstance(value, str):
                # 转义控制字符和引号
                value = value.replace('\n', '\\n')
                value = value.replace('\r', '\\r')
                value = value.replace('\t', '\\t')
                value = value.replace('"', '\\"')
                args[key] = value

        # 特殊处理：允许text参数映射到content
        if action == "summarize_content" and "text" in args:
            args["content"] = args.pop("text")

        for param_name, param_info in parameters.items():
            if param_name in args:
                # 类型检查（简化版）
                value = args[param_name]
                expected_type = param_info["type"]

                if expected_type == "string" and not isinstance(value, str):
                    # 尝试转换
                    value = str(value)
                elif expected_type == "integer" and not isinstance(value, int):
                    # 尝试转换
                    try:
                        value = int(value)
                    except:
                        raise ValueError(f"参数 '{param_name}' 应为整数类型")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    # 尝试转换
                    if isinstance(value, str):
                        value = value.lower() in ["true", "yes", "1"]
                    else:
                        raise ValueError(f"参数 '{param_name}' 应为布尔类型")

                validated[param_name] = value
            elif not param_info.get("optional", False):
                raise ValueError(f"缺少必需参数: {param_name}")
            else:
                # 使用默认值
                if "default" in param_info:
                    validated[param_name] = param_info["default"]

        return validated

    def _format_result(self, action: str, result: Dict[str, Any]) -> str:
        """格式化工具执行结果（安全版）"""
        if not result.get("success", False):
            return f"❌ 工具执行失败: {result.get('error', '未知错误')}"

        if action == "list_files":
            files = result.get("files", [])
            if not files:
                return f"📁 目录 {result.get('directory', '')} 中没有文件"

            # 安全构建文件列表
            file_list = []
            for f in files[:10]:
                safe_name = f['name'].replace('{', '{{').replace('}', '}}')
                file_list.append(f"  - {safe_name} ({f['size_human']}, {f['modified_date']})")

            return """📂 目录: {}
    文件总数: {} 个
    总大小: {}
    文件列表:
    {}""".format(
                result.get('directory', ''),
                result.get('count', 0),
                result.get('total_size_human', '0B'),
                "\n".join(file_list)
            )

        # 其他工具保持不变...
        # 删除日程匹配列表格式化
        elif action == "remove_schedule_by_description":
            if "matches" in result:
                matches = result["matches"]
                match_list = "\n".join([f"  [{m['index']}] {m['event']} @ {m['event_time']}"
                                        for m in matches])
                return f"""🔍 找到多个匹配的日程:
    {match_list}
    📝 请回复要删除的日程索引（例如: 0）"""
            return result.get("message", "无匹配日程")

        # 添加最终答案标识
        if action == "list_files":
            result["is_final_answer"] = True

        # 其他工具保持不变...
        elif action == "read_file":
            content = result.get("content", "")
            file_info = f"📄 文件: {result.get('file_name', '')}\n"
            file_info += f"路径: {result.get('file_path', '')}\n"
            file_info += f"大小: {result.get('file_size', 0)} 字符\n"

            # 返回包含原始内容的格式
            return f"""{file_info}
    文件内容:
    {content}"""

        elif action == "summarize_content":
            summary = result.get("summary", "")

            return f"""📋 内容摘要
    原始长度: {result.get('original_length', 0)} 字符
    摘要长度: {result.get('summary_length', 0)} 字符
    压缩率: {result.get('compression_ratio', '0%')}
    摘要内容:
    {summary}"""

        else:
            return str(result)

    def _format_result(self, action: str, result: Dict[str, Any]) -> str:
        """格式化工具执行结果（增强版）"""
        if not result.get("success", False):
            return f"❌ 工具执行失败: {result.get('error', '未知错误')}"

        if action == "list_files":
            files = result.get("files", [])
            directories = result.get("directories", [])

            if not files and not directories:
                return f"📁 目录 {result.get('directory', '')} 中没有文件或子目录"

            # 构建文件列表
            file_list = ""
            if files:
                file_list = "📝 文件列表:\n" + "\n".join(
                    [f"  - {f['name']} ({f['size_human']}, {f['modified_date']})"
                     for f in files[:10]]  # 最多显示10个文件
                )
                if len(files) > 10:
                    file_list += f"\n  ... 以及另外 {len(files) - 10} 个文件"

            # 构建目录列表
            dir_list = ""
            if directories:
                dir_list = "\n📁 子目录列表:\n" + "\n".join(
                    [f"  - {d['name']}/" for d in directories[:5]]  # 最多显示5个子目录
                )
                if len(directories) > 5:
                    dir_list += f"\n  ... 以及另外 {len(directories) - 5} 个子目录"

            return f"""📂 目录: {result.get('directory', '')}
    文件总数: {result.get('count', 0)} 个
    总大小: {result.get('total_size_human', '0B')}
    {file_list}{dir_list}"""

        elif action == "read_file":
            content = result.get("content", "")
            file_info = f"📄 文件: {result.get('file_name', '')}\n"
            file_info += f"路径: {result.get('file_path', '')}\n"
            file_info += f"大小: {result.get('file_size', 0)} 字符\n"

            # 添加文件类型和截断信息
            if result.get("file_type"):
                file_info += f"类型: {result.get('file_type')}\n"
            if result.get("is_truncated", False):
                file_info += "⚠️ 内容已截断\n"
            if result.get("is_large_file", False):
                file_info += "⚠️ 大文件（使用智能读取）\n"

            # 返回包含原始内容的格式
            return f"""{file_info}
    文件内容:
    {content}"""

        elif action == "summarize_content":
            summary = result.get("summary", "")

            # 添加摘要元数据
            meta_info = f"原始长度: {result.get('original_length', 0)} 字符\n"
            meta_info += f"摘要长度: {result.get('summary_length', 0)} 字符\n"
            if result.get("compression_ratio"):
                meta_info += f"压缩率: {result.get('compression_ratio')}\n"

            return f"""📋 内容摘要
    {meta_info}
    摘要内容:
    {summary}"""

        else:
            # 默认返回JSON格式
            return json.dumps(result, indent=2, ensure_ascii=False)