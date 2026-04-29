# 创建 time_parser_compat.py
from datetime import datetime, timedelta
import re
from typing import Optional


class TimeParserCompat:
    """兼容时间解析器"""

    def parse_natural_time(self, time_str: str, base_time: datetime = None) -> datetime:
        """解析自然语言时间"""
        if base_time is None:
            base_time = datetime.now()

        time_str_lower = time_str.lower().strip()

        # 处理常见的时间格式
        patterns = [
            # 明天/后天
            (r'明天\s*([上下]午)?\s*(\d{1,2})[:点]?(\d{2})?', 1),
            (r'后天\s*([上下]午)?\s*(\d{1,2})[:点]?(\d{2})?', 2),
            # 今天
            (r'今天\s*([上下]午)?\s*(\d{1,2})[:点]?(\d{2})?', 0),
            # 具体日期
            (r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})\s*([上下]午)?\s*(\d{1,2})[:点]?(\d{2})?', None),
        ]

        # 尝试解析
        for pattern, days_offset in patterns:
            match = re.match(pattern, time_str_lower)
            if match:
                result = base_time
                if days_offset is not None:
                    result = result + timedelta(days=days_offset)

                # 提取小时和分钟
                groups = match.groups()
                hour = 9  # 默认9点
                minute = 0

                if days_offset is None:
                    # 具体日期
                    year = int(groups[0])
                    month = int(groups[1])
                    day = int(groups[2])
                    result = datetime(year, month, day)
                    if groups[4]:  # 小时
                        hour = int(groups[4])
                else:
                    # 相对日期
                    if len(groups) >= 2 and groups[1]:
                        hour = int(groups[1])

                # 处理上午/下午
                if groups and groups[0] and '下午' in groups[0] and hour < 12:
                    hour += 12

                result = result.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return result

        # 如果无法解析，返回基础时间+1天
        return base_time + timedelta(days=1)