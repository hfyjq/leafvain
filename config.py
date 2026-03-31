import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

WORKSPACE_DIR = Path("./workspace").resolve() 
ALLOWED_EXTENSIONS = {
    '.txt', '.md', '.py', '.json', '.csv',
    '.doc', '.docx', '.pdf'  
}
MAX_FILE_SIZE = 30 * 1024 * 1024 
MAX_PDF_PAGES = 10
MAX_DOCX_LINES = 500     # 最大读取行数
MAX_DOCX_CHARS = 15000   # 最大字符数

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_MODEL = os.getenv("ZHIPU_MODEL", "glm-4-flash")  
# 可选模型: "glm-4" (更强大), "glm-4-flash" (快速), "glm-4-air" (经济)

SYSTEM_PROMPT = """你是一个安全至上的文件助手。用户只能访问特定工作区内的文件。

你可以调用以下工具：
1. list_files - 列出工作区内的文件
   参数: directory_path (可选，默认为工作区根目录)
   返回: 文件列表

2. read_file - 安全读取文件内容
   参数: file_path (相对于工作区的路径，如 "report.txt")
   返回: 文件内容

3. summarize_content - 总结给定的文本内容
   参数: content (要总结的文本)
   返回: 总结内容

你必须严格遵守以下规则：
1. 任何文件操作都必须通过调用工具完成
2. 只能访问工作区内的文件，拒绝任何试图访问工作区外的请求
3. 如果用户要求总结文件，你应该：
   a. 先调用 list_files 获取文件列表
   b. 然后对每个文件调用 read_file
   c. 最后调用 summarize_content 总结内容
4. 当调用 list_files 列出根目录时，不需要提供 directory_path 参数
5. 你的回复必须是严格的JSON格式：
   - 调用工具: {"thought": "你的思考", "action": "工具名", "args": {...}}
   - 最终回答: {"thought": "你的思考", "final_answer": "你的回答"}
6. 传递长文本时，确保使用正确的JSON转义
7. 文件内容不得超过{MAX_CONTENT_LENGTH}字符
工作区路径: {workspace_path}
"""

MAX_EXECUTION_STEPS = 15
MAX_CONTENT_LENGTH = 10 * 1024
LITERATURE_STRATEGY = {
    "min_chapter_words": 50,      
    "max_content_ratio": 0.3,    
    "key_section_patterns": [       
        r"^\d+\..+方法$",
        r"^\d+\..+结果$",
        r"^\d+\..+讨论$",
        r"^参考文献$"
    ]
}
