# core/api_client.py
import json
import time
import hashlib
from functools import lru_cache, wraps
from typing import List, Dict, Any, Optional
from zhipuai import ZhipuAI  # 新版本导入方式
from config import ZHIPU_API_KEY, ZHIPU_MODEL
import requests


def retry_on_failure(max_retries=3, delay=1, backoff=2):
    """重试装饰器，支持指数退避"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        print(f"⚠️ 尝试 {attempt + 1}/{max_retries} 失败，{current_delay}秒后重试: {str(e)[:100]}...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        print(f"❌ 所有 {max_retries} 次尝试均失败")

            raise last_exception
        return wrapper
    return decorator


class ZhipuAIClient:
    """智谱AI客户端封装（新版本v2.x+）"""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or ZHIPU_API_KEY
        self.model = model or ZHIPU_MODEL

        if not self.api_key:
            raise ValueError("请提供智谱AI API Key")

        # 新版本初始化方式
        self.client = ZhipuAI(api_key=self.api_key)
        print(f"✅ 智谱AI客户端(v2.x+)初始化完成，使用模型: {self.model}")

    @retry_on_failure(max_retries=3, delay=2)
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天补全接口（新版本方式）"""
        params = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 2000),
            "top_p": kwargs.get("top_p", 0.7),
        }

        # 移除空值参数
        params = {k: v for k, v in params.items() if v is not None}

        try:
            # 新版本调用方式
            response = self.client.chat.completions.create(**params)

            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                raise Exception("API响应中没有有效的内容")

        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower() or "额度" in error_msg.lower():
                print("⚠️ 注意：API额度可能不足，请检查账户余额")
            raise

    @lru_cache(maxsize=100)
    def cached_chat_completion(self, message_hash: str, messages_json: str) -> str:
        """带缓存的聊天补全，避免重复请求"""
        messages = json.loads(messages_json)
        return self.chat_completion(messages)

    def generate_message_hash(self, messages: List[Dict[str, str]]) -> str:
        """生成消息的哈希值，用于缓存"""
        messages_str = json.dumps(messages, sort_keys=True)
        return hashlib.md5(messages_str.encode()).hexdigest()


def chat_completion(messages: List[Dict[str, str]], max_tokens: int = 2000,
                   temperature: float = 0.7, model: str = None, **kwargs) -> str:
    """
    统一的聊天补全API调用

    Args:
        messages: 消息列表
        max_tokens: 最大token数
        temperature: 生成温度
        model: 模型名称
        **kwargs: 其他参数

    Returns:
        生成的文本响应
    """
    try:
        # 创建客户端实例
        client = ZhipuAIClient()

        # 调用聊天补全
        return client.chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
            **kwargs
        )
    except Exception as e:
        print(f"❌ API调用失败: {e}")
        # 对于记忆压缩等情况，返回一个简单的错误信息
        if len(messages) > 0 and "summary" in messages[-1]["content"].lower():
            return f"记忆压缩失败: {str(e)[:100]}"
        raise


def generate_response(prompt: str, max_tokens: int = 200, temperature: float = 0.3, **kwargs) -> str:
    """
    生成响应，专门用于记忆压缩等场景

    Args:
        prompt: 提示文本
        max_tokens: 最大token数
        temperature: 生成温度
        **kwargs: 其他参数

    Returns:
        生成的文本响应
    """
    messages = [{"role": "user", "content": prompt}]

    try:
        return chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
    except Exception as e:
        print(f"❌ 生成响应失败: {e}")
        # 返回一个基本的响应，避免程序崩溃
        if "总结" in prompt or "compress" in prompt.lower():
            return "对话总结: 由于API调用失败，无法生成完整总结。"
        return f"响应生成失败: {str(e)[:100]}"


class APIClientFactory:

    @staticmethod
    def create_client(provider="zhipu", **kwargs):
        """创建API客户端实例"""
        if provider == "zhipu":
            return ZhipuAIClient(**kwargs)
        else:
            raise ValueError(f"不支持的API提供商: {provider}")


# 导出
__all__ = [
    "APIClientFactory",
    "ZhipuAIClient",
    "chat_completion",
    "generate_response"
]