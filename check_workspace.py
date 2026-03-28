import os
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import WORKSPACE_DIR


def check_workspace():
    """检查工作区配置"""
    print("=" * 50)
    print("工作区配置检查")
    print("=" * 50)

    print(f"配置的WORKSPACE_DIR: {WORKSPACE_DIR}")
    print(f"绝对路径: {WORKSPACE_DIR.resolve()}")
    print(f"是否存在: {WORKSPACE_DIR.exists()}")
    print(f"是否是目录: {WORKSPACE_DIR.is_dir()}")

    if WORKSPACE_DIR.exists():
        print(f"\n工作区内容:")
        for item in WORKSPACE_DIR.iterdir():
            if item.is_file():
                print(f"  📄 {item.name} ({item.stat().st_size} 字节)")
            elif item.is_dir():
                print(f"  📁 {item.name}/")

    # 检查当前工作目录
    print(f"\n当前工作目录: {os.getcwd()}")

    # 检查相对路径
    relative_path = Path("./workspace")
    print(f"相对路径 './workspace': {relative_path.resolve()}")


if __name__ == "__main__":
    check_workspace()