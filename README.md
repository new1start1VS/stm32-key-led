# STM32F103 学习工程合集

基于 **STM32F103C8 + STM32F10x 标准外设库 (SPL)** 的 Keil MDK 系列学习工程，
按课程章节组织，并附带一个**「Keil 打开自动弹出」的开发记录助手**（带 GUI，可一键上传 GitHub）。

> 开发环境：Keil MDK-ARM (µVision5) · STM32F103C8 · Python 3.x（仅记录助手用到）

---

## 📁 工程目录

每个文件夹是一个独立的 Keil 工程，双击其中的 `*.uvprojx` 即可打开。

| 目录 | 内容 |
| --- | --- |
| `1-1练习` / `1-2练习` / `1-3练习` | GPIO 点灯等基础练习 |
| `3-3蜂鸣器`（含副本） | 蜂鸣器驱动 |
| `3-4呼吸灯` | PWM 呼吸灯 |
| `3-4按钮控制LED` | 按键翻转 LED |
| `3-5光敏传感器和按钮控制` | 光敏传感器 + 按键 |
| `5-2 EXTI中断的引进` | 外部中断 EXTI |
| `6-2 TIM的应用` | 定时器 TIM |
| `stm32Project` | 基础工程模板 |
| 根目录主工程（`3-5.uvprojx` + `user/` `Hardware/` `System/` `start/` `libraries/`） | **按键控制 LED**（详见下方） |
| `_tools/` | **开发记录助手**（见下方「🛠 开发记录助手」） |

> 编译产物（`Objects/`、`Listings/`、`*.o`、`*.crf`、`*.uvoptx` 等）已通过 `.gitignore` 忽略，
> 由 Keil 在本地构建时自动生成，不纳入版本库。

---

## 🛠 开发记录助手（`_tools/`）

一套帮助记录开发过程、并一键上传 GitHub 的小工具。**每次打开 Keil 时会自动弹出。**

| 文件 | 作用 |
| --- | --- |
| `keil_logger.py` | 图形界面「开发记录助手」 |
| `keil_watch.py` | 后台监视器：检测到 Keil(`UV4.exe`)打开 → 自动弹出助手 |
| `打开记录助手.bat` | 手动打开助手 |
| `启动Keil监视器.bat` | 手动启动后台监视器 |
| `config.json` | 项目路径 / GitHub 仓库地址配置 |

### 记录助手能记什么

- ① **main 函数改动 / 实验目标**
- ② **新建或修改的 `.c` / `.h` 文件**（打开时自动扫描最近 7 天的改动并列出）
- ③ **Excalidraw 笔记**（可扫描项目内 `.excalidraw` 文件）
- 🚀 一键 **保存并上传到 GitHub**（自动 `git add / commit / push`）

所有记录追加保存到仓库根目录的 **`DEVLOG.md`**。

### 自动触发原理

通过「登录启动项」在每次开机登录时后台运行 `keil_watch.py`（无窗口）；
监视器轮询 `UV4.exe`，当 Keil 从未运行变为运行时弹出记录助手。
（边沿触发：需「关闭 → 重新打开」Keil 才会弹。）

### 在新电脑上启用

1. 安装 Python 3 与 Git，确认 `pythonw.exe` 路径（默认 `C:\PythonXX\pythonw.exe`）。
2. 修改 `_tools/config.json` 里的 `project_dir` 与 `github_remote`。
3. 把 `_tools/启动Keil监视器.bat` 的快捷方式放进开机启动文件夹
   （`Win+R` → `shell:startup`），或双击它先手动启动一次。

---

## 🔌 根目录主工程：按键控制 LED

用两个独立按键分别翻转两个 LED 的亮灭状态。

### 功能

- 按下 **KEY1** → 翻转 **LED0**（亮 ↔ 灭）
- 按下 **KEY2** → 翻转 **LED1**（亮 ↔ 灭）
- 上拉输入 + 软件消抖（检测到按下后 `Delay_ms(20)`，并等待松手）

### 硬件接线

| 外设 | 引脚 | 配置 | 说明 |
| --- | --- | --- | --- |
| LED0 | PA1 | 推挽输出 | 低电平点亮 |
| LED1 | PA2 | 推挽输出 | 低电平点亮 |
| KEY1 | PA5 | 上拉输入 | 按下为低，键值 1 |
| KEY2 | PA6 | 上拉输入 | 按下为低，键值 2 |

> LED 默认初始化为熄灭（输出高电平）。

### 核心逻辑（`user/main.c`）

```c
Key_Init();
Led_Init();
while (1)
{
    uint8_t KeyNumber = KeyNum();
    if (KeyNumber == 1)       Led0_Toggle();   // KEY1 -> LED0
    else if (KeyNumber == 2)  Led1_Toggle();   // KEY2 -> LED1
}
```

---

## ⚙️ 编译与下载

1. 用 **Keil MDK-ARM (µVision5)** 打开对应工程的 `*.uvprojx`
2. 安装 STM32F1 器件支持包（`Keil::STM32F1xx_DFP`）
3. 编译（F7）→ 连接 ST-Link / J-Link → 下载（F8）
4. 目标芯片：**STM32F103C8**

---

## 许可

仅用于学习用途。
