import os
from time import sleep

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not API_KEY:
    raise SystemExit("未找到 DASHSCOPE_API_KEY / ALYUN_API_KEY，请检查 .env")

# 阿里云百炼的 OpenAI 兼容接口
client = OpenAI(
    api_key=API_KEY,
    base_url="https://ws-bc3k0tje8xskzr6z.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
    max_retries=0,
    timeout=30,
)

MODEL = os.getenv("DASHSCOPE_MODEL", "qwen3.8-flash")

question = """回复一个字：好！
"""

response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": question}],
)

for i in range(8):
    print(response.choices[0].message.content)
    sleep(0.5)
