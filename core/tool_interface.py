from typing import Dict, Any


class ToolInterface:
    """工具接口规范"""

    def __init__(self):
        self.metadata = {
            "name": "",  # 工具唯一标识
            "description": "",  # 工具功能描述
            "parameters": {}  # 参数规范
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        """工具执行方法"""
        raise NotImplementedError