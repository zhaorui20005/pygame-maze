# GDScript: 主控制器节点
extends Node2D

const CELL_SIZE = 26.0
const HUD_HEIGHT = 48.0
const SIDEBAR_WIDTH = 260.0

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
var audio_wolf_player: AudioStreamPlayer = null
var audio_caught_player: AudioStreamPlayer = null
var audio_bgm_menu_player: AudioStreamPlayer = null
var audio_bgm_free_player: AudioStreamPlayer = null
var audio_bgm_challenge_player: AudioStreamPlayer = null
var current_bgm_key: String = ""

# 音量设置 (0.0 ~ 1.0)
var vol_walk: float = 0.7
var vol_sfx: float = 0.8
var vol_bgm: float = 0.6
var dragging_slider: String = ""

var player_tex: Texture2D = null
var mochi_textures: Dictionary = {}
var wolf_textures: Dictionary = {}
var player_skins: Dictionary = {}
var skin_list: Array = ["red_hood", "mochi"]
var current_skin_idx: int = 0

# 大灰狼角色与追赶逻辑
var wolf_active: bool = false
var caught_by_wolf: bool = false
var wolf_pos: Vector2 = Vector2.ZERO
var wolf_facing: String = "down"
var wolf_anim_frame: int = 0
var wolf_step_timer: float = 0.0
var wolf_trail: Array = []
var wolf_crying: bool = false
var wolf_speed: float = 90.0

# 计时器与最佳纪录及积分
var in_menu: bool = true
var game_mode: String = "free" # "free" 或 "challenge"
var challenge_total_time: float = 0.0
var challenge_total_score: int = 0
var challenge_completed: bool = false
var challenge_best_time: float = -1.0
var challenge_best_score: int = 0

var timer_started: bool = false
var start_time_msec: int = 0
var current_time_sec: float = 0.0
var best_records: Dictionary = {}
var total_score: int = 0
var last_round_score: int = 0
var score_doubled: bool = false

# UI Label
@onready var hud_label: Label = $CanvasLayer/HUDMargin/HUDLabel
@onready var total_score_label: Label = $CanvasLayer/Sidebar/Margin/VBox/ScoreCard/Margin/VBox/TotalScoreLabel
@onready var last_score_label: Label = $CanvasLayer/Sidebar/Margin/VBox/ScoreCard/Margin/VBox/LastScoreLabel
@onready var level_label: Label = $CanvasLayer/Sidebar/Margin/VBox/LevelCard/Margin/VBox/LevelLabel
@onready var points_info_label: Label = $CanvasLayer/Sidebar/Margin/VBox/LevelCard/Margin/VBox/PointsInfoLabel
@onready var time_label: Label = $CanvasLayer/Sidebar/Margin/VBox/TimerCard/Margin/VBox/TimeLabel
@onready var best_label: Label = $CanvasLayer/Sidebar/Margin/VBox/TimerCard/Margin/VBox/BestLabel
@onready var status_label: Label = $CanvasLayer/Sidebar/Margin/VBox/StatusCard/Margin/StatusLabel

func _ready() -> void:
	_load_best_records()

	# 优先尝试加载小红帽 / 糯米团子 4 方向多帧精灵序列图 (red_hood_frames, mochi_frames)
	for skin_name in ["red_hood", "mochi"]:
		var folder_name = "red_hood_frames" if skin_name == "red_hood" else "mochi_frames"
		var skin_dict: Dictionary = {}
		for d in ["down", "up", "left", "right"]:
			var frames_arr: Array = []
			for f_name in [d + "_0", d + "_1", d + "_idle"]:
				var path_res = "res://assets/%s/%s.png" % [folder_name, f_name]
				var path_fs = "assets/%s/%s.png" % [folder_name, f_name]
				if ResourceLoader.exists(path_res):
					frames_arr.append(load(path_res))
				elif FileAccess.file_exists(path_fs):
					var img = Image.load_from_file(path_fs)
					if img != null:
						frames_arr.append(ImageTexture.create_from_image(img))
			if frames_arr.size() > 0:
				skin_dict[d] = frames_arr
		if skin_dict.size() > 0:
			player_skins[skin_name] = skin_dict

	if player_skins.has("red_hood"):
		mochi_textures = player_skins["red_hood"]
	elif player_skins.has("mochi"):
		mochi_textures = player_skins["mochi"]

	# 加载大灰狼贴图帧 (down, up, left, right, cry)
	for d in ["down", "up", "left", "right", "cry"]:
		var w_frames: Array = []
		for f_idx in ["0", "1"]:
			var path_res = "res://assets/wolf_frames/%s_%s.png" % [d, f_idx]
			var path_fs = "assets/wolf_frames/%s_%s.png" % [d, f_idx]
			if ResourceLoader.exists(path_res):
				w_frames.append(load(path_res))
			elif FileAccess.file_exists(path_fs):
				var img = Image.load_from_file(path_fs)
				if img != null:
					w_frames.append(ImageTexture.create_from_image(img))
		if w_frames.size() > 0:
			wolf_textures[d] = w_frames

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

	audio_wolf_player = AudioStreamPlayer.new()
	audio_wolf_player.stream = SoundGenerator.create_sound_wolf()
	add_child(audio_wolf_player)

	audio_caught_player = AudioStreamPlayer.new()
	audio_caught_player.stream = SoundGenerator.create_sound_caught()
	add_child(audio_caught_player)

	audio_bgm_menu_player = AudioStreamPlayer.new()
	audio_bgm_menu_player.stream = SoundGenerator.create_sound_bgm_menu()
	add_child(audio_bgm_menu_player)

	audio_bgm_free_player = AudioStreamPlayer.new()
	audio_bgm_free_player.stream = SoundGenerator.create_sound_bgm_free()
	add_child(audio_bgm_free_player)

	audio_bgm_challenge_player = AudioStreamPlayer.new()
	audio_bgm_challenge_player.stream = SoundGenerator.create_sound_bgm_challenge()
	add_child(audio_bgm_challenge_player)

	_apply_volumes()
	_switch_bgm("menu")

	player = MazePlayer.new()
	add_child(player)
	player.connect("step_taken", Callable(self, "_on_player_step"))

	_start_new_game(difficulty_level)
	_return_to_main_menu()

func _lin_to_db(v: float) -> float:
	if v <= 0.001:
		return -80.0
	return 20.0 * (log(v) / log(10.0))

func _switch_bgm(key: String) -> void:
	if current_bgm_key == key:
		return
	if audio_bgm_menu_player != null: audio_bgm_menu_player.stop()
	if audio_bgm_free_player != null: audio_bgm_free_player.stop()
	if audio_bgm_challenge_player != null: audio_bgm_challenge_player.stop()

	current_bgm_key = key
	var target_player: AudioStreamPlayer = null
	if key == "menu": target_player = audio_bgm_menu_player
	elif key == "free": target_player = audio_bgm_free_player
	elif key == "challenge": target_player = audio_bgm_challenge_player

	if target_player != null:
		target_player.volume_db = _lin_to_db(vol_bgm)
		target_player.play()

func _apply_volumes() -> void:
	var db_bgm = _lin_to_db(vol_bgm)
	if audio_step_player != null: audio_step_player.volume_db = _lin_to_db(vol_walk)
	if audio_start_player != null: audio_start_player.volume_db = _lin_to_db(vol_sfx)
	if audio_win_player != null: audio_win_player.volume_db = _lin_to_db(vol_sfx)
	if audio_wolf_player != null: audio_wolf_player.volume_db = _lin_to_db(vol_sfx)
	if audio_caught_player != null: audio_caught_player.volume_db = _lin_to_db(vol_sfx)
	if audio_bgm_menu_player != null: audio_bgm_menu_player.volume_db = db_bgm
	if audio_bgm_free_player != null: audio_bgm_free_player.volume_db = db_bgm
	if audio_bgm_challenge_player != null: audio_bgm_challenge_player.volume_db = db_bgm

func _start_new_game(level: int) -> void:
	difficulty_level = level
	won = false
	caught_by_wolf = false
	wolf_active = false
	wolf_crying = false
	wolf_trail.clear()
	timer_started = false
	start_time_msec = 0
	current_time_sec = 0.0

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
	if maze_data == null:
		return
	var win_size = get_viewport_rect().size
	var avail_w = max(1.0, win_size.x - SIDEBAR_WIDTH)
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
	var avail_w = max(1.0, win_size.x - SIDEBAR_WIDTH)
	var avail_h = max(1.0, win_size.y - HUD_HEIGHT)
	var vc_x = avail_w / 2.0
	var vc_y = HUD_HEIGHT + avail_h / 2.0
	offset_pos.x = vc_x - (player.pixel_position.x + player.size / 2.0) * camera_scale
	offset_pos.y = vc_y - (player.pixel_position.y + player.size / 2.0) * camera_scale

func _start_free_mode() -> void:
	in_menu = false
	game_mode = "free"
	_switch_bgm("free")
	if has_node("CanvasLayer/Sidebar"):
		$CanvasLayer/Sidebar.visible = true
	if has_node("CanvasLayer/HUDMargin"):
		$CanvasLayer/HUDMargin.visible = true
	_start_new_game(5)

func _start_challenge_mode() -> void:
	in_menu = false
	game_mode = "challenge"
	challenge_total_time = 0.0
	challenge_total_score = 0
	challenge_completed = false
	_switch_bgm("challenge")
	if has_node("CanvasLayer/Sidebar"):
		$CanvasLayer/Sidebar.visible = true
	if has_node("CanvasLayer/HUDMargin"):
		$CanvasLayer/HUDMargin.visible = true
	_start_new_game(1)

func _return_to_main_menu() -> void:
	in_menu = true
	_switch_bgm("menu")
	if has_node("CanvasLayer/Sidebar"):
		$CanvasLayer/Sidebar.visible = false
	if has_node("CanvasLayer/HUDMargin"):
		$CanvasLayer/HUDMargin.visible = false
	queue_redraw()

func _unhandled_input(event: InputEvent) -> void:
	var win_size = get_viewport_rect().size
	var cx = win_size.x / 2.0
	var cy = win_size.y / 2.0
	var btn_free_rect = Rect2(cx - 260, cy - 176, 520, 68)
	var btn_chal_rect = Rect2(cx - 260, cy - 96, 520, 68)

	var sound_card_y = cy - 16
	var walk_minus = Rect2(cx - 260 + 120, sound_card_y + 32, 28, 22)
	var walk_plus = Rect2(cx - 260 + 348, sound_card_y + 32, 28, 22)
	var walk_track = Rect2(cx - 260 + 158, sound_card_y + 39, 180, 8)

	var sfx_minus = Rect2(cx - 260 + 120, sound_card_y + 59, 28, 22)
	var sfx_plus = Rect2(cx - 260 + 348, sound_card_y + 59, 28, 22)
	var sfx_track = Rect2(cx - 260 + 158, sound_card_y + 66, 180, 8)

	var bgm_minus = Rect2(cx - 260 + 120, sound_card_y + 86, 28, 22)
	var bgm_plus = Rect2(cx - 260 + 348, sound_card_y + 86, 28, 22)
	var bgm_track = Rect2(cx - 260 + 158, sound_card_y + 93, 180, 8)

	if in_menu:
		if event is InputEventKey and event.pressed:
			if event.keycode == KEY_ESCAPE:
				get_tree().quit()
			elif event.keycode in [KEY_1, KEY_KP_1, KEY_F]:
				_start_free_mode()
			elif event.keycode in [KEY_2, KEY_KP_2, KEY_C]:
				_start_challenge_mode()
		elif event is InputEventMouseButton:
			if event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
				if btn_free_rect.has_point(event.position):
					_start_free_mode()
				elif btn_chal_rect.has_point(event.position):
					_start_challenge_mode()
				elif walk_minus.has_point(event.position):
					vol_walk = max(0.0, snapped(vol_walk - 0.05, 0.05))
					_apply_volumes()
					if audio_step_player != null: audio_step_player.play()
					_save_best_records()
					queue_redraw()
				elif walk_plus.has_point(event.position):
					vol_walk = min(1.0, snapped(vol_walk + 0.05, 0.05))
					_apply_volumes()
					if audio_step_player != null: audio_step_player.play()
					_save_best_records()
					queue_redraw()
				elif walk_track.has_point(event.position):
					dragging_slider = "walk"
					vol_walk = clamp(snapped((event.position.x - walk_track.position.x) / walk_track.size.x, 0.05), 0.0, 1.0)
					_apply_volumes()
					if audio_step_player != null: audio_step_player.play()
					_save_best_records()
					queue_redraw()
				elif sfx_minus.has_point(event.position):
					vol_sfx = max(0.0, snapped(vol_sfx - 0.05, 0.05))
					_apply_volumes()
					if audio_start_player != null: audio_start_player.play()
					_save_best_records()
					queue_redraw()
				elif sfx_plus.has_point(event.position):
					vol_sfx = min(1.0, snapped(vol_sfx + 0.05, 0.05))
					_apply_volumes()
					if audio_start_player != null: audio_start_player.play()
					_save_best_records()
					queue_redraw()
				elif sfx_track.has_point(event.position):
					dragging_slider = "sfx"
					vol_sfx = clamp(snapped((event.position.x - sfx_track.position.x) / sfx_track.size.x, 0.05), 0.0, 1.0)
					_apply_volumes()
					if audio_start_player != null: audio_start_player.play()
					_save_best_records()
					queue_redraw()
				elif bgm_minus.has_point(event.position):
					vol_bgm = max(0.0, snapped(vol_bgm - 0.05, 0.05))
					_apply_volumes()
					_save_best_records()
					queue_redraw()
				elif bgm_plus.has_point(event.position):
					vol_bgm = min(1.0, snapped(vol_bgm + 0.05, 0.05))
					_apply_volumes()
					_save_best_records()
					queue_redraw()
				elif bgm_track.has_point(event.position):
					dragging_slider = "bgm"
					vol_bgm = clamp(snapped((event.position.x - bgm_track.position.x) / bgm_track.size.x, 0.05), 0.0, 1.0)
					_apply_volumes()
					_save_best_records()
					queue_redraw()
			elif not event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
				dragging_slider = ""
		elif event is InputEventMouseMotion and dragging_slider != "":
			if dragging_slider == "walk":
				vol_walk = clamp(snapped((event.position.x - walk_track.position.x) / walk_track.size.x, 0.05), 0.0, 1.0)
			elif dragging_slider == "sfx":
				vol_sfx = clamp(snapped((event.position.x - sfx_track.position.x) / sfx_track.size.x, 0.05), 0.0, 1.0)
			elif dragging_slider == "bgm":
				vol_bgm = clamp(snapped((event.position.x - bgm_track.position.x) / bgm_track.size.x, 0.05), 0.0, 1.0)
			_apply_volumes()
			_save_best_records()
			queue_redraw()
		return

	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_ESCAPE or event.keycode == KEY_M:
			_return_to_main_menu()
		elif event.keycode == KEY_C:
			if not following_player:
				focus_player()
			else:
				fit_to_screen()
			queue_redraw()
		elif event.keycode == KEY_SPACE:
			if won and game_mode == "challenge":
				if difficulty_level < 10:
					_start_new_game(difficulty_level + 1)
				elif challenge_completed:
					_start_challenge_mode()
			else:
				if not following_player:
					focus_player()
				else:
					fit_to_screen()
				queue_redraw()
		elif (event.keycode >= KEY_1 and event.keycode <= KEY_9) and game_mode == "free":
			_start_new_game(event.keycode - KEY_1 + 1)
		elif event.keycode == KEY_0 and game_mode == "free":
			_start_new_game(10)
		elif (event.keycode >= KEY_KP_1 and event.keycode <= KEY_KP_9) and game_mode == "free":
			_start_new_game(event.keycode - KEY_KP_1 + 1)
		elif event.keycode == KEY_KP_0 and game_mode == "free":
			_start_new_game(10)
		elif (event.keycode == KEY_EQUAL or event.keycode == KEY_KP_ADD) and game_mode == "free":
			if difficulty_level < 10:
				_start_new_game(difficulty_level + 1)
		elif (event.keycode == KEY_MINUS or event.keycode == KEY_KP_SUBTRACT) and game_mode == "free":
			if difficulty_level > 1:
				_start_new_game(difficulty_level - 1)
		elif event.keycode == KEY_R:
			if won and game_mode == "challenge":
				if difficulty_level < 10:
					_start_new_game(difficulty_level + 1)
				elif challenge_completed:
					_start_challenge_mode()
			else:
				_start_new_game(difficulty_level)
		elif event.keycode == KEY_P:
			current_skin_idx = (current_skin_idx + 1) % skin_list.size()
			var skin_key = skin_list[current_skin_idx]
			if player_skins.has(skin_key):
				mochi_textures = player_skins[skin_key]
			queue_redraw()
		elif event.keycode == KEY_F:
			if wolf_active:
				wolf_active = false
			else:
				wolf_active = true
				wolf_crying = false
				wolf_pos = Vector2(
					maze_data.entrance.x * CELL_SIZE + CELL_SIZE / 2.0,
					maze_data.entrance.y * CELL_SIZE + CELL_SIZE / 2.0
				)
				wolf_trail.clear()
				if audio_wolf_player != null:
					audio_wolf_player.play()

	elif event is InputEventMouseButton:
		if event.button_index in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT, MOUSE_BUTTON_MIDDLE]:
			if event.pressed:
				if event.position.x < win_size.x - SIDEBAR_WIDTH and event.position.y > HUD_HEIGHT:
					is_dragging = true
					drag_start_mouse = event.position
					drag_start_offset = offset_pos
					following_player = false
			else:
				is_dragging = false
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP and event.pressed:
			if event.position.x < win_size.x - SIDEBAR_WIDTH and event.position.y > HUD_HEIGHT:
				_zoom(1.15, event.position)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and event.pressed:
			if event.position.x < win_size.x - SIDEBAR_WIDTH and event.position.y > HUD_HEIGHT:
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

func _has_movement_input() -> bool:
	return Input.is_action_pressed("ui_left") or Input.is_action_pressed("ui_right") \
		or Input.is_action_pressed("ui_up") or Input.is_action_pressed("ui_down") \
		or Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_D) \
		or Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_S)

func _physics_process(delta: float) -> void:
	if not won and not caught_by_wolf and maze_data != null:
		# 玩家按下方向键后开始按精确到 0.01 秒计时
		if not timer_started:
			if player.is_moving or _has_movement_input():
				timer_started = true
				start_time_msec = Time.get_ticks_msec()

		if timer_started:
			current_time_sec = (Time.get_ticks_msec() - start_time_msec) / 1000.0
			_update_hud()

		player.process_movement(delta, maze_data, CELL_SIZE)

		# 大灰狼追赶与轨迹追踪逻辑
		if wolf_active:
			var p_center = player.pixel_position + Vector2(player.size / 2.0, player.size / 2.0)
			if wolf_trail.size() == 0 or wolf_trail[-1].distance_to(p_center) >= 8.0:
				wolf_trail.append(p_center)

			var target = wolf_trail[0] if wolf_trail.size() > 0 else p_center
			var dir = target - wolf_pos
			var dist = dir.length()

			if dist < 6.0 and wolf_trail.size() > 0:
				wolf_trail.remove_at(0)
				if wolf_trail.size() > 0:
					target = wolf_trail[0]
					dir = target - wolf_pos
					dist = dir.length()

			if dist > 0.001:
				var move_step = min(wolf_speed * delta, dist)
				wolf_pos += dir.normalized() * move_step
				if abs(dir.x) > abs(dir.y):
					wolf_facing = "right" if dir.x > 0 else "left"
				else:
					wolf_facing = "down" if dir.y > 0 else "up"

				wolf_step_timer += delta
				if wolf_step_timer >= 0.15:
					wolf_step_timer = 0.0
					wolf_anim_frame = (wolf_anim_frame + 1) % 2

			# 检查大灰狼是否抓到玩家
			if wolf_pos.distance_to(p_center) < CELL_SIZE * 0.65:
				caught_by_wolf = true
				last_round_score = 0
				score_doubled = false
				_update_hud()
				if audio_caught_player != null:
					audio_caught_player.play()

		if player.check_reached_exit(maze_data, CELL_SIZE):
			won = true
			if wolf_active:
				wolf_crying = true

			if timer_started:
				current_time_sec = (Time.get_ticks_msec() - start_time_msec) / 1000.0

			var has_prev = best_records.has(difficulty_level)
			var prev_best = best_records.get(difficulty_level, 999999.0)
			var is_new_record = false

			if not has_prev or current_time_sec < prev_best:
				is_new_record = true
				best_records[difficulty_level] = current_time_sec

			var base_score = difficulty_level * 100
			if is_new_record:
				last_round_score = base_score * 2
				score_doubled = true
			else:
				last_round_score = base_score
				score_doubled = false

			if game_mode == "free":
				total_score += last_round_score
				_save_best_records()
			elif game_mode == "challenge":
				challenge_total_time += current_time_sec
				challenge_total_score += last_round_score
				if difficulty_level == 10:
					challenge_completed = true
					total_score += challenge_total_score
					if challenge_best_time < 0.0 or challenge_total_time < challenge_best_time:
						challenge_best_time = challenge_total_time
					if challenge_total_score > challenge_best_score:
						challenge_best_score = challenge_total_score
					_save_best_records()
				else:
					_save_best_records()

			_update_hud()

			if audio_win_player != null:
				audio_win_player.play()

		if following_player:
			_update_player_focus()

	elif won and wolf_active:
		wolf_crying = true
		wolf_step_timer += delta
		if wolf_step_timer >= 0.25:
			wolf_step_timer = 0.0
			wolf_anim_frame = (wolf_anim_frame + 1) % 2

	queue_redraw()

func _on_player_step() -> void:
	if audio_step_player != null:
		audio_step_player.play()

func _update_hud() -> void:
	if maze_data == null or maze_data.metrics == null:
		return
	var m = maze_data.metrics
	hud_label.text = "🎮 迷宫大冒险 (%s阶) | 路径 %d 死胡同 %d" % [m.label, m.path_length, m.dead_ends]

	if total_score_label != null:
		total_score_label.text = "累计总分: %d 分" % total_score

	if last_score_label != null:
		if game_mode == "free":
			if last_round_score > 0:
				var d_str = " (破纪录翻倍!)" if score_doubled else ""
				last_score_label.text = "本局得分: +%d 分%s" % [last_round_score, d_str]
			elif caught_by_wolf:
				last_score_label.text = "本局得分: 0 分 (被狼抓)"
			else:
				last_score_label.text = "本局得分: --"
		else:
			last_score_label.text = "闯关累计得分: %d 分" % challenge_total_score

	if level_label != null:
		if game_mode == "free":
			level_label.text = "当前关卡: %s 阶" % m.label
		else:
			level_label.text = "闯关进度: 第 %d / 10 阶" % difficulty_level

	if points_info_label != null:
		var base_pts = difficulty_level * 100
		if game_mode == "free":
			points_info_label.text = "通关: +%d分 | 破纪录: +%d分" % [base_pts, base_pts * 2]
		else:
			points_info_label.text = "本阶得分: +%d分 (破纪录加倍)" % base_pts

	if time_label != null:
		var time_str = ("%.2f 秒" % current_time_sec) if timer_started else "按方向键开始"
		if game_mode == "free":
			time_label.text = "当前用时: %s" % time_str
		else:
			time_label.text = "本阶用时: %s" % time_str

	if best_label != null:
		if game_mode == "free":
			var best_str = ("%.2f 秒" % best_records[difficulty_level]) if best_records.has(difficulty_level) else "无纪录"
			best_label.text = "最佳纪录: %s" % best_str
		else:
			best_label.text = "闯关累计用时: %.2f 秒" % challenge_total_time

	if status_label != null:
		if game_mode == "challenge" and challenge_completed:
			status_label.text = "🏆 大满贯全通关！\n1~10阶总用时: %.2f 秒\n获得全通总分: +%d 分\n👉 按 R 重测，按 M 返回主菜单" % [challenge_total_time, challenge_total_score]
		elif won:
			if game_mode == "free":
				if score_doubled:
					status_label.text = "🎉 成功通关！\n获得积分: +%d 分\n🏆 破纪录积分翻倍！\n👉 按 R 继续，按 M 返回主菜单" % last_round_score
				else:
					status_label.text = "🎉 成功通关！\n获得积分: +%d 分\n再接再厉，挑战更快速度！\n👉 按 R 继续，按 M 返回主菜单" % last_round_score
			else:
				status_label.text = "🎉 突破第 %d 阶！\n获得积分: +%d 分\n👉 按 R / 空格进入第 %d 阶" % [difficulty_level, last_round_score, difficulty_level + 1]
		elif caught_by_wolf:
			status_label.text = "😱 被大灰狼抓住了！\n本局得分: 0 分\n👉 按 R 重新尝试本关"
		else:
			if game_mode == "free":
				status_label.text = "🟢 正在自由模式闯关...\n避开大灰狼到达小屋\n按 M 键可随时返回主菜单"
			else:
				status_label.text = "🟢 闯关挑战中 (%d/10阶)\n顺序挑战 1~10 阶全部迷宫\n创造最快全通时间与最高分！" % difficulty_level

func _load_best_records() -> void:
	var path = "user://best_records.json"
	if FileAccess.file_exists(path):
		var file = FileAccess.open(path, FileAccess.READ)
		if file != null:
			var json = JSON.new()
			if json.parse(file.get_as_text()) == OK:
				var data = json.get_data()
				if data is Dictionary:
					for k in data.keys():
						if str(k) == "total_score":
							total_score = int(data[k])
						elif str(k) == "challenge_best_time":
							challenge_best_time = float(data[k])
						elif str(k) == "challenge_best_score":
							challenge_best_score = int(data[k])
						elif str(k) == "vol_walk":
							vol_walk = float(data[k])
						elif str(k) == "vol_sfx":
							vol_sfx = float(data[k])
						elif str(k) == "vol_bgm":
							vol_bgm = float(data[k])
						else:
							best_records[int(k)] = float(data[k])

func _save_best_records() -> void:
	var file = FileAccess.open("user://best_records.json", FileAccess.WRITE)
	if file != null:
		var data = {}
		for k in best_records.keys():
			data[str(k)] = float(best_records[k])
		data["total_score"] = total_score
		if challenge_best_time >= 0.0:
			data["challenge_best_time"] = challenge_best_time
		data["challenge_best_score"] = challenge_best_score
		data["vol_walk"] = snapped(vol_walk, 0.01)
		data["vol_sfx"] = snapped(vol_sfx, 0.01)
		data["vol_bgm"] = snapped(vol_bgm, 0.01)
		file.store_string(JSON.stringify(data))

func _draw() -> void:
	var win_size = get_viewport_rect().size

	if in_menu:
		_draw_main_menu(win_size)
		return

	if maze_data == null:
		return

	var maze_w = win_size.x - SIDEBAR_WIDTH

	# 背景填充
	draw_rect(Rect2(Vector2.ZERO, win_size), COLOR_BG)

	# 瓦片绘制范围裁剪
	var min_wx = (0.0 - offset_pos.x) / camera_scale
	var max_wx = (maze_w - offset_pos.x) / camera_scale
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

	# 入口与出口绘制 (起点大树，终点小房子)
	_draw_tile_marker(maze_data.entrance, COLOR_ENTRANCE, "tree")
	_draw_tile_marker(maze_data.exit_tile, COLOR_EXIT, "house")

	# 绘制萌系 Q 版小人与大灰狼
	_draw_player()
	_draw_wolf()

	# HUD 顶栏背景
	draw_rect(Rect2(0, 0, maze_w, HUD_HEIGHT), COLOR_HUD_BG)

func _draw_main_menu(win_size: Vector2) -> void:
	draw_rect(Rect2(Vector2.ZERO, win_size), Color(0.05, 0.06, 0.10))
	var cx = win_size.x / 2.0
	var cy = win_size.y / 2.0

	var font_default = ThemeDB.fallback_font
	if font_default == null:
		return

	# 1. 标题与副标题
	draw_string(font_default, Vector2(cx - 180, cy - 235), "🎮 小红帽迷宫大冒险", HORIZONTAL_ALIGNMENT_CENTER, -1, 32, Color(1, 0.88, 0.35))
	draw_string(font_default, Vector2(cx - 180, cy - 198), "—— 请选择游戏模式 & 调整声音设置 ——", HORIZONTAL_ALIGNMENT_CENTER, -1, 16, Color(0.67, 0.75, 0.85))

	# 2. 模式 1：自由模式 (Free Mode)
	var btn1_rect = Rect2(cx - 260, cy - 176, 520, 68)
	draw_rect(btn1_rect, Color(0.09, 0.13, 0.20))
	draw_rect(btn1_rect, Color(0.39, 0.70, 1.0), false, 1.5)

	draw_string(font_default, Vector2(btn1_rect.position.x + 18, btn1_rect.position.y + 28), "🌟 1. 自由模式 (Free Mode)", HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color(1, 0.94, 0.6))
	draw_string(font_default, Vector2(btn1_rect.position.x + 18, btn1_rect.position.y + 52), "按 [1] 键或点击 | 1~10 阶自由切换，无限切关与随心练习", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(0.63, 0.71, 0.80))

	# 3. 模式 2：闯关模式 (Challenge Mode)
	var btn2_rect = Rect2(cx - 260, cy - 96, 520, 68)
	draw_rect(btn2_rect, Color(0.09, 0.13, 0.20))
	draw_rect(btn2_rect, Color(1.0, 0.82, 0.35), false, 1.5)

	draw_string(font_default, Vector2(btn2_rect.position.x + 18, btn2_rect.position.y + 28), "🏆 2. 闯关模式 (Challenge Mode)", HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color(1, 0.86, 0.35))
	draw_string(font_default, Vector2(btn2_rect.position.x + 18, btn2_rect.position.y + 52), "按 [2] 键或点击 | 从 1 阶连续闯关至 10 阶，结算总用时与得分", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(0.63, 0.71, 0.80))

	# 4. 卡片 3：🎵 声音大小设置 (Sound Settings)
	var sound_card = Rect2(cx - 260, cy - 16, 520, 120)
	draw_rect(sound_card, Color(0.09, 0.13, 0.20))
	draw_rect(sound_card, Color(0.24, 0.35, 0.55), false, 1.0)

	draw_string(font_default, Vector2(sound_card.position.x + 16, sound_card.position.y + 24), "🎵 声音大小设置", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color(1, 0.86, 0.35))

	var _draw_vol_row = func(label: String, y_pos: float, vol: float):
		draw_string(font_default, Vector2(sound_card.position.x + 16, y_pos + 15), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(0.86, 0.90, 0.96))

		var bm = Rect2(sound_card.position.x + 120, y_pos, 28, 22)
		draw_rect(bm, Color(0.18, 0.26, 0.38))
		draw_rect(bm, Color(0.39, 0.55, 0.75), false, 1.0)
		draw_string(font_default, Vector2(bm.position.x + 10, bm.position.y + 16), "-", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color(1, 1, 1))

		var track = Rect2(sound_card.position.x + 158, y_pos + 7, 180, 8)
		draw_rect(track, Color(0.16, 0.20, 0.29))
		var fill_w = vol * track.size.x
		if fill_w > 0:
			draw_rect(Rect2(track.position, Vector2(fill_w, track.size.y)), Color(0.39, 0.75, 1.0))
		draw_circle(Vector2(track.position.x + fill_w, track.position.y + 4), 6.0, Color(1.0, 0.92, 0.55))

		var bp = Rect2(sound_card.position.x + 348, y_pos, 28, 22)
		draw_rect(bp, Color(0.18, 0.26, 0.38))
		draw_rect(bp, Color(0.39, 0.55, 0.75), false, 1.0)
		draw_string(font_default, Vector2(bp.position.x + 8, bp.position.y + 16), "+", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color(1, 1, 1))

		draw_string(font_default, Vector2(sound_card.position.x + 388, y_pos + 16), "%d%%" % int(round(vol * 100.0)), HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(1.0, 0.92, 0.59))

	_draw_vol_row.call("🚶 走路音效", sound_card.position.y + 32, vol_walk)
	_draw_vol_row.call("🔔 提示音效", sound_card.position.y + 59, vol_sfx)
	_draw_vol_row.call("🎵 背景音乐", sound_card.position.y + 86, vol_bgm)

	# 5. 排行榜纪录卡片
	var card_rect = Rect2(cx - 260, cy + 116, 520, 75)
	draw_rect(card_rect, Color(0.07, 0.10, 0.16))
	draw_rect(card_rect, Color(0.16, 0.23, 0.35), false, 1.0)

	draw_string(font_default, Vector2(card_rect.position.x + 16, card_rect.position.y + 22), "📊 荣耀排行榜纪录", HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color(1, 0.84, 0.31))
	draw_string(font_default, Vector2(card_rect.position.x + 16, card_rect.position.y + 44), "累计总得分: %d 分" % total_score, HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(0.78, 0.88, 0.96))

	var c_time_str = "%.2f 秒" % challenge_best_time if challenge_best_time >= 0.0 else "暂无纪录"
	var c_score_str = "%d 分" % challenge_best_score if challenge_best_score > 0 else "暂无纪录"
	draw_string(font_default, Vector2(card_rect.position.x + 16, card_rect.position.y + 64), "闯关模式最佳全通: %s | 最高得分: %s" % [c_time_str, c_score_str], HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(0.71, 0.82, 1.0))

	# 6. 提示
	draw_string(font_default, Vector2(cx - 210, win_size.y - 22), "👉 点击模式或调音按钮 | 按 [1]/[2] 启动模式 | 按 [ESC] 退出程序", HORIZONTAL_ALIGNMENT_CENTER, -1, 13, Color(0.51, 0.59, 0.69))

func _draw_tile_marker(tile: Vector2i, color: Color, type: String) -> void:
	var p1 = offset_pos + Vector2(tile.x * CELL_SIZE, tile.y * CELL_SIZE) * camera_scale
	var p2 = offset_pos + Vector2((tile.x + 1) * CELL_SIZE, (tile.y + 1) * CELL_SIZE) * camera_scale
	var rect = Rect2(p1, p2 - p1)
	draw_rect(rect, color)

	# 给终点/起点绘制耀眼高对比外框，防止与背景混淆
	if type == "house":
		draw_rect(rect, Color(1.0, 0.80, 0.30), false, max(1.0, camera_scale * 1.8))
	elif type == "tree":
		draw_rect(rect, Color(0.40, 0.90, 0.40), false, max(1.0, camera_scale * 1.8))
	elif type == "flag":
		draw_rect(rect, Color(1.0, 0.90, 0.20), false, max(1.0, camera_scale * 1.8))

	if rect.size.x >= 6.0:
		if type == "house":
			_draw_mini_house(rect)
		elif type == "tree":
			_draw_mini_tree(rect)
		elif type == "flag":
			_draw_mini_flag(rect)

func _draw_mini_tree(rect: Rect2) -> void:
	var s = rect.size.x
	var pos = rect.position
	# 树干
	var trunk = Rect2(pos + Vector2(s * 0.40, s * 0.55), Vector2(s * 0.20, s * 0.38))
	draw_rect(trunk, Color(0.52, 0.32, 0.18))
	# 树冠 (三重绿色圆/多边形)
	draw_circle(pos + Vector2(s * 0.50, s * 0.38), s * 0.28, Color(0.18, 0.62, 0.25))
	draw_circle(pos + Vector2(s * 0.35, s * 0.42), s * 0.22, Color(0.22, 0.68, 0.30))
	draw_circle(pos + Vector2(s * 0.65, s * 0.42), s * 0.22, Color(0.22, 0.68, 0.30))
	# 顶部高光
	draw_circle(pos + Vector2(s * 0.45, s * 0.28), s * 0.16, Color(0.35, 0.82, 0.42))
	# 红色小小果实点缀
	draw_circle(pos + Vector2(s * 0.36, s * 0.38), s * 0.05, Color(0.92, 0.20, 0.20))
	draw_circle(pos + Vector2(s * 0.62, s * 0.32), s * 0.05, Color(0.92, 0.20, 0.20))

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

			# 果冻 Q 弹跳跃 (通关后一跳一跳的开心跳跃)
			var bounce_y = 0.0
			if won:
				bounce_y = abs(sin(Time.get_ticks_msec() * 0.012)) * rect.size.y * 0.25
			elif player.is_moving:
				bounce_y = abs(sin(Time.get_ticks_msec() * 0.020)) * rect.size.y * 0.08

			var render_rect = Rect2(rect.position - Vector2(0, bounce_y), rect.size)
			draw_texture_rect(cur_tex, render_rect, false)

		elif player_tex != null:
			var s = rect.size.x
			var bounce_y = 0.0
			if won:
				bounce_y = abs(sin(Time.get_ticks_msec() * 0.012)) * s * 0.25
			elif player.is_moving:
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

func _draw_wolf() -> void:
	if not wolf_active:
		return
	var draw_w = CELL_SIZE * 1.35
	var draw_h = CELL_SIZE * 1.35
	var p1 = offset_pos + (wolf_pos - Vector2(draw_w / 2.0, draw_h / 2.0)) * camera_scale
	var p2 = offset_pos + (wolf_pos + Vector2(draw_w / 2.0, draw_h / 2.0)) * camera_scale
	var rect = Rect2(p1, p2 - p1)

	if rect.size.x >= 6.0:
		var facing_key = "cry" if wolf_crying else wolf_facing
		if wolf_textures.has(facing_key):
			var tex_list = wolf_textures[facing_key]
			var idx = wolf_anim_frame % tex_list.size()
			draw_texture_rect(tex_list[idx], rect, false)

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
