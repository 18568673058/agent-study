import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    raise SystemExit("未找到 DEEPSEEK_API_KEY，请检查 .env")

# DeepSeek 官方 OpenAI 兼容接口
client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.deepseek.com",
)

MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

question = """我上个月的报销单为什么被驳回了？
"""

response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": question}],
)

print(response.choices[0].message.content)