# core/base_skill.py
"""
基础技能抽象类 - 增强版
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Tuple
import inspect
import json


class Skill(ABC):
    """Skill抽象基类 - 增强用户体验"""
    
    def __init__(self):
        self.skill_id = self.__class__.__name__.lower().replace('skill', '')
        self.name = "未命名技能"
        self.version = "1.0.0"
        self.description = "技能描述"
        self.author = "未知"
        self.category = ["通用"]
        self.tags = []  # 用于匹配的关键词
        self.icon = ""  # 技能图标
        
        # 用户体验配置
        self.user_experience_config = {
            "auto_finalize": True,  # 是否自动生成最终答案
            "friendly_format": True,  # 是否返回友好格式
            "max_result_length": 1000,  # 结果最大长度
        }
    
    @abstractmethod
    def execute(self, function_name: str, **kwargs) -> Any:
        """执行技能的具体功能"""
        pass
    
    def get_manifest(self) -> Dict[str, Any]:
        """获取技能清单（结构化定义）"""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "category": self.category,
            "tags": self.tags,
            "icon": self.icon,
            "functions": self.get_functions(),
            "examples": self.get_examples(),
            "requirements": self.get_requirements(),
            "safety_rules": self.get_safety_rules(),
            "ux_config": self.user_experience_config,
        }
    
    def get_functions(self) -> List[Dict[str, Any]]:
        """获取技能支持的功能列表"""
        functions = []
        
        # 查找所有以 func_ 开头的方法
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if name.startswith("func_"):
                # 获取函数签名和文档
                func_info = {
                    "name": name[5:],  # 去掉"func_"前缀
                    "description": method.__doc__ or "无描述",
                    "parameters": self._extract_parameters(method),
                    "user_intent_examples": self._get_intent_examples(name[5:]),
                }
                functions.append(func_info)
        
        return functions
    
    def _extract_parameters(self, method: Callable) -> Dict[str, Dict[str, Any]]:
        """从函数签名提取参数信息"""
        sig = inspect.signature(method)
        params = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            param_info = {
                "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "any",
                "description": "",
                "optional": param.default != inspect.Parameter.empty,
            }
            
            if param.default != inspect.Parameter.empty:
                param_info["default"] = param.default
            
            params[param_name] = param_info
        
        return params
    
    def _get_intent_examples(self, function_name: str) -> List[Dict[str, str]]:
        """获取用户意图示例（用于AI理解）"""
        examples = {
            "list_files": [
                {"user": "列出所有文件", "intent": "用户想要查看工作区中的所有文件"},
                {"user": "显示当前目录", "intent": "用户想要查看当前目录的文件列表"},
                {"user": "工作区有哪些文件", "intent": "用户想要查看工作区的文件"},
            ],
            "read_file": [
                {"user": "读取report.md", "intent": "用户想要读取指定文件的内容"},
                {"user": "打开这个文件", "intent": "用户想要查看文件内容"},
            ],
            "list_schedules": [
                {"user": "查看日程", "intent": "用户想要查看所有的日程安排"},
                {"user": "今天有什么安排", "intent": "用户想要查看今天的日程"},
            ],
            "add_schedule": [
                {"user": "添加明天10点的会议", "intent": "用户想要添加一个新的日程"},
                {"user": "提醒我下午开会", "intent": "用户想要设置一个提醒"},
            ],
        }
        
        return examples.get(function_name, [])
    
    def get_examples(self) -> List[Dict[str, str]]:
        """获取使用示例"""
        return []
    
    def get_requirements(self) -> List[str]:
        """获取依赖要求"""
        return []
    
    def get_safety_rules(self) -> List[str]:
        """获取安全规则"""
        return []
    
    def validate_input(self, function_name: str, **kwargs) -> bool:
        """验证输入参数"""
        return True
    
    def format_result(self, result: Any, user_query: str = "") -> Dict[str, Any]:
        """格式化结果，返回统一格式"""
        if isinstance(result, dict) and "success" in result:
            # 已经是统一格式
            formatted = result.copy()
        else:
            # 转换为统一格式
            formatted = {
                "success": True,
                "data": result
            }
        
        # 添加用户体验增强
        formatted.update(self._enhance_user_experience(formatted, user_query))
        
        return formatted
    
    def _enhance_user_experience(self, result: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """增强用户体验"""
        enhanced = {}
        
        # 自动生成友好消息
        if self.user_experience_config.get("friendly_format", True):
            friendly_message = self._generate_friendly_message(result, user_query)
            if friendly_message:
                enhanced["friendly_message"] = friendly_message
        
        # 如果自动完成，添加完成标志
        if self.user_experience_config.get("auto_finalize", True) and result.get("success", False):
            enhanced["is_final_answer"] = True
        
        return enhanced
    
    def _generate_friendly_message(self, result: Dict[str, Any], user_query: str) -> str:
        """生成友好消息（子类可重写）"""
        if not result.get("success", False):
            error = result.get("error", "未知错误")
            return f"❌ 操作失败: {error}"
        
        # 默认实现
        if "formatted_result" in result:
            return result["formatted_result"]
        
        return "✅ 操作成功"
    
    def get_system_prompt_section(self) -> str:
        """返回技能在系统提示中的描述部分"""
        section = f"## {self.icon} {self.name} (ID: {self.skill_id})\n"
        section += f"{self.description}\n\n"
        
        functions = self.get_functions()
        if functions:
            section += "**可用功能:**\n"
            for func in functions:
                section += f"- {func['name']}: {func['description']}\n"
                
                # 添加意图示例
                examples = func.get('user_intent_examples', [])
                if examples:
                    section += "  用户可能这样说:\n"
                    for ex in examples[:2]:  # 只显示前2个
                        section += f"  - \"{ex['user']}\" ({ex['intent']})\n"
        
        return section