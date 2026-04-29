# core/skill_executor.py
"""
技能执行器
"""
import json
from typing import Dict, Any, Optional


class SkillExecutor:
    """技能执行器"""

    def __init__(self, skill_manager):
        self.skill_manager = skill_manager

    def execute(self, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """执行动作，支持skill.开头的技能调用"""
        print(f"⚙️ 执行动作: {action}")

        # 安全记录参数
        try:
            import json
            args_str = json.dumps(args, ensure_ascii=False, indent=2)
            if len(args_str) > 200:
                print(f"   参数: {args_str[:200]}...")
            else:
                print(f"   参数: {args_str}")
        except Exception as e:
            print(f"⚠️ 参数序列化失败: {e}")

        # 检查是否是技能调用
        if not action.startswith("skill."):
            return {
                "success": False,
                "error": f"无效的动作格式: {action}，应该是 skill.<skill_id>.<function_name>"
            }

        # 解析技能调用: skill.<skill_id>.<function_name>
        parts = action.split('.')
        if len(parts) != 3:
            return {
                "success": False,
                "error": f"无效的技能调用格式: {action}，应该是 skill.<skill_id>.<function_name>"
            }

        _, skill_id, function_name = parts

        try:
            # 执行技能
            # 执行技能
            result = self.skill_manager.execute_skill(skill_id, function_name, **args)

            # 调试：打印原始结果
            print(f"🔍 原始技能返回结果类型: {type(result)}")
            if isinstance(result, str):
                print(f"🔍 原始技能返回结果 (前500字符): {result[:500]}")
            elif isinstance(result, dict):
                print(f"🔍 原始技能返回结果键: {list(result.keys())}")

            # 确保返回结果是字典
            if not isinstance(result, dict):
                # 尝试解析字符串为JSON
                if isinstance(result, str):
                    try:
                        import json
                        parsed = json.loads(result)
                        if isinstance(parsed, dict):
                            result = parsed
                            print(f"🔍 成功解析字符串为字典")
                        else:
                            result = {"raw_result": result, "message": "技能返回了非字典结果"}
                    except json.JSONDecodeError:
                        # 不是JSON，保持为字符串
                        result = {"raw_result": result, "message": "技能返回了字符串结果"}
                else:
                    result = {"raw_result": result, "message": "技能返回了非字典结果"}

            # 添加成功标志
            if "success" not in result:
                result["success"] = True

            return result

        except Exception as e:
            import traceback
            error_msg = f"技能执行失败: {e}"
            print(f"❌ {error_msg}")
            traceback.print_exc()
            return {
                "success": False,
                "error": error_msg
            }

    def format_result(self, result: Dict[str, Any]) -> str:
        """格式化结果"""
        if "formatted_result" in result:
            return result["formatted_result"]
        elif "success" in result and not result["success"]:
            return f"❌ 操作失败: {result.get('error', '未知错误')}"
        else:
            return json.dumps(result, ensure_ascii=False, indent=2)