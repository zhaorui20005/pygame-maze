# 🎮 Pygame Maze Game (2D 迷宫游戏)

一款基于 Pygame-CE 打造的动态生成迷宫游戏。支持跨平台（Windows / macOS / Linux）运行，内置程序化音效、自适应摄像机视口以及萌系 Q 版角色动画。

---

## ✨ 功能特色

- **跨平台支持**：支持 Windows、macOS 与 Linux 系统，自动匹配并加载中文字体。
- **10 阶难度递进**：支持 1 至 10 阶不同尺寸与复杂度的完美迷宫生成（算法保证无环、无死区、解唯一且死胡同加深）。
- **智能视角摄像机**：
  - **全景自适应 (Scale-to-Fit)**：新关卡开启时，整个迷宫自动等比例缩放并顶格对齐展现，无需拖拽调整窗口。
  - **追焦与平移**：支持鼠标左/右键拖拽平移、滚轮以鼠标位置为中心缩放，以及键盘一键视角切换。
- **程序化视觉与音效**：
  - 萌系 Q 版小人主角，带有 4 方向移动与脚步迈步动画。
  - 终点与起点配有小房子与胜利小旗子图案。
  - 内存程序化合成复古 8-bit 音效（移动脚步声、新局开场音效、胜利通关和弦）。

---

## 🚀 运行指南

### 前置要求
- Python 3.8 及以上版本

---

### 1. Windows 系统运行

在 PowerShell 中运行以下命令：

```powershell
# 进入项目目录
cd pygame-maze

# 创建并激活虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 升级 pip 并安装依赖
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 运行游戏
python main.py
```

---

### 2. Linux 系统运行

在 Linux 终端中运行以下命令：

```bash
# 进入项目目录
cd pygame-maze

# 安装必要的系统音频与 Python 库 (以 Ubuntu/Debian 为例)
sudo apt update
python3 -m venv .venv
source .venv/bin/activate

# 升级 pip 并安装依赖
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# 运行游戏
python3 main.py
```

---

### 3. macOS 系统运行

在 macOS 终端中运行以下命令：

```bash
# 进入项目目录
cd pygame-maze

# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 升级 pip 并安装依赖
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# 运行游戏
python3 main.py
```

---

## 🎮 游戏操作说明

| 操作按键 / 动作 | 功能说明 |
| :--- | :--- |
| **`W` / `A` / `S` / `D`** 或 **方向键** | 控制小人上下左右移动 |
| **`1` ~ `9`** | 快速切换至 1 ~ 9 阶难度迷宫 |
| **`0`** | 切换至 10 阶（最高阶）巨型迷宫 |
| **`+` / `-`** | 逐阶提升或降低难度等级 |
| **`R`** | 重新随机生成当前阶数的迷宫 |
| **`C` / `Space`** | 切换全景自适应视角与玩家跟随视角 |
| **鼠标左键 / 右键拖拽** | 平移视口查看迷宫地图 |
| **鼠标滚轮** | 放大 / 缩小视口地图 |
| **`Esc`** | 退出游戏 |
