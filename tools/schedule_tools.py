import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from core.tool_interface import ToolInterface
from config import WORKSPACE_DIR
from core.time_parser import TimeParser


class ScheduleTools(ToolInterface):
    """日程管理工具（增强版）"""

    def __init__(self):
        super().__init__()
        self.metadata = {
            "name": "schedule_tools",
            "description": "管理用户日程的工具",
            "parameters": {
                "add_schedule": {
                    "event": {"type": "string", "description": "事件描述"},
                    "event_time": {"type": "string", "description": "事件时间（ISO格式或自然语言如'今天19:00'）"},
                    "remind_before": {"type": "integer", "optional": True, "default": 60,
                                      "description": "提前提醒时间（分钟）"}
                },
                "list_schedules": {
                    "future_only": {"type": "boolean", "optional": True, "default": True,
                                    "description": "是否只显示未来日程"}
                },
                "remove_schedule": {
                    "index": {"type": "integer", "description": "要移除的日程索引"}
                },
                "remove_schedule_by_description": {
                    "description": {"type": "string", "description": "要删除的日程描述（支持模糊匹配）"}
                }
            }
        }
        self.schedule_file = WORKSPACE_DIR / "schedules.json"
        self._ensure_schedule_file()

    def _ensure_schedule_file(self):
        """确保日程文件存在"""
        if not self.schedule_file.exists():
            with open(self.schedule_file, 'w') as f:
                json.dump([], f)

    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具操作"""
        action = kwargs.pop("action", None)
        if action == "add_schedule":
            return self.add_schedule(**kwargs)
        elif action == "list_schedules":
            return self.list_schedules(**kwargs)
        elif action == "remove_schedule":
            return self.remove_schedule(**kwargs)
        elif action == "remove_schedule_by_description":
            return self.remove_schedule_by_description(**kwargs)
        else:
            return {
                "success": False,
                "error": f"未知操作: {action}"
            }

    def add_schedule(self, event: str, event_time: str, remind_before: int = 60) -> Dict[str, Any]:
        """添加新日程（增强时间解析）"""
        try:
            from datetime import datetime, timedelta
            from core.time_parser import TimeParser

            # 获取当前时间
            now = datetime.now()

            # 使用通用时间解析器
            try:
                schedule_time = TimeParser.parse_natural_time(event_time, now)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"时间解析失败: {str(e)}"
                }

            if schedule_time < now:
                return {
                    "success": False,
                    "error": f"不能添加过去时间的日程: {schedule_time}"
                }

            # 读取现有日程
            with open(self.schedule_file, 'r') as f:
                schedules = json.load(f)

            # 检查重复日程
            for s in schedules:
                if s["event"] == event and s["event_time"] == schedule_time.isoformat():
                    return {
                        "success": False,
                        "error": f"重复日程: {event} 在 {schedule_time}"
                    }

            # 添加新日程
            new_schedule = {
                "event": event,
                "event_time": schedule_time.isoformat(),
                "remind_time": (schedule_time - timedelta(minutes=remind_before)).isoformat(),
                "added_at": now.isoformat(),
                "remind_before": remind_before
            }
            schedules.append(new_schedule)

            # 保存更新
            with open(self.schedule_file, 'w') as f:
                json.dump(schedules, f, indent=2)

            return {
                "success": True,
                "message": f"日程添加成功: {event} 在 {schedule_time.strftime('%Y-%m-%d %H:%M')}",
                "remind_message": f"将在 {remind_before} 分钟前提醒",
                "schedule": new_schedule
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"添加日程失败: {str(e)}"
            }

    def refresh_schedules(self):
        """强制刷新日程列表"""
        with open(self.schedule_file, 'r') as f:
            return json.load(f)

    def list_schedules(self, future_only: bool = True) -> Dict[str, Any]:
        """列出日程（修复索引显示）"""

        try:
            schedules = self.refresh_schedules()
            with open(self.schedule_file, 'r') as f:
                schedules = json.load(f)

            now = datetime.now()
            if future_only:
                schedules = [s for s in schedules if datetime.fromisoformat(s["event_time"]) > now]

            # 格式化输出（确保索引从0开始连续）
            formatted = []
            for i, s in enumerate(schedules):
                event_time = datetime.fromisoformat(s["event_time"])
                remind_time = datetime.fromisoformat(s["remind_time"])
                formatted.append({
                    "index": i,  # 确保使用当前循环索引
                    "event": s["event"],
                    "event_time": s["event_time"],
                    "remind_time": s["remind_time"],
                    "time_until": (event_time - now).total_seconds() / 3600,  # 小时
                    "remind_in": (remind_time - now).total_seconds() / 3600  # 小时
                })

            return {
                "success": True,
                "schedules": formatted,
                "count": len(formatted)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"列出日程失败: {str(e)}"
            }

    # 在 schedule_tools.py 中添加
    def cleanup_schedules(self, remove_past: bool = True) -> Dict[str, Any]:
        """清理过期日程"""
        try:
            now = datetime.now()
            with open(self.schedule_file, 'r') as f:
                schedules = json.load(f)

            original_count = len(schedules)

            # 过滤过期日程
            if remove_past:
                schedules = [s for s in schedules if datetime.fromisoformat(s["event_time"]) > now]

            # 保存清理后的日程
            with open(self.schedule_file, 'w') as f:
                json.dump(schedules, f, indent=2)

            # 获取文件大小
            file_size = os.path.getsize(self.schedule_file)
            file_size_human = self._human_readable_size(file_size)

            return {
                "success": True,
                "removed_count": original_count - len(schedules),
                "current_count": len(schedules),
                "file_size": file_size,
                "file_size_human": file_size_human,
                "message": f"清理完成，移除 {original_count - len(schedules)} 个过期日程"
            }
        except Exception as e:
            return {"success": False, "error": f"清理失败: {str(e)}"}

    def remove_schedule(self, index: int) -> Dict[str, Any]:
        """通过索引移除日程（修复索引问题）"""
        try:
            # 刷新日程列表
            schedules = self.refresh_schedules()

            # 验证索引有效性
            if index < 0 or index >= len(schedules):
                return {
                    "success": False,
                    "error": f"无效索引: {index}"
                }

            # 移除日程
            removed = schedules.pop(index)

            # 保存更新
            with open(self.schedule_file, 'w') as f:
                json.dump(schedules, f, indent=2)

            # 返回最新列表
            return self.list_schedules(future_only=True)
        except Exception as e:
            return {
                "success": False,
                "error": f"移除日程失败: {str(e)}"
            }

    def refresh_schedules(self) -> List[Dict[str, Any]]:
        """强制刷新日程列表"""
        if not self.schedule_file.exists():
            return []

        with open(self.schedule_file, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def remove_schedule_by_description(self, description: str) -> Dict[str, Any]:
        """通过描述智能移除日程（增强版）"""
        try:
            # 获取所有日程
            with open(self.schedule_file, 'r') as f:
                schedules = json.load(f)

            now = datetime.now()

            # 增强时间范围解析
            time_period = None
            if "今晚" in description or "今天晚上" in description:
                time_period = (now.replace(hour=18, minute=0, second=0),
                               now.replace(hour=23, minute=59, second=59))
            elif "今天" in description:
                time_period = (now.replace(hour=0, minute=0, second=0),
                               now.replace(hour=23, minute=59, second=59))
            elif "明天早上" in description:
                tomorrow = now + timedelta(days=1)
                time_period = (tomorrow.replace(hour=6, minute=0, second=0),
                               tomorrow.replace(hour=10, minute=0, second=0))
            elif "明天下午" in description:
                tomorrow = now + timedelta(days=1)
                time_period = (tomorrow.replace(hour=12, minute=0, second=0),
                               tomorrow.replace(hour=18, minute=0, second=0))
            elif "明天" in description:
                tomorrow = now + timedelta(days=1)
                time_period = (tomorrow.replace(hour=0, minute=0, second=0),
                               tomorrow.replace(hour=23, minute=59, second=59))
            # 添加更多时间段...

            # 过滤匹配的日程
            matches = []
            for i, s in enumerate(schedules):
                event_time = datetime.fromisoformat(s["event_time"])

                # 检查描述匹配
                desc_match = description.lower() in s["event"].lower()

                # 检查时间匹配
                time_match = True
                if time_period:
                    start, end = time_period
                    time_match = start <= event_time <= end

                if desc_match and time_match:
                    matches.append((i, s))

            # 处理匹配结果
            if not matches:
                return {
                    "success": False,
                    "error": f"未找到匹配的日程: {description}"
                }
            elif len(matches) == 1:
                # 自动删除唯一匹配项
                index, schedule = matches[0]
                return self.remove_schedule(index)
            if len(matches) > 1:
                # 返回匹配列表供用户选择
                return {
                    "success": True,
                    "matches": [
                        {
                            "index": idx,  # 使用实际索引
                            "event": s["event"],
                            "event_time": s["event_time"]
                        } for idx, s in matches
                    ],
                    "message": f"找到 {len(matches)} 个匹配的日程"
                }
            else:
                return {
                    "success": True,
                    "matches": [
                        {
                            "index": idx,
                            "event": s["event"],
                            "event_time": s["event_time"]
                        } for idx, s in matches
                    ],
                    "message": f"找到 {len(matches)} 个匹配的日程"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"智能删除失败: {str(e)}"
            }
