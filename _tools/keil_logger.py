# -*- coding: utf-8 -*-
"""
STM32 开发记录助手  (Keil 打开时自动弹出)
功能:
  - 记录 main 函数改动
  - 自动扫描 / 记录新建或修改的 .c / .h 文件
  - 记录 Excalidraw 笔记 (并扫描 .excalidraw 文件)
  - 一键保存到 DEVLOG.md
  - 一键上传到 GitHub (git init / commit / push)
作者: 自动生成
"""
import os
import sys
import json
import socket
import subprocess
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog, scrolledtext

# ---------------------------------------------------------------------------
# 路径与配置
# ---------------------------------------------------------------------------
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROJECT_DIR = os.path.dirname(TOOLS_DIR)          # 上一级 = D:\STM32PRO
CONFIG_PATH = os.path.join(TOOLS_DIR, "config.json")
SKIP_DIRS = {"objects", "listings", "rte", ".git", "_tools",
             "__pycache__", "dep", "out"}                # 扫描时忽略的构建目录


def load_config():
    cfg = {"project_dir": DEFAULT_PROJECT_DIR, "github_remote": "",
           "git_branch": "main"}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
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
# 文件扫描
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


# ---------------------------------------------------------------------------
# 主界面
# ---------------------------------------------------------------------------
class App:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        root.title("STM32 开发记录助手")
        root.geometry("760x720")
        root.minsize(640, 560)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 顶部: 项目目录
        top = ttk.Frame(root, padding=(10, 8))
        top.pack(fill="x")
        ttk.Label(top, text="项目目录:").pack(side="left")
        self.dir_var = tk.StringVar(value=cfg["project_dir"])
        ttk.Entry(top, textvariable=self.dir_var).pack(
            side="left", fill="x", expand=True, padx=6)
        ttk.Button(top, text="更改", command=self.choose_dir).pack(side="left")

        ttk.Label(root, text="记录时间: " + now,
                  foreground="#666").pack(anchor="w", padx=12)

        # 1) main 函数
        self.t_main = self._section(
            root, "① main 函数改动 / 本次实验目标")
        # 2) .c / .h 文件
        f2 = self._section_frame(root, "② 新建 / 修改的 .C 和 .H 文件")
        self.t_files = self._add_text(f2, height=6)
        ttk.Button(f2, text="🔍 自动扫描最近修改的 .c/.h",
                   command=self.scan_ch).pack(anchor="e", pady=(4, 0))
        # 3) Excalidraw
        f3 = self._section_frame(root, "③ Excalidraw 新加的笔记")
        self.t_exc = self._add_text(f3, height=5)
        ttk.Button(f3, text="🔍 扫描项目内 .excalidraw 文件",
                   command=self.scan_exc).pack(anchor="e", pady=(4, 0))

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

        # 启动时自动扫描一次
        self.root.after(200, self.scan_ch)

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

    def _section(self, root, title, height=5):
        lf = self._section_frame(root, title)
        return self._add_text(lf, height)

    # -- 业务 --
    def project_dir(self):
        return self.dir_var.get().strip() or DEFAULT_PROJECT_DIR

    def choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.project_dir())
        if d:
            self.dir_var.set(d)

    def scan_ch(self):
        files = scan_files(self.project_dir(), {".c", ".h"}, days=7)
        if not files:
            txt = "(最近 7 天没有检测到修改过的 .c / .h 文件)"
        else:
            txt = "\n".join(
                "- {}   [{}]".format(rel, mt.strftime("%m-%d %H:%M"))
                for rel, mt in files[:60])
        self.t_files.delete("1.0", "end")
        self.t_files.insert("1.0", txt)
        self.status.set("已扫描 {} 个最近修改的 .c/.h 文件".format(len(files)))

    def scan_exc(self):
        files = scan_files(self.project_dir(), {".excalidraw", ".excalidraw.png",
                                                ".excalidraw.svg"}, days=3650)
        cur = self.t_exc.get("1.0", "end").strip()
        listing = ("\n".join("- " + rel for rel, _ in files)
                   if files else "(项目内未找到 .excalidraw 文件)")
        self.t_exc.delete("1.0", "end")
        self.t_exc.insert("1.0", (cur + "\n" if cur else "") +
                          "【检测到的 Excalidraw 文件】\n" + listing)
        self.status.set("已扫描 {} 个 .excalidraw 文件".format(len(files)))

    def build_entry(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        main = self.t_main.get("1.0", "end").strip()
        files = self.t_files.get("1.0", "end").strip()
        exc = self.t_exc.get("1.0", "end").strip()
        parts = ["\n## " + now + "\n"]
        parts.append("### ① main 函数 / 实验目标\n" + (main or "_(未填写)_"))
        parts.append("\n### ② 新建 / 修改的 .C 和 .H 文件\n" + (files or "_(无)_"))
        parts.append("\n### ③ Excalidraw 笔记\n" + (exc or "_(无)_"))
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

    def upload_github(self):
        if not self.save_log():
            return
        pd = self.project_dir()
        branch = self.cfg.get("git_branch", "main")
        log = []

        if not os.path.isdir(os.path.join(pd, ".git")):
            rc, out = run_git(["init"], pd); log.append("init:\n" + out)
            run_git(["branch", "-M", branch], pd)
            gi = os.path.join(pd, ".gitignore")
            if not os.path.exists(gi):
                with open(gi, "w", encoding="utf-8") as f:
                    f.write("# Keil 构建产物\nObjects/\nListings/\n*.o\n*.crf\n"
                            "*.d\n*.bak\n*.dep\n*.lst\n*.map\n__pycache__/\n")

        if self.ensure_remote(pd) is None:
            self.status.set("已取消上传 (未填写仓库地址)")
            return

        run_git(["branch", "-M", branch], pd)
        run_git(["add", "-A"], pd)
        rc, out = run_git(
            ["commit", "-m", self.commit_var.get() or "update"], pd)
        log.append("commit:\n" + out)
        rc, out = run_git(["push", "-u", "origin", branch], pd)
        log.append("push:\n" + out)

        ok = rc == 0
        self.status.set("上传成功 ✅" if ok else "上传失败, 详见弹窗 ❌")
        win = tk.Toplevel(self.root)
        win.title("GitHub 上传结果")
        win.geometry("680x420")
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
