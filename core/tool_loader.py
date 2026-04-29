import os
import importlib
import sys
from typing import Dict, Any
from core.tool_interface import ToolInterface


class ToolLoader:
    """动态加载工具"""

    def __init__(self, tools_dir="tools"):
        """初始化工具加载器"""
        self.tools = {}
        self.tools_dir = tools_dir  # 保存目录路径
        self.load_tools()  # 调用时不需要参数

    def load_tools(self) -> None:
        """加载指定目录下的所有工具"""
        directory = self.tools_dir

        print(f"🛠️ 开始加载工具，目录: {directory}")
        # 确保目录存在
        if not os.path.exists(directory):
            print(f"⚠️ 工具目录不存在: {directory}")
            return

        # 添加目录到Python路径
        sys.path.append(os.path.abspath(directory))

        for filename in os.listdir(directory):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = filename[:-3]
                print(f"🔍 尝试加载工具模块: {module_name}")
                try:
                    module = importlib.import_module(f"tools.{module_name}")
                    print(f"✅ 成功导入模块: {module_name}")
                    self._register_tools(module)
                except ImportError as e:
                    print(f"❌ 导入失败: {filename} - {str(e)}")
                except Exception as e:
                    print(f"⚠️ 注册工具时出错: {str(e)}")

    def _register_tools(self, module) -> None:
        """注册模块中的所有工具"""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, ToolInterface) and attr != ToolInterface:
                print(f"🔧 发现工具类: {attr_name}")
                try:
                    tool_instance = attr()
                    tool_name = tool_instance.metadata["name"]
                    print(f"✅ 注册工具: {tool_name}")
                    self.tools[tool_name] = {
                        "instance": tool_instance,
                        "metadata": tool_instance.metadata
                    }
                except Exception as e:
                    print(f"⚠️ 实例化工具失败: {attr_name} - {str(e)}")

    def get_tool_info(self) -> Dict[str, Any]:
        """获取所有工具信息"""
        return {
            name: info["metadata"]
            for name, info in self.tools.items()
        }

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行指定工具的操作（确保始终返回字典）"""
        try:
            if tool_name not in self.tools:
                return {
                    "success": False,
                    "error": f"未知工具: {tool_name}",
                    "available_tools": list(self.tools.keys())
                }

            tool_instance = self.tools[tool_name]["instance"]

            # 从参数中提取 action_name
            action_name = args.pop("action", None)
            if not action_name:
                return {
                    "success": False,
                    "error": "缺少操作名称 (action)"
                }

            # 检查操作是否有效
            if action_name not in tool_instance.metadata["parameters"]:
                return {
                    "success": False,
                    "error": f"工具 '{tool_name}' 不支持操作 '{action_name}'",
                    "available_actions": list(tool_instance.metadata["parameters"].keys())
                }

            # 执行工具的具体操作
            result = getattr(tool_instance, action_name)(**args)

            # 确保返回字典格式
            if isinstance(result, dict):
                return result
            else:
                return {
                    "success": True,
                    "result": result
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"工具执行异常: {str(e)}"
            }