# GDScript: 主控制器节点
extends Node2D

const CELL_SIZE = 26.0
const HUD_HEIGHT = 52.0

var difficulty_level: int = 5
var maze_data: MazeGenerator.MazeData = null
var player: MazePlayer = null
var won: bool = false

# 视口与摄像机控制
var camera_scale: float = 1.0
var fit_scale: float = 1.0
var offset_pos: Vector2 = Vector2(0.0, HUD_HEIGHT)
var following_player: bool = false
var is_dragging: bool = false
var drag_start_mouse: Vector2
var drag_start_offset: Vector2

# 护眼高对比度颜色配置 (森林苔绿道路 + 沉稳深蓝石墙壁 + 超醒目白糯米团子 + 浅金色高亮终点)
const COLOR_BG = Color(0.05, 0.06, 0.09)
const COLOR_WALL = Color(0.09, 0.13, 0.18)
const COLOR_PATH = Color(0.16, 0.32, 0.24)
const COLOR_ENTRANCE = Color(0.88, 0.62, 0.20)
const COLOR_EXIT = Color(0.96, 0.92, 0.78) # 浅亮金光底色 (衬托大红旗子极具对比度)
const COLOR_HUD_BG = Color(0.05, 0.07, 0.10, 0.95)

# 声音播放节点
var audio_step_player: AudioStreamPlayer = null
var audio_start_player: AudioStreamPlayer = null
var audio_win_player: AudioStreamPlayer = null
var player_tex: Texture2D = null
var mochi_textures: Dictionary = {}

# UI Label
@onready var hud_label: Label = $CanvasLayer/HUDMargin/HUDLabel
@onready var win_banner: Control = $CanvasLayer/WinBanner

func _ready() -> void:
	# 优先尝试加载 4 方向多帧精灵序列图 (down, up, left, right)
	for d in ["down", "up", "left", "right"]:
		var frames_arr: Array = []
		for f_name in [d + "_0", d + "_1", d + "_idle"]:
			var path_res = "res://assets/mochi_frames/%s.png" % f_name
			var path_fs = "assets/mochi_frames/%s.png" % f_name
			if ResourceLoader.exists(path_res):
				frames_arr.append(load(path_res))
			elif FileAccess.file_exists(path_fs):
				var img = Image.load_from_file(path_fs)
				if img != null:
					frames_arr.append(ImageTexture.create_from_image(img))
		if frames_arr.size() > 0:
			mochi_textures[d] = frames_arr

	# 备用：加载单图
	if ResourceLoader.exists("res://assets/player_mochi.png"):
		player_tex = load("res://assets/player_mochi.png")
	elif FileAccess.file_exists("assets/player_mochi.png"):
		var img = Image.load_from_file("assets/player_mochi.png")
		if img != null:
			player_tex = ImageTexture.create_from_image(img)

	# 初始化音频节点与程序化合成流
	audio_step_player = AudioStreamPlayer.new()
	audio_step_player.stream = SoundGenerator.create_sound_step()
	add_child(audio_step_player)

	audio_start_player = AudioStreamPlayer.new()
	audio_start_player.stream = SoundGenerator.create_sound_start()
	add_child(audio_start_player)

	audio_win_player = AudioStreamPlayer.new()
	audio_win_player.stream = SoundGenerator.create_sound_win()
	add_child(audio_win_player)

	player = MazePlayer.new()
	add_child(player)
	player.connect("step_taken", Callable(self, "_on_player_step"))

	_start_new_game(difficulty_level)

func _start_new_game(level: int) -> void:
	difficulty_level = level
	won = false
	win_banner.hide()

	if audio_start_player != null:
		audio_start_player.play()

	maze_data = MazeGenerator.generate_maze(str(difficulty_level))

	# 初始化玩家起始位置
	var start_pixel = Vector2(
		maze_data.entrance.x * CELL_SIZE + 6.0,
		maze_data.entrance.y * CELL_SIZE + 6.0
	)
	player.init_player(start_pixel, CELL_SIZE - 12.0)

	fit_to_screen()
	_update_hud()
	queue_redraw()

func fit_to_screen() -> void:
	var win_size = get_viewport_rect().size
	var avail_w = win_size.x
	var avail_h = max(1.0, win_size.y - HUD_HEIGHT)
	var mw = maze_data.cols * CELL_SIZE
	var mh = maze_data.rows * CELL_SIZE

	var scale_w = (avail_w - 16.0) / mw
	var scale_h = (avail_h - 16.0) / mh
	fit_scale = min(1.0, min(scale_w, scale_h))
	camera_scale = fit_scale

	var scaled_w = mw * camera_scale
	var scaled_h = mh * camera_scale

	offset_pos.x = max(8.0, (avail_w - scaled_w) / 2.0)
	offset_pos.y = HUD_HEIGHT + max(8.0, (avail_h - scaled_h) / 2.0) if avail_h > scaled_h else HUD_HEIGHT
	following_player = false

func focus_player() -> void:
	camera_scale = max(1.0, fit_scale)
	following_player = true
	_update_player_focus()

func _update_player_focus() -> void:
	if not following_player:
		return
	var win_size = get_viewport_rect().size
	var avail_h = max(1.0, win_size.y - HUD_HEIGHT)
	var vc_x = win_size.x / 2.0
	var vc_y = HUD_HEIGHT + avail_h / 2.0
	offset_pos.x = vc_x - (player.pixel_position.x + player.size / 2.0) * camera_scale
	offset_pos.y = vc_y - (player.pixel_position.y + player.size / 2.0) * camera_scale

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_ESCAPE:
			get_tree().quit()
		elif event.keycode == KEY_C or event.keycode == KEY_SPACE:
			if not following_player:
				focus_player()
			else:
				fit_to_screen()
			queue_redraw()
		elif event.keycode >= KEY_1 and event.keycode <= KEY_9:
			_start_new_game(event.keycode - KEY_1 + 1)
		elif event.keycode == KEY_0:
			_start_new_game(10)
		elif event.keycode == KEY_KP_1 and event.keycode <= KEY_KP_9:
			_start_new_game(event.keycode - KEY_KP_1 + 1)
		elif event.keycode == KEY_KP_0:
			_start_new_game(10)
		elif event.keycode == KEY_EQUAL or event.keycode == KEY_KP_ADD:
			if difficulty_level < 10:
				_start_new_game(difficulty_level + 1)
		elif event.keycode == KEY_MINUS or event.keycode == KEY_KP_SUBTRACT:
			if difficulty_level > 1:
				_start_new_game(difficulty_level - 1)
		elif event.keycode == KEY_R:
			_start_new_game(difficulty_level)

	elif event is InputEventMouseButton:
		if event.button_index in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT, MOUSE_BUTTON_MIDDLE]:
			if event.pressed:
				if event.position.y > HUD_HEIGHT:
					is_dragging = true
					drag_start_mouse = event.position
					drag_start_offset = offset_pos
					following_player = false
			else:
				is_dragging = false
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			if event.position.y > HUD_HEIGHT:
				_zoom(1.15, event.position)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			if event.position.y > HUD_HEIGHT:
				_zoom(1.0 / 1.15, event.position)

	elif event is InputEventMouseMotion and is_dragging:
		offset_pos = drag_start_offset + (event.position - drag_start_mouse)
		queue_redraw()

func _zoom(factor: float, mouse_pos: Vector2) -> void:
	var old_scale = camera_scale
	var min_s = min(0.2, fit_scale * 0.5)
	var new_scale = clamp(camera_scale * factor, min_s, 3.5)
	if new_scale == old_scale:
		return

	var wx = (mouse_pos.x - offset_pos.x) / old_scale
	var wy = (mouse_pos.y - offset_pos.y) / old_scale

	camera_scale = new_scale
	offset_pos.x = mouse_pos.x - wx * new_scale
	offset_pos.y = mouse_pos.y - wy * new_scale
	following_player = false
	queue_redraw()

func _physics_process(delta: float) -> void:
	if not won and maze_data != null:
		player.process_movement(delta, maze_data, CELL_SIZE)
		if player.check_reached_exit(maze_data, CELL_SIZE):
			won = true
			win_banner.show()
			if audio_win_player != null:
				audio_win_player.play()

		if following_player:
			_update_player_focus()

	queue_redraw()

func _on_player_step() -> void:
	if audio_step_player != null:
		audio_step_player.play()

func _update_hud() -> void:
	if maze_data == null or maze_data.metrics == null:
		return
	var m = maze_data.metrics
	hud_label.text = "难度 %s  |  路径 %d  死胡同 %d  岔路 %d  岔深 %.1f  分数 %.0f    WASD移动  1-9/0选1-10阶  +/-切换  R重随  拖拽平移/滚轮缩放  C/Space视角" % [
		m.label, m.path_length, m.dead_ends, m.decision_cells, m.avg_dead_end_depth, m.score
	]

func _draw() -> void:
	if maze_data == null:
		return

	var win_size = get_viewport_rect().size

	# 背景填充
	draw_rect(Rect2(Vector2.ZERO, win_size), COLOR_BG)

	# 瓦片绘制范围裁剪
	var min_wx = (0.0 - offset_pos.x) / camera_scale
	var max_wx = (win_size.x - offset_pos.x) / camera_scale
	var min_wy = (HUD_HEIGHT - offset_pos.y) / camera_scale
	var max_wy = (win_size.y - offset_pos.y) / camera_scale

	var min_tile_x = max(0, int(min_wx / CELL_SIZE))
	var max_tile_x = min(maze_data.cols - 1, int(max_wx / CELL_SIZE))
	var min_tile_y = max(0, int(min_wy / CELL_SIZE))
	var max_tile_y = min(maze_data.rows - 1, int(max_wy / CELL_SIZE))

	for y in range(min_tile_y, max_tile_y + 1):
		for x in range(min_tile_x, max_tile_x + 1):
			var tile = maze_data.grid[y][x]
			var p1 = offset_pos + Vector2(x * CELL_SIZE, y * CELL_SIZE) * camera_scale
			var p2 = offset_pos + Vector2((x + 1) * CELL_SIZE, (y + 1) * CELL_SIZE) * camera_scale
			var rect = Rect2(p1, p2 - p1)
			var color = COLOR_WALL if tile == MazeGenerator.WALL else COLOR_PATH
			draw_rect(rect, color)

	# 入口与出口绘制
	_draw_tile_marker(maze_data.entrance, COLOR_ENTRANCE, "house")
	_draw_tile_marker(maze_data.exit_tile, COLOR_EXIT, "flag")

	# 绘制萌系 Q 版小人
	_draw_player()

	# HUD 顶栏背景
	draw_rect(Rect2(0, 0, win_size.x, HUD_HEIGHT), COLOR_HUD_BG)

func _draw_tile_marker(tile: Vector2i, color: Color, type: String) -> void:
	var p1 = offset_pos + Vector2(tile.x * CELL_SIZE, tile.y * CELL_SIZE) * camera_scale
	var p2 = offset_pos + Vector2((tile.x + 1) * CELL_SIZE, (tile.y + 1) * CELL_SIZE) * camera_scale
	var rect = Rect2(p1, p2 - p1)
	draw_rect(rect, color)

	# 给终点/起点绘制耀眼高对比金色外框，防止与背景混淆
	if type == "flag":
		draw_rect(rect, Color(1.0, 0.90, 0.20), false, max(1.0, camera_scale * 1.8))
	elif type == "house":
		draw_rect(rect, Color(1.0, 0.80, 0.30), false, max(1.0, camera_scale * 1.8))

	if rect.size.x >= 6.0:
		if type == "house":
			_draw_mini_house(rect)
		elif type == "flag":
			_draw_mini_flag(rect)

func _draw_mini_house(rect: Rect2) -> void:
	var s = rect.size.x
	var pos = rect.position
	# 墙
	var wall = Rect2(pos + Vector2(s * 0.18, s * 0.38), Vector2(s * 0.64, s * 0.54))
	draw_rect(wall, Color(0.9, 0.75, 0.55))
	# 顶
	var pts = PackedVector2Array([
		pos + Vector2(s * 0.50, s * 0.06),
		pos + Vector2(s * 0.08, s * 0.42),
		pos + Vector2(s * 0.92, s * 0.42)
	])
	draw_polygon(pts, PackedColorArray([Color(0.86, 0.24, 0.20)]))
	# 门
	draw_rect(Rect2(pos + Vector2(s * 0.41, s * 0.60), Vector2(s * 0.18, s * 0.32)), Color(0.43, 0.25, 0.14))

func _draw_mini_flag(rect: Rect2) -> void:
	var s = rect.size.x
	var pos = rect.position
	# 耀眼金色旗杆
	var pole_x = pos.x + s * 0.36
	draw_line(Vector2(pole_x, pos.y + s * 0.08), Vector2(pole_x, pos.y + s * 0.88), Color(0.85, 0.65, 0.15), max(1.0, s * 0.08))
	# 旗杆金球
	draw_circle(Vector2(pole_x, pos.y + s * 0.08), max(1.5, s * 0.06), Color(0.98, 0.78, 0.20))

	# 鲜艳大红旗帜 (在浅色底上对比极其鲜明)
	var pts = PackedVector2Array([
		Vector2(pole_x, pos.y + s * 0.12),
		Vector2(pos.x + s * 0.88, pos.y + s * 0.28),
		Vector2(pole_x, pos.y + s * 0.48)
	])
	draw_polygon(pts, PackedColorArray([Color(0.95, 0.18, 0.22)]))
	# 旗帜暗红外边框
	draw_polyline(PackedVector2Array([
		Vector2(pole_x, pos.y + s * 0.12),
		Vector2(pos.x + s * 0.88, pos.y + s * 0.28),
		Vector2(pole_x, pos.y + s * 0.48),
		Vector2(pole_x, pos.y + s * 0.12)
	]), Color(0.65, 0.10, 0.15), max(1.0, s * 0.04))

	# 旗子中间金黄小星
	draw_circle(Vector2(pos.x + s * 0.52, pos.y + s * 0.28), max(1.2, s * 0.06), Color(1.0, 0.90, 0.20))

func _draw_player() -> void:
	var center_p = player.pixel_position + Vector2(player.size / 2.0, player.size / 2.0)
	var draw_w = CELL_SIZE * 1.35
	var draw_h = CELL_SIZE * 1.35
	var p1 = offset_pos + (center_p - Vector2(draw_w / 2.0, draw_h / 2.0)) * camera_scale
	var p2 = offset_pos + (center_p + Vector2(draw_w / 2.0, draw_h / 2.0)) * camera_scale
	var rect = Rect2(p1, p2 - p1)

	if rect.size.x >= 6.0:
		if mochi_textures.has(player.facing):
			# 使用精灵大图切出的 4 方向走动贴图
			var tex_list = mochi_textures[player.facing]
			var cur_tex: Texture2D = null
			if player.is_moving:
				var idx = player.anim_frame % min(2, tex_list.size())
				cur_tex = tex_list[idx]
			else:
				# 待机帧 (优先使用 _idle 帧)
				cur_tex = tex_list[2] if tex_list.size() >= 3 else tex_list[0]

			# 果冻 Q 弹跳跃
			var bounce_y = 0.0
			if player.is_moving:
				bounce_y = abs(sin(Time.get_ticks_msec() * 0.020)) * rect.size.y * 0.08

			var render_rect = Rect2(rect.position - Vector2(0, bounce_y), rect.size)
			draw_texture_rect(cur_tex, render_rect, false)

		elif player_tex != null:
			var s = rect.size.x
			var bounce_y = 0.0
			if player.is_moving:
				bounce_y = abs(sin(Time.get_ticks_msec() * 0.020)) * s * 0.10

			var render_rect = Rect2(rect.position - Vector2(0, bounce_y), rect.size)
			if player.facing == "left":
				var flip_rect = Rect2(render_rect.position + Vector2(render_rect.size.x, 0), Vector2(-render_rect.size.x, render_rect.size.y))
				draw_texture_rect(player_tex, flip_rect, false)
			else:
				draw_texture_rect(player_tex, render_rect, false)
		else:
			_draw_cute_character(rect, player.facing, player.anim_frame)
	else:
		draw_rect(rect, Color(0.27, 0.55, 0.90))

func _draw_cute_character(rect: Rect2, facing: String, frame: int) -> void:
	var s = rect.size.x
	var pos = rect.position
	var center_x = pos.x + s * 0.50

	# Q版 1.5 头身超萌比例
	var head_y = pos.y + s * 0.37
	var head_r = s * 0.30

	var body_top = pos.y + s * 0.60
	var body_h = s * 0.18
	var body_w = s * 0.28
	var leg_top = body_top + body_h
	var leg_h = s * 0.14
	var leg_offset = (s * 0.07) if frame == 1 else (-s * 0.07)

	# 柔和高调卡哇伊配色
	var c_skin = Color(1.0, 0.90, 0.82)          # 嫩粉肤色
	var c_blush = Color(1.0, 0.55, 0.68, 0.80)    # 萌萌红润腮红
	var c_hair = Color(0.35, 0.22, 0.18)         # 柔和栗棕色头发
	var c_hat = Color(0.98, 0.32, 0.45)          # 草莓甜心帽子
	var c_hat_ear = Color(0.85, 0.22, 0.35)      # 帽子猫耳/球球
	var c_shirt = Color(0.25, 0.68, 0.98)        # 晴空蓝小卫衣
	var c_pants = Color(0.20, 0.24, 0.38)        # 藏青小裤子
	var c_shoes = Color(1.0, 0.98, 0.95)         # 亮白萌系鞋子

	# 水汪汪萌萌大眼睛配色
	var c_eye_outer = Color(0.08, 0.08, 0.16)    # 眼眶深色
	var c_eye_iris = Color(0.18, 0.58, 0.98)     # 水蓝色彩瞳
	var c_eye_sparkle = Color(1.0, 1.0, 1.0)     # 高光闪烁点

	if facing == "down":
		# === 正面 (朝下) ===
		# 1. 裤子与小白鞋
		var left_leg = Rect2(Vector2(center_x - s * 0.12, leg_top + leg_offset * 0.4), Vector2(s * 0.09, leg_h))
		var right_leg = Rect2(Vector2(center_x + s * 0.03, leg_top - leg_offset * 0.4), Vector2(s * 0.09, leg_h))
		draw_rect(left_leg, c_pants)
		draw_rect(right_leg, c_pants)
		draw_rect(Rect2(Vector2(left_leg.position.x - s * 0.01, left_leg.position.y + leg_h - s * 0.04), Vector2(s * 0.11, s * 0.05)), c_shoes)
		draw_rect(Rect2(Vector2(right_leg.position.x - s * 0.01, right_leg.position.y + leg_h - s * 0.04), Vector2(s * 0.11, s * 0.05)), c_shoes)

		# 2. 卫衣与摆动手臂
		var body_rect = Rect2(Vector2(center_x - body_w / 2.0, body_top), Vector2(body_w, body_h))
		draw_rect(body_rect, c_shirt)
		draw_rect(Rect2(Vector2(center_x - body_w / 2.0 - s * 0.05, body_top + s * 0.01 - leg_offset * 0.4), Vector2(s * 0.06, s * 0.12)), c_shirt)
		draw_rect(Rect2(Vector2(center_x + body_w / 2.0 - s * 0.01, body_top + s * 0.01 + leg_offset * 0.4), Vector2(s * 0.06, s * 0.12)), c_shirt)
		draw_circle(Vector2(center_x - body_w / 2.0 - s * 0.02, body_top + s * 0.12 - leg_offset * 0.4), s * 0.03, c_skin)
		draw_circle(Vector2(center_x + body_w / 2.0 + s * 0.02, body_top + s * 0.12 + leg_offset * 0.4), s * 0.03, c_skin)

		# 3. 萌萌大圆头
		draw_circle(Vector2(center_x, head_y), head_r, c_skin)

		# 4. 栗色刘海 (头发)
		var hair_l = PackedVector2Array([
			Vector2(center_x - head_r * 0.9, head_y - head_r * 0.1),
			Vector2(center_x - head_r * 0.3, head_y - head_r * 0.2),
			Vector2(center_x - head_r * 0.6, head_y + head_r * 0.15)
		])
		var hair_r = PackedVector2Array([
			Vector2(center_x + head_r * 0.9, head_y - head_r * 0.1),
			Vector2(center_x + head_r * 0.3, head_y - head_r * 0.2),
			Vector2(center_x + head_r * 0.6, head_y + head_r * 0.15)
		])
		draw_polygon(hair_l, PackedColorArray([c_hair]))
		draw_polygon(hair_r, PackedColorArray([c_hair]))

		# 5. 可爱草莓猫耳帽子
		draw_circle(Vector2(center_x, head_y - head_r * 0.35), head_r * 0.88, c_hat)
		draw_circle(Vector2(center_x - head_r * 0.6, head_y - head_r * 0.9), s * 0.07, c_hat_ear)
		draw_circle(Vector2(center_x + head_r * 0.6, head_y - head_r * 0.9), s * 0.07, c_hat_ear)

		# 6. 萌萌粉红腮红
		draw_circle(Vector2(center_x - s * 0.16, head_y + s * 0.09), s * 0.05, c_blush)
		draw_circle(Vector2(center_x + s * 0.16, head_y + s * 0.09), s * 0.05, c_blush)

		# 7. 超级卡哇伊动漫水汪汪大眼睛 (双重高光闪烁)
		var eye_lx = center_x - s * 0.10
		var eye_rx = center_x + s * 0.10
		var eye_y = head_y + s * 0.03
		var eye_w = s * 0.065
		var eye_h = s * 0.085

		# 左眼 (大底框 + 蓝彩瞳 + 主/副双高光)
		draw_rect(Rect2(Vector2(eye_lx - eye_w, eye_y - eye_h / 2.0), Vector2(eye_w * 2.0, eye_h)), c_eye_outer)
		draw_rect(Rect2(Vector2(eye_lx - eye_w * 0.75, eye_y - eye_h * 0.1), Vector2(eye_w * 1.5, eye_h * 0.55)), c_eye_iris)
		draw_circle(Vector2(eye_lx - eye_w * 0.35, eye_y - eye_h * 0.25), s * 0.024, c_eye_sparkle) # 主高光
		draw_circle(Vector2(eye_lx + eye_w * 0.35, eye_y + eye_h * 0.22), s * 0.013, c_eye_sparkle) # 副高光

		# 右眼
		draw_rect(Rect2(Vector2(eye_rx - eye_w, eye_y - eye_h / 2.0), Vector2(eye_w * 2.0, eye_h)), c_eye_outer)
		draw_rect(Rect2(Vector2(eye_rx - eye_w * 0.75, eye_y - eye_h * 0.1), Vector2(eye_w * 1.5, eye_h * 0.55)), c_eye_iris)
		draw_circle(Vector2(eye_rx - eye_w * 0.35, eye_y - eye_h * 0.25), s * 0.024, c_eye_sparkle) # 主高光
		draw_circle(Vector2(eye_rx + eye_w * 0.35, eye_y + eye_h * 0.22), s * 0.013, c_eye_sparkle) # 副高光

		# 8. 萌萌弯弯笑脸
		draw_arc(Vector2(center_x, head_y + s * 0.10), s * 0.035, 0.2, PI - 0.2, 12, Color(0.45, 0.20, 0.25), s * 0.02)

	elif facing == "up":
		# === 背面 (朝上) ===
		var left_leg = Rect2(Vector2(center_x - s * 0.12, leg_top - leg_offset * 0.4), Vector2(s * 0.09, leg_h))
		var right_leg = Rect2(Vector2(center_x + s * 0.03, leg_top + leg_offset * 0.4), Vector2(s * 0.09, leg_h))
		draw_rect(left_leg, c_pants)
		draw_rect(right_leg, c_pants)
		draw_rect(Rect2(Vector2(left_leg.position.x - s * 0.01, left_leg.position.y + leg_h - s * 0.04), Vector2(s * 0.11, s * 0.05)), c_shoes)
		draw_rect(Rect2(Vector2(right_leg.position.x - s * 0.01, right_leg.position.y + leg_h - s * 0.04), Vector2(s * 0.11, s * 0.05)), c_shoes)

		var body_rect = Rect2(Vector2(center_x - body_w / 2.0, body_top), Vector2(body_w, body_h))
		draw_rect(body_rect, c_shirt)

		draw_circle(Vector2(center_x, head_y), head_r, c_skin)
		draw_circle(Vector2(center_x, head_y + s * 0.02), head_r * 0.95, c_hair)
		draw_circle(Vector2(center_x, head_y - head_r * 0.2), head_r * 0.92, c_hat)
		draw_circle(Vector2(center_x - head_r * 0.6, head_y - head_r * 0.8), s * 0.07, c_hat_ear)
		draw_circle(Vector2(center_x + head_r * 0.6, head_y - head_r * 0.8), s * 0.07, c_hat_ear)

	elif facing == "left":
		# === 侧面 (朝左) ===
		var l1 = Rect2(Vector2(center_x - s * 0.05 + leg_offset, leg_top), Vector2(s * 0.10, leg_h))
		var l2 = Rect2(Vector2(center_x - s * 0.05 - leg_offset, leg_top), Vector2(s * 0.10, leg_h))
		draw_rect(l2, c_pants)
		draw_rect(l1, c_pants)
		draw_rect(Rect2(Vector2(l1.position.x - s * 0.03, l1.position.y + leg_h - s * 0.04), Vector2(s * 0.13, s * 0.05)), c_shoes)

		var body_rect = Rect2(Vector2(center_x - s * 0.11, body_top), Vector2(s * 0.22, body_h))
		draw_rect(body_rect, c_shirt)

		draw_circle(Vector2(center_x, head_y), head_r, c_skin)
		draw_circle(Vector2(center_x, head_y - head_r * 0.35), head_r * 0.88, c_hat)
		draw_circle(Vector2(center_x, head_y - head_r * 0.9), s * 0.07, c_hat_ear)

		# 侧面腮红
		draw_circle(Vector2(center_x - s * 0.14, head_y + s * 0.09), s * 0.05, c_blush)

		# 侧面水汪汪大眼睛
		var eye_x = center_x - s * 0.10
		var eye_y = head_y + s * 0.03
		var eye_w = s * 0.065
		var eye_h = s * 0.085
		draw_rect(Rect2(Vector2(eye_x - eye_w, eye_y - eye_h / 2.0), Vector2(eye_w * 2.0, eye_h)), c_eye_outer)
		draw_rect(Rect2(Vector2(eye_x - eye_w * 0.75, eye_y - eye_h * 0.1), Vector2(eye_w * 1.5, eye_h * 0.55)), c_eye_iris)
		draw_circle(Vector2(eye_x - eye_w * 0.35, eye_y - eye_h * 0.25), s * 0.024, c_eye_sparkle)
		draw_circle(Vector2(eye_x + eye_w * 0.35, eye_y + eye_h * 0.22), s * 0.013, c_eye_sparkle)

	elif facing == "right":
		# === 侧面 (朝右) ===
		var l1 = Rect2(Vector2(center_x - s * 0.05 - leg_offset, leg_top), Vector2(s * 0.10, leg_h))
		var l2 = Rect2(Vector2(center_x - s * 0.05 + leg_offset, leg_top), Vector2(s * 0.10, leg_h))
		draw_rect(l2, c_pants)
		draw_rect(l1, c_pants)
		draw_rect(Rect2(Vector2(l1.position.x - s * 0.01, l1.position.y + leg_h - s * 0.04), Vector2(s * 0.13, s * 0.05)), c_shoes)

		var body_rect = Rect2(Vector2(center_x - s * 0.11, body_top), Vector2(s * 0.22, body_h))
		draw_rect(body_rect, c_shirt)

		draw_circle(Vector2(center_x, head_y), head_r, c_skin)
		draw_circle(Vector2(center_x, head_y - head_r * 0.35), head_r * 0.88, c_hat)
		draw_circle(Vector2(center_x, head_y - head_r * 0.9), s * 0.07, c_hat_ear)

		# 侧面腮红
		draw_circle(Vector2(center_x + s * 0.14, head_y + s * 0.09), s * 0.05, c_blush)

		# 侧面水汪汪大眼睛
		var eye_x = center_x + s * 0.10
		var eye_y = head_y + s * 0.03
		var eye_w = s * 0.065
		var eye_h = s * 0.085
		draw_rect(Rect2(Vector2(eye_x - eye_w, eye_y - eye_h / 2.0), Vector2(eye_w * 2.0, eye_h)), c_eye_outer)
		draw_rect(Rect2(Vector2(eye_x - eye_w * 0.75, eye_y - eye_h * 0.1), Vector2(eye_w * 1.5, eye_h * 0.55)), c_eye_iris)
		draw_circle(Vector2(eye_x - eye_w * 0.35, eye_y - eye_h * 0.25), s * 0.024, c_eye_sparkle)
		draw_circle(Vector2(eye_x + eye_w * 0.35, eye_y + eye_h * 0.22), s * 0.013, c_eye_sparkle)
