"""
技能匹配器
根据用户输入匹配最合适的技能
"""
from typing import List, Dict, Any, Optional
import re


class SkillMatcher:
    """技能匹配器"""

    def __init__(self, skill_manager):
        self.skill_manager = skill_manager

    def match_skills(self, user_input: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        匹配最适合的技能

        Args:
            user_input: 用户输入
            context: 上下文信息

        Returns:
            匹配的技能列表
        """
        if context is None:
            context = {}

        # 1. 关键词匹配
        keyword_matches = self._match_by_keywords(user_input)

        # 2. 规则匹配
        rule_matches = self._match_by_rules(user_input, context)

        # 合并结果
        all_matches = {}

        # 合并关键词匹配结果
        for match in keyword_matches:
            skill_id = match["skill_id"]
            if skill_id not in all_matches:
                all_matches[skill_id] = {
                    "skill": match["skill"],
                    "score": 0,
                    "reasons": []
                }
            all_matches[skill_id]["score"] += match["score"]
            all_matches[skill_id]["reasons"].append(match["reason"])

        # 合并规则匹配结果
        for match in rule_matches:
            skill_id = match["skill_id"]
            if skill_id not in all_matches:
                all_matches[skill_id] = {
                    "skill": match["skill"],
                    "score": 0,
                    "reasons": []
                }
            all_matches[skill_id]["score"] += match["score"]
            all_matches[skill_id]["reasons"].append(match["reason"])

        # 转换为最终结果列表
        matches = []
        for skill_id, info in all_matches.items():
            matches.append({
                "skill_id": skill_id,
                "skill": info["skill"],
                "score": info["score"],
                "reason": "; ".join(info["reasons"]),
                "manifest": info["skill"].get_manifest()
            })

        # 按分数排序
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches

    def _match_by_keywords(self, user_input: str) -> List[Dict[str, Any]]:
        """通过关键词匹配"""
        matches = []
        user_input_lower = user_input.lower()

        for skill_id, skill in self.skill_manager.get_all_skills().items():
            score = 0
            reasons = []

            # 匹配技能名称
            if self._contains_word(user_input_lower, skill.name.lower()):
                score += 3
                reasons.append(f"名称匹配: {skill.name}")

            # 匹配技能描述
            if self._contains_word(user_input_lower, skill.description.lower()):
                score += 2
                reasons.append("描述匹配")

            # 匹配标签
            for tag in skill.tags:
                if self._contains_word(user_input_lower, tag.lower()):
                    score += 2
                    reasons.append(f"标签匹配: {tag}")

            # 匹配分类
            for category in skill.category:
                if self._contains_word(user_input_lower, category.lower()):
                    score += 1
                    reasons.append(f"分类匹配: {category}")

            if score > 0:
                matches.append({
                    "skill_id": skill_id,
                    "skill": skill,
                    "score": score,
                    "reason": ", ".join(reasons)
                })

        return matches

    def _match_by_rules(self, user_input: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """通过规则匹配"""
        matches = []
        user_input_lower = user_input.lower()

        # 文件相关操作规则
        file_keywords = [
            ("文件", ["文件", "文档", "文件夹", "目录"]),
            ("读取", ["读取", "打开", "查看", "显示", "浏览"]),
            ("列表", ["列表", "列出", "所有", "全部", "目录"]),
            ("总结", ["总结", "摘要", "概括", "概要"]),
            ("写入", ["写入", "保存", "创建", "新建", "编辑"]),
        ]

        # 日程相关操作规则
        schedule_keywords = [
            ("日程", ["日程", "日历", "计划", "安排", "行程"]),
            ("添加", ["添加", "新建", "创建", "设置", "安排"]),
            ("查看", ["查看", "显示", "列出", "今天", "明天", "周", "月"]),
            ("删除", ["删除", "移除", "取消", "清除"]),
            ("时间", ["时间", "日期", "几点", "何时", "什么时候"]),
        ]

        # 检查文件相关关键词
        file_score = 0
        file_reasons = []
        for keyword_type, keywords in file_keywords:
            for keyword in keywords:
                if keyword in user_input_lower:
                    file_score += 1
                    file_reasons.append(f"文件关键词: {keyword}")
                    break

        # 检查日程相关关键词
        schedule_score = 0
        schedule_reasons = []
        for keyword_type, keywords in schedule_keywords:
            for keyword in keywords:
                if keyword in user_input_lower:
                    schedule_score += 1
                    schedule_reasons.append(f"日程关键词: {keyword}")
                    break

        # 匹配文件技能
        if file_score > 0:
            file_skill = self.skill_manager.get_skill("file")
            if file_skill:
                matches.append({
                    "skill_id": "file",
                    "skill": file_skill,
                    "score": file_score * 2,  # 权重
                    "reason": f"文件操作规则匹配 ({', '.join(file_reasons[:3])})"
                })

        # 匹配日程技能
        if schedule_score > 0:
            schedule_skill = self.skill_manager.get_skill("schedule")
            if schedule_skill:
                matches.append({
                    "skill_id": "schedule",
                    "skill": schedule_skill,
                    "score": schedule_score * 2,  # 权重
                    "reason": f"日程规则匹配 ({', '.join(schedule_reasons[:3])})"
                })

        return matches

    def _contains_word(self, text: str, word: str) -> bool:
        """检查文本是否包含单词（考虑单词边界）"""
        # 简单的实现，后续可以改进
        return word in text

    def get_best_skill(self, user_input: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """获取最佳匹配技能"""
        matches = self.match_skills(user_input, context)
        if matches:
            return matches[0]
        return None