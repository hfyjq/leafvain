import os
import json
import re
from pathlib import Path
from datetime import datetime
from .vector_db import VectorDB
from typing import List, Dict, Any, Optional
from .safety_checker import SafetyChecker
from config import MEDIUM_TERM_MEMORY_DIR, SHORT_TERM_MEMORY_SIZE, MEMORY_COMPRESSION_PROMPT, WORKSPACE_DIR


def safe_path_validation(path: str) -> bool:
    """
    安全的路径验证，确保路径在工作区内

    Args:
        path: 要验证的路径

    Returns:
        bool: 路径是否安全
    """
    try:
        # 使用 SafetyChecker 类的静态方法
        is_valid, normalized_path = SafetyChecker.validate_path(path, allow_directory=True)
        return is_valid

    except Exception as e:
        print(f"⚠️ 路径验证异常: {e}")
        return False


class MemoryManager:
    def __init__(self, api_client):
        self.api_client = api_client
        self.short_term = []
        self.vector_db = VectorDB()

        # 确保目录存在
        os.makedirs(MEDIUM_TERM_MEMORY_DIR, exist_ok=True)

        # 加载历史记忆
        self._load_memories()
        print(f"✅ 记忆管理器初始化完成，短期记忆: {len(self.short_term)} 条")

    def _load_memories(self):
        """加载已有的中期记忆"""
        try:
            if os.path.exists(MEDIUM_TERM_MEMORY_DIR):
                files = [f for f in os.listdir(MEDIUM_TERM_MEMORY_DIR) if f.endswith('.json')]
                files.sort()
                print(f"📁 加载中期记忆文件: {len(files)} 个")
        except Exception as e:
            print(f"⚠️ 加载记忆文件时出错: {e}")

    def recall_memories(self, query: str) -> str:
        """召回三层记忆"""
        memories = []

        # 1. 短期记忆（最近对话）
        if self.short_term:
            memories.append("## 近期对话记忆：")
            recent_count = min(SHORT_TERM_MEMORY_SIZE, len(self.short_term))
            for msg in self.short_term[-recent_count:]:
                # 简化显示，避免过长
                content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                memories.append(f"- {msg['role']}: {content}")

        # 2. 中期记忆（压缩摘要）
        medium_memories = self._load_medium_memories()
        if medium_memories:
            memories.append("\n## 中期重要记忆：")
            for mem in medium_memories:
                # 计算记忆的时效性
                mem_date = datetime.fromisoformat(mem['date'])
                days_old = (datetime.now() - mem_date).days
                if days_old <= 7:  # 一周内的记忆
                    memories.append(f"- {mem['summary']} (最近)")
                elif days_old <= 30:  # 一个月内的记忆
                    memories.append(f"- {mem['summary']} (稍早)")

        # 3. 长期记忆（向量检索）
        long_term_results = self.vector_db.search(query, top_k=2)
        if long_term_results:
            memories.append("\n## 相关长期记忆：")
            for res in long_term_results[:2]:  # 最多显示2条
                score = res.get('score', 0)
                if score > 0.5:  # 相关性阈值
                    content = res['content'][:80] + "..." if len(res['content']) > 80 else res['content']
                    memories.append(f"- {content}")

        if memories:
            return "\n".join(memories)
        return ""

    def store_memory(self, conversation: List[dict]):
        """存储对话记忆"""
        if not conversation or len(conversation) < 2:
            return

        # 获取最后两轮对话（完整的一问一答）
        recent_dialog = conversation[-2:] if len(conversation) >= 2 else conversation

        # 将对话转换为文本
        dialog_text = ""
        for msg in recent_dialog:
            role = "用户" if msg["role"] == "user" else "助手"
            dialog_text += f"{role}: {msg['content']}\n"

        # 添加到向量数据库
        self.vector_db.add_memory(
            content=dialog_text,
            metadata={
                "type": "conversation",
                "timestamp": datetime.now().isoformat(),
                "turns": len(recent_dialog)
            }
        )

    def _clean_assistant_response(self, content: str) -> str:
        """清理助手响应，去除工具调用等非自然语言部分"""
        # 如果是JSON响应，尝试解析
        if content.strip().startswith('{'):
            try:
                data = json.loads(content)
                if 'final_answer' in data:
                    return data['final_answer']
                elif 'thought' in data:
                    return data['thought']
            except:
                pass

        # 去除工具调用标记
        clean = re.sub(r'工具调用:.*?(?=\n|$)', '', content, flags=re.DOTALL)
        clean = re.sub(r'```json.*?```', '', clean, flags=re.DOTALL)
        clean = clean.strip()

        if clean and len(clean) > 5:
            return clean
        return content

    def _compress_to_medium_memory(self):
        """使用LLM压缩对话到中期记忆"""
        if len(self.short_term) < 3:
            return

        # 取最近3-5条对话进行压缩
        recent_count = min(5, len(self.short_term))
        recent_conversations = self.short_term[-recent_count:]
        conversation_text = "\n".join(
            [f"{m['role']}: {m['content']}" for m in recent_conversations]
        )

        # 构建压缩提示
        prompt = f"{MEMORY_COMPRESSION_PROMPT}\n\n{conversation_text}"

        try:
            # 调用API进行压缩
            summary = self.api_client.chat_completion(
                messages=[
                    {"role": "system", "content": MEMORY_COMPRESSION_PROMPT},
                    {"role": "user", "content": conversation_text}
                ],
                max_tokens=200,
                temperature=0.3
            )

            if summary and len(summary) > 10:
                # 存储摘要
                memory_file = os.path.join(MEDIUM_TERM_MEMORY_DIR,
                                           f"memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

                # 使用安全路径验证
                if not safe_path_validation(memory_file):
                    print(f"⚠️ 记忆文件路径不安全: {memory_file}")
                    return

                memory_data = {
                    "date": datetime.now().isoformat(),
                    "summary": summary,
                    "source_excerpt": conversation_text[:500] + "..." if len(
                        conversation_text) > 500 else conversation_text
                }

                with open(memory_file, 'w', encoding='utf-8') as f:
                    json.dump(memory_data, f, ensure_ascii=False, indent=2)

                print(f"💾 已存储中期记忆: {summary[:50]}...")

                # 清理已压缩的短期记忆
                self.short_term = self.short_term[:-recent_count]

        except Exception as e:
            print(f"⚠️ 压缩记忆时出错: {e}")

    def _load_medium_memories(self, limit=3) -> list:
        """加载最近的中期记忆"""
        try:
            if not os.path.exists(MEDIUM_TERM_MEMORY_DIR):
                return []

            files = [f for f in os.listdir(MEDIUM_TERM_MEMORY_DIR) if f.endswith('.json')]
            files.sort(reverse=True)  # 按时间倒序

            memories = []
            for file in files[:limit]:
                file_path = os.path.join(MEDIUM_TERM_MEMORY_DIR, file)

                # 使用安全路径验证
                if not safe_path_validation(file_path):
                    print(f"⚠️ 跳过不安全的记忆文件: {file_path}")
                    continue

                with open(file_path, 'r', encoding='utf-8') as f:
                    memory_data = json.load(f)
                    memories.append(memory_data)

            return memories
        except Exception as e:
            print(f"⚠️ 加载中期记忆时出错: {e}")
            return []

    def cleanup_memories(self, max_medium_files=50):
        """清理过多的中期记忆文件"""
        try:
            if not os.path.exists(MEDIUM_TERM_MEMORY_DIR):
                return

            files = [f for f in os.listdir(MEDIUM_TERM_MEMORY_DIR) if f.endswith('.json')]
            files.sort()  # 按时间正序，最早的在前

            if len(files) > max_medium_files:
                files_to_delete = files[:-max_medium_files]  # 保留最新的max_medium_files个
                for file in files_to_delete:
                    file_path = os.path.join(MEDIUM_TERM_MEMORY_DIR, file)

                    # 使用安全路径验证
                    if not safe_path_validation(file_path):
                        print(f"⚠️ 跳过不安全的记忆文件: {file_path}")
                        continue

                    os.remove(file_path)
                print(f"🧹 已清理 {len(files_to_delete)} 个旧记忆文件")

        except Exception as e:
            print(f"⚠️ 清理记忆时出错: {e}")