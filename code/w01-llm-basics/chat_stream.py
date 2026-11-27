r"""W2 Day1：流式输出 + 首字延迟。

跑法：
    cd code\w01-llm-basics
    .\.venv\Scripts\python.exe chat_stream.py

四个容易错的地方（都在这一个循环里）：
    1. t0 必须放在 create() 之前 —— 放后面会漏掉"建连接 + 首字节到达"的时间
    2. 片段和全文必须是两个变量 —— 混用会打出"你你好你好！"这种雪球
    3. 首字延迟要在第一个非空片段出现时记，且只记一次
    4. 流式下 usage 在最后一个包，那个包的 choices 是空列表
"""

import os
import time

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"

# 问题要够长，否则看不出逐字效果（"你好"两个字，流不流式都是瞬间出现）
QUESTION = "用三句话解释什么是 token，每句不超过 20 字"


def main():
    if not API_KEY:
        raise SystemExit("没读到 DEEPSEEK_API_KEY，检查 .env")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=60)

    t0 = time.perf_counter()  # ← 必须在 create() 之前
    t1 = None                 # 首字时刻，占位
    full = ""                 # 全文，只用于最后校验
    usage = None              # token 统计，最后一个包里才有

    try:
        stream = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": QUESTION}],
            stream=True,
            stream_options={"include_usage": True},  # 不加这个，usage 永远是 None
        )

        for chunk in stream:
            # usage 出现在最后一个包。但各家实现不同：
            #   OpenAI 官方 -> 单独一个包，choices 为空
            #   DeepSeek   -> 挂在带 finish_reason 的那个包上，choices 不为空
            # 所以在每个包里都查一次，不要假设"只有空 choices 的包才有 usage"。
            if chunk.usage:
                usage = chunk.usage

            if not chunk.choices:
                continue

            piece = chunk.choices[0].delta.content  # 片段：这一包新给的字
            if not piece:                           # 首包只有 role、尾包只有 finish_reason
                continue

            if t1 is None:                          # 只在第一个字出现时记一次
                t1 = time.perf_counter()

            print(piece, end="", flush=True)        # flush：不缓冲，立刻显示
            full += piece                           # 全文：单独累加

        t2 = time.perf_counter()

    except OpenAIError as e:
        # 只打类型和截断后的信息，避免异常信息带出请求头
        print(f"\n调用失败：{type(e).__name__}: {str(e)[:100]}")
        return

    print("\n")
    ttft = (t1 - t0) if t1 else float("nan")
    total = t2 - t0
    print(f"首字延迟 {ttft:.2f}s | 总耗时 {total:.2f}s | 全文 {len(full)} 字")

    if usage:
        print(f"tokens  prompt={usage.prompt_tokens} completion={usage.completion_tokens}")
        # 生成速度：扣掉首字等待，剩下的才是模型吐字的速度
        gen = total - ttft
        if gen > 0 and usage.completion_tokens:
            print(f"生成速度 {usage.completion_tokens / gen:.1f} tok/s（已扣除首字等待）")
    else:
        print("没拿到 usage —— 检查 stream_options 是否生效")


if __name__ == "__main__":
    main()
