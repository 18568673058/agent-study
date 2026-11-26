r"""W1 日志脱敏练习。

三个目标：
    1. 打码函数：任何密钥只露出前 4 位，短的一律全遮
    2. 用 logging 替代 print：格式统一、可分级、可挂 Filter
    3. 验证异常路径也不漏 —— 这是三项里唯一真正的验证

跑法：
    cd code\w01-llm-basics
    .\.venv\Scripts\python.exe safe_log.py
"""

import logging
import os
import re

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

load_dotenv()

KEEP = 4  # 保留前几位可见
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen3.8-flash"


def mask(value):
    """把密钥打码。

    三条规则，顺序不能乱：
        1. None / 空串 -> 明确标记，不要抛异常
        2. 短到没法安全遮掩 -> 全遮，绝不原样返回
        3. 正常长度 -> 前 4 位 + 星号

    str(value) 是最后一道防线：万一传进来的是元组（比如赋值时多写了一个
    逗号得到 ("sk-xxx",)），这里会先转成字符串，而不是让 len() 算出 1
    然后走进"短字符串"分支把原文吐出去。
    """
    if not value:
        return "<empty>"

    text = str(value)
    if len(text) <= 8:
        return "*" * len(text)

    return text[:KEEP] + "*" * (len(text) - KEEP)


class SecretFilter(logging.Filter):
    """在日志出口统一抹掉形如 sk-xxxx 的串。

    这才是 logging 比 print 强的关键：
        - print 散落在代码各处，只能靠每次都记得手动打码，而人一定会忘
        - logging 可以在 handler 上挂一个 Filter，一处配置、全局生效

    哪怕哪天有人写了 log.info(f"key={key}") 这种要命的代码，这里也能兜住。
    """

    PATTERN = re.compile(r"(sk-[A-Za-z0-9_\-]{4})[A-Za-z0-9_\-]+")

    def filter(self, record):
        # 先把带参数的记录渲染成完整字符串，再替换，最后清空 args
        message = record.getMessage()
        record.msg = self.PATTERN.sub(r"\1****", message)
        record.args = ()
        return True


def setup_logging():
    """统一配置：时间 + 级别 + 内容，所有输出都过一遍 SecretFilter。"""
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-5s %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    handler.addFilter(SecretFilter())

    logger = logging.getLogger("safe")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def main():
    log = setup_logging()

    # ---------- 1. 打码函数自检：边界先测，而且必须用假数据 ----------
    log.info("--- 打码边界测试（假数据，绝不拿真 key 试） ---")
    for sample in [None, "", "abc", "sk-fake1234567890"]:
        log.info("mask(%r) -> %s", sample, mask(sample))

    key = os.getenv("DASHSCOPE_API_KEY")
    if not key:
        log.error("没读到 DASHSCOPE_API_KEY，检查 .env")
        return

    # 入口处先打码，Filter 只当第二道防线
    log.info("使用 key：%s", mask(key))

    client = OpenAI(api_key=key, base_url=BASE_URL, max_retries=0, timeout=30)

    # ---------- 2. 正常路径 ----------
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "回复一个字：好"}],
            max_tokens=5,
        )
        assert resp.usage is not None
        log.info(
            "调用成功 tokens=%s+%s",
            resp.usage.prompt_tokens,
            resp.usage.completion_tokens,
        )
    except OpenAIError:
        log.exception("正常路径意外失败")

    # ---------- 3. 异常路径：这里最容易把整个请求头打出来 ----------
    try:
        client.chat.completions.create(
            model="not-exist-model-xyz",
            messages=[{"role": "user", "content": "好"}],
            max_tokens=5,
        )
    except OpenAIError:
        log.exception("预期的错误：模型名不存在")

    log.info("--- 检查完毕：上方所有日志里都不应出现完整的 sk- 串 ---")


if __name__ == "__main__":
    main()
