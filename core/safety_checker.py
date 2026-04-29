import os
import re
from _opcode import is_valid
from pathlib import Path
from typing import Union, Tuple
from config import WORKSPACE_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE


class SafetyChecker:
    """安全检查器，确保所有操作在安全范围内"""

    # 危险命令模式
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf",
        r"del\s+/[fqs]",
        r"format\s+",
        r"chmod\s+[0-9]{3,4}",
        r"wget\s+",
        r"curl\s+.*\|\s*(bash|sh|zsh)",
    ]

    @staticmethod
    def validate_path(user_path: str, allow_directory: bool = True) -> Tuple[bool, Union[Path, str]]:
        """
        验证路径是否在安全工作区内

        返回: (是否有效, 解析后的路径或错误信息)
        """
        # 如果是空路径，返回工作区根目录
        if not user_path or not isinstance(user_path, str) or user_path.strip() == "":
            return True, WORKSPACE_DIR

        clean_path = user_path.strip()

        # 安全检查1: 防止路径遍历攻击
        if ".." in clean_path or clean_path.startswith("/") or "~" in clean_path:
            return False, f"路径包含非法字符: {clean_path}"

        try:
            # 解析为绝对路径
            abs_path = (WORKSPACE_DIR / clean_path).resolve()

            # 安全检查2: 确保路径在workspace内
            try:
                if not abs_path.is_relative_to(WORKSPACE_DIR):
                    return False, f"禁止访问工作区外的路径: {clean_path}"
            except ValueError:
                return False, f"路径解析失败: {clean_path}"

            # 安全检查3: 路径规范化
            normalized = os.path.normpath(str(abs_path))
            if normalized != str(abs_path):
                return False, f"路径格式异常: {clean_path}"

            return True, abs_path

        except Exception as e:
            return False, f"路径验证异常: {str(e)}"

    @staticmethod
    def check_file_operation(abs_path: Path, operation: str = "read") -> Tuple[bool, str]:
        """
        检查文件操作是否被允许

        操作类型: read, write, delete
        """
        try:
            # 检查路径是否存在
            if not abs_path.exists():
                if operation == "write":
                    # 写入新文件，检查父目录
                    parent = abs_path.parent
                    if not parent.exists():
                        return False, f"父目录不存在: {parent}"
                else:
                    return False, f"文件不存在: {abs_path.name}"

            if abs_path.is_file():
                # 检查文件类型
                if abs_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                    return False, f"不支持的文件类型: {abs_path.suffix}"

                # 检查文件大小（仅对已存在文件）
                if operation in ["read", "write"] and abs_path.exists():
                    file_size = abs_path.stat().st_size
                    if file_size > MAX_FILE_SIZE:
                        return False, f"文件过大: {file_size}字节，最大允许{MAX_FILE_SIZE}字节"

            # 检查是否是符号链接（防止攻击）
            if abs_path.is_symlink():
                return False, "不支持符号链接"

            # 特殊检查：隐藏文件
           # if abs_path.name.startswith('.') and abs_path.name not in ['.gitignore']:
               # return False, "不允许操作隐藏文件"

            return True, "检查通过"

        except Exception as e:
            return False, f"文件检查异常: {str(e)}"

    @staticmethod
    def validate_command(command: str) -> Tuple[bool, str]:
        """验证命令是否安全"""
        if not command or not isinstance(command, str):
            return False, "命令不能为空"

        # 检查危险模式
        for pattern in SafetyChecker.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"检测到危险命令模式: {pattern}"

        # 检查危险关键词
        dangerous_keywords = ["sudo", "su ", "passwd", "dd ", "mkfs", "fdisk"]
        for keyword in dangerous_keywords:
            if keyword in command.lower():
                return False, f"检测到危险关键词: {keyword}"

        return True, "命令安全检查通过"

    @staticmethod
    def validate_tool_params(tool_name: str, action: str, params: dict) -> bool:
        """验证工具调用参数安全性"""
        # 文件操作工具的特殊检查
        if tool_name == "file_tools":
            if action == "read_file":
                return "file_path" in params and SafetyChecker.is_path_safe(params["file_path"])
            elif action == "list_files":
                if "directory_path" in params:
                    return SafetyChecker.is_path_safe(params["directory_path"])
                return True  # 允许空目录路径
        return True  # 默认通过验证

    @staticmethod
    def validate_path(user_path: str, allow_directory: bool = True) -> Tuple[bool, Union[Path, str]]:
        """增强版路径验证（恢复旧版逻辑）"""
        # 处理空路径
        if not user_path or not isinstance(user_path, str) or user_path.strip() == "":
            return True, WORKSPACE_DIR

        clean_path = user_path.strip()

        # 安全处理：允许相对路径
        if clean_path.startswith("./") or clean_path.startswith(".\\"):
            clean_path = clean_path[2:]

        try:
            # 解析为绝对路径
            abs_path = (WORKSPACE_DIR / clean_path).resolve()

            # 确保路径在workspace内
            if not abs_path.is_relative_to(WORKSPACE_DIR):
                return False, f"禁止访问工作区外的路径: {clean_path}"

            # 检查路径类型
            if not allow_directory and not abs_path.is_file():
                return False, f"路径不是文件: {clean_path}"

            return True, abs_path
        except Exception as e:
            return False, f"路径解析失败: {str(e)}"

    @staticmethod
    def is_path_safe(path: str) -> bool:
        """验证文件路径是否在安全目录内"""
        try:
            workspace_path = Path(WORKSPACE_DIR).resolve()
            requested_path = (workspace_path / path).resolve()
            return requested_path.is_relative_to(workspace_path)
        except Exception:
            return False