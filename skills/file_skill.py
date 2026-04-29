"""
文件操作技能（增强版）
支持多步骤任务和上下文理解
"""
import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import datetime

# 导入现有工具
try:
    from tools.file_tools import FileTools
    from config import WORKSPACE_DIR, ALLOWED_EXTENSIONS
except ImportError as e:
    print(f"⚠️ 导入现有工具失败: {e}")


    # 模拟版本
    class FileTools:
        def list_files(self, **kwargs):
            return {"success": True, "files": [], "formatted_result": "无文件"}

        def read_file(self, **kwargs):
            return {"success": True, "content": "测试内容"}

        def summarize_content(self, **kwargs):
            return {"success": True, "summary": "测试总结"}


    WORKSPACE_DIR = "workspace"
    ALLOWED_EXTENSIONS = ['.txt', '.md', '.pdf', '.docx']

# 导入Skill基类
try:
    from core.base_skill import Skill
except ImportError:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.base_skill import Skill


class FileEnhancedSkill(Skill):
    """增强版文件操作技能 - 支持多步骤任务"""

    def __init__(self):
        super().__init__()
        self.skill_id = "file_enhanced"
        self.name = "文件操作（增强版）"
        self.version = "3.0.0"
        self.description = "这是一个增强的文件操作技能，支持列出文件、读取文件、总结内容，还能自动处理多步骤任务如总结所有文件。"
        self.author = "系统"
        self.category = ["文件", "工作区", "管理", "智能"]
        self.tags = ["文件", "文档", "读取", "总结", "智能", "多步骤", "上下文"]
        self.icon = "🧠📁"

        # 用户体验配置
        self.user_experience_config = {
            "auto_finalize": True,
            "friendly_format": True,
            "max_result_length": 2000,
            "show_usage_hints": True,
        }

        # 技能配置
        self.config = {
            "timeout": 30,
            "max_retries": 3,
            "cache_results": True,
            "max_files_to_process": 5,
            "max_content_length": 5000,
        }

        # 内部状态
        self._initialized = False
        self._dependencies_checked = False
        self._resources = {}

        # 上下文缓存
        self.context = {
            "last_file_list": [],
            "last_file_contents": {},
            "current_task": None
        }

        # 初始化技能
        self._initialize_skill()

    def _initialize_skill(self) -> None:
        """初始化技能"""
        try:
            if self._initialized:
                return

            print(f"🔧 初始化技能: {self.name} v{self.version}")

            # 1. 检查依赖
            self._check_dependencies()

            # 2. 初始化文件工具
            self.file_tools = FileTools()

            # 3. 验证工作区
            self._validate_workspace()

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
                __import__(req.split('>=')[0].split('==')[0])
                print(f"    ✅ {req}")
            except ImportError as e:
                print(f"    ❌ 缺少依赖: {req}")
                print(f"      错误: {e}")

        self._dependencies_checked = True

    def _validate_workspace(self) -> None:
        """验证工作区"""
        workspace_path = Path(WORKSPACE_DIR)
        if not workspace_path.exists():
            print(f"  ⚠️ 工作区不存在: {workspace_path}")
            workspace_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ 已创建工作区: {workspace_path}")

    def execute(self, function_name: str, **kwargs) -> Any:
        """执行技能的具体功能"""
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
                "timestamp": datetime.datetime.now().isoformat()
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
                    "timestamp": datetime.datetime.now().isoformat()
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
                "timestamp": datetime.datetime.now().isoformat()
            }

    def validate_input(self, function_name: str, **kwargs) -> bool:
        """验证输入参数"""
        import inspect

        # 查找方法
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

    def func_list_files(self, directory_path: str = ".", recursive: bool = False,
                        exclude_extensions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        列出工作区内的文件

        Args:
            directory_path: 目录路径，默认为工作区根目录
            recursive: 是否递归遍历子目录
            exclude_extensions: 排除的文件扩展名列表

        Returns:
            包含文件列表的字典
        """
        result = self.file_tools.list_files(
            directory_path=directory_path,
            recursive=recursive
        )

        if result.get("success", False):
            # 本地过滤
            files = result.get("files", [])
            if exclude_extensions:
                filtered_files = []
                for file_info in files:
                    file_path = file_info.get("path", "")
                    if not any(file_path.endswith(ext) for ext in exclude_extensions):
                        filtered_files.append(file_info)
                files = filtered_files

            # 缓存文件列表
            self.context["last_file_list"] = files

            formatted_result = self._format_file_list(files)

            return {
                "success": True,
                "files": files,
                "count": len(files),
                "formatted_result": formatted_result,
                "directory": directory_path,
                "recursive": recursive,
                "is_final_answer": True,
                "suggestion": "如需查看某个文件的内容，请告诉我文件名。"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "未知错误")
            }

    def func_read_file(self, file_path: str, max_lines: int = 1000) -> Dict[str, Any]:
        """
        读取文件内容

        Args:
            file_path: 文件路径
            max_lines: 最大读取行数

        Returns:
            包含文件内容的字典
        """
        result = self.file_tools.read_file(
            file_path=file_path,
            max_lines=max_lines
        )

        if result.get("success", False):
            content = result.get("content", "")
            is_large = result.get("is_large_file", False)

            # 缓存文件内容
            self.context["last_file_contents"][file_path] = content[:1000]

            formatted_result = self._format_file_content(file_path, content, is_large)

            return {
                "success": True,
                "content": content,
                "file_path": file_path,
                "is_large_file": is_large,
                "total_lines": result.get("total_lines", 0),
                "formatted_result": formatted_result,
                "is_final_answer": True,
                "suggestion": "如需总结此文件内容，请告诉我。"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "未知错误")
            }

    def func_summarize_content(self, content: str, max_length: int = 2000) -> Dict[str, Any]:
        """
        总结文本内容

        Args:
            content: 要总结的文本内容
            max_length: 总结的最大长度

        Returns:
            包含总结结果的字典
        """
        result = self.file_tools.summarize_content(
            content=content,
            max_length=max_length
        )

        if result.get("success", False):
            summary = result.get("summary", "")

            formatted_result = self._format_summary(content, summary)

            return {
                "success": True,
                "summary": summary,
                "original_length": len(content),
                "summary_length": len(summary),
                "formatted_result": formatted_result,
                "is_final_answer": True
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "未知错误")
            }

    def func_summarize_all_files(self, directory_path: str = ".",
                                 max_files: int = 5, max_length_per_summary: int = 500) -> Dict[str, Any]:
        """
        总结工作区所有文件

        这是一个复合功能，自动执行多步骤任务：
        1. 列出文件
        2. 读取每个文件
        3. 总结内容
        4. 返回综合报告

        Args:
            directory_path: 目录路径
            max_files: 最大处理文件数
            max_length_per_summary: 每个总结的最大长度

        Returns:
            包含综合总结的字典
        """
        print(f"🧠 开始智能任务: 总结工作区所有文件")

        # 步骤1: 列出文件
        print("  📋 步骤1: 列出文件...")
        list_result = self.func_list_files(directory_path=directory_path, recursive=False)

        if not list_result.get("success", False):
            return list_result

        files = list_result.get("files", [])
        if not files:
            return {
                "success": True,
                "formatted_result": "📁 工作区中没有文件可总结。",
                "is_final_answer": True
            }

        print(f"  ✅ 找到 {len(files)} 个文件")

        # 限制处理文件数量
        files_to_process = files[:max_files]

        all_summaries = []
        processed_files = []

        # 步骤2: 读取并总结每个文件
        for i, file_info in enumerate(files_to_process, 1):
            file_path = file_info.get("path", "")
            file_name = file_info.get("name", "未知文件")

            print(f"  📄 步骤2.{i}: 处理文件 '{file_name}'...")

            # 读取文件
            read_result = self.func_read_file(file_path, max_lines=500)
            if not read_result.get("success", False):
                print(f"    ⚠️ 跳过文件 {file_name}: 读取失败")
                continue

            content = read_result.get("content", "")
            if not content or len(content.strip()) < 10:
                print(f"    ⚠️ 跳过文件 {file_name}: 内容过少或为空")
                continue

            # 总结内容
            summary_result = self.func_summarize_content(content[:5000], max_length_per_summary)
            if summary_result.get("success", False):
                summary = summary_result.get("summary", "")
                all_summaries.append(f"{i}. {file_name}:\n   {summary}")
                processed_files.append(file_name)

        # 步骤3: 组合所有总结
        if not processed_files:
            return {
                "success": True,
                "formatted_result": "📁 未能成功总结任何文件。",
                "is_final_answer": True
            }

        print(f"  ✅ 成功总结 {len(processed_files)} 个文件")

        # 生成最终报告
        total_summary = "\n\n".join(all_summaries)
        combined_summary = self._create_combined_summary(total_summary, max_length=1000)

        formatted_result = self._format_summary_report(processed_files, combined_summary)

        return {
            "success": True,
            "formatted_result": formatted_result,
            "processed_files": processed_files,
            "file_count": len(processed_files),
            "combined_summary": combined_summary,
            "is_final_answer": True
        }

    def func_intelligent_file_task(self, user_query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        智能文件任务

        根据用户查询自动分配合适的功能

        Args:
            user_query: 用户查询
            context: 上下文信息（可选）

        Returns:
            任务执行结果
        """
        print(f"🧠 分析用户查询: {user_query}")

        # 分析用户意图
        query_lower = user_query.lower()

        if any(word in query_lower for word in ["所有文件", "全部文件", "工作区"]):
            if any(word in query_lower for word in ["总结", "概括", "概要", "摘要"]):
                print("  🤔 识别为: 总结所有文件")
                return self.func_summarize_all_files()

        # 默认返回说明
        return {
            "success": True,
            "formatted_result": "🤔 我理解您想要处理文件，但需要更明确的指令。\n\n"
                                "您可以:\n"
                                "1. 列出工作区文件\n"
                                "2. 读取特定文件\n"
                                "3. 总结文件内容\n"
                                "4. 总结所有文件",
            "is_final_answer": True
        }

    def _format_file_list(self, files: List[Dict[str, Any]]) -> str:
        """格式化文件列表"""
        if not files:
            return "📁 工作区中没有文件。"

        total_size = sum(f.get("size", 0) for f in files)

        result = f"📁 工作区文件列表：\n\n"
        result += f"共找到 {len(files)} 个文件，总大小: {self._format_size(total_size)}\n\n"

        for i, file_info in enumerate(files[:10], 1):
            name = file_info.get("name", "未知")
            size = file_info.get("size", 0)
            modified = file_info.get("modified", "")

            result += f"{i}. {name} ({self._format_size(size)})"
            if modified:
                try:
                    dt = datetime.datetime.fromtimestamp(float(modified))
                    result += f" - 修改于: {dt.strftime('%Y-%m-%d %H:%M')}"
                except:
                    pass
            result += "\n"

        if len(files) > 10:
            result += f"\n... 还有 {len(files) - 10} 个文件未显示"

        result += f"\n\n💡 提示: 您可以说 '总结这些文件' 或 '读取某个文件' 来继续。"

        return result

    def _format_file_content(self, file_path: str, content: str, is_large: bool) -> str:
        """格式化文件内容"""
        result = f"📄 文件内容: {file_path}\n\n"

        if is_large:
            result += "⚠️ 文件较大，已截断显示\n\n"

        result += content[:1000]

        if len(content) > 1000:
            result += f"\n\n... 已截断，完整内容共 {len(content)} 字符"

        result += f"\n\n💡 提示: 您可以说 '总结这个文件' 来获取摘要。"

        return result

    def _format_summary(self, original: str, summary: str) -> str:
        """格式化总结结果"""
        result = f"📋 内容总结：\n\n"
        result += f"原文长度: {len(original)} 字符\n"
        result += f"总结长度: {len(summary)} 字符\n\n"
        result += f"总结内容：\n{summary}"

        return result

    def _format_summary_report(self, files: List[str], combined_summary: str) -> str:
        """格式化总结报告"""
        result = f"📊 文件总结报告\n\n"
        result += f"📁 已总结 {len(files)} 个文件:\n"

        for i, file_name in enumerate(files, 1):
            result += f"  {i}. {file_name}\n"

        result += f"\n📋 综合总结:\n{combined_summary}\n\n"
        result += f"✅ 总结完成！"

        return result

    def _create_combined_summary(self, all_summaries: str, max_length: int = 1000) -> str:
        """创建综合总结"""
        if len(all_summaries) <= max_length:
            return all_summaries

        return all_summaries[:max_length] + "..."

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"

    def format_result(self, result: Any) -> str:
        """格式化结果"""
        if isinstance(result, dict):
            if "formatted_result" in result:
                return result["formatted_result"]

            if self.user_experience_config.get("friendly_format", True):
                return self._generate_friendly_message(result, "")

        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, indent=2)

        return str(result)

    def _generate_friendly_message(self, result: Dict[str, Any], user_query: str) -> str:
        """生成友好消息"""
        if not result.get("success", False):
            error = result.get("error", "未知错误")
            return f"❌ 操作失败: {error}"

        if "formatted_result" in result:
            return result["formatted_result"]

        if "data" in result:
            data = result["data"]
            if isinstance(data, dict) and "message" in data:
                return f"✅ {data['message']}"
            return f"✅ 操作成功: {str(data)[:200]}..."

        return "✅ 操作成功"

    def get_examples(self) -> List[Dict[str, str]]:
        """获取使用示例"""
        return [
            {
                "user": "列出工作区所有文件",
                "assistant": "我将为您列出工作区中的所有文件...",
                "function": "list_files"
            },
            {
                "user": "读取report.md文件",
                "assistant": "我将读取report.md文件的内容...",
                "function": "read_file"
            },
            {
                "user": "总结这个文件",
                "assistant": "我来总结这个文件的内容...",
                "function": "summarize_content"
            },
            {
                "user": "总结工作区所有文件",
                "assistant": "🧠 我将智能地总结工作区中的所有文件，这需要几个步骤...",
                "function": "summarize_all_files"
            }
        ]

    def get_requirements(self) -> List[str]:
        """获取依赖要求"""
        return ["pathlib", "PyPDF2", "python-docx"]

    def get_safety_rules(self) -> List[str]:
        """获取安全规则"""
        return [
            "只能访问工作区内的文件",
            "禁止访问系统文件",
            "大文件自动截断，避免内存溢出",
            "不处理敏感个人信息"
        ]

    def get_system_prompt_section(self) -> str:
        """返回技能在系统提示中的描述部分"""
        section = f"## {self.icon} {self.name} (ID: {self.skill_id})\n"
        section += f"**版本:** v{self.version}\n"
        section += f"**描述:** {self.description}\n"
        section += f"**分类:** {', '.join(self.category)}\n"
        section += f"**开发者:** {self.author}\n\n"

        functions = self.get_functions()
        if functions:
            section += "**可用功能:**\n"
            for func in functions:
                func_name = func['name']
                func_desc = func.get('description', '无描述').strip()
                section += f"- **{func_name}**: {func_desc}\n"

                params = func.get('parameters', {})
                if params:
                    section += "  参数:\n"
                    for param_name, param_info in params.items():
                        param_type = param_info.get('type', 'any')
                        optional = " (可选)" if param_info.get('optional', False) else " (必填)"
                        default = f" 默认值: {param_info['default']}" if 'default' in param_info else ""
                        section += f"  - {param_name} ({param_type}){optional}{default}\n"

        examples = self.get_examples()
        if examples and len(examples) > 0:
            section += "\n**使用示例:**\n"
            for ex in examples[:3]:
                section += f"- 用户: {ex.get('user', '')}\n"
                section += f"  AI: 调用 {self.skill_id}.{ex.get('function', 'function')}\n"

        return section

    def on_load(self):
        """技能加载时调用"""
        print(f"🔧 技能 {self.name} 已加载")

    def on_unload(self):
        """技能卸载时调用"""
        print(f"🔧 技能 {self.name} 已卸载")
        self._cleanup_resources()

    def _cleanup_resources(self):
        """清理技能资源"""
        if self._resources:
            for name, resource in self._resources.items():
                if hasattr(resource, 'close'):
                    resource.close()
            self._resources.clear()


# 测试代码
if __name__ == "__main__":
    import sys
    import unittest


    class TestFileEnhancedSkill(unittest.TestCase):
        def setUp(self):
            self.skill = FileEnhancedSkill()

        def test_skill_info(self):
            """测试技能基本信息"""
            self.assertEqual(self.skill.name, "文件操作（增强版）")
            self.assertEqual(self.skill.skill_id, "file_enhanced")
            self.assertEqual(self.skill.version, "3.0.0")

        def test_list_files(self):
            """测试列出文件功能"""
            result = self.skill.execute("list_files", directory_path=".", recursive=False)
            self.assertIn("success", result)
            self.assertIn("files", result)

        def test_summarize_content(self):
            """测试总结内容功能"""
            test_content = "Python是一种高级编程语言，具有简单易学的语法。它广泛用于Web开发、数据分析、人工智能等领域。"
            result = self.skill.execute("summarize_content", content=test_content, max_length=50)
            self.assertIn("success", result)
            self.assertIn("summary", result)

        def test_intelligent_task(self):
            """测试智能任务功能"""
            result = self.skill.execute("intelligent_file_task", user_query="总结工作区文件")
            self.assertIn("success", result)


    # 运行测试
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
        unittest.main(testRunner=runner, argv=sys.argv[:1])
    else:
        # 快速演示
        skill = FileEnhancedSkill()
        print(f"🔧 技能名称: {skill.name}")
        print(f"   版本: v{skill.version}")
        print(f"   描述: {skill.description}")
        print(f"   功能数: {len(skill.get_functions())}")

        # 测试功能
        print(f"\n🧪 测试功能...")
        result = skill.execute("list_files", directory_path=".", recursive=False)
        print(f"   结果: {json.dumps(result, ensure_ascii=False, indent=2)[:200]}...")
