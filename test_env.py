# test_env.py
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 读取配置
api_key = os.getenv("ZHIPU_API_KEY")
model = os.getenv("ZHIPU_MODEL")

print(f"API Key: {'✅ 已设置' if api_key and api_key != 'your_actual_api_key_here' else '❌ 未设置或为默认值'}")
print(f"模型: {model}")
print(f"工作目录: {os.getcwd()}")
print(f".env文件存在: {os.path.exists('.env')}")