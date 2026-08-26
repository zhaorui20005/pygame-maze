# 🎮 Maze Game (迷宫游戏 - Pygame & Godot 4 双版本)

一款支持 **Godot Engine 4.x** 与 **Pygame-CE** 运行的跨平台动态生成迷宫游戏。支持小红帽与大灰狼童话主题、大树起点与小屋终点、**右侧独立记分牌与不遮挡地图的状态栏**、1-10 阶难度得分计算（**破纪录分数翻倍**）、**0.01s 精确计时器**与**最佳纪录及总分持久化保存**。

---

## 🤖 Godot 4 版本运行指南 (推荐)

项目已完整移植并支持 **Godot 4.0+ / 4.1 / 4.2 / 4.3** 引擎！

### 1. 使用 Godot 编辑器运行

1. 下载并安装 [Godot Engine 4 (Standard 版)](https://godotengine.org/download)。
2. 启动 Godot，点击 **"导入" (Import)** 按钮。
3. 选择本项目文件夹中的 `project.godot` 文件，点击 **"导入并编辑" (Import & Edit)**。
4. 在 Godot 编辑器右上角直接按 **F5** 键或点击 **播放按钮 (Play)** 即可立刻启动游戏！

### 2. 使用 Godot 命令行直接运行

系统安装有 Godot 4 命令行工具时：

```bash
# 启动游戏主场景
godot scenes/main.tscn
```

---

## 🐍 Python (Pygame-CE) 版本运行指南

### 前置要求
- Python 3.8 及以上版本

```bash
# 1. 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1

# 2. 安装依赖
python3 -m pip install -r requirements.txt

# 3. 运行游戏
python3 main.py
```

---

## 🎮 游戏操作说明

| 操作按键 / 动作 | 功能说明 |
| :--- | :--- |
| **`W` / `A` / `S` / `D`** 或 **方向键** | 控制小红帽上下左右移动与迈步动画 |
| **`1` ~ `9`** | 快速切换至 1 ~ 9 阶难度迷宫 |
| **`0`** | 切换至 10 阶（最高阶）巨型迷宫 |
| **`+` / `-`** | 逐阶提升或降低难度等级 |
| **`R`** | 重新随机生成当前阶数的迷宫 |
| **`F`** | 召唤 / 消除大灰狼 (最多同时存在 1 只大灰狼) |
| **`P`** | 一键切换玩家角色外观 (小红帽 ↔ 糯米团子) |
| **`C` / `Space`** | 切换全景自适应视角与玩家跟随视角 |
| **鼠标左键 / 右键拖拽** | 平移视口查看迷宫地图 |
| **鼠标滚轮** | 放大 / 缩小视口地图 |
| **`Esc`** | 退出游戏 |

---

## 📂 项目文件结构

```
pygame-maze/
├── project.godot            # Godot 4 项目配置文件
├── scenes/
│   └── main.tscn            # Godot 主场景文件
├── scripts/
│   ├── maze_generator.gd    # Godot GDScript 迷宫生成算法 (移植自 maze.py)
│   ├── player.gd            # Godot 玩家控制器 (移植自 player.py)
│   └── main.gd              # Godot 主场景控制器 (移植自 main.py)
├── main.py                  # Python Pygame 版本入口
├── maze.py                  # Python 迷宫生成算法
├── player.py                # Python 玩家控制器
├── assets.py                # Python 音效与贴图资产
└── requirements.txt         # Python 依赖
```
