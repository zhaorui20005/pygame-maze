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

import random
from collections import deque
from dataclasses import dataclass

# 1 = 墙，0 = 可走。外围一圈永远是墙。
WALL = 1
PATH = 0

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

    @property
    def cols(self) -> int:
        return len(self.grid[0])

    @property
    def rows(self) -> int:
        return len(self.grid)

    def is_wall(self, tile_x: int, tile_y: int) -> bool:
        """越界一律当墙，玩家不会走出地图。"""
        if tile_x < 0 or tile_y < 0 or tile_x >= self.cols or tile_y >= self.rows:
            return True
        return self.grid[tile_y][tile_x] == WALL

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
    """按大关 (world 1/2) 和关卡阶数 (level 1-10) 生成一局迷宫；可选 seed 便于复现。
    World 1 (第一大关：绿野森林)：1-10 阶采用拉长路口 DFS 算法，直观清晰；
    World 2 (第二大关：狼穴地牢)：1-10 阶采用高密转弯 Prim + 伪环路高难算法，烧脑陡升。
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
            if val > 10:
                w_val = 2
                l_val = val - 10
            else:
                w_val = 1
                l_val = val

    w_val = max(1, min(2, w_val))
    l_val = max(1, min(10, l_val))

    if w_val == 2:
        spec = W2_DIFFICULTIES[str(l_val)]
    else:
        spec = W1_DIFFICULTIES[str(l_val)]

    rng = random.Random(seed)
    best: Maze | None = None
    attempts = 1 if seed is not None else _MAX_GENERATE_ATTEMPTS
    display_key = f"{w_val}_{l_val}"

    for _ in range(attempts):
        if w_val == 2:
            maze = _carve_dungeon_maze(spec, display_key, rng)
        else:
            maze = _carve_maze(spec, display_key, rng)
        if best is None or _maze_quality(maze) > _maze_quality(best):
            best = maze
        if w_val == 2 or maze.metrics.avg_dead_end_depth >= spec.get("min_dead_end_depth", 0):
            return maze

    assert best is not None
    return best


def _maze_quality(maze: Maze) -> tuple[float, int, int]:
    """重抽时的比较键：先看岔路深度，再看决策点数和解的长度。"""
    m = maze.metrics
    return (m.avg_dead_end_depth, m.decision_cells, m.path_length)


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


def _carve_dungeon_maze(spec: dict, difficulty_key: str, rng: random.Random) -> Maze:
    """第二大关：暗黑狼穴地牢高难迷宫算法。
    特点：
    1. 普里姆 (Prim) 算法高密转弯，产生九曲十八弯极密通路；
    2. 引入 4% 伪环路打通 (Braid Loops)，打乱单一路线逻辑，极具迷茫感与挑战性。
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

    # 引入伪环路 (Braid Loops)
    candidate_walls = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if grid[y][x] == WALL:
                if grid[y][x - 1] == PATH and grid[y][x + 1] == PATH and grid[y - 1][x] == WALL and grid[y + 1][x] == WALL:
                    candidate_walls.append((x, y))
                elif grid[y - 1][x] == PATH and grid[y + 1][x] == PATH and grid[y][x - 1] == WALL and grid[y][x + 1] == WALL:
                    candidate_walls.append((x, y))

    if candidate_walls:
        loop_ratio = spec.get("loop_ratio", 0.04)
        loop_count = max(1, int(len(candidate_walls) * loop_ratio))
        for x, y in rng.sample(candidate_walls, min(loop_count, len(candidate_walls))):
            grid[y][x] = PATH

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


def _iter_cell_centers(cell_cols: int, cell_rows: int):
    """遍历所有房间中心瓦片（奇数坐标）。"""
    for cy in range(cell_rows):
        for cx in range(cell_cols):
            yield cx * 2 + 1, cy * 2 + 1


def _path_neighbors(grid: list[list[int]], x: int, y: int) -> list[tuple[int, int]]:
    """当前路格的四连通可走路邻居（用于度数、BFS）。"""
    height = len(grid)
    width = len(grid[0])
    result = []
    for dx, dy in NEIGHBOR_STEPS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < width and 0 <= ny < height and grid[ny][nx] == PATH:
            result.append((nx, ny))
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
    """从 start 出发，到每格路瓦片的最短步数。"""
    queue = deque([start])
    dist = {start: 0}
    while queue:
        x, y = queue.popleft()
        for nx, ny in _path_neighbors(grid, x, y):
            if (nx, ny) not in dist:
                dist[(nx, ny)] = dist[(x, y)] + 1
                queue.append((nx, ny))
    return dist


def _dead_end_depth(grid: list[list[int]], start: tuple[int, int]) -> int:
    """从死胡同房间沿走廊走到第一个岔路口（度>=3）的房间步数。

    走廊上的隔墙瓦片度数为 2，房间中心若只有一条出路则度为 1。
    每跨过一个房间（瓦片距离 2）算一步，这样深度和「岔路走了几间房」一致。
    """
    prev: tuple[int, int] | None = None
    current = start
    tile_steps = 0
    # 完美迷宫无环，最多走遍全部路格。
    for _ in range(len(grid) * len(grid[0])):
        neighbors = _path_neighbors(grid, *current)
        nxt = [n for n in neighbors if n != prev]
        if len(neighbors) >= 3:
            break
        if not nxt:
            break
        prev = current
        current = nxt[0]
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
    path_length = dist[exit_tile]
    cell_cols = (len(grid[0]) - 1) // 2
    cell_rows = (len(grid) - 1) // 2
    dead_ends = 0
    decision_cells = 0
    depths: list[int] = []
    for x, y in _iter_cell_centers(cell_cols, cell_rows):
        degree = len(_path_neighbors(grid, x, y))
        if degree == 1:
            dead_ends += 1
            # 入口/出口本身常常是度为 1，不算「骗人的浅岔路」。
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
    """开发期自检：所有房间中心都能从入口走到，出口也可达。"""
    cell_cols = (maze.cols - 1) // 2
    cell_rows = (maze.rows - 1) // 2
    dist = _bfs_distances(maze.grid, maze.entrance)
    for tile in _iter_cell_centers(cell_cols, cell_rows):
        if tile not in dist:
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
    """DFS 深度优先单线探索：每次只沿着一条通路深入试错，遇到死胡同回溯。
    返回: (visited_order, final_path, parent_map)
    """
    stack = [start]
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    visited_order: list[tuple[int, int]] = []
    visited_set = {start}
    found = False

    while stack:
        curr = stack.pop()
        visited_order.append(curr)

        if curr == end:
            found = True
            break

        # 遍历邻居放入栈中（逆序压栈保证正向弹出）
        neighbors = _path_neighbors(grid, curr[0], curr[1])
        for nxt in neighbors:
            if nxt not in visited_set:
                visited_set.add(nxt)
                parent[nxt] = curr
                stack.append(nxt)

    path = []
    if found:
        node: tuple[int, int] | None = end
        while node is not None:
            path.append(node)
            node = parent.get(node)
        path.reverse()

    return visited_order, path, parent
