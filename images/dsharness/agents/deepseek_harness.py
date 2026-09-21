#!/usr/bin/env python3
"""DeepSeek Harness：基于 OpenAI 兼容接口（TokenHub → DeepSeek）的极简 agent 框架。

设计（零第三方依赖，urllib 实现）：
  - chat()          单轮对话（改写/判读类任务）
  - run_task()      工具调用循环（解题类任务）：LLM 决策 → 工具执行 → 结果回填
                    → 直至给出最终答案或达轮次上限
  - 环境变量：OPENAI_BASE_URL / OPENAI_API_KEY / LLM_MODEL（默认 deepseek-v4-flash）

两个使用方：
  agent1（maker）：改写链——issue + 仓库上下文 → 自包含题目（含忠实性自检）
  agent2（validator Phase B）：解题链——题目 + 仓库 → 修复补丁（工具=沙箱内命令）
"""
import json
import os
import re
import time
import urllib.request


class HarnessError(Exception):
    pass


class DeepSeekHarness:
    def __init__(self, base_url=None, api_key=None, model=None, timeout=120):
        self.base = (base_url or os.environ.get("OPENAI_BASE_URL", "")).rstrip("/")
        self.key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model or os.environ.get("LLM_MODEL") \
            or os.environ.get("HERMES_MODEL", "deepseek-v4-flash")
        self.timeout = timeout
        if not (self.base and self.key):
            raise HarnessError("未配置 OPENAI_BASE_URL / OPENAI_API_KEY")

    @property
    def available(self):
        return bool(self.base and self.key)

    # ---------------- 单轮对话 ----------------
    def chat(self, messages, temperature=0.2, max_tokens=4096, retries=3, tools=None):
        payload = {"model": self.model, "messages": messages,
                   "temperature": temperature, "max_tokens": max_tokens}
        if tools:
            payload["tools"] = tools    # 原生 function-calling（deepseek-flash 实测支持）
        delay = 3
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(
                    self.base + "/chat/completions",
                    data=json.dumps(payload).encode(),
                    headers={"Authorization": f"Bearer {self.key}",
                             "Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    data = json.loads(r.read().decode())
                choice = data["choices"][0]
                msg = choice.get("message", {})
                # 推理型模型（deepseek-v4-flash 等）：reasoning 先消耗 token 预算，
                # 预算不足时 content 为空且 finish_reason=length → 预算翻倍重试
                if not (msg.get("content") or "").strip() \
                        and choice.get("finish_reason") == "length":
                    payload["max_tokens"] = min(payload["max_tokens"] * 4, 16384)
                    continue
                return msg
            except Exception as e:
                if attempt < retries:
                    time.sleep(delay)
                    delay = min(delay * 2, 30)
                    continue
                raise HarnessError(f"LLM 调用失败({self.model}): {str(e)[:200]}")

    # ---------------- 工具调用循环 ----------------
    # 文本协议兜底：deepseek-v4-flash 等模型不走原生 function-calling，
    # 而是输出伪 XML（<execute command="..."/>）——识别并执行之
    TEXT_CMD_RE = re.compile(r'<execute\s+command="([^"]+)"\s*/?>')

    def run_task(self, system, task, tools, exec_fn, max_turns=15):
        """通用解题循环（原生 tool_calls + 文本协议双通道）。"""
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": task}]
        transcript = []
        for turn in range(1, max_turns + 1):
            msg = self.chat(messages, temperature=0.2, max_tokens=4096, tools=tools)
            content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls") or []
            # 文本协议通道：无 tool_calls 但内容含 <execute command="..."/>
            if not tool_calls:
                cmds = self.TEXT_CMD_RE.findall(content)
                if cmds:
                    messages.append({"role": "assistant", "content": content})
                    for cmd in cmds[:5]:        # 单轮最多执行 5 条
                        try:
                            result = exec_fn("run_command", {"command": cmd})
                        except Exception as e:
                            result = f"ERROR: {type(e).__name__}: {str(e)[:200]}"
                        transcript.append({"turn": turn, "tool": "run_command(text)",
                                           "args": {"command": cmd},
                                           "result_head": str(result)[:200]})
                        messages.append({"role": "user",
                                         "content": f"[命令输出]\n{str(result)[:8000]}\n"
                                                    f"（继续，直到完成修复后给出简要说明）"})
                    continue
                return {"answer": content.strip(),
                        "turns": turn, "status": "done", "transcript": transcript}
            messages.append({"role": "assistant", "content": content,
                             "tool_calls": tool_calls})
            for tc in tool_calls:
                fn = tc["function"]
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                    result = exec_fn(fn["name"], args)
                except Exception as e:
                    result = f"ERROR: {type(e).__name__}: {str(e)[:200]}"
                transcript.append({"turn": turn, "tool": fn["name"], "args": args,
                                   "result_head": str(result)[:200]})
                messages.append({"role": "tool", "tool_call_id": tc["id"],
                                 "content": str(result)[:8000]})
        return {"answer": "", "turns": max_turns, "status": "max_turns",
                "transcript": transcript}


# ---------------- agent1 改写链 ----------------
def _core_ids(text):
    """核心标识符 = 属性链（time.sleep）与下划线词（_generator）。
    普通英文单词不纳入（中文改写会转述，实测普通词拉低保留率误伤合格改写）。"""
    core = set(re.findall(r"\b[\w]+\.[\w.]+", text))
    core |= set(re.findall(r"\b\w*_\w+\b", text))
    return core


def rewrite_problem(harness, issue_title, issue_body, repo, touched, f2p_names):
    """issue → 自包含题目。改写 + 核心标识符忠实性校验（不过则带反馈重试一次）。"""
    ctx = (f"仓库: {repo}\n涉及文件: {', '.join(touched[:10])}\n"
           f"评分测试（F2P）: {', '.join(f2p_names[:8])}")
    prompt = (
        "把以下 GitHub issue 改写为自包含的编程任务描述，供 AI 编程助手独立求解。\n"
        "要求：\n"
        "1. 中文，100-400 词，不引用外部对话/链接/人名\n"
        "2. 保留所有代码标识符（函数名/类名/参数名/报错消息原文）——这是忠实性红线\n"
        "3. 补充行为级验收标准（何时算修好）\n"
        "4. 不包含测试代码与修复提示\n\n"
        f"【上下文】{ctx}\n\n【issue 标题】{issue_title}\n\n【issue 正文】{issue_body}\n\n"
        "输出改写后的任务描述（Markdown，一级标题开头），不要其他内容。")

    def _rewrite(extra=""):
        out = harness.chat([{"role": "user", "content": prompt + extra}],
                           temperature=0.1, max_tokens=4096)
        return (out.get("content") or "").strip()

    text = _rewrite()
    core = _core_ids(issue_title + issue_body)
    if not core:
        return text, 1.0

    def _ratio(t):
        return sum(1 for i in core if i in t) / len(core)

    ratio = _ratio(text)
    if ratio < 0.5:
        # 带反馈重试：明确列出必须保留的标识符
        missing = sorted(i for i in core if i not in text)[:15]
        text2 = _rewrite(f"\n\n【重要】以下标识符必须在任务描述中原样出现："
                         f"{', '.join(missing)}")
        ratio2 = _ratio(text2)
        if ratio2 < 0.5:
            raise HarnessError(
                f"忠实性校验不过（核心标识符保留率 {ratio:.0%}→{ratio2:.0%}），拒绝使用")
        return text2, ratio2
    return text, ratio
