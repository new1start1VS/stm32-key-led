# remain.md —— 仓库瘦身说明 & Git 基本操作

> 本文件说明这次对仓库做了什么，以及日常用 Git 管理本仓库需要掌握的基本命令。

---

## 一、这次清理做了什么

仓库原本跟踪了 **922 个文件、约 25 MB**，但其中约 **99% 是 ST 官方的厂商样板代码**，
在 12 个课程文件夹里被一模一样地复制了 12 遍。它们包括：

| 目录 | 内容 | 说明 |
|------|------|------|
| `libraries/` | STM32 标准外设库（`stm32f10x_xxx.c/.h`）| ST 官方库，所有工程通用 |
| `start/` | 启动文件 `startup_stm32f10x_*.s`（汇编）+ `core_cm3` | ST 官方启动代码，你看不懂是正常的，不用改 |

**处理方式**：把 `libraries/` 和 `start/` 加入 `.gitignore`，并用 `git rm --cached` 停止跟踪。
- ✅ **本地文件原样保留**，Keil 仍然能正常打开、编译、下载。
- ✅ 仓库（GitHub）上的文件数从 **922 → 141**，只剩你自己写的代码和工程文件。
- ⚠️ 别人 `git clone` 后，需要自己补回标准库才能编译（见下方"如何还原"）。

顺带也清掉了 14 个本就该忽略的 `.uvoptx`（Keil 个人窗口配置，无需入库）。

### 仓库现在保留什么
- `**/Hardware/`、`**/System/`、`**/user/` —— **你亲手写的代码**（LED、按键、定时器、OLED 等）
- `**/*.uvprojx` —— Keil 工程文件（决定工程结构，需要保留）
- `README.md`、`DEVLOG.md`、`_tools/` —— 文档和开发记录工具

---

## 二、如何还原标准库（在新电脑 / 别人 clone 后）

`libraries/` 和 `start/` 是 ST 官方 **STM32F10x 标准外设库（StdPeriph_Lib）** 里的文件，
任何一个课程文件夹里的这两份内容都完全一样。还原有两种办法：

**办法 A（最简单）**：从你本机任一已有工程里，把 `libraries/` 和 `start/` 两个文件夹
直接复制进缺失的工程文件夹即可。

**办法 B**：到 ST 官网下载 `STSW-STM32054`（STM32F10x standard peripheral library），
把其中的 `Libraries/STM32F10x_StdPeriph_Driver/src` 和 `inc`、以及 `CMSIS` 启动文件
对应放进 `libraries/` 和 `start/`。

> 因为本机这两个文件夹一直都在，你自己用 **完全不受影响**，此步骤只为换电脑或他人使用时参考。

---

## 三、Git 基本操作（日常够用版）

### 1. 看状态 —— 改动前后都先看一眼
```bash
git status          # 当前有哪些改动 / 新文件
git status -s       # 精简版（M=改动, D=删除, ??=未跟踪）
```

### 2. 提交三步走 —— 把改动存进本地仓库
```bash
git add .                       # 把所有改动加入暂存区（. 表示当前目录全部）
git add "6-3 定时器的外部时钟"    # 也可只加某个文件夹
git commit -m "说明这次改了什么"  # 提交，引号里写清楚改动内容
```

### 3. 推送 / 拉取 —— 和 GitHub 同步
```bash
git push            # 把本地提交推送到 GitHub（origin main）
git pull            # 把 GitHub 上的最新改动拉到本地
```
> 第一次推送某分支若提示，需要：`git push -u origin main`

### 4. 看历史
```bash
git log --oneline           # 一行一条，看提交历史
git log --oneline -10       # 只看最近 10 条
```

### 5. 撤销 / 反悔（常用救命命令）
```bash
git restore 文件名           # 丢弃某文件还没 add 的改动（恢复到上次提交）
git restore --staged 文件名  # 把已 add 的文件移出暂存区（改动还在）
git checkout -- .           # 丢弃当前目录所有未提交改动（慎用！）
```

### 6. 关于 .gitignore —— 控制"哪些文件不进仓库"
- `.gitignore` 里每一行是一条忽略规则，例如 `libraries/` 表示忽略所有叫 libraries 的文件夹。
- **注意**：`.gitignore` 只能阻止"还没被跟踪"的文件。
  如果文件已经在仓库里了，要先停止跟踪（保留本地文件）：
  ```bash
  git rm --cached -r 文件夹名     # -r 表示递归整个文件夹；--cached 表示只从仓库移除，本地保留
  git commit -m "stop tracking xxx"
  ```

---

## 四、本次清理后的标准提交流程（照着做即可）

```bash
git status -s                       # 1. 确认改动（应看到大量 D 删除 和 .gitignore 修改）
git add -A                          # 2. 暂存所有改动（含删除）
git commit -m "瘦身: 移除重复的 STM32 标准库和启动文件, 仅保留自有代码"
git push                            # 3. 推送到 GitHub
```

推送成功后，刷新 GitHub 仓库页面，文件夹里就只剩你自己的代码了 ✅
