import json
from typing import Dict, Any, Optional
from tools.file_tools import FileTools


class ToolExecutor:
    def __init__(self):
        # FileTools实例
        self.file_tools = FileTools()

        self.tools = {
            "list_files": {
                "function": self.file_tools.list_files,
                "description": "列出工作区内的文件",
                "parameters": {
                    "directory_path": {
                        "type": "string",
                        "description": "目录路径（相对于工作区根目录），可选，默认为根目录",
                        "optional": True
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "是否递归列出子目录",
                        "optional": True,
                        "default": False
                    }
                }
            },
            "read_file": {
                "function": self.file_tools.read_file,
                "description": "安全读取文件内容",
                "parameters": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径（相对于工作区根目录）",
                        "optional": False
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "最大读取行数，可选",
                        "optional": True,
                        "default": 1000
                    }
                }
            },
            "summarize_content": {
                "function": self.file_tools.summarize_content,
                "description": "使用AI总结给定的文本内容",
                "parameters": {
                    "content": {
                        "type": "string",
                        "description": "要总结的文本内容",
                        "optional": False
                    },
                    "max_length": {
                        "type": "integer",
                        "description": "总结的最大长度，可选",
                        "optional": True,
                        "default": 500
                    }
                }
            }
        }

        print(f"✅ 工具执行器初始化完成，可用工具: {', '.join(self.tools.keys())}")
    def get_tool_info(self) -> Dict[str, Any]:
        """获取所有工具信息，用于构建提示词"""
        return {
            "tools": {
                name: {
                    "description": info["description"],
                    "parameters": info["parameters"]
                }
                for name, info in self.tools.items()
            }
        }

    def execute(self, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        if action not in self.tools:
            return {
                "success": False,
                "error": f"未知的工具: {action}",
                "available_tools": list(self.tools.keys())
            }

        tool_info = self.tools[action]
        tool_func = tool_info["function"]

        try:
            validated_args = self._validate_arguments(action, args, tool_info["parameters"])

            print(f"🔧 执行 {action}，参数: {validated_args}")
            result = tool_func(**validated_args)
            if not result.get("success", False):
                print(f"❌ 工具执行失败: {result.get('error', '未知错误')}")

            # 格式化结果以便大模型理解
            formatted_result = self._format_result(action, result)

            return {
                "success": result.get("success", False),  
                "action": action,
                "args": validated_args,
                "raw_result": result,
                "formatted_result": formatted_result,
                "execution_time": None
            }

        except Exception as e:
            error_msg = f"执行工具时出错: {str(e)}"
            print(f"❌ {error_msg}")

            return {
                "success": False,
                "error": error_msg,
                "action": action,
                "args": args
            }

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

        if action == "summarize_content" and "text" in args:
            args["content"] = args.pop("text")

        for param_name, param_info in parameters.items():
            if param_name in args:
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
                    if isinstance(value, str):
                        value = value.lower() in ["true", "yes", "1"]
                    else:
                        raise ValueError(f"参数 '{param_name}' 应为布尔类型")

                validated[param_name] = value
            elif not param_info.get("optional", False):
                raise ValueError(f"缺少必需参数: {param_name}")
            else:
                if "default" in param_info:
                    validated[param_name] = param_info["default"]

        return validated

    def _format_result(self, action: str, result: Dict[str, Any]) -> str:
        """格式化工具执行结果"""
        if not result.get("success", False):
            return f"❌ 工具执行失败: {result.get('error', '未知错误')}"

        if action == "list_files":
            files = result.get("files", [])
            if not files:
                return f"📁 目录 {result.get('directory', '')} 中没有文件"

            file_list = "\n".join([f"  - {f['name']} ({f['size_human']}, {f['modified_date']})"
                                   for f in files[:10]])  # 最多显示10个文件
            if len(files) > 10:
                file_list += f"\n  ... 以及另外 {len(files) - 10} 个文件"

            return f"""📁 目录: {result.get('directory', '')}
    文件总数: {result.get('count', 0)} 个
    总大小: {result.get('total_size_human', '0B')}
    文件列表:
    {file_list}"""

        elif action == "read_file":
            content = result.get("content", "")
            file_info = f"📄 文件: {result.get('file_name', '')}\n"
            file_info += f"路径: {result.get('file_path', '')}\n"
            file_info += f"大小: {result.get('file_size', 0)} 字符\n"

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
