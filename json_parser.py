# json_parser.py
"""
可靠的JSON解析器
"""
import json
import re
from typing import Dict, Any, Optional


def robust_parse_model_response(response: str) -> Dict[str, Any]:
    """
    健壮的模型响应解析
    保证总是返回字典，包含thought和final_answer
    """
    if not response or not isinstance(response, str):
        return {
            "thought": "收到空响应",
            "final_answer": "大模型返回了空响应，请重试。"
        }

    response = response.strip()

    # 记录原始响应用于调试
    print(f"🔍 解析响应 (前500字符): {response[:500]}{'...' if len(response) > 500 else ''}")

    # 方法1: 尝试直接解析
    try:
        parsed = json.loads(response)
        if isinstance(parsed, dict) and parsed:
            print(f"✅ 方法1: 直接解析成功")
            return parsed
    except json.JSONDecodeError as e1:
        pass

    # 方法2: 提取代码块中的JSON
    try:
        # 查找 ```json ... ``` 格式
        json_pattern = r'```json\s*(.*?)\s*```'
        match = re.search(json_pattern, response, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            parsed = json.loads(json_str)
            if isinstance(parsed, dict) and parsed:
                print(f"✅ 方法2: 代码块解析成功")
                return parsed
    except (json.JSONDecodeError, AttributeError) as e2:
        pass

    # 方法3: 查找任何JSON对象
    try:
        # 查找 { ... } 格式
        json_pattern = r'\{.*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)
        for match in matches:
            try:
                parsed = json.loads(match)
                if isinstance(parsed, dict) and parsed:
                    print(f"✅ 方法3: 正则匹配解析成功")
                    return parsed
            except json.JSONDecodeError:
                continue
    except Exception as e3:
        pass

    # 方法4: 修复常见的JSON格式问题
    try:
        # 修复没有引号的键
        fixed = re.sub(r'(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', response)
        # 修复单引号
        fixed = fixed.replace("'", '"')
        # 修复True/False/null
        fixed = fixed.replace('True', 'true').replace('False', 'false').replace('None', 'null')
        # 修复末尾逗号
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)

        parsed = json.loads(fixed)
        if isinstance(parsed, dict) and parsed:
            print(f"✅ 方法4: 修复后解析成功")
            return parsed
    except json.JSONDecodeError as e4:
        pass

    # 方法5: 提取可能的JSON（如果响应以技能名开头）
    lines = response.strip().split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if line and line.startswith('{'):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict) and parsed:
                    print(f"✅ 方法5: 行解析成功")
                    return parsed
            except json.JSONDecodeError:
                continue

    # 方法6: 尝试解析每一行
    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue

        # 检查是否包含JSON结构
        if '{' in line and '}' in line and ':' in line:
            # 提取可能的JSON部分
            start = line.find('{')
            end = line.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = line[start:end]
                try:
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict) and parsed:
                        print(f"✅ 方法6: 提取解析成功")
                        return parsed
                except json.JSONDecodeError:
                    continue

    # 如果所有方法都失败，检查是否是简单的自然语言
    if len(response) < 1000:
        # 检查是否包含常见的AI响应关键词
        keywords = ['列出', '查看', '添加', '删除', '读取', '总结', '文件', '日程', '会议']
        if any(keyword in response for keyword in keywords):
            return {
                "thought": "模型返回了自然语言响应",
                "final_answer": response
            }

    # 最后的手段：返回错误消息
    return {
        "thought": "无法解析模型响应",
        "final_answer": f"模型返回了无法解析的响应。请确保返回正确的JSON格式。\n\n原始响应前200字符:\n{response[:200]}"
    }


def extract_action_and_args(response: str) -> Dict[str, Any]:
    """专门提取action和args的辅助函数"""
    if not response:
        return {}

    result = robust_parse_model_response(response)

    # 确保返回的字典有必要的字段
    if "action" not in result and "final_answer" not in result:
        # 尝试从响应文本中提取
        if "action" in response.lower() or "skill" in response.lower():
            # 使用正则表达式提取
            action_match = re.search(r'"action"\s*:\s*"([^"]*)"', response)
            if not action_match:
                action_match = re.search(r"'action'\s*:\s*'([^']*)'", response)

            args_match = re.search(r'"args"\s*:\s*(\{.*?\})', response, re.DOTALL)
            if not args_match:
                args_match = re.search(r"'args'\s*:\s*(\{.*?\})", response, re.DOTALL)

            if action_match and args_match:
                try:
                    action = action_match.group(1)
                    args_str = args_match.group(1)

                    # 修复args字符串
                    args_str = args_str.replace("'", '"')
                    args = json.loads(args_str)

                    return {
                        "thought": "从响应中提取出action和args",
                        "action": action,
                        "args": args
                    }
                except Exception as e:
                    pass

    return result


def fix_ai_args(args: Dict[str, Any], action: str) -> Dict[str, Any]:
    """修复AI返回的参数"""
    if not args:
        args = {}

    fixed_args = args.copy()

    # 文件操作相关修复
    if "skill.file.list_files" in action:
        # 修复directory_path参数
        if "directory_path" in fixed_args:
            dir_path = fixed_args["directory_path"]
            if isinstance(dir_path, str) and dir_path.lower() in ["default", "", "null", "none"]:
                fixed_args["directory_path"] = "."
                print(f"  🔧 修复directory_path: '{dir_path}' -> '.'")
        elif "directory_path" not in fixed_args:
            fixed_args["directory_path"] = "."
            print(f"  🔧 添加directory_path: '.'")

        # 确保recursive是布尔值
        if "recursive" in fixed_args and not isinstance(fixed_args["recursive"], bool):
            try:
                if isinstance(fixed_args["recursive"], str):
                    fixed_args["recursive"] = fixed_args["recursive"].lower() in ["true", "yes", "1"]
                else:
                    fixed_args["recursive"] = bool(fixed_args["recursive"])
            except:
                fixed_args["recursive"] = False
        elif "recursive" not in fixed_args:
            fixed_args["recursive"] = False

    return fixed_args