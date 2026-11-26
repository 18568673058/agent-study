import os
import sys
import time

import dotenv
import openai
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

PROVIDERS = {
    "bl": {
        "env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3.8-flash",
    },
    "ds": {
        "env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
}
which = sys.argv[1] if len(sys.argv) > 1 else "bl"

p = PROVIDERS[which]

client = OpenAI(
    api_key=os.getenv(p["env"]),
    base_url=p["base_url"],
    max_retries=0,
    timeout=30,
)

TOTAL = 8        # 只发 8 次，别贪多
INTERVAL = 0.2   # 间隔秒数
MODEL = p["model"]

first_error_at = None

for i in range(1, TOTAL + 1):
    start = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "回复一个字：好"}],
            max_tokens=5,          # 压测别烧 token
        )
        cost = time.perf_counter() - start
        print(f"{i:>2} 次  OK      {cost:.2f}s")
    except openai.RateLimitError as e:
        print(f"{i:>2} 次  429 限流  {str(e)[:80]}")
        if first_error_at is None:
            first_error_at = i
    except openai.OpenAIError as e:
        print(f"{i:>2} 次  其他错误  {type(e).__name__}")
    time.sleep(INTERVAL)

print()
print("首次触发：", f"第 {first_error_at} 次" if first_error_at else "未触发")
