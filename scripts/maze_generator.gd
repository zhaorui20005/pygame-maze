# GDScript: 完美迷宫生成算法 (移植自 Python 版 maze.py)
class_name MazeGenerator
extends RefCounted

const WALL = 1
const PATH = 0
const OVERPASS_NS = 2
const OVERPASS_EW = 3
const OVERPASS = OVERPASS_NS

const W1_DIFFICULTIES = {
	"1": {"cell_cols": 8, "cell_rows": 8, "straight_bias": 0.55, "max_straight_run": 3, "min_dead_end_depth": 2.2},
	"2": {"cell_cols": 10, "cell_rows": 10, "straight_bias": 0.60, "max_straight_run": 3, "min_dead_end_depth": 2.8},
	"3": {"cell_cols": 12, "cell_rows": 12, "straight_bias": 0.64, "max_straight_run": 4, "min_dead_end_depth": 3.2},
	"4": {"cell_cols": 15, "cell_rows": 15, "straight_bias": 0.68, "max_straight_run": 4, "min_dead_end_depth": 3.6},
	"5": {"cell_cols": 18, "cell_rows": 18, "straight_bias": 0.72, "max_straight_run": 5, "min_dead_end_depth": 4.0},
	"6": {"cell_cols": 21, "cell_rows": 21, "straight_bias": 0.75, "max_straight_run": 5, "min_dead_end_depth": 4.5},
	"7": {"cell_cols": 25, "cell_rows": 25, "straight_bias": 0.78, "max_straight_run": 6, "min_dead_end_depth": 5.0},
	"8": {"cell_cols": 30, "cell_rows": 30, "straight_bias": 0.81, "max_straight_run": 6, "min_dead_end_depth": 5.5},
	"9": {"cell_cols": 35, "cell_rows": 35, "straight_bias": 0.84, "max_straight_run": 7, "min_dead_end_depth": 6.0},
	"10": {"cell_cols": 40, "cell_rows": 40, "straight_bias": 0.86, "max_straight_run": 8, "min_dead_end_depth": 6.5}
}

const W2_DIFFICULTIES = {
	"1": {"cell_cols": 10, "cell_rows": 10, "loop_ratio": 0.03},
	"2": {"cell_cols": 12, "cell_rows": 12, "loop_ratio": 0.03},
	"3": {"cell_cols": 15, "cell_rows": 15, "loop_ratio": 0.04},
	"4": {"cell_cols": 18, "cell_rows": 18, "loop_ratio": 0.04},
	"5": {"cell_cols": 21, "cell_rows": 21, "loop_ratio": 0.04},
	"6": {"cell_cols": 25, "cell_rows": 25, "loop_ratio": 0.05},
	"7": {"cell_cols": 28, "cell_rows": 28, "loop_ratio": 0.05},
	"8": {"cell_cols": 32, "cell_rows": 32, "loop_ratio": 0.05},
	"9": {"cell_cols": 36, "cell_rows": 36, "loop_ratio": 0.06},
	"10": {"cell_cols": 40, "cell_rows": 40, "loop_ratio": 0.06}
}

const W3_DIFFICULTIES = {
	"1": {"cell_cols": 12, "cell_rows": 12, "pattern": "star", "loop_ratio": 0.05},
	"2": {"cell_cols": 15, "cell_rows": 15, "pattern": "heart", "loop_ratio": 0.05},
	"3": {"cell_cols": 18, "cell_rows": 18, "pattern": "crown", "loop_ratio": 0.06},
	"4": {"cell_cols": 21, "cell_rows": 21, "pattern": "key", "loop_ratio": 0.06},
	"5": {"cell_cols": 25, "cell_rows": 25, "pattern": "shield", "loop_ratio": 0.07},
	"6": {"cell_cols": 28, "cell_rows": 28, "pattern": "sword", "loop_ratio": 0.07},
	"7": {"cell_cols": 32, "cell_rows": 32, "pattern": "diamond", "loop_ratio": 0.08},
	"8": {"cell_cols": 35, "cell_rows": 35, "pattern": "clover", "loop_ratio": 0.08},
	"9": {"cell_cols": 38, "cell_rows": 38, "pattern": "skull", "loop_ratio": 0.09},
	"10": {"cell_cols": 42, "cell_rows": 42, "pattern": "trophy", "loop_ratio": 0.10}
}

const W4_DIFFICULTIES = {
	"1": {"cell_cols": 12, "cell_rows": 12, "shape": "circle", "loop_ratio": 0.04, "name": "圆形迷宫"},
	"2": {"cell_cols": 14, "cell_rows": 14, "shape": "triangle", "loop_ratio": 0.04, "name": "正三角迷宫"},
	"3": {"cell_cols": 16, "cell_rows": 16, "shape": "diamond", "loop_ratio": 0.05, "name": "菱形水晶迷宫"},
	"4": {"cell_cols": 18, "cell_rows": 18, "shape": "donut", "loop_ratio": 0.05, "name": "双同心环迷宫"},
	"5": {"cell_cols": 20, "cell_rows": 20, "shape": "cross", "loop_ratio": 0.06, "name": "圣十字形迷宫"},
	"6": {"cell_cols": 22, "cell_rows": 22, "shape": "star", "loop_ratio": 0.06, "name": "奇幻星形迷宫"},
	"7": {"cell_cols": 25, "cell_rows": 25, "shape": "hexagon", "loop_ratio": 0.07, "name": "六边盾牌迷宫"},
	"8": {"cell_cols": 28, "cell_rows": 28, "shape": "hourglass", "loop_ratio": 0.07, "name": "沙漏双角迷宫"},
	"9": {"cell_cols": 32, "cell_rows": 32, "shape": "heart", "loop_ratio": 0.08, "name": "璀璨心形迷宫"},
	"10": {"cell_cols": 36, "cell_rows": 36, "shape": "mega_polygon", "loop_ratio": 0.08, "name": "异形几何巨阵"}
}

const W5_DIFFICULTIES = {
	"1": {"cell_cols": 12, "cell_rows": 12, "woven_target": 8, "loop_ratio": 0.04, "name": "双层初探立交"},
	"2": {"cell_cols": 15, "cell_rows": 15, "woven_target": 12, "loop_ratio": 0.05, "name": "十字立交迷宫"},
	"3": {"cell_cols": 18, "cell_rows": 18, "woven_target": 16, "loop_ratio": 0.05, "name": "高架编织网"},
	"4": {"cell_cols": 21, "cell_rows": 21, "woven_target": 22, "loop_ratio": 0.06, "name": "三维立体穿梭"},
	"5": {"cell_cols": 25, "cell_rows": 25, "woven_target": 30, "loop_ratio": 0.06, "pattern": "star", "name": "繁华星型立交"},
	"6": {"cell_cols": 28, "cell_rows": 28, "woven_target": 40, "loop_ratio": 0.07, "pattern": "ai", "name": "AI 隐写字样立交"},
	"7": {"cell_cols": 32, "cell_rows": 32, "woven_target": 50, "loop_ratio": 0.07, "pattern": "art", "name": "ART 艺术隐写天桥"},
	"8": {"cell_cols": 35, "cell_rows": 35, "woven_target": 65, "loop_ratio": 0.08, "pattern": "maze", "name": "MAZE 编织字样巨阵"},
	"9": {"cell_cols": 38, "cell_rows": 38, "woven_target": 80, "loop_ratio": 0.08, "pattern": "crown", "name": "皇冠无尽编织天桥"},
	"10": {"cell_cols": 42, "cell_rows": 42, "woven_target": 100, "loop_ratio": 0.09, "pattern": "sword", "name": "宝剑立体极限巨阵"}
}

const PATTERNS = {
	"star": [
		"  *  ",
		" *** ",
		"*****",
		" *** ",
		"*   *"
	],
	"heart": [
		" ** ** ",
		"*******",
		"*******",
		" ***** ",
		"  ***  ",
		"   *   "
	],
	"crown": [
		"*  *  *",
		"*******",
		" *   * ",
		"*******"
	],
	"key": [
		" *** ",
		"*   *",
		" *** ",
		"  *  ",
		" *** ",
		"  *  ",
		"  ** "
	],
	"shield": [
		"*****",
		"*****",
		"*****",
		" *** ",
		"  *  "
	],
	"sword": [
		"  *  ",
		"  *  ",
		"  *  ",
		" *** ",
		"  *  ",
		" * * "
	],
	"diamond": [
		"  *  ",
		" *** ",
		"*****",
		" *** ",
		"  *  "
	],
	"clover": [
		" * * ",
		"*****",
		"  *  ",
		"*****",
		" * * "
	],
	"skull": [
		" *** ",
		"* * *",
		"*****",
		" * * "
	],
	"trophy": [
		"*****",
		"* * *",
		" *** ",
		"  *  ",
		" *** "
	],
	"ai": [
		" ***   *** ",
		"*   *   *  ",
		"*****   *  ",
		"*   *   *  ",
		"*   *  *** "
	],
	"art": [
		" ***   ****  *****",
		"*   *  *   *   *  ",
		"*****  ****    *  ",
		"*   *  *  *    *  ",
		"*   *  *   *   *  "
	],
	"maze": [
		"*   *  ***  ***** *****",
		"** ** *   *    *  *    ",
		"* * * *****   *   ***  ",
		"*   * *   *  *    *    ",
		"*   * *   * ***** *****"
	]
}

const DIFFICULTIES = W1_DIFFICULTIES

const NEIGHBOR_STEPS = [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]
const _MAX_GENERATE_ATTEMPTS = 48

class MazeMetrics:
	var path_length: int
	var dead_ends: int
	var decision_cells: int
	var avg_dead_end_depth: float
	var score: float
	var label: String

class MazeData:
	var grid: Array = [] # 2D Array [y][x]
	var entrance: Vector2i
	var exit_tile: Vector2i
	var difficulty_key: String
	var metrics: MazeMetrics
	var pattern_cells: Array[Vector2i] = []
	var shape_cells: Array[Vector2i] = []
	var overpass_cells: Array[Vector2i] = []
	var cols: int:
		get:
			return grid[0].size() if grid.size() > 0 else 0
	var rows: int:
		get:
			return grid.size()

	func is_wall(tile_x: int, tile_y: int, is_y_axis: bool = false, player_pos: Vector2 = Vector2.ZERO, cell_size: float = 26.0, current_layer: String = "none") -> bool:
		if tile_x < 0 or tile_y < 0 or tile_x >= cols or tile_y >= rows:
			return true
		var val = grid[tile_y][tile_x]
		if val == WALL:
			return true
		if val == OVERPASS_NS:
			if current_layer == "ns_bridge":
				if not is_y_axis:
					return true # 南北桥面上：禁止东西向移动（被桥两侧护栏挡住）
				return false
			elif current_layer == "ew_tunnel":
				if is_y_axis:
					return true # 东西隧道内：禁止南北向移动（被隧道侧水泥墙挡住）
				return false
			return false
		elif val == OVERPASS_EW:
			if current_layer == "ew_bridge":
				if is_y_axis:
					return true # 东西桥面上：禁止南北向移动（被桥两侧护栏挡住）
				return false
			elif current_layer == "ns_tunnel":
				if not is_y_axis:
					return true # 南北隧道内：禁止东西向移动（被隧道侧水泥墙挡住）
				return false
			return false
		return false

	func solve_path() -> Array[Vector2i]:
		return MazeGenerator.solve_path(grid, entrance, exit_tile)

	func solve_path_with_visited() -> Dictionary:
		return MazeGenerator.solve_path_with_visited(grid, entrance, exit_tile)

static func generate_maze(world_val: int = 1, level_val: int = 1, seed_val: int = -1) -> MazeData:
	var w_val = clampi(world_val, 1, 5)
	var l_val = clampi(level_val, 1, 10)
	var key_str = "%d_%d" % [w_val, l_val]

	var spec = W1_DIFFICULTIES[str(l_val)]
	if w_val == 5:
		spec = W5_DIFFICULTIES[str(l_val)]
	elif w_val == 4:
		spec = W4_DIFFICULTIES[str(l_val)]
	elif w_val == 3:
		spec = W3_DIFFICULTIES[str(l_val)]
	elif w_val == 2:
		spec = W2_DIFFICULTIES[str(l_val)]

	var rng = RandomNumberGenerator.new()
	if seed_val != -1:
		rng.seed = seed_val
	else:
		rng.randomize()

	var best: MazeData = null
	var attempts = 1 if seed_val != -1 else (8 if l_val >= 7 else 12)

	for i in range(attempts):
		var maze: MazeData = null
		if w_val == 5:
			maze = _carve_woven_maze(spec, key_str, rng)
		elif w_val == 4:
			maze = _carve_shape_maze(spec, key_str, rng)
		elif w_val == 3:
			maze = _carve_pattern_maze(spec, key_str, rng)
		elif w_val == 2:
			maze = _carve_dungeon_maze(spec, key_str, rng)
		else:
			maze = _carve_maze(spec, key_str, rng)
		if best == null or _maze_quality(maze) > _maze_quality(best):
			best = maze
		var min_path_len = float(spec["cell_cols"] * spec["cell_rows"]) * (0.35 if w_val == 1 else 0.20)
		if maze.metrics.path_length >= min_path_len:
			if w_val in [2, 3, 4, 5] or maze.metrics.avg_dead_end_depth >= float(spec.get("min_dead_end_depth", 0.0)):
				break

	if best != null and w_val in [2, 3, 4]:
		var loop_ratio = float(spec.get("loop_ratio", 0.04 if w_val == 2 else 0.06))
		_add_guarded_braid_loops(best.grid, best.entrance, best.exit_tile, loop_ratio, rng)
		best.metrics = _measure(best.grid, best.entrance, best.exit_tile, key_str)

	return best

static func _maze_quality(maze: MazeData) -> Array:
	var m = maze.metrics
	return [m.path_length, m.decision_cells, m.avg_dead_end_depth]

static func _carve_maze(spec: Dictionary, difficulty_key: String, rng: RandomNumberGenerator) -> MazeData:
	var cell_cols: int = spec["cell_cols"]
	var cell_rows: int = spec["cell_rows"]
	var straight_bias: float = spec["straight_bias"]
	var max_straight_run: int = spec["max_straight_run"]

	var width = cell_cols * 2 + 1
	var height = cell_rows * 2 + 1

	var grid: Array = []
	for y in range(height):
		var row: Array = []
		for x in range(width):
			row.append(WALL)
		grid.append(row)

	var start_cell = Vector2i(0, 0)
	var sx = start_cell.x * 2 + 1
	var sy = start_cell.y * 2 + 1
	grid[sy][sx] = PATH

	var visited = {}
	visited[start_cell] = true
	var stack = [start_cell]

	var enter_dir = {}
	enter_dir[start_cell] = Vector2i(1, 0)
	var run_length = {}
	run_length[start_cell] = 0

	while stack.size() > 0:
		var curr = stack.back()

		var options = []
		for step in NEIGHBOR_STEPS:
			var ncell = curr + step
			if ncell.x >= 0 and ncell.x < cell_cols and ncell.y >= 0 and ncell.y < cell_rows:
				if not visited.has(ncell):
					options.append({"cell": ncell, "dir": step})

		if options.size() == 0:
			stack.pop_back()
			continue

		var incoming = enter_dir.get(curr, Vector2i.ZERO)
		var cur_run = run_length.get(curr, 0)

		var straight = []
		var turns = []
		for opt in options:
			if opt["dir"] == incoming:
				straight.append(opt)
			else:
				turns.append(opt)

		var chosen_list = options
		if incoming != Vector2i.ZERO and cur_run >= max_straight_run and turns.size() > 0:
			chosen_list = turns
		elif incoming != Vector2i.ZERO and rng.randf() < straight_bias and straight.size() > 0:
			chosen_list = straight

		var chosen = chosen_list[rng.randi() % chosen_list.size()]
		var ncell = chosen["cell"]
		var step = chosen["dir"]

		var wall_x = curr.x * 2 + 1 + step.x
		var wall_y = curr.y * 2 + 1 + step.y
		var nx = ncell.x * 2 + 1
		var ny = ncell.y * 2 + 1

		grid[wall_y][wall_x] = PATH
		grid[ny][nx] = PATH

		visited[ncell] = true
		enter_dir[ncell] = step
		run_length[ncell] = (cur_run + 1) if step == incoming else 1
		stack.append(ncell)

	var entrance = Vector2i(sx, sy)
	var exit_tile = _farthest_cell(grid, entrance, cell_cols, cell_rows)
	var metrics = _measure(grid, entrance, exit_tile, difficulty_key)

	var maze = MazeData.new()
	maze.grid = grid
	maze.entrance = entrance
	maze.exit_tile = exit_tile
	maze.difficulty_key = difficulty_key
	maze.metrics = metrics
	return maze

static func _add_guarded_braid_loops(grid: Array, entrance: Vector2i, exit_tile: Vector2i, loop_ratio: float, rng: RandomNumberGenerator) -> void:
	var height = grid.size()
	var width = grid[0].size()
	var candidate_walls = []
	for y in range(1, height - 1):
		for x in range(1, width - 1):
			if grid[y][x] == WALL:
				if grid[y][x - 1] == PATH and grid[y][x + 1] == PATH and grid[y - 1][x] == WALL and grid[y + 1][x] == WALL:
					candidate_walls.append(Vector2i(x, y))
				elif grid[y - 1][x] == PATH and grid[y + 1][x] == PATH and grid[y][x - 1] == WALL and grid[y][x + 1] == WALL:
					candidate_walls.append(Vector2i(x, y))

	if candidate_walls.size() == 0:
		return

	var orig_path = solve_path(grid, entrance, exit_tile)
	var orig_len = orig_path.size()
	var min_allowed_len = max(8, int(float(orig_len) * 0.80))

	var loop_count = max(1, int(float(candidate_walls.size()) * loop_ratio))
	var shuffled = candidate_walls.duplicate()
	for i in range(shuffled.size() - 1, 0, -1):
		var j = rng.randi() % (i + 1)
		var tmp = shuffled[i]
		shuffled[i] = shuffled[j]
		shuffled[j] = tmp

	var added = 0
	var max_checks = min(shuffled.size(), max(12, loop_count * 2))
	for idx in range(max_checks):
		if added >= loop_count:
			break
		var w_pos = shuffled[idx]
		grid[w_pos.y][w_pos.x] = PATH
		var new_path = solve_path(grid, entrance, exit_tile)
		if new_path.size() < min_allowed_len:
			grid[w_pos.y][w_pos.x] = WALL
		else:
			added += 1

static func _carve_dungeon_maze(spec: Dictionary, difficulty_key: String, rng: RandomNumberGenerator) -> MazeData:
	var cell_cols: int = spec["cell_cols"]
	var cell_rows: int = spec["cell_rows"]

	var width = cell_cols * 2 + 1
	var height = cell_rows * 2 + 1

	var grid: Array = []
	for y in range(height):
		var row: Array = []
		for x in range(width):
			row.append(WALL)
		grid.append(row)

	var start_cell = Vector2i(0, 0)
	var sx = start_cell.x * 2 + 1
	var sy = start_cell.y * 2 + 1
	grid[sy][sx] = PATH

	var visited = {}
	visited[start_cell] = true
	var frontier = []

	for step in NEIGHBOR_STEPS:
		var ncell = start_cell + step
		if ncell.x >= 0 and ncell.x < cell_cols and ncell.y >= 0 and ncell.y < cell_rows:
			frontier.append({"from": start_cell, "dir": step, "to": ncell})

	while frontier.size() > 0:
		var idx = rng.randi() % frontier.size()
		var item = frontier[idx]
		frontier.remove_at(idx)

		var ncell = item["to"]
		if visited.has(ncell):
			continue

		visited[ncell] = true
		var from_cell = item["from"]
		var step = item["dir"]

		var wall_x = from_cell.x * 2 + 1 + step.x
		var wall_y = from_cell.y * 2 + 1 + step.y
		var nx = ncell.x * 2 + 1
		var ny = ncell.y * 2 + 1

		grid[wall_y][wall_x] = PATH
		grid[ny][nx] = PATH

		for nstep in NEIGHBOR_STEPS:
			var nncell = ncell + nstep
			if nncell.x >= 0 and nncell.x < cell_cols and nncell.y >= 0 and nncell.y < cell_rows:
				if not visited.has(nncell):
					frontier.append({"from": ncell, "dir": nstep, "to": nncell})

	var entrance = Vector2i(sx, sy)
	var exit_tile = _farthest_cell(grid, entrance, cell_cols, cell_rows)

	var metrics = _measure(grid, entrance, exit_tile, difficulty_key)

	var maze = MazeData.new()
	maze.grid = grid
	maze.entrance = entrance
	maze.exit_tile = exit_tile
	maze.difficulty_key = difficulty_key
	maze.metrics = metrics
	return maze

static func _carve_pattern_maze(spec: Dictionary, difficulty_key: String, rng: RandomNumberGenerator) -> MazeData:
	var cell_cols: int = spec["cell_cols"]
	var cell_rows: int = spec["cell_rows"]
	var pattern_name: String = spec["pattern"]
	var pattern_lines: Array = PATTERNS.get(pattern_name, PATTERNS["star"])

	var width = cell_cols * 2 + 1
	var height = cell_rows * 2 + 1

	var grid: Array = []
	for y in range(height):
		var row: Array = []
		for x in range(width):
			row.append(WALL)
		grid.append(row)

	# 1. 计算图案居中偏移
	var pat_h = pattern_lines.size()
	var pat_w = 0
	for line in pattern_lines:
		if line.length() > pat_w:
			pat_w = line.length()
	var offset_cx = max(1, (cell_cols - pat_w) / 2)
	var offset_cy = max(1, (cell_rows - pat_h) / 2)

	var pattern_cells: Array[Vector2i] = []
	var pattern_rooms: Dictionary = {}

	for py in range(pat_h):
		var line: String = pattern_lines[py]
		for px in range(line.length()):
			if line[px] == '*':
				var rcx = offset_cx + px
				var rcy = offset_cy + py
				if rcx >= 0 and rcx < cell_cols and rcy >= 0 and rcy < cell_rows:
					var rpos = Vector2i(rcx, rcy)
					pattern_rooms[rpos] = true
					var tx = rcx * 2 + 1
					var ty = rcy * 2 + 1
					grid[ty][tx] = PATH
					pattern_cells.append(Vector2i(tx, ty))

	# 打通图案内部相邻房间间的墙
	for rpos in pattern_rooms.keys():
		for step in NEIGHBOR_STEPS:
			var nroom = rpos + step
			if pattern_rooms.has(nroom):
				var wx = rpos.x * 2 + 1 + step.x
				var wy = rpos.y * 2 + 1 + step.y
				grid[wy][wx] = PATH
				pattern_cells.append(Vector2i(wx, wy))

	# 2. 从起点 (0,0) 开始执行 Prim 算法生成连通生成树
	var start_cell = Vector2i(0, 0)
	var sx = start_cell.x * 2 + 1
	var sy = start_cell.y * 2 + 1
	grid[sy][sx] = PATH

	var visited: Dictionary = {}
	visited[start_cell] = true
	if pattern_rooms.has(start_cell):
		for prpos in pattern_rooms.keys():
			visited[prpos] = true

	var frontier: Array = []
	for step in NEIGHBOR_STEPS:
		var ncell = start_cell + step
		if ncell.x >= 0 and ncell.x < cell_cols and ncell.y >= 0 and ncell.y < cell_rows:
			if not visited.has(ncell):
				frontier.append({"from": start_cell, "dir": step, "to": ncell})

	while frontier.size() > 0:
		var idx = rng.randi() % frontier.size()
		var item = frontier[idx]
		frontier.remove_at(idx)

		var ncell = item["to"]
		if visited.has(ncell):
			continue

		var from_cell = item["from"]
		var step = item["dir"]

		if pattern_rooms.has(ncell):
			var newly_visited = []
			for prpos in pattern_rooms.keys():
				if not visited.has(prpos):
					newly_visited.append(prpos)
					visited[prpos] = true

			var wall_x = from_cell.x * 2 + 1 + step.x
			var wall_y = from_cell.y * 2 + 1 + step.y
			grid[wall_y][wall_x] = PATH

			for prpos in newly_visited:
				for nstep in NEIGHBOR_STEPS:
					var nncell = prpos + nstep
					if nncell.x >= 0 and nncell.x < cell_cols and nncell.y >= 0 and nncell.y < cell_rows:
						if not visited.has(nncell):
							frontier.append({"from": prpos, "dir": nstep, "to": nncell})
		else:
			visited[ncell] = true
			var wall_x = from_cell.x * 2 + 1 + step.x
			var wall_y = from_cell.y * 2 + 1 + step.y
			var nx = ncell.x * 2 + 1
			var ny = ncell.y * 2 + 1

			grid[wall_y][wall_x] = PATH
			grid[ny][nx] = PATH

			for nstep in NEIGHBOR_STEPS:
				var nncell = ncell + nstep
				if nncell.x >= 0 and nncell.x < cell_cols and nncell.y >= 0 and nncell.y < cell_rows:
					if not visited.has(nncell):
						frontier.append({"from": ncell, "dir": nstep, "to": nncell})

	var entrance = Vector2i(sx, sy)
	var exit_tile = _farthest_cell(grid, entrance, cell_cols, cell_rows)

	var metrics = _measure(grid, entrance, exit_tile, difficulty_key)

	var maze = MazeData.new()
	maze.grid = grid
	maze.entrance = entrance
	maze.exit_tile = exit_tile
	maze.difficulty_key = difficulty_key
	maze.metrics = metrics
	maze.pattern_cells = pattern_cells
	return maze

static func _is_inside_shape(cx: int, cy: int, cols: int, rows: int, shape_name: String) -> bool:
	var nx = (float(cx) + 0.5 - float(cols) / 2.0) / (float(cols) / 2.0)
	var ny = (float(cy) + 0.5 - float(rows) / 2.0) / (float(rows) / 2.0)

	if shape_name == "circle":
		return (nx * nx + ny * ny) <= 0.92
	elif shape_name == "triangle":
		return ny >= -0.85 and ny <= 0.85 and absf(nx) <= (0.85 - ny) / 1.7 * 0.90
	elif shape_name == "diamond":
		return absf(nx) + absf(ny) <= 0.95
	elif shape_name == "donut":
		var r2 = nx * nx + ny * ny
		return 0.28 * 0.28 <= r2 and r2 <= 0.92 * 0.92
	elif shape_name == "cross":
		return (absf(nx) <= 0.38 and absf(ny) <= 0.92) or (absf(ny) <= 0.38 and absf(nx) <= 0.92)
	elif shape_name == "star":
		var r = sqrt(nx * nx + ny * ny)
		var theta = atan2(ny, nx)
		var r_star = 0.52 + 0.38 * cos(5.0 * theta - PI / 2.0)
		return r <= maxf(0.20, r_star)
	elif shape_name == "hexagon":
		return absf(ny) <= 0.90 and (absf(nx) * 0.866 + absf(ny) * 0.5) <= 0.866
	elif shape_name == "hourglass":
		return absf(ny) <= 0.92 and absf(nx) <= (absf(ny) * 0.85 + 0.10)
	elif shape_name == "heart":
		var x = nx * 1.15
		var y = -ny * 1.15 + 0.25
		return (x * x + y * y - 1.0) * (x * x + y * y - 1.0) * (x * x + y * y - 1.0) - x * x * y * y * y <= 0.0
	elif shape_name == "mega_polygon":
		return absf(nx) <= 0.92 and absf(ny) <= 0.92 and (absf(nx) + absf(ny) <= 1.35) and not (0.22 <= absf(nx) and absf(nx) <= 0.38 and 0.22 <= absf(ny) and absf(ny) <= 0.38)
	return true

static func _carve_shape_maze(spec: Dictionary, difficulty_key: String, rng: RandomNumberGenerator) -> MazeData:
	var cell_cols: int = spec["cell_cols"]
	var cell_rows: int = spec["cell_rows"]
	var shape_name: String = spec["shape"]

	var shape_rooms: Dictionary = {}
	for cy in range(cell_rows):
		for cx in range(cell_cols):
			if _is_inside_shape(cx, cy, cell_cols, cell_rows, shape_name):
				shape_rooms[Vector2i(cx, cy)] = true

	if shape_rooms.size() == 0:
		for cy in range(cell_rows):
			for cx in range(cell_cols):
				shape_rooms[Vector2i(cx, cy)] = true

	var width = cell_cols * 2 + 1
	var height = cell_rows * 2 + 1

	var grid: Array = []
	for y in range(height):
		var row: Array = []
		for x in range(width):
			row.append(WALL)
		grid.append(row)

	var shape_cells: Array[Vector2i] = []

	# 起点选在最靠近顶中部位的有效房间
	var start_cell = Vector2i(0, 0)
	var best_dist = 999999
	for room in shape_rooms.keys():
		var d = abs(room.x - cell_cols / 2) + room.y * 2
		if d < best_dist:
			best_dist = d
			start_cell = room

	var sx = start_cell.x * 2 + 1
	var sy = start_cell.y * 2 + 1
	grid[sy][sx] = PATH
	shape_cells.append(Vector2i(sx, sy))

	var visited: Dictionary = {start_cell: true}
	var frontier: Array = []
	for step in NEIGHBOR_STEPS:
		var ncell = start_cell + step
		if shape_rooms.has(ncell):
			frontier.append({"from": start_cell, "dir": step, "to": ncell})

	while frontier.size() > 0:
		var idx = rng.randi() % frontier.size()
		var item = frontier[idx]
		frontier.remove_at(idx)

		var from_cell: Vector2i = item["from"]
		var step: Vector2i = item["dir"]
		var ncell: Vector2i = item["to"]

		if visited.has(ncell):
			continue

		visited[ncell] = true
		var wall_x = from_cell.x * 2 + 1 + step.x
		var wall_y = from_cell.y * 2 + 1 + step.y
		var nx = ncell.x * 2 + 1
		var ny = ncell.y * 2 + 1

		grid[wall_y][wall_x] = PATH
		grid[ny][nx] = PATH
		shape_cells.append(Vector2i(wall_x, wall_y))
		shape_cells.append(Vector2i(nx, ny))

		for nstep in NEIGHBOR_STEPS:
			var nncell = ncell + nstep
			if shape_rooms.has(nncell) and not visited.has(nncell):
				frontier.append({"from": ncell, "dir": nstep, "to": nncell})

	var entrance = Vector2i(sx, sy)
	var exit_tile = _farthest_cell(grid, entrance, cell_cols, cell_rows)

	var 	metrics = _measure(grid, entrance, exit_tile, difficulty_key)

	var maze = MazeData.new()
	maze.grid = grid
	maze.entrance = entrance
	maze.exit_tile = exit_tile
	maze.difficulty_key = difficulty_key
	maze.metrics = metrics
	maze.shape_cells = shape_cells
	return maze

static func _carve_woven_maze(spec: Dictionary, difficulty_key: String, rng: RandomNumberGenerator) -> MazeData:
	var cell_cols: int = spec["cell_cols"]
	var cell_rows: int = spec["cell_rows"]
	var woven_target: int = spec.get("woven_target", 15)
	var pattern_name: String = spec.get("pattern", "")

	var width = cell_cols * 2 + 1
	var height = cell_rows * 2 + 1

	var grid: Array = []
	for y in range(height):
		var row: Array = []
		for x in range(width):
			row.append(WALL)
		grid.append(row)

	var overpass_cells: Array[Vector2i] = []
	var pattern_cells: Array[Vector2i] = []
	var pattern_rooms: Dictionary = {}

	if pattern_name != "" and PATTERNS.has(pattern_name):
		var pattern_lines: Array = PATTERNS[pattern_name]
		var pat_h = pattern_lines.size()
		var pat_w = 0
		for line in pattern_lines:
			pat_w = max(pat_w, line.length())
		var offset_cx = max(1, (cell_cols - pat_w) / 2)
		var offset_cy = max(1, (cell_rows - pat_h) / 2)

		for py in range(pat_h):
			var line: String = pattern_lines[py]
			for px in range(line.length()):
				if line[px] == '*':
					var rcx = offset_cx + px
					var rcy = offset_cy + py
					if rcx >= 0 and rcx < cell_cols and rcy >= 0 and rcy < cell_rows:
						pattern_rooms[Vector2i(rcx, rcy)] = true
						var tx = rcx * 2 + 1
						var ty = rcy * 2 + 1
						grid[ty][tx] = PATH
						pattern_cells.append(Vector2i(tx, ty))

		for rroom in pattern_rooms.keys():
			for step in NEIGHBOR_STEPS:
				var nroom = rroom + step
				if pattern_rooms.has(nroom):
					var wx = rroom.x * 2 + 1 + step.x
					var wy = rroom.y * 2 + 1 + step.y
					grid[wy][wx] = PATH
					pattern_cells.append(Vector2i(wx, wy))

	var visited: Dictionary = {Vector2i(0, 0): true}
	for pr in pattern_rooms.keys():
		visited[pr] = true

	var sx = 1
	var sy = 1
	grid[sy][sx] = PATH

	var frontier: Array = []
	for init_cell in visited.keys():
		for step in NEIGHBOR_STEPS:
			var ncell = init_cell + step
			if ncell.x >= 0 and ncell.x < cell_cols and ncell.y >= 0 and ncell.y < cell_rows and not visited.has(ncell):
				frontier.append({"from": init_cell, "dir": step, "to": ncell})

	var woven_created = 0

	while frontier.size() > 0:
		var idx = rng.randi() % frontier.size()
		var item = frontier[idx]
		frontier.remove_at(idx)

		var from_cell: Vector2i = item["from"]
		var step: Vector2i = item["dir"]
		var ncell: Vector2i = item["to"]

		if not visited.has(ncell):
			visited[ncell] = true
			var wall_x = from_cell.x * 2 + 1 + step.x
			var wall_y = from_cell.y * 2 + 1 + step.y
			var nx = ncell.x * 2 + 1
			var ny = ncell.y * 2 + 1

			grid[wall_y][wall_x] = PATH
			grid[ny][nx] = PATH

			for nstep in NEIGHBOR_STEPS:
				var nncell = ncell + nstep
				if nncell.x >= 0 and nncell.x < cell_cols and nncell.y >= 0 and nncell.y < cell_rows and not visited.has(nncell):
					frontier.append({"from": ncell, "dir": nstep, "to": nncell})

		elif woven_created < woven_target:
			var nncell = ncell + step
			if nncell.x >= 0 and nncell.x < cell_cols and nncell.y >= 0 and nncell.y < cell_rows and not visited.has(nncell):
				var mid_tx = ncell.x * 2 + 1
				var mid_ty = ncell.y * 2 + 1
				var p_dcx = step.y
				var p_dcy = step.x

				var t_perp1 = grid[mid_ty + p_dcy][mid_tx + p_dcx]
				var t_perp2 = grid[mid_ty - p_dcy][mid_tx - p_dcx]
				var t_para1 = grid[mid_ty + step.y][mid_tx + step.x]
				var t_para2 = grid[mid_ty - step.y][mid_tx - step.x]

				if (t_perp1 == PATH or t_perp1 == OVERPASS_NS or t_perp1 == OVERPASS_EW) and (t_perp2 == PATH or t_perp2 == OVERPASS_NS or t_perp2 == OVERPASS_EW) and t_para1 == WALL and t_para2 == WALL:
					var b_type = OVERPASS_NS if step.y != 0 else OVERPASS_EW
					grid[mid_ty][mid_tx] = b_type
					grid[mid_ty + step.y][mid_tx + step.x] = PATH
					grid[mid_ty - step.y][mid_tx - step.x] = PATH
					overpass_cells.append(Vector2i(mid_tx, mid_ty))

					visited[nncell] = true
					var nnx = nncell.x * 2 + 1
					var nny = nncell.y * 2 + 1
					grid[nny][nnx] = PATH
					woven_created += 1

					for nstep in NEIGHBOR_STEPS:
						var nnncell = nncell + nstep
						if nnncell.x >= 0 and nnncell.x < cell_cols and nnncell.y >= 0 and nnncell.y < cell_rows and not visited.has(nnncell):
							frontier.append({"from": nncell, "dir": nstep, "to": nnncell})

	# 第二轮补全立交桥
	var all_rooms: Array[Vector2i] = []
	for cy in range(1, cell_rows - 1):
		for cx in range(1, cell_cols - 1):
			all_rooms.append(Vector2i(cx, cy))

	for i in range(all_rooms.size() - 1, 0, -1):
		var j = rng.randi() % (i + 1)
		var tmp = all_rooms[i]
		all_rooms[i] = all_rooms[j]
		all_rooms[j] = tmp

	for room in all_rooms:
		if woven_created >= woven_target:
			break
		var tx = room.x * 2 + 1
		var ty = room.y * 2 + 1
		if grid[ty][tx] == PATH:
			if (grid[ty - 1][tx] == PATH or grid[ty - 1][tx] == 2 or grid[ty - 1][tx] == 3) and (grid[ty + 1][tx] == PATH or grid[ty + 1][tx] == 2 or grid[ty + 1][tx] == 3) and grid[ty][tx - 1] == WALL and grid[ty][tx + 1] == WALL:
				var b_type = OVERPASS_NS if rng.randf() < 0.5 else OVERPASS_EW
				grid[ty][tx] = b_type
				grid[ty][tx - 1] = PATH
				grid[ty][tx + 1] = PATH
				overpass_cells.append(Vector2i(tx, ty))
				woven_created += 1
			elif (grid[ty][tx - 1] == PATH or grid[ty][tx - 1] == 2 or grid[ty][tx - 1] == 3) and (grid[ty][tx + 1] == PATH or grid[ty][tx + 1] == 2 or grid[ty][tx + 1] == 3) and grid[ty - 1][tx] == WALL and grid[ty + 1][tx] == WALL:
				var b_type = OVERPASS_NS if rng.randf() < 0.5 else OVERPASS_EW
				grid[ty][tx] = b_type
				grid[ty - 1][tx] = PATH
				grid[ty + 1][tx] = PATH
				overpass_cells.append(Vector2i(tx, ty))
				woven_created += 1

	var entrance = Vector2i(sx, sy)
	var exit_tile = _farthest_cell(grid, entrance, cell_cols, cell_rows)

	var metrics = _measure(grid, entrance, exit_tile, difficulty_key)

	var maze = MazeData.new()
	maze.grid = grid
	maze.entrance = entrance
	maze.exit_tile = exit_tile
	maze.difficulty_key = difficulty_key
	maze.metrics = metrics
	maze.overpass_cells = overpass_cells
	maze.pattern_cells = pattern_cells
	return maze

static func _path_neighbors(grid: Array, pos: Vector2i, dir: Vector2i = Vector2i.ZERO) -> Array:
	var height = grid.size()
	var width = grid[0].size()
	var tile = grid[pos.y][pos.x]
	var res = []
	if tile == OVERPASS_NS or tile == OVERPASS_EW:
		var nxt = pos + dir
		if nxt.x >= 0 and nxt.x < width and nxt.y >= 0 and nxt.y < height and grid[nxt.y][nxt.x] != WALL:
			res.append({"pos": nxt, "dir": dir})
		return res
	else:
		for step in NEIGHBOR_STEPS:
			var nxt = pos + step
			if nxt.x >= 0 and nxt.x < width and nxt.y >= 0 and nxt.y < height and grid[nxt.y][nxt.x] != WALL:
				res.append({"pos": nxt, "dir": step})
		return res

static func _farthest_cell(grid: Array, start: Vector2i, cell_cols: int, cell_rows: int) -> Vector2i:
	var dist = _bfs_distances(grid, start)
	var farthest = start
	var farthest_d = -1
	for cy in range(cell_rows):
		for cx in range(cell_cols):
			var tile = Vector2i(cx * 2 + 1, cy * 2 + 1)
			var d = dist.get(tile, -1)
			if d > farthest_d:
				farthest = tile
				farthest_d = d
	return farthest

static func _bfs_distances(grid: Array, start: Vector2i) -> Dictionary:
	var queue = [{"pos": start, "dir": Vector2i.ZERO}]
	var visited_states = {Vector2(start.x * 1000 + start.y, 0): 0}
	var tile_dist = {start: 0}

	while queue.size() > 0:
		var item = queue.pop_front()
		var curr: Vector2i = item["pos"]
		var cdir: Vector2i = item["dir"]
		var d = tile_dist.get(curr, 0)

		for nxt_item in _path_neighbors(grid, curr, cdir):
			var nxt: Vector2i = nxt_item["pos"]
			var ndir: Vector2i = nxt_item["dir"]
			if not tile_dist.has(nxt) or d + 1 < tile_dist[nxt]:
				tile_dist[nxt] = d + 1
				queue.append({"pos": nxt, "dir": ndir})
	return tile_dist

static func _measure(grid: Array, entrance: Vector2i, exit_tile: Vector2i, difficulty_key: String) -> MazeMetrics:
	var dist = _bfs_distances(grid, entrance)
	var path_length = dist.get(exit_tile, 0)
	var cell_cols = (grid[0].size() - 1) / 2
	var cell_rows = (grid.size() - 1) / 2

	var dead_ends = 0
	var decision_cells = 0
	var total_depth = 0.0
	var depth_count = 0

	for cy in range(cell_rows):
		for cx in range(cell_cols):
			var tile = Vector2i(cx * 2 + 1, cy * 2 + 1)
			var degree = _get_path_degree(grid, tile)
			if degree == 1:
				dead_ends += 1
				if tile != entrance and tile != exit_tile:
					total_depth += _dead_end_depth(grid, tile)
					depth_count += 1
			elif degree >= 3:
				decision_cells += 1

	var avg_depth = (total_depth / float(depth_count)) if depth_count > 0 else 0.0
	var score = path_length * 1.0 + dead_ends * 2.0 + decision_cells * 3.0 + avg_depth * 8.0

	var m = MazeMetrics.new()
	m.path_length = path_length
	m.dead_ends = dead_ends
	m.decision_cells = decision_cells
	m.avg_dead_end_depth = avg_depth
	m.score = score
	if "_" in difficulty_key:
		var parts = difficulty_key.split("_")
		m.label = "大关%s-%s阶" % [parts[0], parts[1]]
	else:
		m.label = difficulty_key + "阶"
	return m

static func _get_path_degree(grid: Array, tile: Vector2i) -> int:
	var count = 0
	var height = grid.size()
	var width = grid[0].size()
	for step in NEIGHBOR_STEPS:
		var nxt = tile + step
		if nxt.x >= 0 and nxt.x < width and nxt.y >= 0 and nxt.y < height:
			if grid[nxt.y][nxt.x] == PATH:
				count += 1
	return count

static func _dead_end_depth(grid: Array, start: Vector2i) -> int:
	var prev = Vector2i(-1, -1)
	var curr = start
	var steps = 0
	var height = grid.size()
	var width = grid[0].size()

	for i in range(width * height):
		var degree = _get_path_degree(grid, curr)
		if degree >= 3:
			break

		var neighbors = []
		for step in NEIGHBOR_STEPS:
			var nxt = curr + step
			if nxt.x >= 0 and nxt.x < width and nxt.y >= 0 and nxt.y < height:
				if grid[nxt.y][nxt.x] == PATH and nxt != prev:
					neighbors.append(nxt)

		if neighbors.size() == 0:
			break

		prev = curr
		curr = neighbors[0]
		steps += 1

	return steps / 2

static func solve_path(grid: Array, start: Vector2i, end: Vector2i) -> Array[Vector2i]:
	var res = solve_path_with_visited(grid, start, end)
	var path: Array[Vector2i] = res["path"]
	return path

static func solve_path_with_visited(grid: Array, start: Vector2i, end: Vector2i) -> Dictionary:
	var stack = [{"pos": start, "dir": Vector2i.ZERO}]
	var parent: Dictionary = {}
	var visited_set: Dictionary = {Vector2i(start.x, start.y): true}
	var visited_order: Array[Vector2i] = []

	var found_item = null
	while stack.size() > 0:
		var curr_item = stack.pop_back()
		var curr_pos: Vector2i = curr_item["pos"]
		var curr_dir: Vector2i = curr_item["dir"]

		if visited_order.size() == 0 or visited_order[visited_order.size() - 1] != curr_pos:
			visited_order.append(curr_pos)

		if curr_pos == end:
			found_item = curr_item
			break

		for nxt_item in _path_neighbors(grid, curr_pos, curr_dir):
			var nxt_pos: Vector2i = nxt_item["pos"]
			var nxt_dir: Vector2i = nxt_item["dir"]
			var key = "%d,%d,%d,%d" % [nxt_pos.x, nxt_pos.y, nxt_dir.x, nxt_dir.y]
			if not visited_set.has(key):
				visited_set[key] = true
				parent[key] = curr_item
				stack.append(nxt_item)

	var path: Array[Vector2i] = []
	if found_item != null:
		var item = found_item
		while item != null:
			path.append(item["pos"])
			var key = "%d,%d,%d,%d" % [item["pos"].x, item["pos"].y, item["dir"].x, item["dir"].y]
			if parent.has(key):
				item = parent[key]
			else:
				break
		path.reverse()

	return {"visited_order": visited_order, "path": path, "parent": parent}
