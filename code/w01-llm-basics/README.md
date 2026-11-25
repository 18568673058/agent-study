# W1：LLM API 与成本基线

这个目录是 W1 的代码目录。`.env` 放在这里，和 `hello_llm.py` 同级。

## 第一次使用

在 PowerShell 里进入本目录：

```powershell
cd "D:\DeepSeek Harness\project\Agents开发学习路线\code\w01-llm-basics"
```

复制模板并填入真实 key：

```powershell
Copy-Item .env.example .env
code .env
```

`.env` 内容示例：

```text
DEEPSEEK_API_KEY=sk-你的真实key
```

## 注意

- `.env` 已在 `.gitignore` 里，不会被提交。
- 不要把 `.env` 发到聊天、截图或 GitHub。
- 如果 key 泄露，立刻去平台撤销并重新生成。
- 运行脚本时，先在 PowerShell 里 `cd` 到本目录，`load_dotenv()` 才能稳定找到 `.env`。
