import os
import time
import threading
from datetime import datetime
from plyer import notification


class NotificationService:
    """后台通知服务"""

    def __init__(self, tool_executor):
        self.tool_executor = tool_executor
        self.running = False
        self.thread = None

    def start(self):
        """启动通知服务"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitor_schedules)
        self.thread.daemon = True
        self.thread.start()
        print("🔔 通知服务已启动")

    def stop(self):
        """停止通知服务"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("🔕 通知服务已停止")

    def _monitor_schedules(self):
        """监控日程并发送通知"""
        while self.running:
            try:
                # 获取即将提醒的日程
                result = self.tool_executor.execute(
                    "schedule_tools.list_schedules",
                    {"future_only": True}
                )

                if result["success"]:
                    now = datetime.now()
                    for schedule in result["schedules"]:
                        remind_time = datetime.fromisoformat(schedule["remind_time"])
                        if now >= remind_time:
                            # 发送通知
                            notification.notify(
                                title="日程提醒",
                                message=f"即将开始: {schedule['event']}",
                                timeout=10
                            )


                # 每分钟检查一次
                time.sleep(60)
            except Exception as e:
                print(f"⚠️ 通知服务出错: {str(e)}")
                time.sleep(60)