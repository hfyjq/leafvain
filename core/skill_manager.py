"""
技能管理器
负责动态加载、管理、执行所有技能
"""
import importlib.util
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Type
import inspect
import sys

# 确保能导入base_skill
try:
    from .base_skill import Skill
except ImportError:
    # 如果从主程序导入
    from core.base_skill import Skill


class SkillManager:
    """技能管理器"""

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, Skill] = {}
        self.registry_path = self.skills_dir / "skill_registry.json"

        # 确保目录存在
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def load_skills(self) -> None:
        """加载所有技能"""
        print(f"🛠️ 开始加载技能，目录: {self.skills_dir}")

        # 加载技能目录下的所有Python模块
        skill_files = list(self.skills_dir.glob("*.py"))
        print(f"🔍 发现技能文件: {len(skill_files)} 个")

        for skill_file in skill_files:
            if skill_file.name.startswith("_"):
                continue

            try:
                skill = self._load_skill_module(skill_file)
                if skill:
                    self.skills[skill.skill_id] = skill
                    print(f"✅ 加载技能: {skill.name} v{skill.version}")
            except Exception as e:
                print(f"❌ 加载技能失败 {skill_file.name}: {e}")
                import traceback
                traceback.print_exc()

    def _load_skill_module(self, skill_file: Path) -> Optional[Skill]:
        """动态加载技能模块"""
        module_name = skill_file.stem

        # 动态导入模块
        spec = importlib.util.spec_from_file_location(module_name, skill_file)
        if spec is None or spec.loader is None:
            return None

        try:
            module = importlib.util.module_from_spec(spec)

            # 将模块添加到sys.modules以便后续导入
            sys.modules[module_name] = module

            # 执行模块代码
            spec.loader.exec_module(module)

            # 查找Skill子类
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                        issubclass(obj, Skill) and
                        obj != Skill and
                        not name.startswith('_')):
                    # 创建技能实例
                    skill_instance = obj()
                    return skill_instance

        except Exception as e:
            print(f"❌ 导入模块 {module_name} 失败: {e}")

        return None

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取指定技能"""
        return self.skills.get(skill_id)

    def get_all_skills(self) -> Dict[str, Skill]:
        """获取所有技能"""
        return self.skills.copy()

    def get_skill_manifest(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取技能清单"""
        skill = self.get_skill(skill_id)
        if skill:
            return skill.get_manifest()
        return None

    def execute_skill(self, skill_id: str, function_name: str, **kwargs) -> Any:
        """执行技能"""
        skill = self.get_skill(skill_id)
        if not skill:
            raise ValueError(f"技能不存在: {skill_id}")

        # 验证输入
        if not skill.validate_input(function_name, **kwargs):
            raise ValueError(f"输入验证失败: {function_name}")

        # 执行技能
        result = skill.execute(function_name, **kwargs)

        # 返回原始结果，不要格式化
        return result

    def search_skills(self, query: str) -> List[Dict[str, Any]]:
        """搜索技能（基于关键词）"""
        results = []
        query_lower = query.lower()

        for skill_id, skill in self.skills.items():
            score = 0
            reasons = []

            # 匹配技能名称
            if query_lower in skill.name.lower():
                score += 3
                reasons.append("技能名称匹配")

            # 匹配技能描述
            if query_lower in skill.description.lower():
                score += 2
                reasons.append("描述匹配")

            # 匹配标签
            for tag in skill.tags:
                if query_lower in tag.lower():
                    score += 1
                    reasons.append(f"标签匹配: {tag}")

            # 匹配分类
            for category in skill.category:
                if query_lower in category.lower():
                    score += 1
                    reasons.append(f"分类匹配: {category}")

            if score > 0:
                results.append({
                    "skill_id": skill_id,
                    "skill": skill,
                    "score": score,
                    "reason": ", ".join(reasons),
                    "manifest": skill.get_manifest()
                })

        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def save_registry(self) -> None:
        """保存技能注册表"""
        registry = {}
        for skill_id, skill in self.skills.items():
            registry[skill_id] = skill.get_manifest()

        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)

        print(f"💾 技能注册表已保存: {self.registry_path}")

    def load_registry(self) -> Dict[str, Any]:
        """加载技能注册表"""
        if self.registry_path.exists():
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_all_manifests(self) -> Dict[str, Dict[str, Any]]:
        """获取所有技能的清单"""
        manifests = {}
        for skill_id, skill in self.skills.items():
            manifests[skill_id] = skill.get_manifest()
        return manifests