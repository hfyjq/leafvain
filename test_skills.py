# test_skills_final.py
# !/usr/bin/env python3
"""
最终技能系统测试脚本
测试修复后的技能与现有工具的完全兼容性
"""
import sys
import os
from pathlib import Path

# 添加到系统路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def test_final_skill_system():
    """测试修复后的技能系统"""
    print("=" * 60)
    print("🧪 最终技能系统测试")
    print("=" * 60)

    # 初始化技能管理器
    try:
        from core.skill_manager import SkillManager
        from core.skill_matcher import SkillMatcher

        skill_manager = SkillManager("skills")
        skill_manager.load_skills()

        print(f"\n✅ 成功加载 {len(skill_manager.skills)} 个技能")

        # 测试文件技能
        file_skill = skill_manager.get_skill("file")
        if file_skill:
            print("\n📁 测试文件技能:")

            # 测试列出文件
            print("1. 测试 list_files:")
            try:
                result = file_skill.execute("list_files", directory_path=".", recursive=False)
                print(f"   结果: {result.get('success', False)}")
                print(f"   文件数: {result.get('count', 0)}")
            except Exception as e:
                print(f"   ❌ 失败: {e}")

            # 测试总结内容
            print("\n2. 测试 summarize_content:")
            try:
                test_content = "这是一段测试文本。" * 100
                result = file_skill.execute("summarize_content", content=test_content, max_length=100)
                print(f"   结果: {result.get('success', False)}")
                if result.get('success'):
                    print(f"   总结长度: {result.get('summary_length', 0)}")
            except Exception as e:
                print(f"   ❌ 失败: {e}")

        # 测试日程技能
        schedule_skill = skill_manager.get_skill("schedule")
        if schedule_skill:
            print("\n📅 测试日程技能:")

            # 测试列出日程
            print("1. 测试 list_schedules:")
            try:
                result = schedule_skill.execute("list_schedules", future_only=True)
                print(f"   结果: {result.get('success', False)}")
                print(f"   日程数: {result.get('count', 0)}")
            except Exception as e:
                print(f"   ❌ 失败: {e}")

            # 测试添加日程
            print("\n2. 测试 add_schedule (ISO格式):")
            try:
                result = schedule_skill.execute("add_schedule",
                                                event="测试会议",
                                                event_time="2024-12-25T10:00",
                                                remind_before=15)
                print(f"   结果: {result.get('success', False)}")
                if result.get('success'):
                    print(f"   消息: {result.get('message', '')}")
            except Exception as e:
                print(f"   ❌ 失败: {e}")

            # 测试添加日程（自然语言时间）
            print("\n3. 测试 add_schedule (自然语言时间):")
            try:
                result = schedule_skill.execute("add_schedule",
                                                event="明天测试",
                                                event_time="明天上午10点",
                                                remind_before=0)
                print(f"   结果: {result.get('success', False)}")
                if result.get('success'):
                    print(f"   消息: {result.get('message', '')}")
                else:
                    print(f"   错误: {result.get('error', '未知')}")
            except Exception as e:
                print(f"   ⚠️ 可能的时间解析错误: {e}")

        # 测试技能匹配
        print("\n🔍 测试技能匹配:")
        skill_matcher = SkillMatcher(skill_manager)

        test_cases = [
            ("总结文档内容", "应该匹配文件技能的summarize_content"),
            ("添加明天的会议", "应该匹配日程技能的add_schedule"),
            ("删除日程", "应该匹配日程技能的remove_schedule_by_description"),
        ]

        for query, expected in test_cases:
            print(f"\n查询: '{query}'")
            matches = skill_matcher.match_skills(query)

            if matches:
                best_match = matches[0]
                print(f"   最佳匹配: {best_match['skill'].name} (分数: {best_match['score']:.1f})")
                print(f"   原因: {best_match['reason'][:80]}...")

                # 显示技能功能
                functions = best_match['manifest'].get('functions', [])
                if functions:
                    print(f"   可用功能: {', '.join([f['name'] for f in functions[:3]])}")
            else:
                print("   ❌ 未找到匹配技能")

        # 保存注册表
        skill_manager.save_registry()

        # 显示技能清单
        print("\n📋 最终技能清单:")
        manifests = skill_manager.get_all_manifests()
        for skill_id, manifest in manifests.items():
            print(f"\n🔧 {manifest['name']} (v{manifest['version']}):")
            print(f"   描述: {manifest['description'][:80]}...")
            print(f"   功能: {len(manifest.get('functions', []))} 个")
            print(f"   标签: {', '.join(manifest.get('tags', [])[:5])}")

        print("\n" + "=" * 60)
        print("✅ 最终技能系统测试完成!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_final_skill_system()
    sys.exit(0 if success else 1)