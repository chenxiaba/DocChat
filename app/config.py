import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
API_BASE = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1")

# 统一数据存储路径到data目录
DB_PATH = "data/memory.sqlite"
VECTOR_DB_PATH = "data/vector_store"
CHAT_HISTORY_PATH = "data/chat_history.pkl"
