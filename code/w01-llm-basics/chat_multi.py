r"""W2：多轮对话 + 上下文截断。

跑法：
    cd code\w01-llm-basics
    .\.venv\Scripts\python.exe chat_multi.py

在 chat_stream.py 的基础上多了三件事：
    1. while 循环，可以连续对话
    2. messages 累积历史 —— 模型的"记忆"完全靠这个，它自己是无状态的
    3. 截断：system 永久保留，历史只留最近 KEEP_ROUNDS 轮，且必须按整轮切

三个容易错的地方：
    1. t0 必须放在 create() 之前 —— 放后面会漏掉"建连接 + 首字节到达"的时间
    2. 片段和全文必须是两个变量 —— 混用会打出"你你好你好！"这种雪球
    3. 截断只从 messages[1:] 下手，永远别碰 messages[0]（system），
       且用 KEEP_ROUNDS * 2 把"轮"换算成"条"，判断和截取用同一单位
"""

import os
import time

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessageParam

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"


def main():
    
    messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": "你是一个乐于助人的Ai助手，回复尽量简洁"}]
            
    if not API_KEY:
        raise SystemExit("没读到 DEEPSEEK_API_KEY，检查 .env")
    
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=60)
    
    KEEP_ROUNDS = 10 # 保留最近 10 轮对话
    system_msg = messages[0]
  
    
    while True:
        history = messages[1:]
        # 限制消息长度，防止上下文超限
        if len(history) > KEEP_ROUNDS * 2:
            history = history[-KEEP_ROUNDS * 2:]
        messages = [system_msg] + history
            
        user_input = input("你：")
        
        # 退出机制
        if user_input.lower() in ["q","exit","quit"]:
            break
        if not user_input.strip():
            continue
        
        # 普通机制
        messages.append({"role": "user", "content": user_input})


        t0 = time.perf_counter()  # ← 必须在 create() 之前
        t1 = None                 # 首字时刻，占位
        full = ""                 # 全文，只用于最后校验
        usage = None              # token 统计，最后一个包里才有

        try:
            stream = client.chat.completions.create(
                model=MODEL,
                messages=messages,
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
            
            messages.append({"role": "assistant", "content": full})   #记录下全文

        except OpenAIError as e:
            # 只打类型和截断后的信息，避免异常信息带出请求头
            print(f"\n调用失败：{type(e).__name__}: {str(e)[:100]}")
            messages.pop()  # 移除失败的 user 消息
            continue   # 继续下一次循环，不打印失败信息
        
        t2 = time.perf_counter()
        print()
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