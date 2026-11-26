# W1：LLM API 与成本基线

> 产出物不是"跑通三个 hello world"，而是 `notes/api-baseline.md` 里那张能回答"多少钱、多快、谁中文好"的表。

## 文件清单

| 文件 | 作用 |
|---|---|
| `hello_llm.py` | 最小调用（百炼），验证 key 和网络 |
| `bench.py` | 三家的延迟 / token / 成本测量。**当前作为"答案册"，先试着自己写一版** |
| `timing.py` | 待写：单次调用计时，练 `perf_counter` + `resp.usage` |
| `results/baseline.csv` | 实测结果，追加写入。可提交，是学习证据 |
| `.env` | 真实 key，**永不提交** |
| `.env.example` | 模板，可提交 |
| `requirements.txt` | 依赖清单 |

## 虚拟环境（重要）

本目录有自己的 `.venv`，**依赖不装在全局**。所有命令直接用 venv 里的解释器，不需要"激活"：

```powershell
cd "D:\DeepSeek Harness\project\Agents开发学习路线\code\w01-llm-basics"

.\.venv\Scripts\python.exe hello_llm.py
.\.venv\Scripts\python.exe bench.py
.\.venv\Scripts\ruff.exe check .
```

**为什么不 `Activate.ps1`**：本机 PowerShell 执行策略是 Restricted，脚本会被拦。直接调 `.exe` 效果一样，还少一层状态。

装新依赖也用它：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## keys

`.env` 里两个都配好了（百炼 / DeepSeek）。变量名必须和 `bench.py` 里的 `env` 字段一致：

```text
DASHSCOPE_API_KEY=...
DEEPSEEK_API_KEY=...
```

## 注意

- `.env` 已在 `.gitignore` 里，不会被提交。**每次 push 前亲眼确认一次**。
- 不要把 `.env` 发到聊天、截图或 GitHub。泄露了立刻去平台撤销重发。
- 运行脚本前先 `cd` 到本目录，`load_dotenv()` 才能稳定找到 `.env`。
- `results/` 会进 git（不忽略），这样每次重跑的对比都留得下。
