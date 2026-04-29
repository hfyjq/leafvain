import os
import chromadb
from pathlib import Path
from typing import List, Dict, Any, Optional
from .safety_checker import SafetyChecker
from config import LONG_TERM_VECTOR_DB, WORKSPACE_DIR


def safe_path_validation(path: str) -> bool:
    """
    安全的路径验证，确保路径在工作区内
    """
    try:
        is_valid, normalized_path = SafetyChecker.validate_path(path, allow_directory=True)
        return is_valid
    except Exception as e:
        print(f"⚠️ 向量数据库路径验证异常: {e}")
        return False


class VectorDB:
    def __init__(self):
        # 验证路径安全性
        if not safe_path_validation(LONG_TERM_VECTOR_DB):
            raise PermissionError(f"向量数据库路径不安全: {LONG_TERM_VECTOR_DB}")

        os.makedirs(LONG_TERM_VECTOR_DB, exist_ok=True)

        try:
            # 尝试不同版本的初始化方式
            self.client = self._initialize_client()

            # 创建或获取集合
            self.collection = self.client.get_or_create_collection(
                name="long_term_memories",
                metadata={"description": "长期记忆存储"}
            )

            count = self.collection.count()
            print(f"✅ 向量数据库初始化完成，现有记忆: {count} 条")

        except Exception as e:
            print(f"❌ 向量数据库初始化失败: {e}")
            # 回退到内存存储
            self.collection = None

    def _initialize_client(self):
        """初始化向量数据库客户端，支持不同版本"""
        try:
            # 方式1: 新版本 chromadb (>=0.4.0)
            try:
                from chromadb.config import Settings
                return chromadb.PersistentClient(
                    path=LONG_TERM_VECTOR_DB,
                    settings=Settings(anonymized_telemetry=False)
                )
            except ImportError:
                pass

            # 方式2: 旧版本 chromadb (<0.4.0) 或没有 Settings
            try:
                return chromadb.PersistentClient(
                    path=LONG_TERM_VECTOR_DB
                )
            except Exception as e:
                raise ValueError(f"无法初始化向量数据库客户端: {e}")

        except Exception as e:
            raise Exception(f"向量数据库客户端初始化失败: {e}")

    def add_memory(self, content: str, metadata: Optional[Dict] = None):
        """添加记忆到向量数据库"""
        if not self.collection or not content or len(content) < 5:
            return False

        try:
            # 生成唯一ID
            from datetime import datetime
            import hashlib
            import uuid

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            # 使用更可靠的ID生成方式
            unique_id = f"memory_{uuid.uuid4().hex[:8]}"

            # 准备元数据
            mem_metadata = {
                "timestamp": timestamp,
                "length": len(content),
                "type": "assistant_response"
            }

            if metadata:
                mem_metadata.update(metadata)

            # 添加文档
            self.collection.add(
                documents=[content],
                ids=[unique_id],
                metadatas=[mem_metadata]
            )

            return True

        except Exception as e:
            print(f"⚠️ 添加记忆到向量数据库失败: {e}")
            return False

    def search(self, query: str, top_k: int = 3, min_score: float = 0.5) -> List[Dict[str, Any]]:
        """检索相关记忆"""
        if not self.collection or not query or self.collection.count() == 0:
            return []

        try:
            # 执行查询
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, self.collection.count())
            )

            memories = []
            if results.get('documents') and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    # 获取元数据
                    metadata = results.get('metadatas', [[]])[0][i] if results.get('metadatas') else {}

                    # 计算相似度分数
                    if results.get('distances'):
                        distance = results['distances'][0][i] if i < len(results['distances'][0]) else 1.0
                        # 距离越小越相似，转换为0-1的相似度
                        similarity = 1.0 / (1.0 + distance)
                    else:
                        similarity = 0.8  # 默认相似度

                    # 过滤低分结果
                    if similarity >= min_score:
                        memories.append({
                            "content": doc,
                            "score": round(similarity, 3),
                            "timestamp": metadata.get("timestamp", ""),
                            "metadata": metadata
                        })

            # 按分数排序
            memories.sort(key=lambda x: x["score"], reverse=True)
            return memories

        except Exception as e:
            print(f"⚠️ 向量数据库检索失败: {e}")
            return []

    def get_memory_count(self) -> int:
        """获取记忆数量"""
        if not self.collection:
            return 0
        try:
            return self.collection.count()
        except:
            return 0

    def clear_memories(self) -> bool:
        """清空所有记忆"""
        if not self.collection:
            return False

        try:
            # 获取所有ID
            all_data = self.collection.get()
            if all_data.get('ids'):
                self.collection.delete(ids=all_data['ids'])
                print("🧹 已清空所有向量记忆")
                return True
        except Exception as e:
            print(f"⚠️ 清空向量记忆失败: {e}")

        return False

    def get_all_memories(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取所有记忆（用于调试）"""
        if not self.collection:
            return []

        try:
            results = self.collection.get(limit=limit)
            memories = []

            if results.get('documents'):
                for i, doc in enumerate(results['documents']):
                    metadata = results.get('metadatas', [{}])[i] if results.get('metadatas') else {}
                    memory_id = results.get('ids', [''])[i] if results.get('ids') else ''

                    memories.append({
                        "id": memory_id,
                        "content": doc,
                        "metadata": metadata
                    })

            return memories
        except Exception as e:
            print(f"⚠️ 获取所有记忆失败: {e}")
            return []


# 简化的向量数据库（用于测试或回退）
class SimpleVectorDB:
    """简化版向量数据库，用于测试或回退"""

    def __init__(self):
        self.memories = []
        print("⚠️ 使用简化版向量数据库（仅用于测试）")

    def add_memory(self, content: str, metadata: Optional[Dict] = None) -> bool:
        try:
            from datetime import datetime
            import uuid

            memory = {
                "id": f"simple_{uuid.uuid4().hex[:8]}",
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            self.memories.append(memory)
            return True
        except:
            return False

    def search(self, query: str, top_k: int = 3, min_score: float = 0.5) -> List[Dict[str, Any]]:
        """简化搜索：基于关键词匹配"""
        if not query or not self.memories:
            return []

        results = []
        query_lower = query.lower()

        for memory in self.memories:
            content = memory.get("content", "").lower()

            # 简单关键词匹配
            if query_lower in content:
                score = 0.7  # 默认分数

                # 计算匹配度
                words_query = set(query_lower.split())
                words_content = set(content.split())
                if words_query and words_content:
                    common = len(words_query.intersection(words_content))
                    total = len(words_query.union(words_content))
                    if total > 0:
                        score = common / total

                if score >= min_score:
                    results.append({
                        "content": memory["content"],
                        "score": round(score, 3),
                        "timestamp": memory.get("timestamp", ""),
                        "metadata": memory.get("metadata", {})
                    })

        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def get_memory_count(self) -> int:
        return len(self.memories)

    def clear_memories(self) -> bool:
        self.memories = []
        return True


# 创建向量数据库工厂函数
def create_vector_db(use_chromadb: bool = True) -> VectorDB:
    """
    创建向量数据库实例

    Args:
        use_chromadb: 是否使用 ChromaDB，如果为 False 则使用简化版

    Returns:
        VectorDB 实例
    """
    if use_chromadb:
        try:
            return VectorDB()
        except Exception as e:
            print(f"⚠️ 创建 ChromaDB 失败，使用简化版: {e}")

            # 回退到简化版
            class HybridVectorDB(VectorDB):
                def __init__(self):
                    self.simple_db = SimpleVectorDB()
                    self.collection = None

                def add_memory(self, content: str, metadata=None):
                    return self.simple_db.add_memory(content, metadata)

                def search(self, query: str, top_k=3, min_score=0.5):
                    return self.simple_db.search(query, top_k, min_score)

                def get_memory_count(self):
                    return self.simple_db.get_memory_count()

                def clear_memories(self):
                    return self.simple_db.clear_memories()

            return HybridVectorDB()
    else:
        # 直接使用简化版
        class SimpleWrapper(SimpleVectorDB):
            def __init__(self):
                super().__init__()

        return SimpleWrapper()