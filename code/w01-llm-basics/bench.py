r"""W1 基线测试：延迟、token、成本。

用法（在 code/w01-llm-basics 目录下）：
    .\.venv\Scripts\python.exe bench.py            # 两家都跑
    .\.venv\Scripts\python.exe bench.py deepseek   # 只跑一家

产出：
    results/baseline.csv   （追加写入，不会覆盖历史）

设计要点（读懂这四行再跑）：
    1. 只测总延迟，不测 TTFT —— TTFT 要流式，W2 再说
    2. 每家跑 5 次，第 1 次丢掉（建连/冷启动会污染数据）
    3. 用中位数，不用平均值（一次偶发超时会毁掉均值）
    4. 串行 + sleep(1)，并发测到的是限流不是延迟
"""

import csv
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

load_dotenv()

# 单价：元 / 百万 token，抄自各平台定价页（见 notes/api-baseline.md 表 1）
PROVIDERS = [
    {
        "name": "百炼",
        "env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen3.8-flash",
        "price_in": 0.8,
        "price_out": 2.7,
    },
    {
        "name": "DeepSeek",
        "env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "price_in": 2.0,
        "price_out": 8.0,
    },
]

PROMPT = (
    "我们是一家做企业报销系统的公司，客户反馈上传发票后识别经常失败。"
    "请用 150 字以内分析最可能的三个原因，并按可能性从高到低排序。"
)
MAX_TOKENS = 300
TEMPERATURE = 0.3
REPEATS = 5          # 每家跑几次（第 1 次会被丢掉）
SLEEP_BETWEEN = 1.0  # 每次调用之间的间隔，防止触发限流
RESULTS_DIR = Path(__file__).parent / "results"


def call_once(client, provider):
    """调一次，返回 (延迟秒, prompt_tokens, completion_tokens, 回答文本)。"""
    start = time.perf_counter()
    resp = client.chat.completions.create(
        model=provider["model"],
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )
    latency = time.perf_counter() - start

    usage = resp.usage
    return latency, usage.prompt_tokens, usage.completion_tokens, resp.choices[0].message.content


def cost_of(p_tokens, c_tokens, provider):
    """单次成本（元）。公式：token 数 × 单价 / 100 万。"""
    return (p_tokens * provider["price_in"] + c_tokens * provider["price_out"]) / 1_000_000


def bench(provider):
    api_key = os.getenv(provider["env"])
    if not api_key:
        print(f"[跳过] {provider['name']}：环境变量 {provider['env']} 没设置")
        return None

    client = OpenAI(api_key=api_key, base_url=provider["base_url"], timeout=60)
    latencies, p_tokens, c_tokens, answer = [], 0, 0, ""

    for i in range(REPEATS):
        try:
            lat, pt, ct, answer = call_once(client, provider)
        except OpenAIError as e:
            # 只打印异常类型和第一行，避免日志里带出 key
            print(f"[失败] {provider['name']} 第 {i+1} 次：{type(e).__name__}: {str(e)[:120]}")
            time.sleep(SLEEP_BETWEEN)
            continue

        if i == 0:
            print(f"[预热] {provider['name']} 首次 {lat:.2f}s（已丢弃，不参与统计）")
        else:
            latencies.append(lat)
            p_tokens, c_tokens = pt, ct  # 同 prompt + 同参数，token 数基本恒定

        time.sleep(SLEEP_BETWEEN)

    if not latencies:
        print(f"[无数据] {provider['name']} 全部失败")
        return None

    median_lat = statistics.median(latencies)
    one_cost = cost_of(p_tokens, c_tokens, provider)

    print(
        f"[完成] {provider['name']} 中位延迟 {median_lat:.2f}s"
        f"（{', '.join(f'{x:.2f}' for x in latencies)}）"
        f" | tokens {p_tokens}+{c_tokens} | 单次 ¥{one_cost:.6f} | 1000 次 ¥{one_cost*1000:.2f}"
    )
    print(f"       回答开头：{answer[:60].replace(chr(10), ' ')}...")

    return {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "provider": provider["name"],
        "model": provider["model"],
        "latency_median_s": round(median_lat, 3),
        "latency_all_s": "/".join(f"{x:.2f}" for x in latencies),
        "prompt_tokens": p_tokens,
        "completion_tokens": c_tokens,
        "cost_one_cny": round(one_cost, 6),
        "cost_1000_cny": round(one_cost * 1000, 4),
    }


def main():
    only = sys.argv[1].lower() if len(sys.argv) > 1 else None
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / "baseline.csv"

    rows = []
    for p in PROVIDERS:
        if only and only not in p["name"].lower() and only not in p["model"].lower():
            continue
        print(f"\n=== {p['name']} / {p['model']} ===")
        r = bench(p)
        if r:
            rows.append(r)

    if not rows:
        print("\n没有任何数据。先检查 .env 里的 key。")
        return

    # 追加写入；文件不存在时先写表头
    new_file = not out.exists()
    with out.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if new_file:
            writer.writeheader()
        writer.writerows(rows)

    print(f"\n已追加 {len(rows)} 行到 {out}")

    print("\n=== 汇总（填进 notes/api-baseline.md） ===")
    print(f"{'供应商':<10}{'模型':<18}{'中位延迟':>8}{'tokens':>12}{'1000次(¥)':>12}")
    for r in rows:
        tk = f"{r['prompt_tokens']}+{r['completion_tokens']}"
        print(f"{r['provider']:<10}{r['model']:<18}{r['latency_median_s']:>7.2f}s{tk:>12}{r['cost_1000_cny']:>11.2f}")


if __name__ == "__main__":
    main()
