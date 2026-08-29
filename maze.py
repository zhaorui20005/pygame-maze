"""完美迷宫生成与难度度量。

网格数据与 Pygame 无关，之后可以原样拿到 Godot 里用。
生成结果始终是一棵生成树：每个房间恰好访问一次，任意两格之间只有唯一通路，
因此不存在环路，也不会出现走不到的死区。

关于「看起来太简单」：纯随机的递归回溯会走出一条弯弯绕绕的主路，
岔路往往一两格就到头，站在路口一眼能看出哪边是死胡同。
这里仍然用递归回溯（永远扩展栈顶，保证岔路能挖深），但：
1. 大部分时候沿当前方向继续走，把每一条岔路拉长；
2. 连续直行过长时强制转弯，避免一条笔直走廊把尽头暴露出来。
"""

from __future__ import annotations

import math
import heapq
import random
from collections import deque
from dataclasses import dataclass, field

# 1 = 墙，0 = 可走，2 = 南北高架立交桥 (OVERPASS_NS)，3 = 东西高架立交桥 (OVERPASS_EW)。
WALL = 1
PATH = 0
OVERPASS_NS = 2
OVERPASS_EW = 3
OVERPASS = OVERPASS_NS

# 第一大关：绿野森林 (DFS 算法) 1-10 阶参数配置
W1_DIFFICULTIES = {
    "1": {"cell_cols": 8, "cell_rows": 8, "straight_bias": 0.55, "max_straight_run": 3, "min_dead_end_depth": 2.2},
    "2": {"cell_cols": 10, "cell_rows": 10, "straight_bias": 0.60, "max_straight_run": 3, "min_dead_end_depth": 2.8},
    "3": {"cell_cols": 12, "cell_rows": 12, "straight_bias": 0.64, "max_straight_run": 4, "min_dead_end_depth": 3.2},
    "4": {"cell_cols": 15, "cell_rows": 15, "straight_bias": 0.68, "max_straight_run": 4, "min_dead_end_depth": 3.6},
    "5": {"cell_cols": 18, "cell_rows": 18, "straight_bias": 0.72, "max_straight_run": 5, "min_dead_end_depth": 4.0},
    "6": {"cell_cols": 21, "cell_rows": 21, "straight_bias": 0.75, "max_straight_run": 5, "min_dead_end_depth": 4.5},
    "7": {"cell_cols": 25, "cell_rows": 25, "straight_bias": 0.78, "max_straight_run": 6, "min_dead_end_depth": 5.0},
    "8": {"cell_cols": 30, "cell_rows": 30, "straight_bias": 0.81, "max_straight_run": 6, "min_dead_end_depth": 5.5},
    "9": {"cell_cols": 35, "cell_rows": 35, "straight_bias": 0.84, "max_straight_run": 7, "min_dead_end_depth": 6.0},
    "10": {"cell_cols": 40, "cell_rows": 40, "straight_bias": 0.86, "max_straight_run": 8, "min_dead_end_depth": 6.5},
}

# 第二大关：狼穴地牢 (Prim + 伪环路高难算法) 1-10 阶参数配置
W2_DIFFICULTIES = {
    "1": {"cell_cols": 10, "cell_rows": 10, "loop_ratio": 0.03},
    "2": {"cell_cols": 12, "cell_rows": 12, "loop_ratio": 0.03},
    "3": {"cell_cols": 15, "cell_rows": 15, "loop_ratio": 0.04},
    "4": {"cell_cols": 18, "cell_rows": 18, "loop_ratio": 0.04},
    "5": {"cell_cols": 21, "cell_rows": 21, "loop_ratio": 0.04},
    "6": {"cell_cols": 25, "cell_rows": 25, "loop_ratio": 0.05},
    "7": {"cell_cols": 28, "cell_rows": 28, "loop_ratio": 0.05},
    "8": {"cell_cols": 32, "cell_rows": 32, "loop_ratio": 0.05},
    "9": {"cell_cols": 36, "cell_rows": 36, "loop_ratio": 0.06},
    "10": {"cell_cols": 40, "cell_rows": 40, "loop_ratio": 0.06},
}

# 第三大关：图案秘境 (Opt-Maze 隐写融合算法) 1-10 阶参数配置
W3_DIFFICULTIES = {
    "1": {"cell_cols": 12, "cell_rows": 12, "pattern": "star", "loop_ratio": 0.05},
    "2": {"cell_cols": 15, "cell_rows": 15, "pattern": "heart", "loop_ratio": 0.05},
    "3": {"cell_cols": 18, "cell_rows": 18, "pattern": "crown", "loop_ratio": 0.06},
    "4": {"cell_cols": 21, "cell_rows": 21, "pattern": "key", "loop_ratio": 0.06},
    "5": {"cell_cols": 25, "cell_rows": 25, "pattern": "shield", "loop_ratio": 0.07},
    "6": {"cell_cols": 28, "cell_rows": 28, "pattern": "sword", "loop_ratio": 0.07},
    "7": {"cell_cols": 32, "cell_rows": 32, "pattern": "diamond", "loop_ratio": 0.08},
    "8": {"cell_cols": 35, "cell_rows": 35, "pattern": "clover", "loop_ratio": 0.08},
    "9": {"cell_cols": 38, "cell_rows": 38, "pattern": "skull", "loop_ratio": 0.09},
    "10": {"cell_cols": 42, "cell_rows": 42, "pattern": "trophy", "loop_ratio": 0.10},
}

# 第四大关：异形几何秘境 (Geometric Shape Mask) 1-10 阶参数配置
W4_DIFFICULTIES = {
    "1": {"cell_cols": 12, "cell_rows": 12, "shape": "circle", "loop_ratio": 0.04, "name": "圆形迷宫"},
    "2": {"cell_cols": 14, "cell_rows": 14, "shape": "triangle", "loop_ratio": 0.04, "name": "正三角迷宫"},
    "3": {"cell_cols": 16, "cell_rows": 16, "shape": "diamond", "loop_ratio": 0.05, "name": "菱形水晶迷宫"},
    "4": {"cell_cols": 18, "cell_rows": 18, "shape": "donut", "loop_ratio": 0.05, "name": "双同心环迷宫"},
    "5": {"cell_cols": 20, "cell_rows": 20, "shape": "cross", "loop_ratio": 0.06, "name": "圣十字形迷宫"},
    "6": {"cell_cols": 22, "cell_rows": 22, "shape": "star", "loop_ratio": 0.06, "name": "奇幻星形迷宫"},
    "7": {"cell_cols": 25, "cell_rows": 25, "shape": "hexagon", "loop_ratio": 0.07, "name": "六边盾牌迷宫"},
    "8": {"cell_cols": 28, "cell_rows": 28, "shape": "hourglass", "loop_ratio": 0.07, "name": "沙漏双角迷宫"},
    "9": {"cell_cols": 32, "cell_rows": 32, "shape": "heart", "loop_ratio": 0.08, "name": "璀璨心形迷宫"},
    "10": {"cell_cols": 36, "cell_rows": 36, "shape": "mega_polygon", "loop_ratio": 0.08, "name": "异形几何巨阵"},
}

# 第五大关：立交编织秘境 (Woven / 3D Overpass Maze) 1-10 阶参数配置
W5_DIFFICULTIES = {
    "1": {"cell_cols": 12, "cell_rows": 12, "woven_target": 8, "loop_ratio": 0.04, "name": "双层初探立交"},
    "2": {"cell_cols": 15, "cell_rows": 15, "woven_target": 12, "loop_ratio": 0.05, "name": "十字立交迷宫"},
    "3": {"cell_cols": 18, "cell_rows": 18, "woven_target": 16, "loop_ratio": 0.05, "name": "高架编织网"},
    "4": {"cell_cols": 21, "cell_rows": 21, "woven_target": 22, "loop_ratio": 0.06, "name": "三维立体穿梭"},
    "5": {"cell_cols": 25, "cell_rows": 25, "woven_target": 30, "loop_ratio": 0.06, "pattern": "star", "name": "繁华星型立交"},
    "6": {"cell_cols": 28, "cell_rows": 28, "woven_target": 40, "loop_ratio": 0.07, "pattern": "ai", "name": "AI 隐写字样立交"},
    "7": {"cell_cols": 32, "cell_rows": 32, "woven_target": 50, "loop_ratio": 0.07, "pattern": "art", "name": "ART 艺术隐写天桥"},
    "8": {"cell_cols": 35, "cell_rows": 35, "woven_target": 65, "loop_ratio": 0.08, "pattern": "maze", "name": "MAZE 编织字样巨阵"},
    "9": {"cell_cols": 38, "cell_rows": 38, "woven_target": 80, "loop_ratio": 0.08, "pattern": "crown", "name": "皇冠无尽编织天桥"},
    "10": {"cell_cols": 42, "cell_rows": 42, "woven_target": 100, "loop_ratio": 0.09, "pattern": "sword", "name": "宝剑立体极限巨阵"},
}

# 第六大关：提示词隐语阵 (Opt-Maze Word Prompt Realm - KEEP GOING!) 1-10 阶参数配置
W6_DIFFICULTIES = {
    "1": {"cell_cols": 22, "cell_rows": 28, "word": "K", "loop_ratio": 0.06, "name": "字母 K - Keep 序章", "description": "KEEP GOING! 1/10"},
    "2": {"cell_cols": 22, "cell_rows": 28, "word": "E", "loop_ratio": 0.06, "name": "字母 E - Energy 能量", "description": "KEEP GOING! 2/10"},
    "3": {"cell_cols": 22, "cell_rows": 28, "word": "E", "loop_ratio": 0.06, "name": "字母 E - Explore 探索", "description": "KEEP GOING! 3/10"},
    "4": {"cell_cols": 22, "cell_rows": 28, "word": "P", "loop_ratio": 0.07, "name": "字母 P - Power 力量", "description": "KEEP GOING! 4/10"},
    "5": {"cell_cols": 24, "cell_rows": 28, "word": "G", "loop_ratio": 0.07, "name": "字母 G - Growth 生长", "description": "KEEP GOING! 5/10"},
    "6": {"cell_cols": 24, "cell_rows": 28, "word": "O", "loop_ratio": 0.07, "name": "字母 O - Overcome 跨越", "description": "KEEP GOING! 6/10"},
    "7": {"cell_cols": 16, "cell_rows": 28, "word": "I", "loop_ratio": 0.07, "name": "字母 I - Insight 洞察", "description": "KEEP GOING! 7/10"},
    "8": {"cell_cols": 24, "cell_rows": 28, "word": "N", "loop_ratio": 0.08, "name": "字母 N - Never Give Up", "description": "KEEP GOING! 8/10"},
    "9": {"cell_cols": 26, "cell_rows": 30, "word": "G", "loop_ratio": 0.08, "name": "字母 G - Glory 荣耀", "description": "KEEP GOING! 9/10"},
    "10": {"cell_cols": 18, "cell_rows": 32, "word": "!", "loop_ratio": 0.09, "name": "感叹号 ! - 永不放弃!", "description": "KEEP GOING! 10/10"},
}

HIGH_RES_LETTERS = {
    "K": [
        "**    **",
        "**   ** ",
        "**  **  ",
        "*****   ",
        "***     ",
        "*****   ",
        "**  **  ",
        "**   ** ",
        "**    **",
    ],
    "E": [
        "*******",
        "**     ",
        "**     ",
        "*****  ",
        "**     ",
        "**     ",
        "*******",
    ],
    "P": [
        "****** ",
        "**   **",
        "**   **",
        "****** ",
        "**     ",
        "**     ",
        "**     ",
    ],
    "G": [
        " ***** ",
        "**   **",
        "**     ",
        "**  ***",
        "**   **",
        "**   **",
        " ***** ",
    ],
    "O": [
        " ***** ",
        "**   **",
        "**   **",
        "**   **",
        "**   **",
        "**   **",
        " ***** ",
    ],
    "I": [
        "*****",
        " **  ",
        " **  ",
        " **  ",
        " **  ",
        " **  ",
        "*****",
    ],
    "N": [
        "**    **",
        "***   **",
        "****  **",
        "** ** **",
        "**  ****",
        "**   ***",
        "**    **",
    ],
    "!": [
        "***",
        "***",
        "***",
        "***",
        "** ",
        "   ",
        "** ",
        "** ",
    ],
}

PIXEL_FONT = {
    "A": [" *** ", "*   *", "*****", "*   *", "*   *"],
    "B": ["**** ", "*   *", "**** ", "*   *", "**** "],
    "C": [" ****", "*    ", "*    ", "*    ", " ****"],
    "D": ["**** ", "*   *", "*   *", "*   *", "**** "],
    "E": ["*****", "*    ", "**** ", "*    ", "*****"],
    "F": ["*****", "*    ", "**** ", "*    ", "*    "],
    "G": [" ****", "*    ", "* ***", "*   *", " ****"],
    "H": ["*   *", "*   *", "*****", "*   *", "*   *"],
    "I": ["***", " * ", " * ", " * ", "***"],
    "J": ["  ***", "   * ", "   * ", "*  * ", " **  "],
    "K": ["*  *", "* * ", "**  ", "* * ", "*  *"],
    "L": ["*    ", "*    ", "*    ", "*    ", "*****"],
    "M": ["*   *", "** **", "* * *", "*   *", "*   *"],
    "N": ["*   *", "**  *", "* * *", "*  **", "*   *"],
    "O": [" *** ", "*   *", "**** ", "*    ", "*    "],
    "P": ["**** ", "*   *", "**** ", "*    ", "*    "],
    "Q": [" *** ", "*   *", "* * *", "*  **", " ****"],
    "R": ["**** ", "*   *", "**** ", "*  * ", "*   *"],
    "S": [" ****", "*    ", " *** ", "    *", "**** "],
    "T": ["*****", "  *  ", "  *  ", "  *  ", "  *  "],
    "U": ["*   *", "*   *", "*   *", "*   *", " *** "],
    "V": ["*   *", "*   *", "*   *", " * * ", "  *  "],
    "W": ["*   *", "*   *", "* * *", "** **", "*   *"],
    "X": ["*   *", " * * ", "  *  ", " * * ", "*   *"],
    "Y": ["*   *", " * * ", "  *  ", "  *  ", "  *  "],
    "Z": ["*****", "   * ", "  *  ", " *   ", "*****"],
    "0": [" *** ", "*  **", "* * *", "**  *", " *** "],
    "1": ["  *  ", " **  ", "  *  ", "  *  ", " *** "],
    "2": [" *** ", "*   *", "  ** ", " *   ", "*****"],
    "3": ["**** ", "    *", " *** ", "    *", "**** "],
    "4": ["*  * ", "*  * ", "*****", "   * ", "   * "],
    "5": ["*****", "*    ", "**** ", "    *", "**** "],
    "6": [" ****", "*    ", "**** ", "*   *", " *** "],
    "7": ["*****", "   * ", "  *  ", " *   ", " *   "],
    "8": [" *** ", "*   *", " *** ", "*   *", " *** "],
    "9": [" *** ", "*   *", " ****", "    *", " ****"],
    " ": ["  ", "  ", "  ", "  ", "  "],
}


def string_to_pattern(text: str) -> list[str]:
    text_upper = text.upper()
    if len(text_upper) == 1 and text_upper in HIGH_RES_LETTERS:
        return list(HIGH_RES_LETTERS[text_upper])

    pattern_lines = ["", "", "", "", ""]
    for i, ch in enumerate(text_upper):
        glyph = PIXEL_FONT.get(ch, PIXEL_FONT.get(" ", ["  ", "  ", "  ", "  ", "  "]))
        for row in range(5):
            pattern_lines[row] += glyph[row]
            if i < len(text_upper) - 1:
                pattern_lines[row] += " "
    return pattern_lines


def get_keep_going_progress(level: int) -> str:
    chars = ["K", "E", "E", "P", "G", "O", "I", "N", "G", "!"]
    res = ""
    for i in range(len(chars)):
        if i == 4:
            res += "  "
        if i < level:
            res += chars[i] + " "
        else:
            res += "_ "
    return res.strip()

PATTERNS = {
    "star": [
        "  *  ",
        " *** ",
        "*****",
        " *** ",
        "*   *",
    ],
    "heart": [
        " ** ** ",
        "*******",
        "*******",
        " ***** ",
        "  ***  ",
        "   *   ",
    ],
    "crown": [
        "*  *  *",
        "*******",
        " *   * ",
        "*******",
    ],
    "key": [
        " *** ",
        "*   *",
        " *** ",
        "  *  ",
        " *** ",
        "  *  ",
        "  ** ",
    ],
    "shield": [
        "*****",
        "*****",
        "*****",
        " *** ",
        "  *  ",
    ],
    "sword": [
        "  *  ",
        "  *  ",
        "  *  ",
        " *** ",
        "  *  ",
        " * * ",
    ],
    "diamond": [
        "  *  ",
        " *** ",
        "*****",
        " *** ",
        "  *  ",
    ],
    "clover": [
        " * * ",
        "*****",
        "  *  ",
        "*****",
        " * * ",
    ],
    "skull": [
        " *** ",
        "* * *",
        "*****",
        " * * ",
    ],
    "trophy": [
        "*****",
        "* * *",
        " *** ",
        "  *  ",
        " *** ",
    ],
    "ai": [
        " ***   *** ",
        "*   *   *  ",
        "*****   *  ",
        "*   *   *  ",
        "*   *  *** ",
    ],
    "art": [
        " ***   ****  *****",
        "*   *  *   *   *  ",
        "*****  ****    *  ",
        "*   *  *  *    *  ",
        "*   *  *   *   *  ",
    ],
    "maze": [
        "*   *  ***  ***** *****",
        "** ** *   *    *  *    ",
        "* * * *****   *   ***  ",
        "*   * *   *  *    *    ",
        "*   * *   * ***** *****",
    ],
}

DIFFICULTIES = W1_DIFFICULTIES

_DIFFICULTY_ALIASES = {
    "easy": "1_3",
    "normal": "1_5",
    "hard": "2_5",
}

# 房间坐标上的四连通：右、左、下、上。
NEIGHBOR_STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))

# 重抽上限：宁可用当前最好的一局，也不要卡在生成循环里。
_MAX_GENERATE_ATTEMPTS = 48


@dataclass(frozen=True)
class MazeMetrics:
    """给 HUD 看的统计：越长的唯一解、越深的死胡同、越多的决策点，分数越高。"""

    path_length: int  # 入口到出口的瓦片步数
    dead_ends: int  # 度为 1 的房间（典型死胡同）
    decision_cells: int  # 度 >= 3 的岔路房间
    avg_dead_end_depth: float  # 死胡同平均深度（房间步数）
    score: float
    label: str


@dataclass
class Maze:
    grid: list[list[int]]
    entrance: tuple[int, int]
    exit: tuple[int, int]
    difficulty_key: str
    metrics: MazeMetrics
    pattern_cells: set[tuple[int, int]] = field(default_factory=set)
    shape_cells: set[tuple[int, int]] = field(default_factory=set)
    overpass_cells: set[tuple[int, int]] = field(default_factory=set)
    item_tiles: set[tuple[int, int]] = field(default_factory=set)
    word_prompt: str = ""

    @property
    def cols(self) -> int:
        return len(self.grid[0])

    @property
    def rows(self) -> int:
        return len(self.grid)

    def is_wall(
        self,
        tile_x: int,
        tile_y: int,
        is_y_axis: bool = False,
        player_x: float | None = None,
        player_y: float | None = None,
        cell_size: int = 26,
        current_layer: str = "none",
    ) -> bool:
        """越界一律当墙，玩家不会走出地图。支持 World 5 南北高架与东西高架立交桥的通道与方向约束。"""
        if tile_x < 0 or tile_y < 0 or tile_x >= self.cols or tile_y >= self.rows:
            return True
        val = self.grid[tile_y][tile_x]
        if val == WALL:
            return True
        if val in (OVERPASS_NS, OVERPASS_EW):
            if player_x is not None and player_y is not None:
                pcx = int(player_x // cell_size)
                pcy = int(player_y // cell_size)
                if pcx == tile_x and pcy == tile_y:
                    if val == OVERPASS_NS:
                        if current_layer == "ns_bridge":
                            return not is_y_axis
                        elif current_layer == "ew_tunnel":
                            return is_y_axis
                        return False
                    else:  # OVERPASS_EW
                        if current_layer == "ew_bridge":
                            return is_y_axis
                        elif current_layer == "ns_tunnel":
                            return not is_y_axis
                        return False
                elif pcx == tile_x and pcy != tile_y:
                    # 玩家中心在过街楼的正上方或正下方 (南北方向轴上)：交互只能沿南北通道！
                    return not is_y_axis
                elif pcy == tile_y and pcx != tile_x:
                    # 玩家中心在过街楼的正左方或正右方 (东西方向轴上)：交互只能沿东西通道！
                    return is_y_axis
                else:
                    # 位于斜角邻居瓦片，禁止斜向切入立交桥护栏
                    return True
            else:
                return False
        return False

    def solve_path(self) -> list[tuple[int, int]]:
        """求解从入口到出口的路径。"""
        return solve_path(self.grid, self.entrance, self.exit)

    def solve_path_with_visited(
        self,
    ) -> tuple[list[tuple[int, int]], list[tuple[int, int]], dict[tuple[int, int], tuple[int, int] | None]]:
        """求解从入口到出口的路径，同时返回 DFS 探索节点顺序与父节点映射关系。"""
        return solve_path_with_visited(self.grid, self.entrance, self.exit)


def generate_maze(
    difficulty_key: str | int = "1_5", seed: int | None = None, world: int | None = None, level: int | None = None
) -> Maze:
    """按大关 (world 1/2/3/4) 和关卡阶数 (level 1-10) 生成一局迷宫；可选 seed 便于复现。
    World 1 (第一大关：绿野森林)：1-10 阶采用拉长路口 DFS 算法，直观清晰；
    World 2 (第二大关：狼穴地牢)：1-10 阶采用高密转弯 Prim + 伪环路高难算法，烧脑陡升；
    World 3 (第三大关：图案秘境)：1-10 阶采用 Opt-Maze 隐写融合算法，中央嵌入像素星心皇冠等奇幻图形！
    World 4 (第四大关：异形几何)：1-10 阶采用几何掩码算法，生成圆形、正三角、菱形、双同心环、五角星、心形等多样非正方形迷宫！
    """
    if world is not None and level is not None:
        w_val = int(world)
        l_val = int(level)
    else:
        key_str = str(difficulty_key).lower()
        if key_str in _DIFFICULTY_ALIASES:
            key_str = _DIFFICULTY_ALIASES[key_str]
        if "_" in key_str:
            parts = key_str.split("_")
            w_val = int(parts[0])
            l_val = int(parts[1])
        else:
            val = int(key_str)
            if val > 50:
                w_val = 6
                l_val = val - 50
            elif val > 40:
                w_val = 5
                l_val = val - 40
            elif val > 30:
                w_val = 4
                l_val = val - 30
            elif val > 20:
                w_val = 3
                l_val = val - 20
            elif val > 10:
                w_val = 2
                l_val = val - 10
            else:
                w_val = 1
                l_val = val

    w_val = max(1, min(6, w_val))
    l_val = max(1, min(10, l_val))

    if w_val == 6:
        spec = W6_DIFFICULTIES[str(l_val)]
    elif w_val == 5:
        spec = W5_DIFFICULTIES[str(l_val)]
    elif w_val == 4:
        spec = W4_DIFFICULTIES[str(l_val)]
    elif w_val == 3:
        spec = W3_DIFFICULTIES[str(l_val)]
    elif w_val == 2:
        spec = W2_DIFFICULTIES[str(l_val)]
    else:
        spec = W1_DIFFICULTIES[str(l_val)]

    rng = random.Random(seed)
    best: Maze | None = None
    attempts = 1 if seed is not None else (8 if l_val >= 7 else 12)
    display_key = f"{w_val}_{l_val}"

    for _ in range(attempts):
        if w_val == 6:
            word = spec.get("word", "K")
            maze = _carve_word_prompt_maze(spec, word, display_key, rng)
        elif w_val == 5:
            maze = _carve_woven_maze(spec, display_key, rng)
        elif w_val == 4:
            maze = _carve_shape_maze(spec, display_key, rng)
        elif w_val == 3:
            maze = _carve_pattern_maze(spec, display_key, rng)
        elif w_val == 2:
            maze = _carve_dungeon_maze(spec, display_key, rng)
        else:
            maze = _carve_maze(spec, display_key, rng)

        if best is None or _maze_quality(maze) > _maze_quality(best):
            best = maze

        min_path_len = spec["cell_cols"] * spec["cell_rows"] * (0.35 if w_val == 1 else 0.20)
        if maze.metrics.path_length >= min_path_len:
            if w_val in (2, 3, 4, 5, 6) or maze.metrics.avg_dead_end_depth >= spec.get("min_dead_end_depth", 0):
                break

    assert best is not None
    if w_val in (2, 3, 4, 5, 6):
        if w_val in (2, 3, 4):
            loop_ratio = spec.get("loop_ratio", 0.04 if w_val == 2 else 0.06)
            _add_guarded_braid_loops(best.grid, best.entrance, best.exit, loop_ratio, rng)
        best = Maze(
            grid=best.grid,
            entrance=best.entrance,
            exit=best.exit,
            difficulty_key=display_key,
            metrics=_measure(best.grid, best.entrance, best.exit, display_key),
            pattern_cells=getattr(best, "pattern_cells", set()),
            shape_cells=getattr(best, "shape_cells", set()),
            overpass_cells=getattr(best, "overpass_cells", set()),
            word_prompt=getattr(best, "word_prompt", ""),
        )
    best.item_tiles = _place_items(best.grid, best.entrance, best.exit, l_val, rng)
    return best


def _place_items(
    grid: list[list[int]],
    entrance: tuple[int, int],
    exit_tile: tuple[int, int],
    level: int,
    rng: random.Random,
) -> set[tuple[int, int]]:
    """在迷宫可走路径 (PATH 瓦片) 上散落放置过关必需收集的支线道具 (每局 7 个)。
    使用 BFS 连通性校验，绝对保证所有道具 100% 均可被玩家步行到达。
    """
    target_count = 7
    dist = _bfs_distances(grid, entrance)
    candidates: list[tuple[int, int]] = []
    height = len(grid)
    width = len(grid[0])
    for y in range(height):
        for x in range(width):
            if grid[y][x] == PATH and (x, y) in dist:
                if (x, y) != entrance and (x, y) != exit_tile:
                    candidates.append((x, y))

    if not candidates:
        return set()

    if len(candidates) >= target_count * 2:
        rng.shuffle(candidates)
        selected: list[tuple[int, int]] = []
        for c in candidates:
            if abs(c[0] - entrance[0]) + abs(c[1] - entrance[1]) <= 2:
                continue
            if abs(c[0] - exit_tile[0]) + abs(c[1] - exit_tile[1]) <= 2:
                continue
            too_close = False
            for sc in selected:
                if abs(c[0] - sc[0]) + abs(c[1] - sc[1]) <= 2:
                    too_close = True
                    break
            if not too_close:
                selected.append(c)
                if len(selected) >= target_count:
                    break
        if len(selected) < target_count:
            for c in candidates:
                if c not in selected and c != entrance and c != exit_tile:
                    selected.append(c)
                    if len(selected) >= target_count:
                        break
        return set(selected)
    else:
        return set(rng.sample(candidates, min(len(candidates), target_count)))


def _maze_quality(maze: Maze) -> tuple[int, int, float]:
    """重抽时的比较键：优先保证迷宫被充分探索（更长的主解路线），其次决策点数和死胡同深度。"""
    m = maze.metrics
    return (m.path_length, m.decision_cells, m.avg_dead_end_depth)


def _carve_maze(spec: dict, difficulty_key: str, rng: random.Random) -> Maze:
    """递归回溯挖墙：栈顶优先，保证当前这条路会一直挖到走不动。"""
    cell_cols = spec["cell_cols"]
    cell_rows = spec["cell_rows"]
    straight_bias = spec["straight_bias"]
    max_straight_run = spec["max_straight_run"]

    width = cell_cols * 2 + 1
    height = cell_rows * 2 + 1
    # 先铺满墙，再把房间中心和打通的隔墙改成路。
    grid = [[WALL for _ in range(width)] for _ in range(height)]

    def cell_to_tile(cx: int, cy: int) -> tuple[int, int]:
        """房间 (cx, cy) 对应瓦片坐标。奇数行/列才是房间中心。"""
        return cx * 2 + 1, cy * 2 + 1

    start_cx, start_cy = 0, 0
    sx, sy = cell_to_tile(start_cx, start_cy)
    grid[sy][sx] = PATH

    visited = {(start_cx, start_cy)}
    stack = [(start_cx, start_cy)]
    # 走进每个房间时用的方向，用来做「直行偏好」。
    enter_dir: dict[tuple[int, int], tuple[int, int]] = {(start_cx, start_cy): (1, 0)}
    # 走到该房间时，已经连续直行了几步。
    run_length: dict[tuple[int, int], int] = {(start_cx, start_cy): 0}

    while stack:
        cx, cy = stack[-1]

        options = []
        for dcx, dcy in NEIGHBOR_STEPS:
            ncx, ncy = cx + dcx, cy + dcy
            if 0 <= ncx < cell_cols and 0 <= ncy < cell_rows and (ncx, ncy) not in visited:
                options.append((ncx, ncy, dcx, dcy))

        if not options:
            stack.pop()
            continue

        incoming = enter_dir.get((cx, cy))
        cur_run = run_length.get((cx, cy), 0)
        straight = [opt for opt in options if incoming is not None and (opt[2], opt[3]) == incoming]
        turns = [opt for opt in options if incoming is None or (opt[2], opt[3]) != incoming]

        # 直行太长且还能拐弯：强制转弯，避免从路口一眼看到底。
        if incoming is not None and cur_run >= max_straight_run and turns:
            options = turns
        elif incoming is not None and rng.random() < straight_bias and straight:
            options = straight

        ncx, ncy, dcx, dcy = rng.choice(options)
        # 两个房间中心之间隔着一格墙，把它打通。
        wall_x = cx * 2 + 1 + dcx
        wall_y = cy * 2 + 1 + dcy
        nx, ny = cell_to_tile(ncx, ncy)
        grid[wall_y][wall_x] = PATH
        grid[ny][nx] = PATH
        visited.add((ncx, ncy))
        enter_dir[(ncx, ncy)] = (dcx, dcy)
        run_length[(ncx, ncy)] = cur_run + 1 if incoming == (dcx, dcy) else 1
        stack.append((ncx, ncy))

    entrance = cell_to_tile(start_cx, start_cy)
    # 出口取距离入口最远的房间，保证解尽可能长。
    exit_tile = _farthest_cell(grid, entrance, cell_cols, cell_rows)
    metrics = _measure(grid, entrance, exit_tile, difficulty_key)
    return Maze(
        grid=grid,
        entrance=entrance,
        exit=exit_tile,
        difficulty_key=difficulty_key,
        metrics=metrics,
    )


def _add_guarded_braid_loops(
    grid: list[list[int]],
    entrance: tuple[int, int],
    exit_tile: tuple[int, int],
    loop_ratio: float,
    rng: random.Random,
) -> None:
    """智能守护的伪环路打通：
    在死胡同与旁支通道间打通环路以增加九曲回环的迷茫感与误导性，
    但严禁打穿直达终点的超短捷径，确保主解路线的充分长度与挑战难度。
    """
    height = len(grid)
    width = len(grid[0])
    candidate_walls = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if grid[y][x] == WALL:
                if grid[y][x - 1] == PATH and grid[y][x + 1] == PATH and grid[y - 1][x] == WALL and grid[y + 1][x] == WALL:
                    candidate_walls.append((x, y))
                elif grid[y - 1][x] == PATH and grid[y + 1][x] == PATH and grid[y][x - 1] == WALL and grid[y][x + 1] == WALL:
                    candidate_walls.append((x, y))

    if not candidate_walls:
        return

    orig_path = solve_path(grid, entrance, exit_tile)
    orig_len = len(orig_path)
    min_allowed_len = max(8, int(orig_len * 0.80))

    loop_count = max(1, int(len(candidate_walls) * loop_ratio))
    shuffled = rng.sample(candidate_walls, len(candidate_walls))

    added = 0
    max_checks = min(len(shuffled), max(12, loop_count * 2))
    for i in range(max_checks):
        if added >= loop_count:
            break
        x, y = shuffled[i]
        grid[y][x] = PATH
        new_path = solve_path(grid, entrance, exit_tile)
        if len(new_path) < min_allowed_len:
            grid[y][x] = WALL
        else:
            added += 1


def _carve_dungeon_maze(spec: dict, difficulty_key: str, rng: random.Random) -> Maze:
    """第二大关：暗黑狼穴地牢高难迷宫算法。
    特点：
    1. 普里姆 (Prim) 算法高密转弯，产生九曲十八弯极密通路；
    2. 智能守护伪环路 (Guarded Braid Loops)，形成九曲分支迷宫的同时，防止直达捷径把主路线缩短。
    """
    cell_cols = spec["cell_cols"]
    cell_rows = spec["cell_rows"]

    width = cell_cols * 2 + 1
    height = cell_rows * 2 + 1
    grid = [[WALL for _ in range(width)] for _ in range(height)]

    def cell_to_tile(cx: int, cy: int) -> tuple[int, int]:
        return cx * 2 + 1, cy * 2 + 1

    start_cx, start_cy = 0, 0
    sx, sy = cell_to_tile(start_cx, start_cy)
    grid[sy][sx] = PATH

    visited = {(start_cx, start_cy)}
    frontier = []
    for dcx, dcy in NEIGHBOR_STEPS:
        ncx, ncy = start_cx + dcx, start_cy + dcy
        if 0 <= ncx < cell_cols and 0 <= ncy < cell_rows:
            frontier.append((start_cx, start_cy, dcx, dcy))

    while frontier:
        idx = rng.randrange(len(frontier))
        cx, cy, dcx, dcy = frontier.pop(idx)
        ncx, ncy = cx + dcx, cy + dcy

        if (ncx, ncy) in visited:
            continue

        visited.add((ncx, ncy))
        wall_x = cx * 2 + 1 + dcx
        wall_y = cy * 2 + 1 + dcy
        nx, ny = cell_to_tile(ncx, ncy)
        grid[wall_y][wall_x] = PATH
        grid[ny][nx] = PATH

        for ndcx, ndcy in NEIGHBOR_STEPS:
            nncx, nncy = ncx + ndcx, ncy + ndcy
            if 0 <= nncx < cell_cols and 0 <= nncy < cell_rows and (nncx, nncy) not in visited:
                frontier.append((ncx, ncy, ndcx, ndcy))

    entrance = cell_to_tile(start_cx, start_cy)
    exit_tile = _farthest_cell(grid, entrance, cell_cols, cell_rows)

    metrics = _measure(grid, entrance, exit_tile, difficulty_key)
    return Maze(
        grid=grid,
        entrance=entrance,
        exit=exit_tile,
        difficulty_key=difficulty_key,
        metrics=metrics,
    )


def _pattern_components(pattern_rooms: set[tuple[int, int]]) -> dict[tuple[int, int], set[tuple[int, int]]]:
    """计算图案房间的正交连通分量，按连通块管理 Prim 访问状态，防止离散像素导致孤岛。"""
    room_map: dict[tuple[int, int], set[tuple[int, int]]] = {}
    unvisited = set(pattern_rooms)
    while unvisited:
        start = next(iter(unvisited))
        comp = {start}
        unvisited.remove(start)
        q = [start]
        while q:
            curr = q.pop()
            for dx, dy in NEIGHBOR_STEPS:
                nbr = (curr[0] + dx, curr[1] + dy)
                if nbr in unvisited:
                    unvisited.remove(nbr)
                    comp.add(nbr)
                    q.append(nbr)
        for r in comp:
            room_map[r] = comp
    return room_map


def _get_word_stroke(word: str) -> list[tuple[int, int]]:
    """获取字母/符号 1-步正交 1D 连续一笔画描边房间坐标 (cx, cy) 序列。"""
    word_upper = word.upper()
    strokes: dict[str, list[tuple[int, int]]] = {}

    # 'K'
    k: list[tuple[int, int]] = []
    for y in range(1, 14): k.append((1, y))
    k.append((2, 13))
    for y in range(12, 6, -1): k.append((2, y))
    cx, cy = 2, 7
    for _ in range(5): cx += 1; k.append((cx, cy)); cy -= 1; k.append((cx, cy))
    cy += 1; k.append((cx, cy))
    for _ in range(4): cx -= 1; k.append((cx, cy)); cy += 1; k.append((cx, cy))
    for _ in range(5): cx += 1; k.append((cx, cy)); cy += 1; k.append((cx, cy))
    strokes["K"] = k

    # 'E'
    e: list[tuple[int, int]] = []
    for x in range(1, 9): e.append((x, 1))
    e.append((8, 2))
    for x in range(7, 1, -1): e.append((x, 2))
    for y in range(3, 7): e.append((2, y))
    for x in range(3, 8): e.append((x, 6))
    e.append((7, 7))
    for x in range(6, 1, -1): e.append((x, 7))
    for y in range(8, 12): e.append((2, y))
    for x in range(3, 9): e.append((x, 11))
    strokes["E"] = e

    # 'P'
    p: list[tuple[int, int]] = []
    for y in range(1, 14): p.append((1, y))
    p.append((2, 13))
    for y in range(12, 6, -1): p.append((2, y))
    for x in range(3, 8): p.append((x, 7))
    for y in range(6, 0, -1): p.append((7, y))
    for x in range(6, 1, -1): p.append((x, 1))
    strokes["P"] = p

    # 'G'
    g: list[tuple[int, int]] = []
    for x in range(8, 0, -1): g.append((x, 1))
    for y in range(2, 13): g.append((1, y))
    for x in range(2, 9): g.append((x, 12))
    for y in range(11, 6, -1): g.append((8, y))
    for x in range(7, 3, -1): g.append((x, 7))
    strokes["G"] = g

    # 'O'
    o: list[tuple[int, int]] = []
    for x in range(1, 9): o.append((x, 1))
    for y in range(2, 13): o.append((8, y))
    for x in range(7, 0, -1): o.append((x, 12))
    for y in range(11, 1, -1): o.append((1, y))
    strokes["O"] = o

    # 'I'
    i_str: list[tuple[int, int]] = []
    for x in range(1, 9): i_str.append((x, 1))
    for x in range(8, 3, -1): i_str.append((x, 2))
    for y in range(3, 12): i_str.append((4, y))
    for x in range(5, 9): i_str.append((x, 11))
    for x in range(8, 0, -1): i_str.append((x, 12))
    strokes["I"] = i_str

    # 'N'
    n: list[tuple[int, int]] = []
    for y in range(1, 14): n.append((1, y))
    n.append((2, 13))
    for y in range(12, 0, -1): n.append((2, y))
    cx, cy = 2, 1
    for _ in range(5):
        cx += 1; n.append((cx, cy))
        cy += 1; n.append((cx, cy))
        cy += 1; n.append((cx, cy))
    for y in range(10, 0, -1): n.append((7, y))
    strokes["N"] = n

    # '!'
    ex: list[tuple[int, int]] = []
    for y in range(1, 9): ex.append((1, y))
    ex.append((2, 8))
    for y in range(7, 0, -1): ex.append((2, y))
    ex.append((3, 1))
    for y in range(2, 12): ex.append((3, y))
    ex.append((2, 11))
    ex.append((1, 11))
    strokes["!"] = ex

    return strokes.get(word_upper, strokes["K"])


def _find_stroke_connector(
    src: tuple[int, int], dst: tuple[int, int], stroke_set: set[tuple[int, int]], cols: int, rows: int
) -> list[tuple[int, int]]:
    pq = [(0, src)]
    dist = {src: 0}
    parent: dict[tuple[int, int], tuple[int, int] | None] = {src: None}
    while pq:
        d, curr = heapq.heappop(pq)
        if curr == dst:
            break
        if d > dist.get(curr, 1e9):
            continue
        cx, cy = curr
        for dx, dy in NEIGHBOR_STEPS:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < cols and 0 <= ny < rows:
                cost = 1 if (nx, ny) not in stroke_set or (nx, ny) == dst else 1000
                if d + cost < dist.get((nx, ny), 1e9):
                    dist[(nx, ny)] = d + cost
                    parent[(nx, ny)] = curr
                    heapq.heappush(pq, (d + cost, (nx, ny)))
    res = []
    curr: tuple[int, int] | None = dst
    while curr is not None:
        res.append(curr)
        curr = parent.get(curr)
    res.reverse()
    return res


def _carve_word_prompt_maze(spec: dict, word: str, difficulty_key: str, rng: random.Random) -> Maze:
    """第六大关：提示词隐语阵 (Opt-Maze 1D 连续一笔画描边解法路径算法)
    特点：
    1. 迷宫主解法路径 (entrance -> exit) 自身 100% 精确勾勒出目标字母/字符轨迹！
    2. 入口与出口通过安全连通线无缝对接字母起始与终点；
    3. 主路径四周通过 Prim 算法密布死胡同分支树，保证迷宫可玩性与难度。
    """
    cell_cols = spec["cell_cols"]
    cell_rows = spec["cell_rows"]
    stroke_rooms = _get_word_stroke(word)

    width = cell_cols * 2 + 1
    height = cell_rows * 2 + 1
    grid = [[WALL for _ in range(width)] for _ in range(height)]

    def cell_to_tile(cx: int, cy: int) -> tuple[int, int]:
        return cx * 2 + 1, cy * 2 + 1

    max_cx = max(cx for cx, cy in stroke_rooms)
    max_cy = max(cy for cx, cy in stroke_rooms)
    off_x = max(1, (cell_cols - 1 - max_cx) // 2)
    off_y = max(1, (cell_rows - 1 - max_cy) // 2)

    centered_stroke = [(cx + off_x, cy + off_y) for cx, cy in stroke_rooms]
    stroke_set = set(centered_stroke)

    ent_path = _find_stroke_connector((0, 0), centered_stroke[0], stroke_set, cell_cols, cell_rows)[:-1]
    exit_path = _find_stroke_connector(
        centered_stroke[-1], (cell_cols - 1, cell_rows - 1), stroke_set, cell_cols, cell_rows
    )[1:]

    full_main_path_rooms = ent_path + centered_stroke + exit_path

    pattern_cells: set[tuple[int, int]] = set()
    visited_rooms: set[tuple[int, int]] = set()

    for i in range(len(full_main_path_rooms)):
        rcx, rcy = full_main_path_rooms[i]
        tx, ty = cell_to_tile(rcx, rcy)
        grid[ty][tx] = PATH
        visited_rooms.add((rcx, rcy))
        if (rcx, rcy) in stroke_set:
            pattern_cells.add((tx, ty))

        if i > 0:
            prcx, prcy = full_main_path_rooms[i - 1]
            wx = (rcx + prcx) + 1
            wy = (rcy + prcy) + 1
            grid[wy][wx] = PATH
            if (rcx, rcy) in stroke_set and (prcx, prcy) in stroke_set:
                pattern_cells.add((wx, wy))

    frontier = []
    for rcx, rcy in list(visited_rooms):
        for dcx, dcy in NEIGHBOR_STEPS:
            ncx, ncy = rcx + dcx, rcy + dcy
            if 0 <= ncx < cell_cols and 0 <= ncy < cell_rows and (ncx, ncy) not in visited_rooms:
                frontier.append((rcx, rcy, dcx, dcy))

    while frontier:
        idx = rng.randrange(len(frontier))
        cx, cy, dcx, dcy = frontier.pop(idx)
        ncx, ncy = cx + dcx, cy + dcy
        if (ncx, ncy) in visited_rooms:
            continue
        visited_rooms.add((ncx, ncy))
        wx, wy = cx * 2 + 1 + dcx, cy * 2 + 1 + dcy
        nx, ny = cell_to_tile(ncx, ncy)
        grid[wy][wx] = PATH
        grid[ny][nx] = PATH
        for ndcx, ndcy in NEIGHBOR_STEPS:
            nncx, nncy = ncx + ndcx, ncy + ndcy
            if 0 <= nncx < cell_cols and 0 <= nncy < cell_rows and (nncx, nncy) not in visited_rooms:
                frontier.append((ncx, ncy, ndcx, ndcy))

    entrance = cell_to_tile(0, 0)
    exit_tile = cell_to_tile(cell_cols - 1, cell_rows - 1)

    metrics = _measure(grid, entrance, exit_tile, difficulty_key)
    return Maze(
        grid=grid,
        entrance=entrance,
        exit=exit_tile,
        difficulty_key=difficulty_key,
        metrics=metrics,
        pattern_cells=pattern_cells,
        word_prompt=word,
    )


def _carve_pattern_maze(spec: dict, difficulty_key: str, rng: random.Random) -> Maze:
    """第三大关/第六大关：图案秘境与提示词阵 (Opt-Maze 隐写融合算法)
    特点：
    1. 在迷宫正中央精准融嵌入像素图案或字母提示词阵；
    2. 将图案瓦片贯通入迷宫主通路网，四周交织普里姆九曲路与环路；
    3. 严格保证全地图 100% 连通与高长度的穿梭解法路径。
    """
    cell_cols = spec["cell_cols"]
    cell_rows = spec["cell_rows"]
    pattern_lines = spec.get("pattern_lines")
    if not pattern_lines:
        pattern_name = spec.get("pattern", "star")
        pattern_lines = PATTERNS.get(pattern_name, PATTERNS["star"])

    width = cell_cols * 2 + 1
    height = cell_rows * 2 + 1
    grid = [[WALL for _ in range(width)] for _ in range(height)]

    def cell_to_tile(cx: int, cy: int) -> tuple[int, int]:
        return cx * 2 + 1, cy * 2 + 1

    # 1. 计算图案在房间网格中的居中偏移
    pat_h = len(pattern_lines)
    pat_w = max(len(line) for line in pattern_lines)
    offset_cx = max(1, (cell_cols - pat_w) // 2)
    offset_cy = max(1, (cell_rows - pat_h) // 2)

    pattern_cells: set[tuple[int, int]] = set()
    pattern_rooms: set[tuple[int, int]] = set()

    for py, line in enumerate(pattern_lines):
        for px, char in enumerate(line):
            if char == '*':
                rcx = offset_cx + px
                rcy = offset_cy + py
                if 0 <= rcx < cell_cols and 0 <= rcy < cell_rows:
                    pattern_rooms.add((rcx, rcy))
                    tx, ty = cell_to_tile(rcx, rcy)
                    grid[ty][tx] = PATH
                    pattern_cells.add((tx, ty))

    # 打通图案内部相邻房间之间的墙
    for rcx, rcy in list(pattern_rooms):
        for dcx, dcy in NEIGHBOR_STEPS:
            nroom = (rcx + dcx, rcy + dcy)
            if nroom in pattern_rooms:
                wx = rcx * 2 + 1 + dcx
                wy = rcy * 2 + 1 + dcy
                grid[wy][wx] = PATH
                pattern_cells.add((wx, wy))

    pattern_comp_map = _pattern_components(pattern_rooms)

    # 2. 从起点 (0,0) 开始执行 Prim 算法生成连通生成树
    start_cx, start_cy = 0, 0
    sx, sy = cell_to_tile(start_cx, start_cy)
    grid[sy][sx] = PATH

    visited = {(start_cx, start_cy)}
    if (start_cx, start_cy) in pattern_rooms:
        visited |= pattern_comp_map[(start_cx, start_cy)]

    frontier = []
    for dcx, dcy in NEIGHBOR_STEPS:
        ncx, ncy = start_cx + dcx, start_cy + dcy
        if 0 <= ncx < cell_cols and 0 <= ncy < cell_rows and (ncx, ncy) not in visited:
            frontier.append((start_cx, start_cy, dcx, dcy))

    while frontier:
        idx = rng.randrange(len(frontier))
        cx, cy, dcx, dcy = frontier.pop(idx)
        ncx, ncy = cx + dcx, cy + dcy

        if (ncx, ncy) in visited:
            continue

        if (ncx, ncy) in pattern_rooms:
            # 首次触达图案区域连通块：打通连接入口墙，并将连通块房间并入 visited
            comp = pattern_comp_map[(ncx, ncy)]
            newly_visited = comp - visited
            visited |= comp
            wall_x = cx * 2 + 1 + dcx
            wall_y = cy * 2 + 1 + dcy
            grid[wall_y][wall_x] = PATH

            for pr_cx, pr_cy in newly_visited:
                for ndcx, ndcy in NEIGHBOR_STEPS:
                    nncx, nncy = pr_cx + ndcx, pr_cy + ndcy
                    if 0 <= nncx < cell_cols and 0 <= nncy < cell_rows and (nncx, nncy) not in visited:
                        frontier.append((pr_cx, pr_cy, ndcx, ndcy))
        else:
            visited.add((ncx, ncy))
            wall_x = cx * 2 + 1 + dcx
            wall_y = cy * 2 + 1 + dcy
            nx, ny = cell_to_tile(ncx, ncy)
            grid[wall_y][wall_x] = PATH
            grid[ny][nx] = PATH

            for ndcx, ndcy in NEIGHBOR_STEPS:
                nncx, nncy = ncx + ndcx, ncy + ndcy
                if 0 <= nncx < cell_cols and 0 <= nncy < cell_rows and (nncx, nncy) not in visited:
                    frontier.append((ncx, ncy, ndcx, ndcy))

    entrance = cell_to_tile(start_cx, start_cy)
    exit_tile = _farthest_cell(grid, entrance, cell_cols, cell_rows)

    metrics = _measure(grid, entrance, exit_tile, difficulty_key)
    return Maze(
        grid=grid,
        entrance=entrance,
        exit=exit_tile,
        difficulty_key=difficulty_key,
        metrics=metrics,
        pattern_cells=pattern_cells,
    )


def _is_inside_shape(cx: int, cy: int, cols: int, rows: int, shape_name: str) -> bool:
    """归一化坐标判定 (cx, cy) 是否落入指定的几何形状掩码内部 [-1.0, 1.0]。"""
    nx = (cx + 0.5 - cols / 2.0) / (cols / 2.0)
    ny = (cy + 0.5 - rows / 2.0) / (rows / 2.0)

    if shape_name == "circle":
        return (nx * nx + ny * ny) <= 0.92
    elif shape_name == "triangle":
        return ny >= -0.85 and ny <= 0.85 and abs(nx) <= (0.85 - ny) / 1.7 * 0.90
    elif shape_name == "diamond":
        return abs(nx) + abs(ny) <= 0.95
    elif shape_name == "donut":
        r2 = nx * nx + ny * ny
        return 0.28 * 0.28 <= r2 <= 0.92 * 0.92
    elif shape_name == "cross":
        return (abs(nx) <= 0.38 and abs(ny) <= 0.92) or (abs(ny) <= 0.38 and abs(nx) <= 0.92)
    elif shape_name == "star":
        r = math.sqrt(nx * nx + ny * ny)
        theta = math.atan2(ny, nx)
        r_star = 0.52 + 0.38 * math.cos(5 * theta - math.pi / 2.0)
        return r <= max(0.20, r_star)
    elif shape_name == "hexagon":
        return abs(ny) <= 0.90 and (abs(nx) * 0.866 + abs(ny) * 0.5) <= 0.866
    elif shape_name == "hourglass":
        return abs(ny) <= 0.92 and abs(nx) <= (abs(ny) * 0.85 + 0.10)
    elif shape_name == "heart":
        x = nx * 1.15
        y = -ny * 1.15 + 0.25
        return (x * x + y * y - 1.0) ** 3 - x * x * y * y * y <= 0.0
    elif shape_name == "mega_polygon":
        return abs(nx) <= 0.92 and abs(ny) <= 0.92 and (abs(nx) + abs(ny) <= 1.35) and not (0.22 <= abs(nx) <= 0.38 and 0.22 <= abs(ny) <= 0.38)
    return True


def _carve_shape_maze(spec: dict, difficulty_key: str, rng: random.Random) -> Maze:
    """第四大关：异形几何秘境 (Geometric Shape Masking)
    特点：
    1. 根据圆形、正三角、菱形、环形、五角星、心形等几何掩码裁剪房间网格；
    2. 在形状有效区域内连通雕刻，自然呈现规则几何外观；
    3. 100% 兼容 2D 像素风与所有平滑算法。
    """
    cell_cols = spec["cell_cols"]
    cell_rows = spec["cell_rows"]
    shape_name = spec["shape"]

    shape_rooms = set()
    for cy in range(cell_rows):
        for cx in range(cell_cols):
            if _is_inside_shape(cx, cy, cell_cols, cell_rows, shape_name):
                shape_rooms.add((cx, cy))

    if not shape_rooms:
        shape_rooms = {(cx, cy) for cy in range(cell_rows) for cx in range(cell_cols)}

    width = cell_cols * 2 + 1
    height = cell_rows * 2 + 1
    grid = [[WALL for _ in range(width)] for _ in range(height)]
    shape_cells: set[tuple[int, int]] = set()

    def cell_to_tile(cx: int, cy: int) -> tuple[int, int]:
        return cx * 2 + 1, cy * 2 + 1

    # 起点选在最靠近顶中部位的有效房间
    start_cx, start_cy = min(shape_rooms, key=lambda p: (abs(p[0] - cell_cols // 2) + p[1] * 2))
    sx, sy = cell_to_tile(start_cx, start_cy)
    grid[sy][sx] = PATH
    shape_cells.add((sx, sy))

    visited = {(start_cx, start_cy)}
    frontier = []
    for dcx, dcy in NEIGHBOR_STEPS:
        ncx, ncy = start_cx + dcx, start_cy + dcy
        if (ncx, ncy) in shape_rooms:
            frontier.append((start_cx, start_cy, dcx, dcy))

    while frontier:
        idx = rng.randrange(len(frontier))
        cx, cy, dcx, dcy = frontier.pop(idx)
        ncx, ncy = cx + dcx, cy + dcy

        if (ncx, ncy) in visited:
            continue

        visited.add((ncx, ncy))
        wall_x = cx * 2 + 1 + dcx
        wall_y = cy * 2 + 1 + dcy
        nx, ny = cell_to_tile(ncx, ncy)
        grid[wall_y][wall_x] = PATH
        grid[ny][nx] = PATH
        shape_cells.add((wall_x, wall_y))
        shape_cells.add((nx, ny))

        for ndcx, ndcy in NEIGHBOR_STEPS:
            nncx, nncy = ncx + ndcx, ncy + ndcy
            if (nncx, nncy) in shape_rooms and (nncx, nncy) not in visited:
                frontier.append((ncx, ncy, ndcx, ndcy))

    entrance = cell_to_tile(start_cx, start_cy)
    exit_tile = _farthest_cell(grid, entrance, cell_cols, cell_rows)

    metrics = _measure(grid, entrance, exit_tile, difficulty_key)
    return Maze(
        grid=grid,
        entrance=entrance,
        exit=exit_tile,
        difficulty_key=difficulty_key,
        metrics=metrics,
        shape_cells=shape_cells,
    )


def _carve_woven_maze(spec: dict, difficulty_key: str, rng: random.Random) -> Maze:
    """第五大关：立交编织秘境 (Woven / 3D Overpass Maze)
    特点：
    1. 生成双层/立交桥结构，通道可在不重合的情况下互相打通与交错跨越；
    2. 支持融合 Opt-Maze 隐写图案 (如 "AI", "ART", "MAZE" 字母型立交桥)；
    3. OVERPASS 瓦片 (值为 2) 具备三维立交属性，南北通道在桥上，东西通道在隧道下方；
    4. 玩家、大灰狼与寻路算法皆支持立交规则。
    """
    cell_cols = spec["cell_cols"]
    cell_rows = spec["cell_rows"]
    woven_target = spec.get("woven_target", 15)
    pattern_name = spec.get("pattern")

    width = cell_cols * 2 + 1
    height = cell_rows * 2 + 1
    grid = [[WALL for _ in range(width)] for _ in range(height)]
    overpass_cells: set[tuple[int, int]] = set()
    pattern_cells: set[tuple[int, int]] = set()
    pattern_rooms: set[tuple[int, int]] = set()

    def cell_to_tile(cx: int, cy: int) -> tuple[int, int]:
        return cx * 2 + 1, cy * 2 + 1

    # 1. 若配置了隐写图案，先在中心位置镂刻图案房间与贯通边
    if pattern_name and pattern_name in PATTERNS:
        pattern_lines = PATTERNS[pattern_name]
        pat_h = len(pattern_lines)
        pat_w = max(len(line) for line in pattern_lines)
        offset_cx = max(1, (cell_cols - pat_w) // 2)
        offset_cy = max(1, (cell_rows - pat_h) // 2)

        for py, line in enumerate(pattern_lines):
            for px, char in enumerate(line):
                if char == '*':
                    rcx = offset_cx + px
                    rcy = offset_cy + py
                    if 0 <= rcx < cell_cols and 0 <= rcy < cell_rows:
                        pattern_rooms.add((rcx, rcy))
                        tx, ty = cell_to_tile(rcx, rcy)
                        grid[ty][tx] = PATH
                        pattern_cells.add((tx, ty))

        for rcx, rcy in list(pattern_rooms):
            for dcx, dcy in NEIGHBOR_STEPS:
                nroom = (rcx + dcx, rcy + dcy)
                if nroom in pattern_rooms:
                    wx = rcx * 2 + 1 + dcx
                    wy = rcy * 2 + 1 + dcy
                    grid[wy][wx] = PATH
                    pattern_cells.add((wx, wy))

    pattern_comp_map = _pattern_components(pattern_rooms)

    visited = {(0, 0)}
    if (0, 0) in pattern_rooms:
        visited |= pattern_comp_map[(0, 0)]

    sx, sy = cell_to_tile(0, 0)
    grid[sy][sx] = PATH

    frontier = []
    # 初始化迷宫起点的前沿边
    for init_cx, init_cy in list(visited):
        for dcx, dcy in NEIGHBOR_STEPS:
            ncx, ncy = init_cx + dcx, init_cy + dcy
            if 0 <= ncx < cell_cols and 0 <= ncy < cell_rows and (ncx, ncy) not in visited:
                frontier.append((init_cx, init_cy, dcx, dcy))

    woven_created = 0

    while frontier:
        idx = rng.randrange(len(frontier))
        cx, cy, dcx, dcy = frontier.pop(idx)
        ncx, ncy = cx + dcx, cy + dcy

        if (ncx, ncy) not in visited:
            if (ncx, ncy) in pattern_rooms:
                comp = pattern_comp_map[(ncx, ncy)]
                newly_visited = comp - visited
                visited |= comp
                wall_x = cx * 2 + 1 + dcx
                wall_y = cy * 2 + 1 + dcy
                grid[wall_y][wall_x] = PATH

                for pr_cx, pr_cy in newly_visited:
                    for ndcx, ndcy in NEIGHBOR_STEPS:
                        nncx, nncy = pr_cx + ndcx, pr_cy + ndcy
                        if 0 <= nncx < cell_cols and 0 <= nncy < cell_rows and (nncx, nncy) not in visited:
                            frontier.append((pr_cx, pr_cy, ndcx, ndcy))
            else:
                visited.add((ncx, ncy))
                wall_x = cx * 2 + 1 + dcx
                wall_y = cy * 2 + 1 + dcy
                nx, ny = cell_to_tile(ncx, ncy)
                grid[wall_y][wall_x] = PATH
                grid[ny][nx] = PATH

                for ndcx, ndcy in NEIGHBOR_STEPS:
                    nncx, nncy = ncx + ndcx, ncy + ndcy
                    if 0 <= nncx < cell_cols and 0 <= nncy < cell_rows and (nncx, nncy) not in visited:
                        frontier.append((ncx, ncy, ndcx, ndcy))

        elif woven_created < woven_target:
            nncx, nncy = ncx + dcx, ncy + dcy
            if 0 <= nncx < cell_cols and 0 <= nncy < cell_rows and (nncx, nncy) not in visited:
                mid_tx, mid_ty = cell_to_tile(ncx, ncy)
                p_dcx, p_dcy = dcy, dcx

                t_perp1 = grid[mid_ty + p_dcy][mid_tx + p_dcx]
                t_perp2 = grid[mid_ty - p_dcy][mid_tx - p_dcx]
                t_para1 = grid[mid_ty + dcy][mid_tx + dcx]
                t_para2 = grid[mid_ty - dcy][mid_tx - dcx]

                if t_perp1 in (PATH, OVERPASS_NS, OVERPASS_EW) and t_perp2 in (PATH, OVERPASS_NS, OVERPASS_EW) and t_para1 == WALL and t_para2 == WALL:
                    # 根据当前走向动态生成南北桥 (OVERPASS_NS) 或东西桥 (OVERPASS_EW)
                    b_type = OVERPASS_NS if dcy != 0 else OVERPASS_EW
                    grid[mid_ty][mid_tx] = b_type
                    grid[mid_ty + dcy][mid_tx + dcx] = PATH
                    grid[mid_ty - dcy][mid_tx - dcx] = PATH
                    overpass_cells.add((mid_tx, mid_ty))

                    visited.add((nncx, nncy))
                    nnx, nny = cell_to_tile(nncx, nncy)
                    grid[nny][nnx] = PATH
                    woven_created += 1

                    for ndcx, ndcy in NEIGHBOR_STEPS:
                        nnncx, nnncy = nncx + ndcx, nncy + ndcy
                        if 0 <= nnncx < cell_cols and 0 <= nnncy < cell_rows and (nnncx, nnncy) not in visited:
                            frontier.append((nncx, nncy, ndcx, ndcy))

    # 第二轮补全立交桥：在现有直穿走廊上放置更多南北向与东西向 OVERPASS
    all_rooms = [(cx, cy) for cy in range(1, cell_cols - 1) for cx in range(1, cell_rows - 1)]
    rng.shuffle(all_rooms)
    for cx, cy in all_rooms:
        if woven_created >= woven_target:
            break
        tx, ty = cell_to_tile(cx, cy)
        if grid[ty][tx] == PATH:
            if grid[ty - 1][tx] in (PATH, 2, 3) and grid[ty + 1][tx] in (PATH, 2, 3) and grid[ty][tx - 1] == WALL and grid[ty][tx + 1] == WALL:
                if tx - 2 >= 0 and tx + 2 < len(grid[0]) and grid[ty][tx - 2] != WALL and grid[ty][tx + 2] != WALL:
                    grid[ty][tx] = OVERPASS_NS
                    grid[ty][tx - 1] = PATH
                    grid[ty][tx + 1] = PATH
                    overpass_cells.add((tx, ty))
                    woven_created += 1
            elif grid[ty][tx - 1] in (PATH, 2, 3) and grid[ty][tx + 1] in (PATH, 2, 3) and grid[ty - 1][tx] == WALL and grid[ty + 1][tx] == WALL:
                if ty - 2 >= 0 and ty + 2 < len(grid) and grid[ty - 2][tx] != WALL and grid[ty + 2][tx] != WALL:
                    grid[ty][tx] = OVERPASS_EW
                    grid[ty - 1][tx] = PATH
                    grid[ty + 1][tx] = PATH
                    overpass_cells.add((tx, ty))
                    woven_created += 1

    entrance = cell_to_tile(0, 0)
    exit_tile = _farthest_cell(grid, entrance, cell_cols, cell_rows)

    metrics = _measure(grid, entrance, exit_tile, difficulty_key)
    return Maze(
        grid=grid,
        entrance=entrance,
        exit=exit_tile,
        difficulty_key=difficulty_key,
        metrics=metrics,
        overpass_cells=overpass_cells,
        pattern_cells=pattern_cells,
    )


def _iter_cell_centers(cell_cols: int, cell_rows: int):
    """遍历所有房间中心瓦片（奇数坐标）。"""
    for cy in range(cell_rows):
        for cx in range(cell_cols):
            yield cx * 2 + 1, cy * 2 + 1


def _path_neighbors(grid: list[list[int]], x: int, y: int, dir_x: int = 0, dir_y: int = 0) -> list[tuple[int, int, int, int]]:
    """当前路格的可走路邻居 (nx, ny, ndx, ndy)。支持南北/东西立交桥单向直行。"""
    height = len(grid)
    width = len(grid[0])
    tile = grid[y][x]
    if tile in (OVERPASS_NS, OVERPASS_EW):
        # 立交桥：只能沿进入方向 (dir_x, dir_y) 直行！
        nx, ny = x + dir_x, y + dir_y
        if 0 <= nx < width and 0 <= ny < height and grid[ny][nx] != WALL:
            return [(nx, ny, dir_x, dir_y)]
        return []
    else:
        # 普通 PATH 瓦片：可往 4 个方向探索
        result = []
        for dx, dy in NEIGHBOR_STEPS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and grid[ny][nx] != WALL:
                result.append((nx, ny, dx, dy))
        return result


def _farthest_cell(
    grid: list[list[int]],
    start: tuple[int, int],
    cell_cols: int,
    cell_rows: int,
) -> tuple[int, int]:
    """BFS 距离最远的房间中心，用作出口。"""
    dist = _bfs_distances(grid, start)
    farthest = start
    farthest_d = -1
    for tile in _iter_cell_centers(cell_cols, cell_rows):
        d = dist.get(tile, -1)
        if d > farthest_d:
            farthest = tile
            farthest_d = d
    return farthest


def _bfs_distances(grid: list[list[int]], start: tuple[int, int]) -> dict[tuple[int, int], int]:
    """从 start 出发，到每格路瓦片的最短步数 (支持 OVERPASS)。"""
    queue = deque([(start[0], start[1], 0, 0)])
    visited_states = {(start[0], start[1], 0, 0): 0}
    tile_dist: dict[tuple[int, int], int] = {start: 0}

    while queue:
        cx, cy, cdx, cdy = queue.popleft()
        d = visited_states[(cx, cy, cdx, cdy)]

        for nx, ny, ndx, ndy in _path_neighbors(grid, cx, cy, cdx, cdy):
            nxt_st = (nx, ny, ndx, ndy)
            if nxt_st not in visited_states:
                visited_states[nxt_st] = d + 1
                if (nx, ny) not in tile_dist or d + 1 < tile_dist[(nx, ny)]:
                    tile_dist[(nx, ny)] = d + 1
                queue.append(nxt_st)
    return tile_dist


def _dead_end_depth(grid: list[list[int]], start: tuple[int, int]) -> int:
    """从死胡同房间沿走廊走到第一个岔路口（度>=3）的房间步数。"""
    prev: tuple[int, int] | None = None
    current = start
    tile_steps = 0
    dir_x, dir_y = 0, 0
    for _ in range(len(grid) * len(grid[0])):
        neighbors = _path_neighbors(grid, current[0], current[1], dir_x, dir_y)
        nxt = [(n[0], n[1], n[2], n[3]) for n in neighbors if (n[0], n[1]) != prev]
        if len(neighbors) >= 3:
            break
        if not nxt:
            break
        prev = current
        current = (nxt[0][0], nxt[0][1])
        dir_x, dir_y = nxt[0][2], nxt[0][3]
        tile_steps += 1
    return tile_steps // 2


def _measure(
    grid: list[list[int]],
    entrance: tuple[int, int],
    exit_tile: tuple[int, int],
    difficulty_key: str,
) -> MazeMetrics:
    """统计解长、死胡同数量/深度、岔路数，并合成一个粗分数。"""
    dist = _bfs_distances(grid, entrance)
    path_length = dist.get(exit_tile, 10)
    cell_cols = (len(grid[0]) - 1) // 2
    cell_rows = (len(grid) - 1) // 2
    dead_ends = 0
    decision_cells = 0
    depths: list[int] = []
    for x, y in _iter_cell_centers(cell_cols, cell_rows):
        degree = len(_path_neighbors(grid, x, y))
        if degree == 1:
            dead_ends += 1
            if (x, y) != entrance and (x, y) != exit_tile:
                depths.append(_dead_end_depth(grid, (x, y)))
        elif degree >= 3:
            decision_cells += 1
    avg_depth = sum(depths) / len(depths) if depths else 0.0
    score = (
        path_length * 1.0
        + dead_ends * 2.0
        + decision_cells * 3.0
        + avg_depth * 8.0
    )
    if "_" in difficulty_key:
        w, l = difficulty_key.split("_")
        lbl = f"大关{w}-{l}阶"
    else:
        lbl = f"{difficulty_key}阶"

    return MazeMetrics(
        path_length=path_length,
        dead_ends=dead_ends,
        decision_cells=decision_cells,
        avg_dead_end_depth=avg_depth,
        score=score,
        label=lbl,
    )


def assert_perfect_maze(maze: Maze) -> None:
    """开发期自检：所有非墙房间中心都能从入口走到，出口也可达。"""
    cell_cols = (maze.cols - 1) // 2
    cell_rows = (maze.rows - 1) // 2
    dist = _bfs_distances(maze.grid, maze.entrance)
    for tile in _iter_cell_centers(cell_cols, cell_rows):
        if maze.grid[tile[1]][tile[0]] != WALL and tile not in dist:
            raise AssertionError(f"Unreachable cell {tile}")
    if maze.exit not in dist:
        raise AssertionError("Exit is unreachable")


def solve_path(
    grid: list[list[int]], start: tuple[int, int], end: tuple[int, int]
) -> list[tuple[int, int]]:
    """求解从 start 到 end 的路径瓦片坐标列表 [(x0,y0), (x1,y1), ...]"""
    _, path, _ = solve_path_with_visited(grid, start, end)
    return path


def solve_path_with_visited(
    grid: list[list[int]], start: tuple[int, int], end: tuple[int, int]
) -> tuple[list[tuple[int, int]], list[tuple[int, int]], dict[tuple[int, int], tuple[int, int] | None]]:
    """DFS 深度优先单线探索：每次只沿着一条通路深入试错，支持 OVERPASS 立交桥。
    返回: (visited_order, final_path, parent_map)
    """
    stack = [(start[0], start[1], 0, 0)]
    parent: dict[tuple[int, int, int, int], tuple[int, int, int, int] | None] = {(start[0], start[1], 0, 0): None}
    visited_order_tiles: list[tuple[int, int]] = []
    visited_states = {(start[0], start[1], 0, 0)}
    found_state: tuple[int, int, int, int] | None = None

    while stack:
        curr = stack.pop()
        cx, cy, cdx, cdy = curr
        if not visited_order_tiles or visited_order_tiles[-1] != (cx, cy):
            visited_order_tiles.append((cx, cy))

        if (cx, cy) == end:
            found_state = curr
            break

        neighbors = _path_neighbors(grid, cx, cy, cdx, cdy)
        for nx, ny, ndx, ndy in neighbors:
            nxt_state = (nx, ny, ndx, ndy)
            if nxt_state not in visited_states:
                visited_states.add(nxt_state)
                parent[nxt_state] = curr
                stack.append(nxt_state)

    path: list[tuple[int, int]] = []
    parent_map: dict[tuple[int, int], tuple[int, int] | None] = {}

    if found_state is not None:
        st: tuple[int, int, int, int] | None = found_state
        while st is not None:
            path.append((st[0], st[1]))
            p = parent.get(st)
            if p is not None:
                parent_map[(st[0], st[1])] = (p[0], p[1])
            st = p
        path.reverse()

    return visited_order_tiles, path, parent_map
