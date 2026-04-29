# skills/template_skill.py
"""
标准Skill模板
所有新技能应基于此模板创建，确保一致性和可维护性。
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
import inspect

# 尝试导入Skill基类
try:
    from core.base_skill import Skill
except ImportError:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.base_skill import Skill


class TemplateSkill(Skill):
    """
    标准Skill模板类

    创建新技能时，请按照以下步骤：
    1. 复制此文件，重命名为 {skill_name}_skill.py
    2. 修改类名为 {SkillName}Skill（PascalCase）
    3. 按照TODO注释修改各个部分
    4. 实现所需的功能方法
    5. 在__init__中初始化技能所需资源
    6. 创建测试文件验证功能
    """

    def __init__(self):
        # 调用父类初始化
        super().__init__()

        # ========== 基本信息配置 ==========
        # TODO: 修改以下基本信息
        self.skill_id = "template"  # 技能ID，使用英文，小写，不含空格
        self.name = "技能模板"  # 技能显示名称
        self.version = "1.0.0"  # 技能版本，遵循语义化版本
        self.description = "这是一个技能模板，描述了技能的功能和用途。"  # 技能详细描述
        self.author = "开发者名称"  # 开发者名称
        self.category = ["工具", "示例"]  # 技能分类列表
        self.tags = ["模板", "示例"]  # 技能标签列表，用于匹配用户查询
        self.icon = "🛠️"  # 技能图标

        # ========== 用户体验配置 ==========
        self.user_experience_config = {
            "auto_finalize": True,  # 是否自动生成最终答案
            "friendly_format": True,  # 是否返回友好格式
            "max_result_length": 1000,  # 结果最大长度
            "show_usage_hints": True,  # 是否显示使用提示
        }

        # ========== 技能配置 ==========
        # TODO: 添加技能特定的配置
        self.config = {
            "timeout": 30,  # 执行超时时间（秒）
            "max_retries": 3,  # 最大重试次数
            "cache_results": True,  # 是否缓存结果
        }

        # ========== 内部状态 ==========
        self._initialized = False
        self._dependencies_checked = False
        self._resources = {}  # 存储技能资源

        # ========== 初始化技能 ==========
        self._initialize_skill()

    def _initialize_skill(self) -> None:
        """
        初始化技能

        在这里初始化技能所需的资源，如：
        - 加载配置文件
        - 初始化外部库
        - 建立数据库连接
        - 检查依赖
        """
        try:
            if self._initialized:
                return

            print(f"🔧 初始化技能: {self.name} v{self.version}")

            # 1. 检查依赖
            self._check_dependencies()

            # 2. 加载配置
            self._load_configuration()

            # 3. 初始化资源
            self._initialize_resources()

            # 4. 验证功能
            self._validate_functions()

            self._initialized = True
            print(f"✅ 技能初始化完成: {self.name}")

        except Exception as e:
            print(f"❌ 技能初始化失败: {self.name} - {e}")
            raise

    def _check_dependencies(self) -> None:
        """检查技能依赖"""
        if self._dependencies_checked:
            return

        requirements = self.get_requirements()
        if not requirements:
            self._dependencies_checked = True
            return

        print(f"  📦 检查依赖 ({len(requirements)} 个)...")

        for req in requirements:
            try:
                # 尝试导入
                __import__(req.split('>=')[0].split('==')[0])
                print(f"    ✅ {req}")
            except ImportError as e:
                print(f"    ❌ 缺少依赖: {req}")
                print(f"      错误: {e}")
                # 可以在这里抛出异常或尝试自动安装

        self._dependencies_checked = True

    def _load_configuration(self) -> None:
        """加载技能配置"""
        # TODO: 从文件或环境变量加载配置
        pass

    def _initialize_resources(self) -> None:
        """初始化技能资源"""
        # TODO: 初始化技能所需的资源
        pass

    def _validate_functions(self) -> None:
        """验证功能方法"""
        functions = self.get_functions()
        if not functions:
            print(f"  ⚠️ 技能没有定义任何功能")

    def execute(self, function_name: str, **kwargs) -> Any:
        """
        执行技能的具体功能

        Args:
            function_name: 要执行的功能名称
            **kwargs: 功能参数

        Returns:
            执行结果，必须返回字典格式

        Raises:
            ValueError: 如果功能不存在
            Exception: 执行过程中的异常
        """
        # 确保技能已初始化
        if not self._initialized:
            self._initialize_skill()

        # 查找功能方法
        method_name = f"func_{function_name}"
        if not hasattr(self, method_name):
            raise ValueError(f"功能不存在: {function_name}")

        method = getattr(self, method_name)

        # 验证参数
        if not self.validate_input(function_name, **kwargs):
            return {
                "success": False,
                "error": f"参数验证失败: {function_name}",
                "function": function_name,
                "timestamp": datetime.now().isoformat()
            }

        try:
            # 执行功能
            print(f"  🚀 执行功能: {function_name}")
            result = method(**kwargs)

            # 确保结果是字典
            if not isinstance(result, dict):
                result = {
                    "success": True,
                    "data": result,
                    "function": function_name,
                    "timestamp": datetime.now().isoformat()
                }

            # 添加技能信息
            result["skill_id"] = self.skill_id
            result["skill_name"] = self.name

            # 格式化结果
            formatted_result = self.format_result(result)
            if formatted_result and "formatted_result" not in result:
                result["formatted_result"] = formatted_result

            return result

        except Exception as e:
            print(f"  ❌ 执行失败: {function_name} - {e}")
            return {
                "success": False,
                "error": f"执行失败: {str(e)}",
                "function": function_name,
                "skill_id": self.skill_id,
                "timestamp": datetime.now().isoformat()
            }

    def validate_input(self, function_name: str, **kwargs) -> bool:
        """
        验证输入参数

        子类可以重写此方法以提供更严格的验证

        Args:
            function_name: 功能名称
            **kwargs: 输入参数

        Returns:
            bool: 是否验证通过
        """
        # 默认实现：检查必要参数是否存在
        method_name = f"func_{function_name}"
        if not hasattr(self, method_name):
            return False

        method = getattr(self, method_name)
        sig = inspect.signature(method)

        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            # 检查必填参数
            if param.default == inspect.Parameter.empty and param_name not in kwargs:
                print(f"  ❌ 缺少必填参数: {param_name}")
                return False

        return True

    def format_result(self, result: Any) -> str:
        """
        格式化结果

        Args:
            result: 原始结果

        Returns:
            str: 格式化后的字符串
        """
        if isinstance(result, dict):
            # 如果已经有格式化结果，直接使用
            if "formatted_result" in result:
                return result["formatted_result"]

            # 生成友好消息
            if self.user_experience_config.get("friendly_format", True):
                return self._generate_friendly_message(result, "")

        # 默认格式化
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, indent=2)

        return str(result)

    def _generate_friendly_message(self, result: Dict[str, Any], user_query: str) -> str:
        """生成友好消息（可重写）"""
        if not result.get("success", False):
            error = result.get("error", "未知错误")
            return f"❌ 操作失败: {error}"

        # 默认友好消息
        if "formatted_result" in result:
            return result["formatted_result"]

        if "data" in result:
            data = result["data"]
            if isinstance(data, dict) and "message" in data:
                return f"✅ {data['message']}"
            return f"✅ 操作成功: {str(data)[:200]}..."

        return "✅ 操作成功"

    # ========== 功能方法示例 ==========
    # 所有功能方法应以"func_"开头，以便自动发现

    def func_example_function(self, param1: str, param2: int = 10) -> Dict[str, Any]:
        """
        示例功能

        这是功能方法的示例，请按照此格式编写功能方法。

        Args:
            param1: 参数1的描述
            param2: 参数2的描述，默认值10

        Returns:
            包含执行结果的字典，必须包含"success"字段

        Examples:
            >>> skill.func_example_function("test", 5)
            {"success": True, "data": "处理完成: test 次数: 5"}
        """
        try:
            # 1. 参数验证
            if not param1 or len(param1) < 3:
                return {
                    "success": False,
                    "error": "参数param1长度不能小于3"
                }

            # 2. 执行业务逻辑
            result = f"处理完成: {param1} 次数: {param2}"

            # 3. 返回格式化的结果
            return {
                "success": True,
                "data": result,
                "message": "示例功能执行成功",
                "formatted_result": f"✅ 示例功能执行成功: {result}",
                "execution_time": datetime.now().isoformat(),
                "is_final_answer": True,  # 如果是最终结果，设置为True
            }

        except Exception as e:
            # 4. 异常处理
            return {
                "success": False,
                "error": f"执行失败: {str(e)}",
                "formatted_result": f"❌ 示例功能执行失败: {str(e)}"
            }

    def func_another_function(self, query: str) -> Dict[str, Any]:
        """
        另一个功能示例

        Args:
            query: 查询字符串

        Returns:
            查询结果
        """
        # 功能实现...
        return {
            "success": True,
            "data": {"result": f"查询: {query}"},
            "formatted_result": f"🔍 查询结果: {query}"
        }

    # ========== 技能元数据方法 ==========

    def get_examples(self) -> List[Dict[str, str]]:
        """
        获取使用示例

        返回用户如何使用此技能的示例对话。
        这些示例会显示在帮助信息中，并用于AI训练。
        """
        return [
            {
                "user": "示例查询1",
                "assistant": "示例回答1，说明技能如何被调用",
                "function": "example_function",  # 可选：关联的功能
                "args": {"param1": "值1", "param2": 5}  # 可选：示例参数
            },
            {
                "user": "示例查询2",
                "assistant": "示例回答2，展示技能的不同功能",
                "function": "another_function",
                "args": {"query": "测试查询"}
            }
        ]

    def get_requirements(self) -> List[str]:
        """
        获取依赖要求

        返回此技能所需的Python包列表。
        格式可以是: ["package_name", "package_name>=1.0.0"]
        """
        return [
            "requests",  # 常用HTTP库
            "pillow",  # 图像处理
            # 添加你的依赖...
        ]

    def get_safety_rules(self) -> List[str]:
        """
        获取安全规则

        返回此技能的安全使用规则列表。
        这些规则会显示在帮助信息中，并用于安全检查。
        """
        return [
            "仅用于合法用途",
            "不要处理敏感个人信息",
            "遵守相关法律法规",
            # 添加你的安全规则...
        ]

    def get_system_prompt_section(self) -> str:
        """
        返回技能在系统提示中的描述部分

        重写此方法以提供更详细的技能描述。
        """
        section = f"## {self.icon} {self.name} (ID: {self.skill_id})\n"
        section += f"**版本:** v{self.version}\n"
        section += f"**描述:** {self.description}\n"
        section += f"**分类:** {', '.join(self.category)}\n"
        section += f"**开发者:** {self.author}\n\n"

        # 功能列表
        functions = self.get_functions()
        if functions:
            section += "**可用功能:**\n"
            for func in functions:
                func_name = func['name']
                func_desc = func.get('description', '无描述').strip()
                section += f"- **{func_name}**: {func_desc}\n"

                # 参数说明
                params = func.get('parameters', {})
                if params:
                    section += "  参数:\n"
                    for param_name, param_info in params.items():
                        param_type = param_info.get('type', 'any')
                        optional = " (可选)" if param_info.get('optional', False) else " (必填)"
                        default = f" 默认值: {param_info['default']}" if 'default' in param_info else ""
                        section += f"  - {param_name} ({param_type}){optional}{default}\n"

        # 使用示例
        examples = self.get_examples()
        if examples and len(examples) > 0:
            section += "\n**使用示例:**\n"
            for ex in examples[:3]:  # 只显示前3个示例
                section += f"- 用户: {ex.get('user', '')}\n"
                section += f"  AI: 调用 {self.skill_id}.{ex.get('function', 'function')}\n"

        return section

    # ========== 生命周期方法 ==========

    def on_load(self):
        """技能加载时调用"""
        print(f"🔧 技能 {self.name} 已加载")

    def on_unload(self):
        """技能卸载时调用"""
        print(f"🔧 技能 {self.name} 已卸载")
        # 清理资源
        self._cleanup_resources()

    def _cleanup_resources(self):
        """清理技能资源"""
        if self._resources:
            for name, resource in self._resources.items():
                if hasattr(resource, 'close'):
                    resource.close()
            self._resources.clear()


# 快速测试
if __name__ == "__main__":
    # 创建技能实例
    skill = TemplateSkill()

    # 打印技能信息
    print(f"🔧 技能名称: {skill.name}")
    print(f"   版本: v{skill.version}")
    print(f"   描述: {skill.description}")
    print(f"   功能数: {len(skill.get_functions())}")

    # 测试功能
    print(f"\n🧪 测试功能...")
    result = skill.execute("example_function", param1="测试参数", param2=5)
    print(f"   结果: {json.dumps(result, ensure_ascii=False, indent=2)}")