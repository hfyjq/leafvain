import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.safety_checker import SafetyChecker
from core.api_client import APIClientFactory
from config import WORKSPACE_DIR


class FileTools:
    """文件操作工具集"""

    def __init__(self):
        # 初始化API客户端
        self.api_client = None

    def _get_api_client(self):
        """获取API客户端（懒加载）"""
        if self.api_client is None:
            self.api_client = APIClientFactory.create_client("zhipu")
        return self.api_client

    def _simple_summary(self, content: str, max_length: int = 500) -> Dict[str, Any]:
        """简单的文本摘要（备用）"""
        if not content or len(content.strip()) == 0:
            return {
                "success": False,
                "error": "内容为空"
            }

        # 简单摘要算法：取前几行和非空行
        lines = [line.strip() for line in content.split('\n') if line.strip()]

        if len(lines) <= 5:
            summary = content
        else:
            # 取开头、中间和结尾部分
            first_lines = lines[:3]
            middle_lines = lines[len(lines) // 2 - 1:len(lines) // 2 + 2] if len(lines) > 6 else []
            last_lines = lines[-2:] if len(lines) > 5 else []

            summary_lines = first_lines
            if middle_lines:
                summary_lines.append("...")
                summary_lines.extend(middle_lines)
            if last_lines:
                if middle_lines:
                    summary_lines.append("...")
                summary_lines.extend(last_lines)

            summary = '\n'.join(summary_lines)

        # 限制长度
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return {
            "success": True,
            "summary": summary,
            "original_length": len(content),
            "summary_length": len(summary),
            "compression_ratio": f"{len(summary) / max(len(content), 1) * 100:.1f}%"
        }

    def summarize_content(self, content: str, max_length: int = 500) -> Dict[str, Any]:
        """
        使用大模型总结文本内容（增强版）
        """
        try:
            # 预处理：还原转义字符
            content = content.replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t').replace('\\"', '"')

            if not content or len(content.strip()) == 0:
                return {
                    "success": False,
                    "error": "内容为空"
                }

            # 如果内容太短，使用简单总结
            if len(content) < 200:
                return self._simple_summary(content, max_length)

            # 调用大模型API进行总结
            client = self._get_api_client()
            prompt = f"请总结以下内容（不超过{max_length}字）：\n\n{content[:5000]}"  # 限制输入长度

            response = client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_length
            )

            summary = response.choices[0].message.content.strip()
            return {
                "success": True,
                "summary": summary,
                "original_length": len(content),
                "summary_length": len(summary),
                "compression_ratio": f"{len(summary) / max(len(content), 1) * 100:.1f}%"
            }
        except Exception as e:
            print(f"⚠️ 大模型总结失败: {str(e)}")
            return self._simple_summary(content, max_length)

    def list_files(self, directory_path: str = "", recursive: bool = False) -> Dict[str, Any]:
        """
        列出工作区内的文件

        参数:
            directory_path: 目录路径（相对于工作区根目录），默认为空表示根目录
            recursive: 是否递归列出子目录
        """
        try:
            # 处理特殊情况：如果路径包含占位符或无效字符，使用根目录
            if not directory_path or directory_path.strip() == "" or "{workspace_path}" in directory_path:
                target_dir = WORKSPACE_DIR
            else:
                # 验证路径
                is_valid, path_result = SafetyChecker.validate_path(directory_path, allow_directory=True)
                if not is_valid:
                    return {
                        "success": False,
                        "error": f"路径验证失败: {path_result}",
                        "files": []
                    }

                target_dir = path_result

            if not target_dir.is_dir():
                return {
                    "success": False,
                    "error": f"不是目录: {target_dir}",
                    "files": []
                }

            # 列出文件
            files = []
            dirs = []

            for item in target_dir.iterdir():
                try:
                    if item.is_file():
                        stat = item.stat()
                        files.append({
                            "name": item.name,
                            "path": str(item.relative_to(WORKSPACE_DIR)),
                            "size": stat.st_size,
                            "size_human": self._human_readable_size(stat.st_size),
                            "modified": stat.st_mtime,
                            "modified_date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                            "extension": item.suffix.lower()
                        })
                    elif item.is_dir() and recursive:
                        dirs.append({
                            "name": item.name,
                            "path": str(item.relative_to(WORKSPACE_DIR)),
                            "type": "directory"
                        })
                except (PermissionError, OSError) as e:
                    # 忽略无法访问的文件/目录
                    continue

            # 按修改时间排序（最新优先）
            files.sort(key=lambda x: x["modified"], reverse=True)

            return {
                "success": True,
                "files": files[:50],  # 最多返回50个文件
                "directories": dirs[:20] if recursive else [],
                "count": len(files),
                "directory": str(target_dir.relative_to(WORKSPACE_DIR)),
                "total_size": sum(f["size"] for f in files),
                "total_size_human": self._human_readable_size(sum(f["size"] for f in files))
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"列出文件时出错: {str(e)}",
                "files": []
            }

    def read_file(self, file_path: str, max_lines: int = 1000) -> Dict[str, Any]:
        """安全读取文件内容"""
        try:
            # 验证路径
            is_valid, path_result = SafetyChecker.validate_path(file_path, allow_directory=False)
            if not is_valid:
                return {
                    "success": False,
                    "error": f"路径验证失败: {path_result}"
                }

            abs_path = path_result

            # 检查文件操作
            is_safe, msg = SafetyChecker.check_file_operation(abs_path, "read")
            if not is_safe:
                return {
                    "success": False,
                    "error": f"文件安全检查失败: {msg}"
                }

            # 读取文件
            try:
                with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            lines.append(f"... [文件过长，已截断前{max_lines}行]")
                            break
                        lines.append(line.rstrip('\n'))
                    content = '\n'.join(lines)
            except UnicodeDecodeError:
                # 尝试其他编码
                with open(abs_path, 'r', encoding='gbk', errors='ignore') as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            lines.append(f"... [文件过长，已截断前{max_lines}行]")
                            break
                        lines.append(line.rstrip('\n'))
                    content = '\n'.join(lines)

            # 获取文件信息
            stat = abs_path.stat()

            return {
                "success": True,
                "content": content,  # 原始内容
                "file_name": abs_path.name,
                "file_path": str(abs_path.relative_to(WORKSPACE_DIR)),
                "file_size": len(content),
                "file_size_bytes": stat.st_size,
                "line_count": len(content.split('\n')),
                "modified": stat.st_mtime,
                "is_truncated": len(content.split('\n')) >= max_lines
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"读取文件时出错: {str(e)}"
            }

    @staticmethod
    def _human_readable_size(size_bytes: int) -> str:
        """将字节数转换为人类可读的格式"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}PB"