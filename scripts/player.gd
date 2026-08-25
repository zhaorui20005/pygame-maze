# GDScript: 玩家控制器逻辑
class_name MazePlayer
extends Node2D

var pixel_position: Vector2
var speed: float = 192.0 # 像素/秒
var size: float = 14.0

var facing: String = "down"
var anim_frame: int = 0
var is_moving: bool = false
var _step_timer: float = 0.0

signal step_taken
signal reached_exit_signal

func init_player(start_pos: Vector2, p_size: float = 14.0) -> void:
	pixel_position = start_pos
	position = start_pos
	size = p_size
	facing = "down"
	anim_frame = 0
	is_moving = false
	_step_timer = 0.0

func process_movement(delta: float, maze_data: MazeGenerator.MazeData, cell_size: float) -> void:
	var move_vec = Vector2.ZERO
	if Input.is_action_pressed("ui_left") or Input.is_key_pressed(KEY_A):
		move_vec.x -= 1.0
	if Input.is_action_pressed("ui_right") or Input.is_key_pressed(KEY_D):
		move_vec.x += 1.0
	if Input.is_action_pressed("ui_up") or Input.is_key_pressed(KEY_W):
		move_vec.y -= 1.0
	if Input.is_action_pressed("ui_down") or Input.is_key_pressed(KEY_S):
		move_vec.y += 1.0

	var moved = false
	var old_pos = pixel_position

	if move_vec.x < 0:
		facing = "left"
	elif move_vec.x > 0:
		facing = "right"
	elif move_vec.y < 0:
		facing = "up"
	elif move_vec.y > 0:
		facing = "down"

	if move_vec.x != 0:
		_move_axis(move_vec.x * speed * delta, 0, maze_data, cell_size)
	if move_vec.y != 0:
		_move_axis(0, move_vec.y * speed * delta, maze_data, cell_size)

	if pixel_position != old_pos:
		moved = true

	position = pixel_position
	is_moving = moved

	if is_moving:
		_step_timer += delta
		if _step_timer >= 0.18:
			_step_timer = 0.0
			anim_frame = 1 - anim_frame
			emit_signal("step_taken")
	else:
		anim_frame = 0
		_step_timer = 0.0

func _move_axis(dx: float, dy: float, maze_data: MazeGenerator.MazeData, cell_size: float) -> void:
	var trial_pos = pixel_position + Vector2(dx, dy)
	var trial_rect = Rect2(trial_pos, Vector2(size, size))
	if not _hits_wall(trial_rect, maze_data, cell_size):
		pixel_position = trial_pos

func _hits_wall(rect: Rect2, maze_data: MazeGenerator.MazeData, cell_size: float) -> bool:
	var left = int(rect.position.x / cell_size)
	var right = int((rect.position.x + rect.size.x - 0.1) / cell_size)
	var top = int(rect.position.y / cell_size)
	var bottom = int((rect.position.y + rect.size.y - 0.1) / cell_size)

	for tile_y in range(top, bottom + 1):
		for tile_x in range(left, right + 1):
			if maze_data.is_wall(tile_x, tile_y):
				return true
	return false

func check_reached_exit(maze_data: MazeGenerator.MazeData, cell_size: float) -> bool:
	var exit_pos = Vector2(maze_data.exit_tile.x * cell_size, maze_data.exit_tile.y * cell_size)
	var exit_rect = Rect2(exit_pos + Vector2(cell_size * 0.125, cell_size * 0.125), Vector2(cell_size * 0.75, cell_size * 0.75))
	var player_rect = Rect2(pixel_position, Vector2(size, size))
	return player_rect.intersects(exit_rect)
