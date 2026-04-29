"""
日程管理技能
封装了日程工具的所有功能
"""
import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# 尝试导入现有工具
try:
    from tools.schedule_tools import ScheduleTools
    from core.time_parser import TimeParser
except ImportError as e:
    print(f"⚠️ 导入现有工具失败: {e}")
    # 模拟版本，用于测试
    class ScheduleTools:
        def add_schedule(self, **kwargs):
            return {"success": True, "message": "日程添加成功", "schedule": kwargs}
        def list_schedules(self, **kwargs):
            return {"success": True, "schedules": [], "formatted_result": "无日程"}
        def remove_schedule(self, **kwargs):
            return {"success": True, "message": "日程删除成功"}
        def remove_schedule_by_description(self, **kwargs):
            return {"success": True, "message": "日程删除成功"}

    class TimeParser:
        def parse_natural_time(self, time_str, base_time=None):
            return datetime.now()

# 导入Skill基类
try:
    from core.base_skill import Skill
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.base_skill import Skill


class CompatibleTimeParser:
    """兼容时间解析器，处理各种时间格式"""

    def parse_natural_time(self, time_str: str, base_time: datetime = None) -> datetime:
        """解析自然语言时间"""
        if base_time is None:
            base_time = datetime.now()

        time_str = time_str.strip()
        time_str_lower = time_str.lower()

        print(f"⏰ 解析时间: '{time_str}' (基准时间: {base_time.strftime('%Y-%m-%d %H:%M')})")

        # 1. 首先尝试各种常见日期格式
        # 尝试ISO格式
        if "T" in time_str and time_str.startswith("20"):
            try:
                if time_str.endswith("Z"):
                    time_str = time_str[:-1] + "+00:00"
                dt = datetime.fromisoformat(time_str)
                print(f"   ✅ 识别为ISO格式: {dt}")
                return dt
            except ValueError:
                pass

        # 尝试空格分隔的日期时间格式
        if " " in time_str and time_str.startswith("20"):
            try:
                # 尝试多种可能的空格分隔格式
                formats_to_try = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M",
                    "%Y/%m/%d %H:%M:%S",
                    "%Y/%m/%d %H:%M",
                ]

                for fmt in formats_to_try:
                    try:
                        dt = datetime.strptime(time_str, fmt)
                        print(f"   ✅ 识别为{fmt}格式: {dt}")
                        return dt
                    except ValueError:
                        continue
            except Exception:
                pass

        # 2. 处理星期几
        weekday_map = {
            "一": 0, "二": 1, "三": 2, "四": 3,
            "五": 4, "六": 5, "日": 6, "天": 6
        }

        result_time = base_time
        days_offset = 0

        # 检查是否是星期几
        for chinese_day, weekday_num in weekday_map.items():
            if f"星期{chinese_day}" in time_str_lower or f"周{chinese_day}" in time_str_lower:
                # 计算最近的星期几
                target_weekday = weekday_num
                current_weekday = base_time.weekday()

                # 计算距离目标星期几还有几天
                days_ahead = target_weekday - current_weekday
                if days_ahead <= 0:  # 如果已经过了，就到下周
                    days_ahead += 7

                result_time = base_time + timedelta(days=days_ahead)
                print(f"   📅 解析为星期{chinese_day}，距离今天{days_ahead}天")
                break

        # 3. 如果没有匹配到星期几，处理"今天"、"明天"、"后天"
        if days_offset == 0:
            if "今天" in time_str_lower or "今晚" in time_str_lower:
                days_offset = 0
            elif "明天" in time_str_lower or "明早" in time_str_lower or "明晚" in time_str_lower:
                days_offset = 1
            elif "后天" in time_str_lower:
                days_offset = 2
            elif "大后天" in time_str_lower:
                days_offset = 3
            else:
                days_offset = 0

        result_time = result_time + timedelta(days=days_offset)

        # 4. 提取时间部分
        hour = None
        minute = 0
        is_pm = False

        # 先尝试匹配具体时间
        time_patterns = [
            r'(\d{1,2})[:点](\d{1,2})分?',
            r'(\d{1,2})[:点]',
            r'(\d{1,2})',
        ]

        matched_exact_time = False
        for pattern in time_patterns:
            match = re.search(pattern, time_str)
            if match:
                groups = match.groups()
                hour = int(groups[0])
                if len(groups) > 1 and groups[1]:
                    minute = int(groups[1])
                print(f"   🔍 匹配到具体时间: {hour}:{minute}")
                matched_exact_time = True
                break

        # 如果没有匹配到具体时间，根据时间段设置合理默认
        if not matched_exact_time:
            hour = 9  # 默认上午9点

            # 根据时间段设置更合理的默认时间
            if "早上" in time_str_lower or "早晨" in time_str_lower or "清晨" in time_str_lower:
                hour = 8
            elif "上午" in time_str_lower or "早上" in time_str_lower:
                hour = 10
            elif "中午" in time_str_lower or "午间" in time_str_lower:
                hour = 12
            elif "下午" in time_str_lower:
                hour = 15  # 下午3点更合理
            elif "傍晚" in time_str_lower or "黄昏" in time_str_lower:
                hour = 18
            elif "晚上" in time_str_lower or "夜晚" in time_str_lower or "今晚" in time_str_lower:
                hour = 20
            elif "半夜" in time_str_lower or "凌晨" in time_str_lower:
                hour = 2
                # 如果是半夜，可能需要调整到第二天
                if "半夜" in time_str_lower or "凌晨" in time_str_lower:
                    result_time += timedelta(days=1)
            elif "深夜" in time_str_lower:
                hour = 23
            print(f"   🔍 使用时间段默认时间: {hour}:{minute}")

        # 处理上午/下午/晚上标志
        if "下午" in time_str_lower or "晚上" in time_str_lower or "pm" in time_str_lower:
            is_pm = True
        elif "上午" in time_str_lower or "早上" in time_str_lower or "am" in time_str_lower:
            is_pm = False

        # 如果是下午/晚上且hour<12，则加12小时
        if is_pm and hour < 12:
            hour += 12
            print(f"   🔧 下午/晚上时间调整: {hour}:{minute}")

        # 如果是上午且hour>=12，调整为上午时间
        if not is_pm and hour >= 12 and hour != 12:
            hour = hour - 12
            print(f"   🔧 上午时间调整: {hour}:{minute}")

        # 中午12点特殊处理
        if "中午" in time_str_lower and hour == 12:
            is_pm = False
            print(f"   🔧 中午12点不变")

        # 处理24小时制
        if hour == 24:
            hour = 0
            result_time += timedelta(days=1)

        # 设置时间
        result_time = result_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

        print(f"   ✅ 解析结果: {result_time.strftime('%Y-%m-%dT%H:%M')}")
        return result_time


class ScheduleSkill(Skill):
    """日程管理技能"""

    def __init__(self):
        super().__init__()
        self.skill_id = "schedule"
        self.name = "日程管理"
        self.version = "2.0.0"
        self.description = "这是一个管理日程的skill，你可以添加、查看、删除日程安排。"
        self.author = "系统"
        self.category = ["日程", "时间", "管理"]
        self.tags = ["日程", "日历", "提醒", "安排", "事件", "时间", "会议", "计划"]
        self.icon = "📅"

        # 用户体验配置
        self.user_experience_config = {
            "auto_finalize": True,
            "friendly_format": True,
            "max_result_length": 1000,
            "show_usage_hints": True,
        }

        # 技能配置
        self.config = {
            "timeout": 30,
            "max_retries": 3,
            "cache_results": True,
            "default_remind_before": 15,
        }

        # 内部状态
        self._initialized = False
        self._dependencies_checked = False
        self._resources = {}

        # 初始化日程工具
        self.schedule_tools = ScheduleTools()

        # 使用兼容时间解析器
        try:
            from core.time_parser import TimeParser
            self.time_parser = TimeParser()
        except (ImportError, AttributeError) as e:
            self.time_parser = CompatibleTimeParser()

        # 初始化技能
        self._initialize_skill()

        # 本地存储
        self.storage_file = Path("schedules.json")
        self._ensure_storage()

    def _ensure_storage(self):
        """确保存储文件存在"""
        if not self.storage_file.exists():
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def _load_schedules(self) -> List[Dict[str, Any]]:
        """加载日程列表"""
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_schedules(self, schedules: List[Dict[str, Any]]):
        """保存日程列表"""
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(schedules, f, ensure_ascii=False, indent=2)

    def _initialize_skill(self) -> None:
        """初始化技能"""
        try:
            if self._initialized:
                return

            print(f"🔧 初始化技能: {self.name} v{self.version}")

            # 1. 检查依赖
            self._check_dependencies()

            # 2. 加载配置
            self._load_configuration()

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

    def _load_configuration(self) -> None:
        """加载技能配置"""
        # TODO: 从文件或环境变量加载配置
        pass

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

    def func_add_schedule(self, event: str, event_time: str, remind_before: int = 0) -> Dict[str, Any]:
        """
        添加日程

        Args:
            event: 事件名称
            event_time: 事件时间（自然语言或ISO格式）
            remind_before: 提前提醒时间（分钟），默认0表示不提醒

        Returns:
            添加结果
        """
        original_time = event_time
        print(f"📅 尝试添加日程: {event} @ {event_time}")

        try:
            # 修复remind_before参数
            if isinstance(remind_before, str):
                # 尝试从字符串中提取数字
                match = re.search(r'(\d+)', remind_before)
                if match:
                    remind_before = int(match.group(1))
                    print(f"  🔧 提取提醒时间: {remind_before} 分钟")
                else:
                    remind_before = 0
                    print(f"  ⚠️ 无法解析提醒时间，使用默认值: 0 分钟")
            elif not isinstance(remind_before, int):
                remind_before = 0
                print(f"  ⚠️ 提醒时间类型错误，使用默认值: 0 分钟")

            # 检查是否已经是常见的时间格式
            is_formatted_time = False

            # 尝试ISO格式
            if "T" in event_time and event_time.startswith("20"):
                try:
                    datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                    is_formatted_time = True
                    print(f"   ⏰ 识别为ISO格式: {event_time}")
                except ValueError:
                    is_formatted_time = False

            # 尝试空格分隔的格式
            if not is_formatted_time and " " in event_time and event_time.startswith("20"):
                try:
                    datetime.strptime(event_time, "%Y-%m-%d %H:%M")
                    is_formatted_time = True
                    print(f"   ⏰ 识别为空格分隔格式: {event_time}")
                except ValueError:
                    is_formatted_time = False

            # 如果不是格式化的时间，尝试解析自然语言
            if not is_formatted_time:
                try:
                    parsed_time = self.time_parser.parse_natural_time(event_time)
                    event_time = parsed_time.strftime("%Y-%m-%dT%H:%M")
                    print(f"   ⏰ 解析自然语言时间: '{original_time}' -> {event_time}")
                except Exception as parse_error:
                    print(f"   ❌ 时间解析失败: {parse_error}")
                    return {
                        "success": False,
                        "error": f"时间解析失败: {parse_error}",
                        "original_time": original_time,
                        "formatted_result": f"❌ 时间解析失败: '{original_time}' 无法识别"
                    }

            # 确保时间是未来
            try:
                event_datetime = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                now = datetime.now()

                if event_datetime < now:
                    time_diff = now - event_datetime
                    if time_diff.days > 0:
                        error_msg = f"不能添加过去时间的日程: {event_time} ({time_diff.days}天前)"
                    else:
                        hours = int(time_diff.seconds / 3600)
                        minutes = int((time_diff.seconds % 3600) / 60)
                        error_msg = f"不能添加过去时间的日程: {event_time} ({hours}小时{minutes}分钟前)"

                    print(f"   ❌ {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "original_time": original_time,
                        "formatted_result": f"❌ {error_msg}"
                    }

                print(f"   ✅ 时间验证通过: {event_time} 是未来时间")

            except Exception as time_check_error:
                print(f"   ⚠️ 时间验证异常: {time_check_error}")

            # 创建日程对象
            schedule = {
                "event": event,
                "event_time": event_time,
                "remind_before": remind_before,
                "created_at": datetime.now().isoformat(),
                "id": str(hash(f"{event}_{event_time}_{remind_before}"))
            }

            # 保存到本地存储
            schedules = self._load_schedules()
            schedules.append(schedule)
            self._save_schedules(schedules)

            success_message = f"✅ 日程添加成功: {event} @ {event_time}"
            if remind_before > 0:
                success_message += f" (提前{remind_before}分钟提醒)"

            print(f"   {success_message}")
            return {
                "success": True,
                "message": "日程添加成功",
                "schedule": schedule,
                "formatted_result": success_message,
                "is_final_answer": True
            }

        except Exception as e:
            error_msg = f"添加日程时发生异常: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "original_time": original_time,
                "formatted_result": f"❌ {error_msg}"
            }

    def func_list_schedules(self, future_only: bool = True) -> Dict[str, Any]:
        """
        列出日程

        Args:
            future_only: 是否只显示未来日程

        Returns:
            日程列表
        """
        print(f"📅 列出日程 (future_only={future_only})")

        try:
            schedules = self._load_schedules()
            print(f"🔍 从存储加载到 {len(schedules)} 个日程")

            if future_only:
                now = datetime.now()
                # 过滤未来日程
                future_schedules = []
                for schedule in schedules:
                    try:
                        event_time = schedule.get("event_time", "")
                        if event_time:
                            event_datetime = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                            if event_datetime >= now:
                                future_schedules.append(schedule)
                    except Exception as e:
                        # 如果解析失败，保留日程
                        print(f"⚠️ 解析日程时间失败: {e}")
                        future_schedules.append(schedule)

                schedules = future_schedules

            if not schedules:
                formatted_result = "📅 目前没有日程安排。"
            else:
                formatted_result = f"📅 找到 {len(schedules)} 个日程安排：\n\n"
                for i, schedule in enumerate(schedules[:5], 1):
                    event = schedule.get("event", "未命名")
                    event_time = schedule.get("event_time", "未知时间")
                    remind_before = schedule.get("remind_before", 0)

                    # 格式化时间
                    try:
                        dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                        time_str = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        time_str = event_time

                    formatted_result += f"{i}. {event} - {time_str}"
                    if remind_before > 0:
                        formatted_result += f" (提前{remind_before}分钟提醒)"
                    formatted_result += "\n"

                if len(schedules) > 5:
                    formatted_result += f"\n... 还有 {len(schedules) - 5} 个日程未显示"

            print(f"   ✅ 找到 {len(schedules)} 个日程")
            return {
                "success": True,
                "schedules": schedules,
                "count": len(schedules),
                "formatted_result": formatted_result,
                "is_final_answer": True
            }
        except Exception as e:
            error_msg = f"列出日程失败: {e}"
            print(f"   ❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

    def func_remove_schedule(self, index: int) -> Dict[str, Any]:
        """
        通过索引删除日程

        Args:
            index: 日程索引

        Returns:
            删除结果
        """
        print(f"🗑️ 删除日程 (索引: {index})")

        try:
            schedules = self._load_schedules()
            if index < 0 or index >= len(schedules):
                error_msg = f"无效的索引: {index}"
                print(f"   ❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }

            removed = schedules.pop(index)
            self._save_schedules(schedules)

            success_message = f"✅ 日程删除成功 (索引: {index})"
            print(f"   {success_message}")
            return {
                "success": True,
                "message": "日程删除成功",
                "formatted_result": success_message,
                "is_final_answer": True
            }
        except Exception as e:
            error_msg = f"删除日程失败: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

    def func_remove_schedule_by_description(self, description: str) -> Dict[str, Any]:
        """
        通过描述删除日程

        Args:
            description: 日程描述

        Returns:
            删除结果
        """
        print(f"🗑️ 通过描述删除日程: '{description}'")

        try:
            schedules = self._load_schedules()
            matches = []

            for i, schedule in enumerate(schedules):
                event = schedule.get("event", "")
                if description.lower() in event.lower():
                    matches.append({
                        "index": i,
                        "event": event,
                        "event_time": schedule.get("event_time", "")
                    })

            if not matches:
                error_msg = f"没有找到匹配的日程: {description}"
                print(f"   ❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }

            if len(matches) == 1:
                # 只有一个匹配项，直接删除
                index = matches[0]["index"]
                removed = schedules.pop(index)
                self._save_schedules(schedules)

                success_message = f"✅ 日程删除成功: {description}"
                print(f"   {success_message}")
                return {
                    "success": True,
                    "message": "日程删除成功",
                    "formatted_result": success_message,
                    "is_final_answer": True
                }
            else:
                # 多个匹配项，返回列表让用户选择
                formatted_result = f"🔍 找到 {len(matches)} 个匹配的日程，请选择索引:\n"
                for match in matches:
                    formatted_result += f"  [{match['index']}] {match['event']} @ {match['event_time']}\n"

                print(f"   🔍 找到 {len(matches)} 个匹配的日程")
                return {
                    "success": True,
                    "matches": matches,
                    "message": "找到多个匹配的日程，请选择索引",
                    "formatted_result": formatted_result,
                    "is_final_answer": True
                }
        except Exception as e:
            error_msg = f"删除日程失败: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

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

        if "schedules" in result:
            count = result.get("count", 0)
            if count == 0:
                return "📅 目前没有日程安排。"
            else:
                schedules = result.get("schedules", [])
                message = f"📅 找到 {count} 个日程安排：\n\n"
                for i, schedule in enumerate(schedules[:5], 1):
                    event = schedule.get("event", "未命名")
                    event_time = schedule.get("event_time", "未知时间")
                    message += f"{i}. {event} - {event_time}\n"
                if count > 5:
                    message += f"\n... 还有 {count - 5} 个日程未显示"
                return message

        elif "schedule" in result:
            schedule = result.get("schedule", {})
            event = schedule.get("event", "未命名")
            event_time = schedule.get("event_time", "未知时间")
            return f"✅ 日程添加成功！\n\n事件：{event}\n时间：{event_time}"

        elif "message" in result and "删除" in result["message"]:
            return f"✅ {result['message']}"

        return "✅ 操作成功"

    def get_examples(self) -> List[Dict[str, str]]:
        """获取使用示例"""
        return [
            {
                "user": "添加一个明天上午9点的会议",
                "assistant": "我将为您添加明天上午9点的会议日程...",
                "function": "add_schedule"
            },
            {
                "user": "查看我今天的安排",
                "assistant": "我来查看您今天的日程安排...",
                "function": "list_schedules"
            },
            {
                "user": "删除今晚的聚餐",
                "assistant": "我将查找并删除今晚的聚餐安排...",
                "function": "remove_schedule_by_description"
            },
            {
                "user": "列出所有日程",
                "assistant": "我来列出您的所有日程安排...",
                "function": "list_schedules"
            }
        ]

    def get_requirements(self) -> List[str]:
        """获取依赖要求"""
        return []

    def get_safety_rules(self) -> List[str]:
        """获取安全规则"""
        return [
            "只能管理当前用户的日程",
            "时间必须是未来时间",
            "敏感操作需要确认",
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

    class TestScheduleSkill(unittest.TestCase):
        def setUp(self):
            self.skill = ScheduleSkill()

        def test_skill_info(self):
            """测试技能基本信息"""
            self.assertEqual(self.skill.name, "日程管理")
            self.assertEqual(self.skill.skill_id, "schedule")
            self.assertEqual(self.skill.version, "2.0.0")

        def test_list_schedules(self):
            """测试列出日程功能"""
            result = self.skill.execute("list_schedules", future_only=True)
            self.assertIn("success", result)
            self.assertIn("schedules", result)

        def test_add_schedule(self):
            """测试添加日程功能"""
            # 使用未来时间进行测试
            future_time = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00")
            result = self.skill.execute("add_schedule",
                                       event="测试会议",
                                       event_time=future_time,
                                       remind_before=15)
            self.assertIn("success", result)

        def test_remove_schedule(self):
            """测试删除日程功能"""
            result = self.skill.execute("remove_schedule", index=0)
            self.assertIn("success", result)

    # 运行测试
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
        unittest.main(testRunner=runner, argv=sys.argv[:1])
    else:
        # 快速演示
        skill = ScheduleSkill()
        print(f"🔧 技能名称: {skill.name}")
        print(f"   版本: v{skill.version}")
        print(f"   描述: {skill.description}")
        print(f"   功能数: {len(skill.get_functions())}")

        # 测试功能
        print(f"\n🧪 测试功能...")
        result = skill.execute("list_schedules", future_only=True)
        print(f"   结果: {json.dumps(result, ensure_ascii=False, indent=2)[:200]}...")
