# core/task_planner.py
"""
智能任务规划器
帮助AI理解多步骤任务
"""
from typing import Dict, List, Any, Optional, Tuple
import re


class TaskPlanner:
    """任务规划器"""

    def __init__(self, skill_manager):
        self.skill_manager = skill_manager

    def plan_task(self, user_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        规划任务执行步骤

        Returns:
            包含步骤计划或直接技能调用的字典
        """
        query_lower = user_query.lower()

        # 识别常见多步骤任务模式
        task_patterns = [
            {
                "pattern": r"(总结|概括|概述|摘要)(工作区|所有|全部)?(文件|文档)",
                "description": "总结所有文件",
                "type": "multi_step",
                "skills": ["file_enhanced"],
                "function": "summarize_all_files"
            },
            {
                "pattern": r"读取(并)?(总结|概括)(.*?)文件",
                "description": "读取并总结文件",
                "type": "multi_step",
                "skills": ["file", "file_enhanced"],
                "function": "intelligent_file_task"
            }
        ]

        for pattern_info in task_patterns:
            if re.search(pattern_info["pattern"], query_lower):
                print(f"🧠 识别到多步骤任务: {pattern_info['description']}")

                # 检查是否有对应的增强技能
                for skill_id in pattern_info["skills"]:
                    skill = self.skill_manager.get_skill(skill_id)
                    if skill and hasattr(skill, f"func_{pattern_info['function']}"):
                        return {
                            "type": "direct_skill",
                            "skill_id": skill_id,
                            "function": pattern_info["function"],
                            "description": f"使用{skill.name}的{pattern_info['function']}功能处理多步骤任务"
                        }

        # 如果没有匹配到多步骤模式，返回空让AI自行决定
        return {
            "type": "ai_decision",
            "description": "由AI决定如何执行"
        }

    def get_enhanced_system_prompt(self, base_prompt: str, user_query: str,
                                   context: Dict[str, Any]) -> str:
        """获取增强的系统提示，包含任务规划信息"""

        # 分析任务
        task_plan = self.plan_task(user_query, context)

        enhanced_prompt = base_prompt

        if task_plan["type"] == "direct_skill":
            skill = self.skill_manager.get_skill(task_plan["skill_id"])
            if skill:
                enhanced_prompt += f"\n\n## 🧠 任务分析\n"
                enhanced_prompt += f"系统检测到用户可能想要执行多步骤任务: {task_plan['description']}\n"
                enhanced_prompt += f"建议直接调用: `skill.{task_plan['skill_id']}.{task_plan['function']}`\n"
                enhanced_prompt += f"这个功能会自动处理多个步骤，更高效地完成任务。"

        elif task_plan["type"] == "multi_step":
            enhanced_prompt += f"\n\n## 🧠 任务分析\n"
            enhanced_prompt += f"这是一个多步骤任务，建议分步执行:\n"
            enhanced_prompt += f"1. 列出相关文件\n"
            enhanced_prompt += f"2. 读取文件内容\n"
            enhanced_prompt += f"3. 处理内容（如总结）\n"
            enhanced_prompt += f"4. 返回综合结果"

        return enhanced_prompt