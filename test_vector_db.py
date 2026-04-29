# test_vector_db.py
import sys
from pathlib import Path

# 添加到系统路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

try:
    from core.vector_db import create_vector_db

    print("🔧 测试向量数据库...")

    # 创建向量数据库实例
    vector_db = create_vector_db()

    # 测试添加记忆
    test_memories = [
        "我今天学习了Python编程",
        "明天要参加AI技术研讨会",
        "项目需要在周五前完成",
        "Python的列表推导式很强大",
        "机器学习需要大量数据"
    ]

    print("📝 添加测试记忆...")
    for i, memory in enumerate(test_memories):
        success = vector_db.add_memory(memory, {"index": i})
        if success:
            print(f"  ✅ 添加记忆 {i + 1}: {memory[:30]}...")

    # 获取记忆数量
    count = vector_db.get_memory_count()
    print(f"\n📊 记忆总数: {count}")

    # 测试搜索
    test_queries = ["Python", "AI", "项目", "机器学习"]

    for query in test_queries:
        print(f"\n🔍 搜索: '{query}'")
        results = vector_db.search(query, top_k=2)

        if results:
            for i, result in enumerate(results):
                print(f"  [{i + 1}] 相似度: {result['score']}")
                print(f"      内容: {result['content'][:50]}...")
        else:
            print("  ❌ 无匹配结果")

    # 测试清空
    print(f"\n🧹 清空向量数据库...")
    if hasattr(vector_db, 'clear_memories'):
        vector_db.clear_memories()
        print(f"✅ 清空完成，剩余记忆: {vector_db.get_memory_count()}")

    print("\n✅ 向量数据库测试完成！")

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback

    traceback.print_exc()