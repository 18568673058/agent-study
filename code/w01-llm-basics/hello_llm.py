"""W1 最小调用：阿里云百炼 / DashScope 的 OpenAI 兼容接口。

运行前：
1. 复制 .env.example 为 .env
2. 填入 DASHSCOPE_API_KEY（或沿用 ALYUN_API_KEY）
3. 在项目目录执行：python hello_llm.py

注意：任何时候都不要把 key 打印出来或提交到 Git。
"""

import os

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
)

MODEL = os.getenv("DASHSCOPE_MODEL", "qwen3.8-flash")

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "user", "content": "用一句话介绍你自己，并说明你是什么模型。"}
    ],
)

print(response.choices[0].message.content)

if response.usage:
    print(
        "tokens: "
        f"prompt={response.usage.prompt_tokens}, "
        f"completion={response.usage.completion_tokens}, "
        f"total={response.usage.total_tokens}"
    )
