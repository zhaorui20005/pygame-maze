# GDScript: 完美迷宫生成算法 (移植自 Python 版 maze.py)
class_name MazeGenerator
extends RefCounted

const WALL = 1
const PATH = 0

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
	var cols: int:
		get:
			return grid[0].size() if grid.size() > 0 else 0
	var rows: int:
		get:
			return grid.size()

	func is_wall(tile_x: int, tile_y: int) -> bool:
		if tile_x < 0 or tile_y < 0 or tile_x >= cols or tile_y >= rows:
			return true
		return grid[tile_y][tile_x] == WALL

	func solve_path() -> Array[Vector2i]:
		return MazeGenerator.solve_path(grid, entrance, exit_tile)

	func solve_path_with_visited() -> Dictionary:
		return MazeGenerator.solve_path_with_visited(grid, entrance, exit_tile)

static func generate_maze(world_val: int = 1, level_val: int = 1, seed_val: int = -1) -> MazeData:
	var w_val = clampi(world_val, 1, 2)
	var l_val = clampi(level_val, 1, 10)
	var key_str = "%d_%d" % [w_val, l_val]

	var spec = W2_DIFFICULTIES[str(l_val)] if w_val == 2 else W1_DIFFICULTIES[str(l_val)]
	var rng = RandomNumberGenerator.new()
	if seed_val != -1:
		rng.seed = seed_val
	else:
		rng.randomize()

	var best: MazeData = null
	var attempts = 1 if seed_val != -1 else _MAX_GENERATE_ATTEMPTS

	for i in range(attempts):
		var maze: MazeData = null
		if w_val == 2:
			maze = _carve_dungeon_maze(spec, key_str, rng)
		else:
			maze = _carve_maze(spec, key_str, rng)
		if best == null or _maze_quality(maze) > _maze_quality(best):
			best = maze
		var min_d = float(spec.get("min_dead_end_depth", 0.0))
		if w_val == 2 or maze.metrics.avg_dead_end_depth >= min_d:
			return maze

	return best

static func _maze_quality(maze: MazeData) -> Array:
	var m = maze.metrics
	return [m.avg_dead_end_depth, m.decision_cells, m.path_length]

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

	# 引入 4% 伪环路 (Braid Loops)
	var candidate_walls = []
	for y in range(1, height - 1):
		for x in range(1, width - 1):
			if grid[y][x] == WALL:
				if grid[y][x - 1] == PATH and grid[y][x + 1] == PATH and grid[y - 1][x] == WALL and grid[y + 1][x] == WALL:
					candidate_walls.append(Vector2i(x, y))
				elif grid[y - 1][x] == PATH and grid[y + 1][x] == PATH and grid[y][x - 1] == WALL and grid[y][x + 1] == WALL:
					candidate_walls.append(Vector2i(x, y))

	if candidate_walls.size() > 0:
		var loop_ratio = float(spec.get("loop_ratio", 0.04))
		var loop_count = max(1, int(candidate_walls.size() * loop_ratio))
		for k in range(loop_count):
			var c_idx = rng.randi() % candidate_walls.size()
			var w_pos = candidate_walls[c_idx]
			grid[w_pos.y][w_pos.x] = PATH
			candidate_walls.remove_at(c_idx)

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
	var queue = [start]
	var dist = {start: 0}
	var height = grid.size()
	var width = grid[0].size()

	while queue.size() > 0:
		var curr = queue.pop_front()
		var d_curr = dist[curr]
		for step in NEIGHBOR_STEPS:
			var nxt = curr + step
			if nxt.x >= 0 and nxt.x < width and nxt.y >= 0 and nxt.y < height:
				if grid[nxt.y][nxt.x] == PATH and not dist.has(nxt):
					dist[nxt] = d_curr + 1
					queue.append(nxt)
	return dist

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
	var stack: Array = [start]
	var parent: Dictionary = {start: Vector2i(-1, -1)}
	var visited_set: Dictionary = {start: true}
	var visited_order: Array[Vector2i] = []
	var height = grid.size()
	var width = grid[0].size()

	var found = false
	while stack.size() > 0:
		var curr = stack.pop_back()
		visited_order.append(curr)

		if curr == end:
			found = true
			break

		for step in NEIGHBOR_STEPS:
			var nxt = curr + step
			if nxt.x >= 0 and nxt.x < width and nxt.y >= 0 and nxt.y < height:
				if grid[nxt.y][nxt.x] == PATH and not visited_set.has(nxt):
					visited_set[nxt] = true
					parent[nxt] = curr
					stack.append(nxt)

	var path: Array[Vector2i] = []
	if found:
		var curr = end
		while curr != Vector2i(-1, -1):
			path.append(curr)
			if parent.has(curr):
				curr = parent[curr]
			else:
				break
		path.reverse()

	return {"visited_order": visited_order, "path": path, "parent": parent}
