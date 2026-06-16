# -*- coding: utf-8 -*-
"""
STM32 开发记录助手  (Keil 打开时自动弹出)
功能:
  ① 记录 main 函数改动 / 实验目标  (可一键自动提取最近改动的 main() 函数体)
  ② 自动扫描 / 记录新建或修改的 .c / .h 文件 (含代码量统计)
  ③ AI 总结: 把本次改动 (main 函数 + 改动文件 + git diff) 喂给外部 AI,
     生成中文开发总结写入文档。默认连本地 Ollama (免费/离线/无需 Key);
     OpenAI 兼容接口直接 HTTP 调用, 不经过 agent。
  - 自动识别当前实验 (最近改动的工程文件夹)
  - 一键保存到 DEVLOG.md (排版好的 Markdown)
  - 一键上传到 GitHub: 仅当有真实改动时才提交, 未变化的文件不会重复上传
作者: 自动生成
"""
import os
import re
import sys
import json
import socket
import threading
import subprocess
import datetime
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog, scrolledtext

# ---------------------------------------------------------------------------
# 路径与配置
# ---------------------------------------------------------------------------
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROJECT_DIR = os.path.dirname(TOOLS_DIR)          # 上一级 = D:\STM32PRO
CONFIG_PATH = os.path.join(TOOLS_DIR, "config.json")
# 扫描 / 统计时忽略的目录: 构建产物 + 标准外设库 (库文件不算"本次改动")
SKIP_DIRS = {"objects", "listings", "rte", ".git", "_tools",
             "__pycache__", "dep", "out",
             "libraries", "library", "cmsis", "start", "startup"}

# 默认使用本地 Ollama (OpenAI 兼容, 免费/离线/无需 Key)。
# 换成在线服务时, 填 base_url/model/api_key 即可 (例如智谱 glm-4-flash 免费)。
DEFAULT_AI = {
    "base_url": "http://localhost:11434/v1",
    "model": "qwen2.5:3b",
    "api_key": "",
}

AI_SYSTEM_PROMPT = (
    "你是一名嵌入式开发助教。根据用户提供的 STM32 工程本次改动信息"
    "(实验名称、main 函数、改动的源文件列表、git diff), 用简体中文写一段"
    "简洁、条理清晰的开发总结, 输出 Markdown。要求:\n"
    "1. 用 2~4 句话概括本次实现了什么功能 / 解决了什么问题;\n"
    "2. 用要点列出关键改动 (涉及的外设、寄存器/库函数、配置思路);\n"
    "3. 如发现可能的 bug 或可改进点, 末尾用『💡 建议』给出 1~3 条;\n"
    "不要编造代码里没有的内容, 不要复述完整代码。"
)

# 上传 GitHub 前, 用 AI 把 commit 信息润色成一行规范的提交说明。
AI_COMMIT_PROMPT = (
    "你是一名严谨的嵌入式工程师, 负责写 git 提交信息。根据用户给出的本次改动"
    "(实验名称、改动较大的函数、改动文件列表、git diff 摘要, 以及用户原始的"
    "commit 草稿), 生成一条简洁规范的中文 commit message。要求:\n"
    "1. 只输出一行(不超过 50 个汉字), 不要任何解释、引号或 Markdown;\n"
    "2. 用动词开头, 概括做了什么(例如『新增』『修复』『优化』『重构』);\n"
    "3. 如有明确模块/外设, 用『模块: 说明』格式(例如『USART: 增加 DMA 收发』);\n"
    "4. 忠于实际改动, 不要编造代码里没有的内容。"
)


def load_config():
    cfg = {"project_dir": DEFAULT_PROJECT_DIR, "github_remote": "",
           "git_branch": "main", "ai": dict(DEFAULT_AI)}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    # 合并 ai 默认值 (用户可能只填了 api_key)
    ai = dict(DEFAULT_AI)
    ai.update(cfg.get("ai") or {})
    cfg["ai"] = ai
    if not os.path.isdir(cfg.get("project_dir", "")):
        cfg["project_dir"] = DEFAULT_PROJECT_DIR
    return cfg


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("save_config failed:", e)


# ---------------------------------------------------------------------------
# 单实例保护 (避免 Keil 多次触发时弹出多个窗口)
# ---------------------------------------------------------------------------
def acquire_single_instance(port=51763):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        s.listen(1)
        return s            # 保持引用, 进程退出前不释放
    except OSError:
        return None


# ---------------------------------------------------------------------------
# 文件扫描 / 代码统计
# ---------------------------------------------------------------------------
def scan_files(project_dir, exts, days=7):
    """返回最近 days 天内修改的指定后缀文件 (相对路径, 修改时间)。"""
    out = []
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
        for fn in files:
            if os.path.splitext(fn)[1].lower() in exts:
                full = os.path.join(root, fn)
                try:
                    mt = datetime.datetime.fromtimestamp(os.path.getmtime(full))
                except OSError:
                    continue
                if mt >= cutoff:
                    rel = os.path.relpath(full, project_dir)
                    out.append((rel, mt))
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def count_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def code_stats(project_dir, days=7):
    """返回 (文件数, 总行数) — 本次改动的 .c/.h 代码量。"""
    files = scan_files(project_dir, {".c", ".h"}, days=days)
    total = sum(count_lines(os.path.join(project_dir, rel)) for rel, _ in files)
    return len(files), total


def detect_current_experiment(project_dir):
    """根据最近改动的 .c/.h 文件, 推断当前实验所在的顶层文件夹。"""
    files = scan_files(project_dir, {".c", ".h"}, days=3650)
    if not files:
        return ""
    rel = files[0][0].replace("\\", "/")
    parts = rel.split("/")
    return parts[0] if len(parts) > 1 else ""


def find_main_c(project_dir, prefer_folder=""):
    """找最近改动的 main.c; 若给定 prefer_folder 则优先该文件夹内的。"""
    candidates = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
        for fn in files:
            if fn.lower() == "main.c":
                full = os.path.join(root, fn)
                try:
                    mt = os.path.getmtime(full)
                except OSError:
                    continue
                pref = prefer_folder and (os.sep + prefer_folder + os.sep) in (
                    full + os.sep)
                candidates.append((1 if pref else 0, mt, full))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return candidates[0][2]


def extract_main_function(path):
    """从 main.c 中粗略提取 main() 函数体 (按花括号配对)。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return None
    idx = text.find("int main")
    if idx < 0:
        idx = text.find(" main(")
    if idx < 0:
        return None
    brace = text.find("{", idx)
    if brace < 0:
        return None
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[idx:i + 1]
    return text[idx:]


# ---------------------------------------------------------------------------
# C 函数级解析 (用于"改动较大的函数")
# ---------------------------------------------------------------------------
_C_CTRL = {"if", "for", "while", "switch", "do", "else", "return", "sizeof"}
_IDENT_RE = re.compile(r"[A-Za-z_]\w*")


def parse_c_functions(text):
    """粗略解析 C 源码, 返回 [(name, start_line, end_line)] (行号从 1 起)。

    跳过注释与字符串里的花括号, 按顶层 {} 配对识别函数定义。
    """
    line_starts = [0]
    for idx, ch in enumerate(text):
        if ch == "\n":
            line_starts.append(idx + 1)

    def line_of(pos):
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    funcs = []
    depth = 0
    func_start_pos = -1
    i, n = 0, len(text)
    in_line_c = in_block_c = in_str = in_chr = False
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_line_c:
            if ch == "\n":
                in_line_c = False
        elif in_block_c:
            if ch == "*" and nxt == "/":
                in_block_c = False
                i += 1
        elif in_str:
            if ch == "\\":
                i += 1
            elif ch == '"':
                in_str = False
        elif in_chr:
            if ch == "\\":
                i += 1
            elif ch == "'":
                in_chr = False
        elif ch == "/" and nxt == "/":
            in_line_c = True
            i += 1
        elif ch == "/" and nxt == "*":
            in_block_c = True
            i += 1
        elif ch == '"':
            in_str = True
        elif ch == "'":
            in_chr = True
        elif ch == "{":
            if depth == 0:
                # 顶层 '{': 向前找函数签名 (名字紧贴其参数表的 '(' 之前)。
                # 在 ';' '}' 处停止; 同时不跨越空行或预处理行(#...), 以免把
                # 上一段 #include / 注释 误并入函数体。
                header_start = i
                j = i - 1
                while j >= 0 and text[j] not in ";}":
                    if text[j] == "\n":
                        # 该换行所在前一行: 空行或以 # 开头 → 视作边界
                        ls = text.rfind("\n", 0, j) + 1
                        prev_line = text[ls:j].strip()
                        if prev_line == "" or prev_line.startswith("#"):
                            break
                    header_start = j
                    j -= 1
                header = text[header_start:i]
                name = _func_name_from_header(header)
                func_start_pos = header_start if name else -1
                if name:
                    func_start_pos = (header_start, name)
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and isinstance(func_start_pos, tuple):
                    sp, name = func_start_pos
                    # 跳过签名前的空白/换行, 让起始行落在签名所在行
                    while sp < i and text[sp] in " \t\r\n":
                        sp += 1
                    funcs.append((name, line_of(sp), line_of(i)))
                    func_start_pos = -1
        i += 1
    return funcs


def _func_name_from_header(header):
    """从 '{' 之前的文本里取函数名 (与参数表 '(' 紧邻的标识符)。失败返回 None。"""
    paren = header.rfind("(")
    if paren < 0:
        return None
    before = header[:paren].rstrip()
    m = None
    for m in _IDENT_RE.finditer(before):
        pass
    if not m:
        return None
    name = m.group(0)
    if name in _C_CTRL:
        return None
    return name


def _changed_lines_by_file(pd):
    """解析 git diff (新文件侧), 返回 {相对路径: set(改动行号)}。"""
    rc, diff = run_git(["diff", "HEAD", "--unified=0"], pd)
    if rc != 0 or not diff:
        return {}
    result = {}
    cur = None
    new_ln = 0
    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
    for ln in diff.splitlines():
        if ln.startswith("+++ "):
            path = ln[4:].strip()
            if path.startswith("b/"):
                path = path[2:]
            cur = None if path == "/dev/null" else path.replace("/", os.sep)
            result.setdefault(cur, set())
        elif ln.startswith("@@"):
            m = hunk_re.match(ln)
            if m and cur is not None:
                new_ln = int(m.group(1))
                # 删除型 hunk (新侧 0 行) 也归到该锚点行
                if (m.group(2) or "1") == "0":
                    result[cur].add(max(new_ln, 1))
        elif cur is not None and ln.startswith("+") and not ln.startswith("+++"):
            result[cur].add(new_ln)
            new_ln += 1
        elif cur is not None and ln.startswith("-") and not ln.startswith("---"):
            pass  # 删除行不前进新侧行号
        elif cur is not None and not ln.startswith("\\"):
            new_ln += 1  # 上下文行 (-U0 下基本不出现)
    return result


def changed_functions(pd, top_n=3, max_body=2000):
    """找出本次改动最大的若干函数。

    返回 [{file, name, changed, body}], 按改动行数降序。
    依赖 git diff; 若非 git 仓库或无改动则返回 []。
    """
    changed_map = _changed_lines_by_file(pd)
    rc, untracked = run_git(["ls-files", "--others", "--exclude-standard"], pd)
    untracked_files = []
    if rc == 0:
        untracked_files = [u.strip() for u in untracked.splitlines()
                           if u.strip().lower().endswith((".c", ".h"))]

    ranked = []
    seen = set()

    def consider(rel, lineset, whole_new=False):
        full = os.path.join(pd, rel)
        if not os.path.isfile(full) or full in seen:
            return
        seen.add(full)
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception:
            return
        for name, s, e in parse_c_functions(text):
            if whole_new:
                cnt = e - s + 1
            else:
                cnt = sum(1 for L in lineset if s <= L <= e)
            if cnt <= 0:
                continue
            body = "\n".join(text.splitlines()[s - 1:e])
            if len(body) > max_body:
                body = body[:max_body] + "\n/* …(已截断)… */"
            ranked.append({"file": rel.replace("\\", "/"), "name": name,
                           "changed": cnt, "body": body})

    for rel, lineset in changed_map.items():
        if rel and rel.lower().endswith((".c", ".h")):
            consider(rel, lineset)
    for rel in untracked_files:
        consider(rel.replace("/", os.sep), None, whole_new=True)

    ranked.sort(key=lambda d: d["changed"], reverse=True)
    return ranked[:top_n]


# ---------------------------------------------------------------------------
# Git 操作
# ---------------------------------------------------------------------------
def run_git(args, cwd):
    try:
        p = subprocess.run(["git"] + args, cwd=cwd, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, "找不到 git, 请确认已安装并加入 PATH。"


def git_changed_files(pd):
    """返回 (改动文件列表, 原始 porcelain 文本)。空列表 = 工作区干净。"""
    rc, out = run_git(["status", "--porcelain"], pd)
    if rc != 0:
        return None, out
    files = [ln for ln in out.splitlines() if ln.strip()]
    return files, out


def git_diff(pd, max_chars=8000):
    """已跟踪文件相对上次提交的 diff + 未跟踪新文件名, 截断到 max_chars。"""
    rc, diff = run_git(["diff", "HEAD"], pd)
    if rc != 0:
        diff = ""
    rc2, untracked = run_git(["ls-files", "--others", "--exclude-standard"], pd)
    extra = ""
    if rc2 == 0 and untracked.strip():
        extra = "\n[新增未跟踪文件]\n" + untracked.strip()
    full = (diff or "").strip() + extra
    if len(full) > max_chars:
        full = full[:max_chars] + "\n...(diff 已截断)..."
    return full


# ---------------------------------------------------------------------------
# 外部 AI 调用 (OpenAI 兼容 /chat/completions, 仅用标准库)
# ---------------------------------------------------------------------------
def ai_chat(cfg, user_content, system_prompt=None, temperature=0.4):
    ai = cfg.get("ai") or {}
    base = (ai.get("base_url") or DEFAULT_AI["base_url"]).rstrip("/")
    key = (ai.get("api_key") or "").strip()      # 本地 Ollama 无需 Key, 可留空
    model = ai.get("model") or DEFAULT_AI["model"]
    is_local = ("localhost" in base) or ("127.0.0.1" in base)
    url = base + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt or AI_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": temperature,
        "stream": False,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if key:                                       # 仅在线服务才带鉴权头
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            obj = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        hint = ""
        if is_local and "model" in body.lower():
            hint = "\n提示: 模型 \"%s\" 可能还没拉取, 先运行: ollama pull %s" % (
                model, model)
        raise RuntimeError("AI 接口返回 %s: %s%s" % (e.code, body[:500], hint))
    except urllib.error.URLError as e:
        if is_local:
            raise RuntimeError(
                "连不上本地 Ollama (%s)。请确认:\n"
                "  1. 已安装并启动 Ollama (命令行运行 `ollama serve` 或打开 Ollama 应用)\n"
                "  2. 已拉取模型: `ollama pull %s`\n"
                "原始错误: %s" % (base, model, e.reason))
        raise RuntimeError("无法连接 AI 接口: %s" % e.reason)
    return obj["choices"][0]["message"]["content"].strip()


def polish_commit_message(cfg, draft, context):
    """调用 AI 把 commit 草稿润色成一行规范提交说明。失败时抛异常。"""
    user = ("【用户原始 commit 草稿】\n" + (draft or "(空)") +
            "\n\n【本次改动信息】\n" + context)
    text = ai_chat(cfg, user, system_prompt=AI_COMMIT_PROMPT, temperature=0.3)
    # 模型可能多嘴, 只取第一行非空内容并去掉首尾引号/反引号
    for line in text.splitlines():
        line = line.strip().strip("`").strip('"').strip("'").strip()
        if line:
            return line[:80]
    return draft


# ---------------------------------------------------------------------------
# 主界面
# ---------------------------------------------------------------------------
class App:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        root.title("STM32 开发记录助手")
        root.geometry("780x760")
        root.minsize(660, 600)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 顶部: 项目目录
        top = ttk.Frame(root, padding=(10, 8))
        top.pack(fill="x")
        ttk.Label(top, text="项目目录:").pack(side="left")
        self.dir_var = tk.StringVar(value=cfg["project_dir"])
        ttk.Entry(top, textvariable=self.dir_var).pack(
            side="left", fill="x", expand=True, padx=6)
        ttk.Button(top, text="更改", command=self.choose_dir).pack(side="left")

        # 时间 + 当前实验
        info = ttk.Frame(root, padding=(12, 0))
        info.pack(fill="x")
        ttk.Label(info, text="记录时间: " + now,
                  foreground="#666").pack(side="left")
        self.exp_var = tk.StringVar(value="实验: (检测中…)")
        ttk.Label(info, textvariable=self.exp_var,
                  foreground="#1a6").pack(side="left", padx=16)

        # ① 改动较大的函数 / 本次实验目标
        f1 = self._section_frame(root, "① 改动较大的函数 / 本次实验目标")
        self.t_main = self._add_text(f1, height=8)
        f1btns = ttk.Frame(f1)
        f1btns.pack(anchor="e", pady=(4, 0))
        ttk.Button(f1btns, text="🔥 提取本次改动最大的函数",
                   command=self.fill_changed_funcs).pack(side="left")
        ttk.Button(f1btns, text="🧩 仅提取 main()",
                   command=self.fill_main).pack(side="left", padx=(6, 0))

        # ② .c / .h 文件
        f2 = self._section_frame(root, "② 新建 / 修改的 .C 和 .H 文件")
        self.t_files = self._add_text(f2, height=6)
        ttk.Button(f2, text="🔍 自动扫描最近修改的 .c/.h (含代码量统计)",
                   command=self.scan_ch).pack(anchor="e", pady=(4, 0))

        # ③ AI 总结
        f3 = self._section_frame(root, "③ AI 总结 (本地 Ollama, 免费离线)")
        self.t_ai = self._add_text(f3, height=7)
        self.ai_btn = ttk.Button(
            f3, text="🤖 生成 AI 总结", command=self.gen_ai_summary)
        self.ai_btn.pack(anchor="e", pady=(4, 0))

        # commit message + 按钮
        bottom = ttk.Frame(root, padding=(10, 8))
        bottom.pack(fill="x")
        ttk.Label(bottom, text="提交信息(commit):").pack(side="left")
        self.commit_var = tk.StringVar(
            value="记录 " + datetime.datetime.now().strftime("%m-%d %H:%M"))
        ttk.Entry(bottom, textvariable=self.commit_var).pack(
            side="left", fill="x", expand=True, padx=6)

        btns = ttk.Frame(root, padding=(10, 0, 10, 12))
        btns.pack(fill="x")
        ttk.Button(btns, text="💾 保存记录到 DEVLOG.md",
                   command=self.save_log).pack(side="left")
        ttk.Button(btns, text="🚀 保存并上传到 GitHub",
                   command=self.upload_github).pack(side="left", padx=6)
        ttk.Button(btns, text="📄 打开 DEVLOG",
                   command=self.open_devlog).pack(side="left")
        ttk.Button(btns, text="关闭", command=root.destroy).pack(side="right")

        self.status = tk.StringVar(value="就绪")
        ttk.Label(root, textvariable=self.status, relief="sunken",
                  anchor="w").pack(fill="x", side="bottom")

        # 启动时自动: 扫描文件 + 识别实验
        self.root.after(200, self.startup_scan)

    # -- UI 辅助 --
    def _section_frame(self, root, title):
        lf = ttk.LabelFrame(root, text=title, padding=8)
        lf.pack(fill="both", expand=True, padx=10, pady=4)
        return lf

    def _add_text(self, parent, height=5):
        t = scrolledtext.ScrolledText(parent, height=height, wrap="word",
                                      font=("Consolas", 10))
        t.pack(fill="both", expand=True)
        return t

    # -- 业务 --
    def project_dir(self):
        return self.dir_var.get().strip() or DEFAULT_PROJECT_DIR

    def choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.project_dir())
        if d:
            self.dir_var.set(d)

    def startup_scan(self):
        exp = detect_current_experiment(self.project_dir())
        self.exp_var.set("实验: " + (exp or "(未识别)"))
        self.scan_ch()

    def scan_ch(self):
        pd = self.project_dir()
        files = scan_files(pd, {".c", ".h"}, days=7)
        n, lines = code_stats(pd, days=7)
        if not files:
            txt = "(最近 7 天没有检测到修改过的 .c / .h 文件)"
        else:
            txt = "\n".join(
                "- {}   [{}]".format(rel, mt.strftime("%m-%d %H:%M"))
                for rel, mt in files[:60])
            txt += "\n\n📊 代码量统计: {} 个文件, 共 {} 行".format(n, lines)
        self.t_files.delete("1.0", "end")
        self.t_files.insert("1.0", txt)
        self.status.set("已扫描 {} 个 .c/.h 文件 (共 {} 行)".format(n, lines))

    def fill_main(self):
        exp = detect_current_experiment(self.project_dir())
        path = find_main_c(self.project_dir(), prefer_folder=exp)
        if not path:
            messagebox.showinfo("提示", "项目内未找到 main.c。")
            return
        body = extract_main_function(path)
        if not body:
            messagebox.showinfo("提示", "在 main.c 中未找到 main() 函数。")
            return
        rel = os.path.relpath(path, self.project_dir())
        block = "// 来自 {}\n{}".format(rel, body.strip())
        self.t_main.delete("1.0", "end")
        self.t_main.insert("1.0", block)
        self.status.set("已提取 main() 函数: " + rel)

    def fill_changed_funcs(self):
        """按 git diff 改动行数, 提取本次改动最大的几个函数体。"""
        pd = self.project_dir()
        funcs = changed_functions(pd, top_n=3)
        if not funcs:
            # 没有 git 改动 (或非 git 仓库) → 退回到 main()
            self.fill_main()
            self.status.set("未检测到 git 改动, 已退回提取 main()")
            return
        blocks = []
        for f in funcs:
            blocks.append("// 来自 {}  ·  {}()  ·  本次改动 {} 行\n{}".format(
                f["file"], f["name"], f["changed"], f["body"].strip()))
        self.t_main.delete("1.0", "end")
        self.t_main.insert("1.0", "\n\n".join(blocks))
        names = ", ".join("{}({})".format(f["name"], f["changed"]) for f in funcs)
        self.status.set("已提取改动最大的函数: " + names)

    def _ai_context(self):
        pd = self.project_dir()
        exp = detect_current_experiment(pd)
        main = self.t_main.get("1.0", "end").strip()
        files = self.t_files.get("1.0", "end").strip()
        diff = git_diff(pd)
        parts = ["【实验名称】\n" + (exp or "(未识别)")]
        parts.append("\n【改动较大的函数 / 实验目标】\n" + (main or "(未填写)"))
        parts.append("\n【本次改动的 .c/.h 文件】\n" + (files or "(无)"))
        parts.append("\n【git diff (相对上次提交)】\n" + (diff or "(无 / 非 git 仓库)"))
        return "\n".join(parts)

    def gen_ai_summary(self):
        self.ai_btn.config(state="disabled")
        self.status.set("正在调用本地 AI 生成总结…")
        self.t_ai.delete("1.0", "end")
        self.t_ai.insert("1.0", "⏳ 正在生成, 请稍候…")
        ctx = self._ai_context()

        def worker():
            try:
                text = ai_chat(self.cfg, ctx)
                self.root.after(0, lambda: self._ai_done(text, None))
            except Exception as e:
                self.root.after(0, lambda: self._ai_done(None, str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _ai_done(self, text, err):
        self.ai_btn.config(state="normal")
        self.t_ai.delete("1.0", "end")
        if err:
            self.t_ai.insert("1.0", "❌ 生成失败:\n" + err)
            self.status.set("AI 总结失败")
        else:
            self.t_ai.insert("1.0", text)
            self.status.set("AI 总结已生成 ✅ (可手动编辑后再保存)")

    def build_entry(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pd = self.project_dir()
        exp = detect_current_experiment(pd)
        n, lines = code_stats(pd, days=7)
        main = self.t_main.get("1.0", "end").strip()
        files = self.t_files.get("1.0", "end").strip()
        ai = self.t_ai.get("1.0", "end").strip()
        parts = ["\n## " + now]
        if exp:
            parts.append("\n> **本次实验:** " + exp +
                         "　|　**代码量:** {} 文件 / {} 行".format(n, lines))
        parts.append("\n### ① 改动较大的函数 / 实验目标\n")
        if main:
            parts.append("```c\n" + main + "\n```")
        else:
            parts.append("_(未填写)_")
        parts.append("\n### ② 新建 / 修改的 .C 和 .H 文件\n" + (files or "_(无)_"))
        parts.append("\n### ③ AI 总结\n" + (ai or "_(未生成)_"))
        return "\n".join(parts) + "\n\n---\n"

    def save_log(self):
        pd = self.project_dir()
        if not os.path.isdir(pd):
            messagebox.showerror("错误", "项目目录不存在:\n" + pd)
            return False
        path = os.path.join(pd, "DEVLOG.md")
        try:
            new = not os.path.exists(path)
            with open(path, "a", encoding="utf-8") as f:
                if new:
                    f.write("# STM32 开发记录 (DEVLOG)\n")
                f.write(self.build_entry())
        except Exception as e:
            messagebox.showerror("写入失败", str(e))
            return False
        self.status.set("已保存到 " + path)
        return True

    def open_devlog(self):
        path = os.path.join(self.project_dir(), "DEVLOG.md")
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showinfo("提示", "还没有 DEVLOG.md, 请先保存一次记录。")

    def ensure_remote(self, pd):
        remote = self.cfg.get("github_remote", "").strip()
        rc, out = run_git(["remote", "get-url", "origin"], pd)
        if rc == 0 and out.strip():
            return out.strip()
        if not remote:
            remote = simpledialog.askstring(
                "GitHub 仓库地址",
                "首次上传, 请输入 GitHub 仓库地址:\n"
                "(例如 https://github.com/用户名/仓库.git)")
            if not remote:
                return None
            self.cfg["github_remote"] = remote.strip()
            save_config(self.cfg)
        run_git(["remote", "remove", "origin"], pd)
        run_git(["remote", "add", "origin", remote.strip()], pd)
        return remote.strip()

    def _ai_polish_commit(self, draft, log):
        """上传时调用功能三润色 commit 信息, 弹窗让用户确认/编辑。

        返回最终 commit 文本; 用户取消则返回 None; AI 失败则回退到 draft。
        """
        self.status.set("正在调用 AI 润色 commit 信息…")
        self.root.update_idletasks()
        context = self._ai_context()
        try:
            polished = polish_commit_message(self.cfg, draft, context)
            log.append("commit 润色: 「%s」→「%s」" % (draft, polished))
        except Exception as e:
            polished = draft
            log.append("commit 润色失败(用原草稿): " + str(e))
            self.status.set("AI 润色失败, 使用原 commit 信息")

        # 让用户确认/微调最终提交信息
        final = simpledialog.askstring(
            "确认提交信息", "AI 已润色 commit 信息, 可直接确认或修改:",
            initialvalue=polished, parent=self.root)
        if final is None:
            return None
        final = final.strip() or polished
        self.commit_var.set(final)
        return final

    def upload_github(self):
        if not self.save_log():
            return
        pd = self.project_dir()
        branch = self.cfg.get("git_branch", "main")
        log = []

        first_time = not os.path.isdir(os.path.join(pd, ".git"))
        if first_time:
            rc, out = run_git(["init"], pd); log.append("init:\n" + out)
            run_git(["branch", "-M", branch], pd)
            gi = os.path.join(pd, ".gitignore")
            if not os.path.exists(gi):
                with open(gi, "w", encoding="utf-8") as f:
                    f.write("# Keil 构建产物\nObjects/\nListings/\n*.o\n*.crf\n"
                            "*.d\n*.bak\n*.dep\n*.lst\n*.map\n__pycache__/\n")

        # 仅当有真实改动时才提交, 避免未变化文件重复上传
        if not first_time:
            changed, _ = git_changed_files(pd)
            if changed is not None and len(changed) == 0:
                self.status.set("没有任何文件改动, 无需上传 ✅")
                messagebox.showinfo("无需上传",
                                    "相比上次提交没有改动的文件, 无需重复上传。")
                return

        if self.ensure_remote(pd) is None:
            self.status.set("已取消上传 (未填写仓库地址)")
            return

        run_git(["branch", "-M", branch], pd)
        run_git(["add", "-A"], pd)
        # 记录本次实际纳入提交的文件
        rc, staged = run_git(["diff", "--cached", "--name-status"], pd)
        log.append("本次改动文件:\n" + (staged.strip() or "(无)"))

        # 调用功能三(AI): 把 commit 草稿润色成一行规范提交说明, 失败则用原草稿
        commit_msg = self.commit_var.get().strip() or "update"
        polished = self._ai_polish_commit(commit_msg, log)
        if polished is None:                 # 用户在确认框里取消了上传
            self.status.set("已取消上传")
            return
        commit_msg = polished
        rc, out = run_git(["commit", "-m", commit_msg], pd)
        log.append("commit (" + commit_msg + "):\n" + out)
        rc, out = run_git(["push", "-u", "origin", branch], pd)
        log.append("push:\n" + out)

        ok = rc == 0
        self.status.set("上传成功 ✅" if ok else "上传失败, 详见弹窗 ❌")
        win = tk.Toplevel(self.root)
        win.title("GitHub 上传结果")
        win.geometry("680x440")
        box = scrolledtext.ScrolledText(win, wrap="word",
                                        font=("Consolas", 9))
        box.pack(fill="both", expand=True)
        box.insert("1.0", "\n".join(log))
        box.config(state="disabled")


def main():
    lock = acquire_single_instance()
    if lock is None:
        return                      # 已有窗口在运行
    cfg = load_config()
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except Exception:
        pass
    App(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()
