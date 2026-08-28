# GDScript: 主控制器节点
extends Node2D

const CELL_SIZE = 26.0
const HUD_HEIGHT = 48.0
const SIDEBAR_WIDTH = 280.0

var current_world: int = 1
var difficulty_level: int = 1
var maze_data: MazeGenerator.MazeData = null
var player: MazePlayer = null
var won: bool = false
var auto_advance_timer: float = -1.0

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
var audio_bgm_dungeon_player: AudioStreamPlayer = null
var audio_bgm_pattern_player: AudioStreamPlayer = null
var audio_bgm_shape_player: AudioStreamPlayer = null
var audio_bgm_woven_player: AudioStreamPlayer = null
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

const WORLD_ITEM_INFO = {
	1: {"name": "蘑菇", "icon": "🍄", "unit": "朵"},
	2: {"name": "肉块", "icon": "🥩", "unit": "块"},
	3: {"name": "钥匙", "icon": "🔑", "unit": "把"},
	4: {"name": "宝石", "icon": "💎", "unit": "颗"},
	5: {"name": "能量核心", "icon": "⚡", "unit": "核"}
}

var item_tiles: Array[Vector2i] = []
var total_items_count: int = 0
var gate_locked_tip_timer: float = 0.0
var audio_item_player: AudioStreamPlayer = null

var timer_started: bool = false
var start_time_msec: int = 0
var current_time_sec: float = 0.0
var best_records: Dictionary = {}
var total_score: int = 0
var last_round_score: int = 0
var score_doubled: bool = false

var show_auto_path: bool = false
var regen_cooldown_msec: int = 0
var auto_visited_order: Array[Vector2i] = []
var auto_path: Array[Vector2i] = []
var auto_parent_map: Dictionary = {}
var auto_search_idx: float = 0.0
var auto_path_idx: float = 0.0
var auto_path_phase: String = "idle" # "idle", "search", "path", "complete"
var sidebar_btn_auto: Button = null
var sidebar_btn_view: Button = null

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

	audio_item_player = AudioStreamPlayer.new()
	audio_item_player.stream = SoundGenerator.create_sound_item()
	add_child(audio_item_player)

	audio_bgm_menu_player = AudioStreamPlayer.new()
	audio_bgm_menu_player.stream = SoundGenerator.create_sound_bgm_menu()
	add_child(audio_bgm_menu_player)

	audio_bgm_free_player = AudioStreamPlayer.new()
	audio_bgm_free_player.stream = SoundGenerator.create_sound_bgm_free()
	add_child(audio_bgm_free_player)

	audio_bgm_challenge_player = AudioStreamPlayer.new()
	audio_bgm_challenge_player.stream = SoundGenerator.create_sound_bgm_challenge()
	add_child(audio_bgm_challenge_player)

	audio_bgm_dungeon_player = AudioStreamPlayer.new()
	audio_bgm_dungeon_player.stream = SoundGenerator.create_sound_bgm_dungeon()
	add_child(audio_bgm_dungeon_player)

	audio_bgm_pattern_player = AudioStreamPlayer.new()
	audio_bgm_pattern_player.stream = SoundGenerator.create_sound_bgm_pattern()
	add_child(audio_bgm_pattern_player)

	audio_bgm_shape_player = AudioStreamPlayer.new()
	audio_bgm_shape_player.stream = SoundGenerator.create_sound_bgm_shape()
	add_child(audio_bgm_shape_player)

	audio_bgm_woven_player = AudioStreamPlayer.new()
	audio_bgm_woven_player.stream = SoundGenerator.create_sound_bgm_woven()
	add_child(audio_bgm_woven_player)

	_apply_volumes()
	_switch_bgm("menu")

	player = MazePlayer.new()
	add_child(player)
	player.connect("step_taken", Callable(self, "_on_player_step"))

	_setup_sidebar_level_select_buttons()
	_start_new_game(difficulty_level)
	_return_to_main_menu()

var sidebar_level_buttons: Dictionary = {} # Vector2i(world, level) -> Button

func _setup_sidebar_level_select_buttons() -> void:
	if not has_node("CanvasLayer/Sidebar/Margin/VBox/LevelCard/Margin/VBox"):
		return
	var parent_vbox = $CanvasLayer/Sidebar/Margin/VBox/LevelCard/Margin/VBox

	var sel_title = Label.new()
	sel_title.text = "🎯 调试选关 (点击直跳):"
	sel_title.add_theme_color_override("font_color", Color(1, 0.88, 0.3))
	sel_title.add_theme_font_size_override("font_size", 12)
	parent_vbox.add_child(sel_title)

	var w1_lbl = Label.new()
	w1_lbl.text = "🌲 第一大关 (绿野森林):"
	w1_lbl.add_theme_color_override("font_color", Color(0.5, 0.9, 0.6))
	w1_lbl.add_theme_font_size_override("font_size", 11)
	parent_vbox.add_child(w1_lbl)

	var grid1 = GridContainer.new()
	grid1.columns = 5
	grid1.add_theme_constant_override("h_separation", 3)
	grid1.add_theme_constant_override("v_separation", 3)
	parent_vbox.add_child(grid1)

	for i in range(1, 11):
		var btn = Button.new()
		btn.text = str(i)
		btn.custom_minimum_size = Vector2(38, 22)
		btn.add_theme_font_size_override("font_size", 11)
		var lvl_num = i
		btn.pressed.connect(func():
			_start_free_mode_at_level(1, lvl_num)
		)
		grid1.add_child(btn)
		sidebar_level_buttons[Vector2i(1, i)] = btn

	var w2_lbl = Label.new()
	w2_lbl.text = "🏰 第二大关 (狼穴地牢):"
	w2_lbl.add_theme_color_override("font_color", Color(1.0, 0.5, 0.5))
	w2_lbl.add_theme_font_size_override("font_size", 11)
	parent_vbox.add_child(w2_lbl)

	var grid2 = GridContainer.new()
	grid2.columns = 5
	grid2.add_theme_constant_override("h_separation", 3)
	grid2.add_theme_constant_override("v_separation", 3)
	parent_vbox.add_child(grid2)

	for i in range(1, 11):
		var btn = Button.new()
		btn.text = str(i)
		btn.custom_minimum_size = Vector2(38, 22)
		btn.add_theme_font_size_override("font_size", 11)
		var lvl_num = i
		btn.pressed.connect(func():
			_start_free_mode_at_level(2, lvl_num)
		)
		grid2.add_child(btn)
		sidebar_level_buttons[Vector2i(2, i)] = btn

	var w3_lbl = Label.new()
	w3_lbl.text = "🌟 第三大关 (图案秘境):"
	w3_lbl.add_theme_color_override("font_color", Color(0.82, 0.55, 1.0))
	w3_lbl.add_theme_font_size_override("font_size", 11)
	parent_vbox.add_child(w3_lbl)

	var grid3 = GridContainer.new()
	grid3.columns = 5
	grid3.add_theme_constant_override("h_separation", 3)
	grid3.add_theme_constant_override("v_separation", 3)
	parent_vbox.add_child(grid3)

	for i in range(1, 11):
		var btn = Button.new()
		btn.text = str(i)
		btn.custom_minimum_size = Vector2(38, 22)
		btn.add_theme_font_size_override("font_size", 11)
		var lvl_num = i
		btn.pressed.connect(func():
			_start_free_mode_at_level(3, lvl_num)
		)
		grid3.add_child(btn)
		sidebar_level_buttons[Vector2i(3, i)] = btn

	var w4_lbl = Label.new()
	w4_lbl.text = "🌀 第四大关 (异形几何):"
	w4_lbl.add_theme_color_override("font_color", Color(0.4, 0.9, 0.86))
	w4_lbl.add_theme_font_size_override("font_size", 11)
	parent_vbox.add_child(w4_lbl)

	var grid4 = GridContainer.new()
	grid4.columns = 5
	grid4.add_theme_constant_override("h_separation", 3)
	grid4.add_theme_constant_override("v_separation", 3)
	parent_vbox.add_child(grid4)

	for i in range(1, 11):
		var btn = Button.new()
		btn.text = str(i)
		btn.custom_minimum_size = Vector2(38, 22)
		btn.add_theme_font_size_override("font_size", 11)
		var lvl_num = i
		btn.pressed.connect(func():
			_start_free_mode_at_level(4, lvl_num)
		)
		grid4.add_child(btn)
		sidebar_level_buttons[Vector2i(4, i)] = btn

	var w5_lbl = Label.new()
	w5_lbl.text = "🌉 第五大关 (立交编织):"
	w5_lbl.add_theme_color_override("font_color", Color(0.47, 0.86, 1.0))
	w5_lbl.add_theme_font_size_override("font_size", 11)
	parent_vbox.add_child(w5_lbl)

	var grid5 = GridContainer.new()
	grid5.columns = 5
	grid5.add_theme_constant_override("h_separation", 3)
	grid5.add_theme_constant_override("v_separation", 3)
	parent_vbox.add_child(grid5)

	for i in range(1, 11):
		var btn = Button.new()
		btn.text = str(i)
		btn.custom_minimum_size = Vector2(38, 22)
		btn.add_theme_font_size_override("font_size", 11)
		var lvl_num = i
		btn.pressed.connect(func():
			_start_free_mode_at_level(5, lvl_num)
		)
		grid5.add_child(btn)
		sidebar_level_buttons[Vector2i(5, i)] = btn

	var btn_auto = Button.new()
	btn_auto.text = "🧭 自动寻路：已关闭 [点击演示]"
	btn_auto.custom_minimum_size = Vector2(210, 26)
	btn_auto.add_theme_font_size_override("font_size", 12)
	btn_auto.pressed.connect(func():
		trigger_auto_path()
	)
	parent_vbox.add_child(btn_auto)
	sidebar_btn_auto = btn_auto

	var btn_view = Button.new()
	btn_view.text = "🔍 视角: 放大跟随 [点击还原全景]"
	btn_view.custom_minimum_size = Vector2(210, 26)
	btn_view.add_theme_font_size_override("font_size", 12)
	btn_view.pressed.connect(func():
		if not following_player:
			focus_player()
		else:
			fit_to_screen()
		_update_view_btn_text()
		queue_redraw()
	)
	parent_vbox.add_child(btn_view)
	sidebar_btn_view = btn_view

func trigger_auto_path() -> void:
	show_auto_path = not show_auto_path
	if show_auto_path and maze_data != null:
		var res = maze_data.solve_path_with_visited()
		auto_visited_order = res["visited_order"]
		auto_path = res["path"]
		auto_parent_map = res["parent"]
		auto_search_idx = 0.0
		auto_path_idx = 0.0
		auto_path_phase = "search"
	else:
		auto_path_phase = "idle"
	_update_auto_btn_text()
	queue_redraw()

func _update_auto_btn_text() -> void:
	if sidebar_btn_auto != null:
		if show_auto_path:
			if auto_path_phase == "search":
				var progress = int(float(auto_search_idx) / max(1, auto_visited_order.size()) * 100.0)
				sidebar_btn_auto.text = "🧭 算法探索中... (%d%%)" % progress
			elif auto_path_phase == "path":
				var progress = int(float(auto_path_idx) / max(1, auto_path.size()) * 100.0)
				sidebar_btn_auto.text = "🧭 生成路线中... (%d%%)" % progress
			else:
				sidebar_btn_auto.text = "🧭 自动寻路：已开启"
		else:
			sidebar_btn_auto.text = "🧭 自动寻路：已关闭 [点击演示]"
	_update_view_btn_text()

func _update_view_btn_text() -> void:
	if sidebar_btn_view == null:
		return
	if following_player:
		sidebar_btn_view.text = "🔍 视角: 放大跟随 [点击还原全景]"
	else:
		sidebar_btn_view.text = "🔍 视角: 全景还原 [点击放大跟随]"

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
	if audio_bgm_dungeon_player != null: audio_bgm_dungeon_player.stop()
	if audio_bgm_pattern_player != null: audio_bgm_pattern_player.stop()
	if audio_bgm_shape_player != null: audio_bgm_shape_player.stop()
	if audio_bgm_woven_player != null: audio_bgm_woven_player.stop()

	current_bgm_key = key
	var target_player: AudioStreamPlayer = null
	if key == "menu": target_player = audio_bgm_menu_player
	elif key == "free": target_player = audio_bgm_free_player
	elif key == "challenge": target_player = audio_bgm_challenge_player
	elif key == "dungeon": target_player = audio_bgm_dungeon_player
	elif key == "pattern": target_player = audio_bgm_pattern_player
	elif key == "shape": target_player = audio_bgm_shape_player
	elif key == "woven": target_player = audio_bgm_woven_player

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
	if audio_item_player != null: audio_item_player.volume_db = _lin_to_db(vol_sfx)
	if audio_bgm_menu_player != null: audio_bgm_menu_player.volume_db = db_bgm
	if audio_bgm_free_player != null: audio_bgm_free_player.volume_db = db_bgm
	if audio_bgm_challenge_player != null: audio_bgm_challenge_player.volume_db = db_bgm
	if audio_bgm_dungeon_player != null: audio_bgm_dungeon_player.volume_db = db_bgm
	if audio_bgm_pattern_player != null: audio_bgm_pattern_player.volume_db = db_bgm
	if audio_bgm_shape_player != null: audio_bgm_shape_player.volume_db = db_bgm
	if audio_bgm_woven_player != null: audio_bgm_woven_player.volume_db = db_bgm

func _start_new_game(world: int = 1, level: int = 1) -> void:
	var now_msec = Time.get_ticks_msec()
	if now_msec - regen_cooldown_msec < 350:
		return
	regen_cooldown_msec = now_msec

	current_world = clampi(world, 1, 5)
	difficulty_level = clampi(level, 1, 10)
	won = false
	auto_advance_timer = -1.0
	caught_by_wolf = false
	wolf_active = false
	wolf_crying = false
	wolf_trail.clear()
	timer_started = false
	start_time_msec = 0
	current_time_sec = 0.0

	if current_world == 5:
		_switch_bgm("woven")
	elif current_world == 4:
		_switch_bgm("shape")
	elif current_world == 3:
		_switch_bgm("pattern")
	elif current_world == 2:
		_switch_bgm("dungeon")
	elif game_mode == "challenge":
		_switch_bgm("challenge")
	else:
		_switch_bgm("free")

	if audio_start_player != null:
		audio_start_player.play()

	maze_data = MazeGenerator.generate_maze(current_world, difficulty_level)
	if maze_data != null:
		item_tiles = maze_data.item_tiles.duplicate()
		total_items_count = item_tiles.size()
	else:
		item_tiles.clear()
		total_items_count = 0
	gate_locked_tip_timer = 0.0
	if show_auto_path and maze_data != null:
		var res = maze_data.solve_path_with_visited()
		auto_visited_order = res["visited_order"]
		auto_path = res["path"]
		auto_parent_map = res["parent"]
		auto_search_idx = 0.0
		auto_path_idx = 0.0
		auto_path_phase = "search"
	else:
		auto_visited_order.clear()
		auto_path.clear()
		auto_parent_map.clear()
		auto_search_idx = 0.0
		auto_path_idx = 0.0
		auto_path_phase = "idle"
	_update_auto_btn_text()

	# 初始化玩家起始位置
	var start_pixel = Vector2(
		maze_data.entrance.x * CELL_SIZE + 6.0,
		maze_data.entrance.y * CELL_SIZE + 6.0
	)
	player.init_player(start_pixel, CELL_SIZE - 12.0)

	focus_player()
	_update_hud()
	queue_redraw()

func fit_to_screen() -> void:
	if maze_data == null:
		return
	var win_size = get_viewport_rect().size
	var avail_w = maxf(1.0, win_size.x - SIDEBAR_WIDTH)
	var avail_h = maxf(1.0, win_size.y - HUD_HEIGHT)
	var mw = maze_data.cols * CELL_SIZE
	var mh = maze_data.rows * CELL_SIZE

	var scale_w = (avail_w - 16.0) / mw
	var scale_h = (avail_h - 16.0) / mh
	fit_scale = minf(1.0, minf(scale_w, scale_h))
	camera_scale = fit_scale

	var scaled_w = mw * camera_scale
	var scaled_h = mh * camera_scale

	offset_pos.x = maxf(8.0, (avail_w - scaled_w) / 2.0)
	offset_pos.y = HUD_HEIGHT + maxf(8.0, (avail_h - scaled_h) / 2.0) if avail_h > scaled_h else HUD_HEIGHT
	following_player = false

func focus_player() -> void:
	if maze_data != null:
		var win_size = get_viewport_rect().size
		var avail_w = maxf(1.0, win_size.x - SIDEBAR_WIDTH)
		var avail_h = maxf(1.0, win_size.y - HUD_HEIGHT)
		var mw = maze_data.cols * CELL_SIZE
		var mh = maze_data.rows * CELL_SIZE
		var scale_w = (avail_w - 16.0) / mw
		var scale_h = (avail_h - 16.0) / mh
		fit_scale = minf(1.0, minf(scale_w, scale_h))

	var target_render_size = 30.0 # 保持与 Level 10 同等舒适的放大渲染尺寸 (约 1.15 倍)
	camera_scale = maxf(1.0, target_render_size / CELL_SIZE)
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

func _start_free_mode_at_level(world: int = 1, level: int = 1) -> void:
	in_menu = false
	game_mode = "free"
	if has_node("CanvasLayer/Sidebar"):
		$CanvasLayer/Sidebar.visible = true
	if has_node("CanvasLayer/HUDMargin"):
		$CanvasLayer/HUDMargin.visible = true
	_start_new_game(world, level)

func _start_free_mode() -> void:
	_start_free_mode_at_level(1, 1)

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
	_start_new_game(1, 1)

func _advance_next_level() -> void:
	if game_mode == "challenge":
		if current_world == 1:
			if difficulty_level < 10:
				difficulty_level += 1
			else:
				current_world = 2
				difficulty_level = 1
			_start_new_game(current_world, difficulty_level)
		elif current_world == 2:
			if difficulty_level < 10:
				difficulty_level += 1
				_start_new_game(current_world, difficulty_level)
			else:
				current_world = 3
				difficulty_level = 1
				_start_new_game(current_world, difficulty_level)
		elif current_world == 3:
			if difficulty_level < 10:
				difficulty_level += 1
				_start_new_game(current_world, difficulty_level)
			else:
				current_world = 4
				difficulty_level = 1
				_start_new_game(current_world, difficulty_level)
		elif current_world == 4:
			if difficulty_level < 10:
				difficulty_level += 1
				_start_new_game(current_world, difficulty_level)
			else:
				current_world = 5
				difficulty_level = 1
				_start_new_game(current_world, difficulty_level)
		elif current_world == 5:
			if difficulty_level < 10:
				difficulty_level += 1
				_start_new_game(current_world, difficulty_level)
			else:
				_start_challenge_mode()
	else:
		if difficulty_level < 10:
			difficulty_level += 1
		else:
			if current_world == 1:
				current_world = 2
				difficulty_level = 1
			elif current_world == 2:
				current_world = 3
				difficulty_level = 1
			elif current_world == 3:
				current_world = 4
				difficulty_level = 1
			elif current_world == 4:
				current_world = 5
				difficulty_level = 1
			else:
				current_world = 1
				difficulty_level = 1
		_start_new_game(current_world, difficulty_level)

func _prev_level() -> void:
	if difficulty_level > 1:
		difficulty_level -= 1
	else:
		if current_world == 5:
			current_world = 4
			difficulty_level = 10
		elif current_world == 4:
			current_world = 3
			difficulty_level = 10
		elif current_world == 3:
			current_world = 2
			difficulty_level = 10
		elif current_world == 2:
			current_world = 1
			difficulty_level = 10
		else:
			current_world = 5
			difficulty_level = 10
	_start_new_game(current_world, difficulty_level)

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
	var btn_free_rect = Rect2(cx - 290, cy - 202, 580, 50)
	var btn_chal_rect = Rect2(cx - 290, cy - 146, 580, 50)

	var sound_card_y = cy + 84
	var walk_minus = Rect2(cx - 290 + 120, sound_card_y + 26, 28, 22)
	var walk_plus = Rect2(cx - 290 + 388, sound_card_y + 26, 28, 22)
	var walk_track = Rect2(cx - 290 + 158, sound_card_y + 33, 220, 8)

	var sfx_minus = Rect2(cx - 290 + 120, sound_card_y + 51, 28, 22)
	var sfx_plus = Rect2(cx - 290 + 388, sound_card_y + 51, 28, 22)
	var sfx_track = Rect2(cx - 290 + 158, sound_card_y + 58, 220, 8)

	var bgm_minus = Rect2(cx - 290 + 120, sound_card_y + 76, 28, 22)
	var bgm_plus = Rect2(cx - 290 + 388, sound_card_y + 76, 28, 22)
	var bgm_track = Rect2(cx - 290 + 158, sound_card_y + 83, 220, 8)

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
				for i in range(1, 11):
					var bx = cx - 290 + 190 + (i - 1) * 37
					var b1 = Rect2(bx, cy - 90 + 6, 33, 24)
					if b1.has_point(event.position):
						_start_free_mode_at_level(1, i)
						return
					var b2 = Rect2(bx, cy - 90 + 37, 33, 24)
					if b2.has_point(event.position):
						_start_free_mode_at_level(2, i)
						return
					var b3 = Rect2(bx, cy - 90 + 68, 33, 24)
					if b3.has_point(event.position):
						_start_free_mode_at_level(3, i)
						return
					var b4 = Rect2(bx, cy - 90 + 99, 33, 24)
					if b4.has_point(event.position):
						_start_free_mode_at_level(4, i)
						return
					var b5 = Rect2(bx, cy - 90 + 130, 33, 24)
					if b5.has_point(event.position):
						_start_free_mode_at_level(5, i)
						return
				if btn_free_rect.has_point(event.position):
					_start_free_mode_at_level(1, 1)
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
		elif event.keycode == KEY_C or event.keycode == KEY_Z:
			if not following_player:
				focus_player()
			else:
				fit_to_screen()
			_update_view_btn_text()
			queue_redraw()
		elif event.keycode == KEY_SPACE or event.keycode == KEY_ENTER or event.keycode == KEY_KP_ENTER:
			if won:
				auto_advance_timer = -1.0
				if not (game_mode == "challenge" and challenge_completed):
					_advance_next_level()
				else:
					_start_challenge_mode()
			else:
				if not following_player:
					focus_player()
				else:
					fit_to_screen()
				_update_view_btn_text()
				queue_redraw()
		elif (event.keycode >= KEY_1 and event.keycode <= KEY_9) and game_mode == "free":
			_start_new_game(current_world, event.keycode - KEY_1 + 1)
		elif event.keycode == KEY_0 and game_mode == "free":
			_start_new_game(current_world, 10)
		elif (event.keycode >= KEY_KP_1 and event.keycode <= KEY_KP_9) and game_mode == "free":
			_start_new_game(current_world, event.keycode - KEY_KP_1 + 1)
		elif event.keycode == KEY_KP_0 and game_mode == "free":
			_start_new_game(current_world, 10)
		elif (event.keycode == KEY_EQUAL or event.keycode == KEY_KP_ADD or event.keycode == KEY_PAGEDOWN) and game_mode == "free":
			_advance_next_level()
		elif (event.keycode == KEY_MINUS or event.keycode == KEY_KP_SUBTRACT or event.keycode == KEY_PAGEUP) and game_mode == "free":
			_prev_level()
		elif event.keycode == KEY_R:
			if won:
				auto_advance_timer = -1.0
				if not (game_mode == "challenge" and challenge_completed):
					_advance_next_level()
				else:
					_start_challenge_mode()
			else:
				_start_new_game(current_world, difficulty_level)
		elif event.keycode == KEY_P:
			current_skin_idx = (current_skin_idx + 1) % skin_list.size()
			var skin_key = skin_list[current_skin_idx]
			if player_skins.has(skin_key):
				mochi_textures = player_skins[skin_key]
			queue_redraw()
		elif event.keycode == KEY_H:
			trigger_auto_path()
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
		if event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
			if won:
				auto_advance_timer = -1.0
				if not (game_mode == "challenge" and challenge_completed):
					_advance_next_level()
				else:
					_start_challenge_mode()
				return
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
	if show_auto_path:
		if auto_path_phase == "search":
			var search_speed = max(0.5, float(auto_visited_order.size()) / 200.0)
			auto_search_idx += search_speed
			if auto_search_idx >= auto_visited_order.size():
				auto_search_idx = float(auto_visited_order.size())
				auto_path_phase = "path"
			_update_auto_btn_text()
			queue_redraw()
		elif auto_path_phase == "path":
			var path_speed = max(0.25, float(auto_path.size()) / 100.0)
			auto_path_idx += path_speed
			if auto_path_idx >= auto_path.size():
				auto_path_idx = float(auto_path.size())
				auto_path_phase = "complete"
			_update_auto_btn_text()
			queue_redraw()

	if gate_locked_tip_timer > 0.0:
		gate_locked_tip_timer = maxf(0.0, gate_locked_tip_timer - delta)
		queue_redraw()

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

		# 检查玩家是否踩到支线道具格
		var p_center = player.pixel_position + Vector2(player.size * 0.5, player.size * 0.5)
		var p_tile = Vector2i(int(p_center.x / CELL_SIZE), int(p_center.y / CELL_SIZE))
		var item_idx = item_tiles.find(p_tile)
		if item_idx != -1:
			item_tiles.remove_at(item_idx)
			if audio_item_player != null:
				audio_item_player.play()
			_update_hud()
			queue_redraw()

		# 大灰狼追赶与轨迹追踪逻辑
		if wolf_active:
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
			if item_tiles.is_empty():
				won = true
				if not (game_mode == "challenge" and challenge_completed):
					auto_advance_timer = 1.2
				if wolf_active:
					wolf_crying = true

				if timer_started:
					current_time_sec = (Time.get_ticks_msec() - start_time_msec) / 1000.0

				var rec_key = "%d_%d" % [current_world, difficulty_level]
				var has_prev = best_records.has(rec_key)
				var prev_best = float(best_records.get(rec_key, 999999.0))
				var is_new_record = false

				if not has_prev or current_time_sec < prev_best:
					is_new_record = true
					best_records[rec_key] = current_time_sec

				var base_score = (current_world - 1) * 1000 + difficulty_level * 100
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
					if current_world == 5 and difficulty_level == 10:
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
			else:
				gate_locked_tip_timer = 2.0
				_update_hud()
				queue_redraw()

		if following_player:
			_update_player_focus()

	elif won:
		if not (game_mode == "challenge" and challenge_completed):
			if auto_advance_timer > 0.0:
				auto_advance_timer -= delta
				if auto_advance_timer <= 0.0:
					auto_advance_timer = -1.0
					_advance_next_level()
		if wolf_active:
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

	var stage_idx = (current_world - 1) * 10 + difficulty_level
	if level_label != null:
		var world_tag = "🌉 立交编织" if current_world == 5 else ("🌀 异形几何" if current_world == 4 else ("🌟 图案秘境" if current_world == 3 else ("🏰 狼穴地牢" if current_world == 2 else "🌲 绿野森林")))
		if game_mode == "free":
			level_label.text = "%s (第%d大关 %d阶)" % [world_tag, current_world, difficulty_level]
		else:
			level_label.text = "%s (第%d/50关)" % [world_tag, stage_idx]

	if points_info_label != null:
		var base_pts = (current_world - 1) * 1000 + difficulty_level * 100
		if game_mode == "free":
			points_info_label.text = "通关: +%d分 | 破纪录: +%d分" % [base_pts, base_pts * 2]
		else:
			points_info_label.text = "本阶得分: +%d分 (破纪录加倍)" % base_pts

	for key in sidebar_level_buttons.keys():
		var b = sidebar_level_buttons[key]
		if key == Vector2i(current_world, difficulty_level):
			b.add_theme_color_override("font_color", Color(1, 0.9, 0.3))
		else:
			b.add_theme_color_override("font_color", Color(0.9, 0.9, 0.9))

	if time_label != null:
		var time_str = ("%.2f 秒" % current_time_sec) if timer_started else "按方向键开始"
		if game_mode == "free":
			time_label.text = "当前用时: %s" % time_str
		else:
			time_label.text = "本阶用时: %s" % time_str

	if best_label != null:
		if game_mode == "free":
			var rec_key = "%d_%d" % [current_world, difficulty_level]
			var best_str = ("%.2f 秒" % best_records[rec_key]) if best_records.has(rec_key) else "无纪录"
			best_label.text = "最佳纪录: %s" % best_str
		else:
			best_label.text = "闯关累计用时: %.2f 秒" % challenge_total_time

	if status_label != null:
		if game_mode == "challenge" and challenge_completed:
			status_label.text = "🏆 大满贯全通关！\n1~50关总用时: %.2f 秒\n获得全通总分: +%d 分\n👉 按 R 重测，按 M 返回主菜单" % [challenge_total_time, challenge_total_score]
		elif won:
			var next_str = "第%d大关 %d阶" % [current_world, difficulty_level + 1] if difficulty_level < 10 else ("第2大关 1阶" if current_world == 1 else ("第3大关 1阶" if current_world == 2 else ("第4大关 1阶" if current_world == 3 else ("第5大关 1阶" if current_world == 4 else "第1大关 1阶"))))
			if auto_advance_timer > 0.0:
				status_label.text = "🎉 成功通关！ 获得积分: +%d 分\n👉 %.1fs后自动进入 %s (按空格/点击加速)" % [last_round_score, auto_advance_timer, next_str]
			else:
				status_label.text = "🎉 成功通关！ 获得积分: +%d 分\n👉 按 R / 空格 / 点击进入 %s" % [last_round_score, next_str]
		elif caught_by_wolf:
			status_label.text = "😱 被大灰狼抓住了！\n本局得分: 0 分\n👉 按 R 重新尝试本关"
		else:
			var item_info = WORLD_ITEM_INFO.get(current_world, WORLD_ITEM_INFO[1])
			var rem = item_tiles.size()
			var col = total_items_count - rem
			if rem > 0:
				status_label.text = "🎒 支线: 收集 %s%s (已收集 %d 个，还有 %d 个未收集)\n🔒 大门上锁！需集齐 7 个后方可通关" % [item_info["icon"], item_info["name"], col, rem]
			else:
				status_label.text = "🎒 支线: %s%s 已全部集齐 (已收集 7 个，还有 0 个未收集)\n🔓 出口大门已成功解封，请进屋通关！" % [item_info["icon"], item_info["name"]]

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
							best_records[str(k)] = float(data[k])

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

	var cur_bg = COLOR_BG
	var cur_wall = COLOR_WALL
	var cur_path = COLOR_PATH
	if current_world == 5:
		cur_bg = Color(0.05, 0.06, 0.11)
		cur_wall = Color(0.14, 0.18, 0.25)
		cur_path = Color(0.10, 0.35, 0.43)
	elif current_world == 4:
		cur_bg = Color(0.04, 0.09, 0.13)
		cur_wall = Color(0.10, 0.29, 0.37)
		cur_path = Color(0.14, 0.47, 0.43)
	elif current_world == 3:
		cur_bg = Color(0.07, 0.05, 0.13)
		cur_wall = Color(0.18, 0.12, 0.27)
		cur_path = Color(0.12, 0.31, 0.43)
	elif current_world == 2:
		cur_bg = Color(0.08, 0.04, 0.06)
		cur_wall = Color(0.16, 0.08, 0.12)
		cur_path = Color(0.30, 0.12, 0.16)

	# 背景填充
	draw_rect(Rect2(Vector2.ZERO, win_size), cur_bg)

	# 瓦片绘制范围裁剪
	var min_wx = (0.0 - offset_pos.x) / camera_scale
	var max_wx = (maze_w - offset_pos.x) / camera_scale
	var min_wy = (HUD_HEIGHT - offset_pos.y) / camera_scale
	var max_wy = (win_size.y - offset_pos.y) / camera_scale

	var min_tile_x = max(0, int(min_wx / CELL_SIZE))
	var max_tile_x = min(maze_data.cols - 1, int(max_wx / CELL_SIZE))
	var min_tile_y = max(0, int(min_wy / CELL_SIZE))
	var max_tile_y = min(maze_data.rows - 1, int(max_wy / CELL_SIZE))

	# 判断 Player 与 Wolf 是否处于东西或南北地下隧道穿梭状态 (在桥下方)
	var p_center = player.pixel_position + Vector2(player.size / 2.0, player.size / 2.0) if player != null else Vector2.ZERO
	var p_tx = int(p_center.x / CELL_SIZE)
	var p_ty = int(p_center.y / CELL_SIZE)
	var p_in_tunnel = false
	if player != null and p_tx >= 0 and p_tx < maze_data.cols and p_ty >= 0 and p_ty < maze_data.rows:
		var cur_t = maze_data.grid[p_ty][p_tx]
		if cur_t == MazeGenerator.OVERPASS_NS and player.overpass_layer == "ew_tunnel":
			p_in_tunnel = true
		elif cur_t == MazeGenerator.OVERPASS_EW and player.overpass_layer == "ns_tunnel":
			p_in_tunnel = true

	var w_tx = int(wolf_pos.x / CELL_SIZE) if wolf_active else -1
	var w_ty = int(wolf_pos.y / CELL_SIZE) if wolf_active else -1
	var w_in_tunnel = false

	for y in range(min_tile_y, max_tile_y + 1):
		for x in range(min_tile_x, max_tile_x + 1):
			var tile = maze_data.grid[y][x]
			var p1 = offset_pos + Vector2(x * CELL_SIZE, y * CELL_SIZE) * camera_scale
			var p2 = offset_pos + Vector2((x + 1) * CELL_SIZE, (y + 1) * CELL_SIZE) * camera_scale
			var rect = Rect2(p1, p2 - p1)

			if tile == MazeGenerator.WALL:
				draw_rect(rect, cur_wall)
			elif tile == MazeGenerator.PATH:
				var color = cur_path
				var is_pat = (maze_data.pattern_cells.has(Vector2i(x, y)))
				var is_shp = (current_world == 4 and maze_data.shape_cells.has(Vector2i(x, y)))
				if is_pat:
					color = Color(0.51, 0.18, 0.43) if current_world == 5 else Color(0.37, 0.18, 0.49)
				elif is_shp:
					color = Color(0.12, 0.35, 0.43)
				draw_rect(rect, color)

				# 3D 坡道起伏引桥渲染
				if y + 1 < maze_data.rows and (maze_data.grid[y + 1][x] == MazeGenerator.OVERPASS_NS or maze_data.grid[y + 1][x] == MazeGenerator.OVERPASS_EW):
					_draw_ramp_slope(rect, camera_scale, "south")
				elif y - 1 >= 0 and (maze_data.grid[y - 1][x] == MazeGenerator.OVERPASS_NS or maze_data.grid[y - 1][x] == MazeGenerator.OVERPASS_EW):
					_draw_ramp_slope(rect, camera_scale, "north")

				if is_pat and rect.size.x >= 4.0:
					draw_rect(rect, Color(0.86, 0.63, 1.0), false, 1.0)
				elif is_shp and rect.size.x >= 4.0:
					draw_rect(rect, Color(0.58, 0.94, 1.0), false, 1.0)

				# 绘制待收集过关支线道具
				if item_tiles.has(Vector2i(x, y)):
					_draw_item_icon(rect, current_world, camera_scale)

			elif tile == MazeGenerator.OVERPASS_NS:
				_draw_overpass_underpass(rect, camera_scale, cur_path, cur_wall)
				if p_in_tunnel and x == p_tx and y == p_ty:
					_draw_player()
				if w_in_tunnel and x == w_tx and y == w_ty:
					_draw_wolf()
				_draw_overpass_bridge_deck(rect, camera_scale, cur_wall)

			elif tile == MazeGenerator.OVERPASS_EW:
				_draw_overpass_ew_underpass(rect, camera_scale, cur_path, cur_wall)
				if p_in_tunnel and x == p_tx and y == p_ty:
					_draw_player()
				if w_in_tunnel and x == w_tx and y == w_ty:
					_draw_wolf()
				_draw_overpass_ew_bridge_deck(rect, camera_scale, cur_wall)

	# 入口与出口绘制 (起点大树，终点小房子)
	_draw_tile_marker(maze_data.entrance, COLOR_ENTRANCE, "tree")
	_draw_tile_marker(maze_data.exit_tile, COLOR_EXIT, "house")

	# 自动寻路动画绘制 (DFS 单线探索与通关路线生成)
	if show_auto_path:
		var search_idx_int = int(auto_search_idx)
		var path_idx_int = int(auto_path_idx)

		# 1. 深度优先单线探索演示
		if auto_visited_order.size() > 0 and search_idx_int > 0:
			var limit = min(search_idx_int, auto_visited_order.size())

			# A) 绘制历史试错痕迹 (深灰蓝/暗蓝色方块)
			for i in range(limit):
				var tile = auto_visited_order[i]
				var p1 = offset_pos + Vector2(tile.x * CELL_SIZE, tile.y * CELL_SIZE) * camera_scale
				var p2 = offset_pos + Vector2((tile.x + 1) * CELL_SIZE, (tile.y + 1) * CELL_SIZE) * camera_scale
				var rect = Rect2(p1, p2 - p1)
				draw_rect(rect, Color(0.12, 0.22, 0.35, 0.8))

			# B) 绘制当前唯一正在尝试的单线通路 (亮青色单轨，绝无分叉)
			if auto_path_phase == "search" and not auto_parent_map.is_empty():
				var curr_node = auto_visited_order[min(search_idx_int - 1, auto_visited_order.size() - 1)]
				var active_trail: Array[Vector2i] = []
				var node = curr_node
				while node != Vector2i(-1, -1) and auto_parent_map.has(node):
					active_trail.append(node)
					node = auto_parent_map[node]
				active_trail.reverse()

				var trail_pts: PackedVector2Array = []
				for tile in active_trail:
					var center_w = Vector2(tile.x + 0.5, tile.y + 0.5) * CELL_SIZE
					var screen_p = offset_pos + center_w * camera_scale
					trail_pts.append(screen_p)

				if trail_pts.size() >= 2:
					var glow_w = max(3.0, camera_scale * 8.0)
					var core_w = max(1.0, camera_scale * 3.0)
					draw_polyline(trail_pts, Color(0.0, 0.90, 1.0, 0.9), glow_w)
					draw_polyline(trail_pts, Color(0.9, 1.0, 1.0, 1.0), core_w)

				if trail_pts.size() > 0:
					var tip_p = trail_pts[-1]
					draw_circle(tip_p, max(4.0, camera_scale * 7.0), Color(0.0, 1.0, 0.7))

		# 2. 找到终点后，绘制从起点延伸至终点的最终最优路径 (金黄色光轨)
		if auto_path.size() > 0 and path_idx_int > 0 and (auto_path_phase == "path" or auto_path_phase == "complete"):
			var pts: PackedVector2Array = []
			var limit = min(path_idx_int, auto_path.size())
			for i in range(limit):
				var tile = auto_path[i]
				var center_w = Vector2(tile.x + 0.5, tile.y + 0.5) * CELL_SIZE
				var screen_p = offset_pos + center_w * camera_scale
				pts.append(screen_p)

			if pts.size() >= 2:
				if current_world == 5:
					var glow_w = maxf(5.0, camera_scale * 10.0)
					var core_w = maxf(3.0, camera_scale * 5.0)
					draw_polyline(pts, Color(0.55, 0.06, 0.06, 1.0), glow_w)
					draw_polyline(pts, Color(0.90, 0.16, 0.16, 1.0), core_w)
					var r_dot = maxf(2.0, camera_scale * 3.5)
					for p in pts:
						draw_circle(p, r_dot, Color(0.90, 0.16, 0.16))
				else:
					var glow_w = max(3.0, camera_scale * 8.0)
					var core_w = max(1.0, camera_scale * 3.0)
					draw_polyline(pts, Color(1.0, 0.78, 0.20, 0.9), glow_w)
					draw_polyline(pts, Color(1.0, 1.0, 0.85, 1.0), core_w)
					var r_dot = max(2.0, camera_scale * 3.0)
					for p in pts:
						draw_circle(p, r_dot, Color(1.0, 0.88, 0.35))

			if auto_path_phase == "path" and pts.size() > 0:
				var tip_p = pts[-1]
				draw_circle(tip_p, max(4.0, camera_scale * 7.0), Color(1.0, 1.0, 0.47))

	# 绘制萌系 Q 版小人与大灰狼 (若不在地下隧道穿梭状态，在最上层绘制)
	if not p_in_tunnel:
		_draw_player()
	if not w_in_tunnel:
		_draw_wolf()

	# 绘制微缩小地图 (在地图放大跟随模式下显示于左侧)
	_draw_minimap()

	# HUD 顶栏背景
	draw_rect(Rect2(0, 0, maze_w, HUD_HEIGHT), COLOR_HUD_BG)

	# 绘制尝试未集齐进门时的醒目警告横幅
	if gate_locked_tip_timer > 0.0 and not item_tiles.is_empty():
		var font_default = ThemeDB.fallback_font
		if font_default != null:
			var item_info = WORLD_ITEM_INFO[current_world]
			var rem = item_tiles.size()
			var col = total_items_count - rem
			var tip_str = "🔒 大门未开启！需集齐 7 个 %s%s (已收集 %d 个，还有 %d 个未收集)" % [item_info["icon"], item_info["name"], col, rem]
			var txt_sz = font_default.get_string_size(tip_str, HORIZONTAL_ALIGNMENT_CENTER, -1, 15)
			var bg_w = txt_sz.x + 28.0
			var bg_h = 32.0
			var bg_rect = Rect2((maze_w - bg_w) * 0.5, HUD_HEIGHT + 10.0, bg_w, bg_h)
			draw_rect(bg_rect, Color(0.63, 0.08, 0.14, 0.95))
			draw_rect(bg_rect, Color(1.0, 0.84, 0.0), false, 2.0)
			draw_string(font_default, Vector2((maze_w - txt_sz.x) * 0.5, HUD_HEIGHT + 31.0), tip_str, HORIZONTAL_ALIGNMENT_CENTER, -1, 15, Color(1.0, 0.92, 0.45))

func _draw_minimap() -> void:
	if not following_player or maze_data == null:
		return

	var win_size = get_viewport_rect().size
	var maze_w = maxf(1.0, win_size.x - SIDEBAR_WIDTH)
	var avail_h = maxf(1.0, win_size.y - HUD_HEIGHT)

	var max_mm_w = 160.0
	var max_mm_h = 160.0
	var mm_x = 16.0
	var mm_y = HUD_HEIGHT + 16.0

	var scale_w = max_mm_w / (maze_data.cols * CELL_SIZE)
	var scale_h = max_mm_h / (maze_data.rows * CELL_SIZE)
	var mm_scale = minf(scale_w, scale_h)

	var mm_w = maxf(70.0, maze_data.cols * CELL_SIZE * mm_scale)
	var mm_h = maxf(70.0, maze_data.rows * CELL_SIZE * mm_scale)

	var box_w = mm_w + 12.0
	var box_h = mm_h + 26.0
	var box_rect = Rect2(mm_x, mm_y, box_w, box_h)

	# 1. 绘制半透明精致深色框底背板
	draw_rect(box_rect, Color(0.05, 0.07, 0.12, 0.85))
	draw_rect(box_rect, Color(0.24, 0.55, 0.78, 0.9), false, 2.0)

	# 2. 标头说明文字
	var font_default = ThemeDB.fallback_font
	if font_default != null:
		draw_string(font_default, Vector2(mm_x + 8.0, mm_y + 16.0), "📍 小地图 (C/Space还原)", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0.8, 0.9, 1.0))

	var map_start_x = mm_x + 6.0
	var map_start_y = mm_y + 20.0

	var cw = mm_w / float(maze_data.cols)
	var ch = mm_h / float(maze_data.rows)

	# 3. 绘制迷宫网格
	for y in range(maze_data.rows):
		var row = maze_data.grid[y]
		for x in range(maze_data.cols):
			var tile = row[x]
			var tx = map_start_x + float(x) * cw
			var ty = map_start_y + float(y) * ch
			var t_rect = Rect2(tx, ty, maxf(1.0, cw), maxf(1.0, ch))
			if tile == MazeGenerator.WALL:
				draw_rect(t_rect, Color(0.11, 0.15, 0.22))
			elif tile == MazeGenerator.OVERPASS_NS or tile == MazeGenerator.OVERPASS_EW:
				draw_rect(t_rect, Color(0.31, 0.43, 0.63))
			else:
				draw_rect(t_rect, Color(0.18, 0.31, 0.39))

	# 起点 & 终点
	var ent_x = map_start_x + (float(maze_data.entrance.x) + 0.5) * cw
	var ent_y = map_start_y + (float(maze_data.entrance.y) + 0.5) * ch
	draw_circle(Vector2(ent_x, ent_y), maxf(2.0, minf(cw, ch) * 1.2), Color(0.16, 0.86, 0.39))

	var exit_x = map_start_x + (float(maze_data.exit_tile.x) + 0.5) * cw
	var exit_y = map_start_y + (float(maze_data.exit_tile.y) + 0.5) * ch
	draw_circle(Vector2(exit_x, exit_y), maxf(2.0, minf(cw, ch) * 1.2), Color(1.0, 0.24, 0.24))

	# 待收集支线道具在小地图上的发光标记点
	if not item_tiles.is_empty():
		var item_color = Color(1.0, 0.31, 0.31) if current_world == 1 else (Color(1.0, 0.47, 0.55) if current_world == 2 else (Color(1.0, 0.84, 0.0) if current_world == 3 else (Color(0.0, 0.90, 1.0) if current_world == 4 else Color(1.0, 0.16, 0.78))))
		for it in item_tiles:
			var it_x = map_start_x + (float(it.x) + 0.5) * cw
			var it_y = map_start_y + (float(it.y) + 0.5) * ch
			draw_circle(Vector2(it_x, it_y), maxf(2.0, minf(cw, ch) * 1.3), item_color)

	# 自动寻路线
	if show_auto_path and auto_path.size() > 0 and int(auto_path_idx) > 0:
		var ap_pts: PackedVector2Array = []
		var limit = min(int(auto_path_idx), auto_path.size())
		for i in range(limit):
			var tile = auto_path[i]
			var ap_x = map_start_x + (float(tile.x) + 0.5) * cw
			var ap_y = map_start_y + (float(tile.y) + 0.5) * ch
			ap_pts.append(Vector2(ap_x, ap_y))
		if ap_pts.size() >= 2:
			draw_polyline(ap_pts, Color(1.0, 0.84, 0.0), maxf(1.0, minf(cw, ch)))

	# 追赶的大灰狼
	if wolf_active:
		var wx_cell = wolf_pos.x / CELL_SIZE
		var wy_cell = wolf_pos.y / CELL_SIZE
		var w_x = map_start_x + wx_cell * cw
		var w_y = map_start_y + wy_cell * ch
		draw_circle(Vector2(w_x, w_y), maxf(3.0, minf(cw, ch) * 1.5), Color(1.0, 0.2, 0.31))

	# 玩家位置
	if player != null:
		var p_center = player.pixel_position + Vector2(player.size / 2.0, player.size / 2.0)
		var px_cell = p_center.x / CELL_SIZE
		var py_cell = p_center.y / CELL_SIZE
		var p_x = map_start_x + px_cell * cw
		var p_y = map_start_y + py_cell * ch
		var p_r = maxf(3.0, minf(cw, ch) * 1.8)
		draw_circle(Vector2(p_x, p_y), p_r, Color(0.0, 1.0, 1.0))
		draw_circle(Vector2(p_x, p_y), maxf(1.0, p_r - 2.0), Color(1.0, 1.0, 1.0))

	# 4. 当前镜头视口框
	var min_wx = maxf(0.0, (0.0 - offset_pos.x) / camera_scale)
	var max_wx = minf(maze_data.cols * CELL_SIZE, (maze_w - offset_pos.x) / camera_scale)
	var min_wy = maxf(0.0, (HUD_HEIGHT - offset_pos.y) / camera_scale)
	var max_wy = minf(maze_data.rows * CELL_SIZE, (HUD_HEIGHT + avail_h - offset_pos.y) / camera_scale)

	var vx1 = map_start_x + (min_wx / CELL_SIZE) * cw
	var vy1 = map_start_y + (min_wy / CELL_SIZE) * ch
	var vx2 = map_start_x + (max_wx / CELL_SIZE) * cw
	var vy2 = map_start_y + (max_wy / CELL_SIZE) * ch

	var v_rect = Rect2(Vector2(vx1, vy1), Vector2(maxf(4.0, vx2 - vx1), maxf(4.0, vy2 - vy1)))
	draw_rect(v_rect, Color(1.0, 0.90, 0.39, 0.9), false, 1.0)

func _draw_main_menu(win_size: Vector2) -> void:
	draw_rect(Rect2(Vector2.ZERO, win_size), Color(0.05, 0.06, 0.10))
	var cx = win_size.x / 2.0
	var cy = win_size.y / 2.0

	var font_default = ThemeDB.fallback_font
	if font_default == null:
		return

	# 1. 标题与副标题
	draw_string(font_default, Vector2(cx - 180, cy - 255), "🎮 小红帽迷宫大冒险", HORIZONTAL_ALIGNMENT_CENTER, -1, 32, Color(1, 0.88, 0.35))
	draw_string(font_default, Vector2(cx - 180, cy - 222), "—— 请选择游戏模式 & 调整声音设置 ——", HORIZONTAL_ALIGNMENT_CENTER, -1, 16, Color(0.67, 0.75, 0.85))

	var card_w = 580.0

	# 2. 模式 1：自由模式 (Free Mode)
	var btn1_rect = Rect2(cx - card_w / 2.0, cy - 202, card_w, 50)
	draw_rect(btn1_rect, Color(0.09, 0.13, 0.20))
	draw_rect(btn1_rect, Color(0.39, 0.70, 1.0), false, 1.5)

	draw_string(font_default, Vector2(btn1_rect.position.x + 18, btn1_rect.position.y + 22), "🌟 1. 自由模式 (Free Mode)", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color(1, 0.94, 0.6))
	draw_string(font_default, Vector2(btn1_rect.position.x + 18, btn1_rect.position.y + 42), "按 [1] 键或点击 | 1~10 阶自由切换，无限切关与随心练习", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(0.63, 0.71, 0.80))

	# 3. 模式 2：闯关模式 (Challenge Mode)
	var btn2_rect = Rect2(cx - card_w / 2.0, cy - 146, card_w, 50)
	draw_rect(btn2_rect, Color(0.09, 0.13, 0.20))
	draw_rect(btn2_rect, Color(1.0, 0.82, 0.35), false, 1.5)

	draw_string(font_default, Vector2(btn2_rect.position.x + 18, btn2_rect.position.y + 22), "🏆 2. 闯关模式 (Challenge Mode)", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color(1, 0.86, 0.35))
	draw_string(font_default, Vector2(btn2_rect.position.x + 18, btn2_rect.position.y + 42), "按 [2] 键或点击 | 森林 + 地牢 + 秘境 + 异形 + 立交 共 50 关连续大满贯", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(0.63, 0.71, 0.80))

	# 4. 调试/自由选关卡片 (五大关 50 阶)
	var lvl_card = Rect2(cx - card_w / 2.0, cy - 90, card_w, 166)
	draw_rect(lvl_card, Color(0.09, 0.13, 0.20))
	draw_rect(lvl_card, Color(0.24, 0.35, 0.55), false, 1.0)

	# 第一大关
	draw_string(font_default, Vector2(lvl_card.position.x + 16, lvl_card.position.y + 22), "🌲 第一大关 (绿野森林):", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0.5, 0.9, 0.6))
	for i in range(1, 11):
		var bx = lvl_card.position.x + 190 + (i - 1) * 37
		var by = lvl_card.position.y + 6
		var brect = Rect2(bx, by, 33, 24)
		draw_rect(brect, Color(0.11, 0.27, 0.18))
		draw_rect(brect, Color(0.39, 0.82, 0.51), false, 1.0)
		draw_string(font_default, Vector2(bx + 11, by + 16), str(i), HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(1, 1, 1))

	# 第二大关
	draw_string(font_default, Vector2(lvl_card.position.x + 16, lvl_card.position.y + 53), "🏰 第二大关 (狼穴地牢):", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(1.0, 0.5, 0.5))
	for i in range(1, 11):
		var bx = lvl_card.position.x + 190 + (i - 1) * 37
		var by = lvl_card.position.y + 37
		var brect = Rect2(bx, by, 33, 24)
		draw_rect(brect, Color(0.33, 0.11, 0.17))
		draw_rect(brect, Color(1.0, 0.43, 0.51), false, 1.0)
		draw_string(font_default, Vector2(bx + 11, by + 16), str(i), HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(1, 1, 1))

	# 第三大关
	draw_string(font_default, Vector2(lvl_card.position.x + 16, lvl_card.position.y + 84), "🌟 第三大关 (图案秘境):", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0.82, 0.55, 1.0))
	for i in range(1, 11):
		var bx = lvl_card.position.x + 190 + (i - 1) * 37
		var by = lvl_card.position.y + 68
		var brect = Rect2(bx, by, 33, 24)
		draw_rect(brect, Color(0.28, 0.11, 0.37))
		draw_rect(brect, Color(0.82, 0.55, 1.0), false, 1.0)
		draw_string(font_default, Vector2(bx + 11, by + 16), str(i), HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(1, 1, 1))

	# 第四大关
	draw_string(font_default, Vector2(lvl_card.position.x + 16, lvl_card.position.y + 115), "🌀 第四大关 (异形几何):", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0.39, 0.90, 0.86))
	for i in range(1, 11):
		var bx = lvl_card.position.x + 190 + (i - 1) * 37
		var by = lvl_card.position.y + 99
		var brect = Rect2(bx, by, 33, 24)
		draw_rect(brect, Color(0.11, 0.31, 0.31))
		draw_rect(brect, Color(0.39, 0.90, 0.86), false, 1.0)
		draw_string(font_default, Vector2(bx + 11, by + 16), str(i), HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(1, 1, 1))

	# 第五大关
	draw_string(font_default, Vector2(lvl_card.position.x + 16, lvl_card.position.y + 146), "🌉 第五大关 (立交编织):", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0.47, 0.86, 1.0))
	for i in range(1, 11):
		var bx = lvl_card.position.x + 190 + (i - 1) * 37
		var by = lvl_card.position.y + 130
		var brect = Rect2(bx, by, 33, 24)
		draw_rect(brect, Color(0.11, 0.25, 0.38))
		draw_rect(brect, Color(0.47, 0.86, 1.0), false, 1.0)
		draw_string(font_default, Vector2(bx + 11, by + 16), str(i), HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(1, 1, 1))

	# 5. 卡片 4：🎵 声音大小设置 (Sound Settings)
	var sound_card = Rect2(cx - card_w / 2.0, cy + 84, card_w, 110)
	draw_rect(sound_card, Color(0.09, 0.13, 0.20))
	draw_rect(sound_card, Color(0.24, 0.35, 0.55), false, 1.0)

	draw_string(font_default, Vector2(sound_card.position.x + 16, sound_card.position.y + 20), "🎵 声音大小设置", HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color(1, 0.86, 0.35))

	var _draw_vol_row = func(label: String, y_pos: float, vol: float):
		draw_string(font_default, Vector2(sound_card.position.x + 16, y_pos + 15), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(0.86, 0.90, 0.96))

		var bm = Rect2(sound_card.position.x + 120, y_pos, 28, 22)
		draw_rect(bm, Color(0.18, 0.26, 0.38))
		draw_rect(bm, Color(0.39, 0.55, 0.75), false, 1.0)
		draw_string(font_default, Vector2(bm.position.x + 10, bm.position.y + 16), "-", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color(1, 1, 1))

		var track = Rect2(sound_card.position.x + 158, y_pos + 7, 220, 8)
		draw_rect(track, Color(0.16, 0.20, 0.29))
		var fill_w = vol * track.size.x
		if fill_w > 0:
			draw_rect(Rect2(track.position, Vector2(fill_w, track.size.y)), Color(0.39, 0.75, 1.0))
		draw_circle(Vector2(track.position.x + fill_w, track.position.y + 4), 6.0, Color(1.0, 0.92, 0.55))

		var bp = Rect2(sound_card.position.x + 388, y_pos, 28, 22)
		draw_rect(bp, Color(0.18, 0.26, 0.38))
		draw_rect(bp, Color(0.39, 0.55, 0.75), false, 1.0)
		draw_string(font_default, Vector2(bp.position.x + 8, bp.position.y + 16), "+", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color(1, 1, 1))

		draw_string(font_default, Vector2(sound_card.position.x + 428, y_pos + 16), "%d%%" % int(round(vol * 100.0)), HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(1.0, 0.92, 0.59))

	_draw_vol_row.call("🚶 走路音效", sound_card.position.y + 26, vol_walk)
	_draw_vol_row.call("🔔 提示音效", sound_card.position.y + 51, vol_sfx)
	_draw_vol_row.call("🎵 背景音乐", sound_card.position.y + 76, vol_bgm)

	# 6. 排行榜纪录卡片
	var card_rect = Rect2(cx - card_w / 2.0, cy + 202, card_w, 66)
	draw_rect(card_rect, Color(0.07, 0.10, 0.16))
	draw_rect(card_rect, Color(0.16, 0.23, 0.35), false, 1.0)

	draw_string(font_default, Vector2(card_rect.position.x + 16, card_rect.position.y + 20), "📊 荣耀排行榜纪录", HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color(1, 0.84, 0.31))
	draw_string(font_default, Vector2(card_rect.position.x + 16, card_rect.position.y + 40), "累计总得分: %d 分" % total_score, HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(0.78, 0.88, 0.96))

	var c_time_str = "%.2f 秒" % challenge_best_time if challenge_best_time >= 0.0 else "暂无纪录"
	var c_score_str = "%d 分" % challenge_best_score if challenge_best_score > 0 else "暂无纪录"
	draw_string(font_default, Vector2(card_rect.position.x + 16, card_rect.position.y + 58), "闯关模式最佳全通: %s | 最高得分: %s" % [c_time_str, c_score_str], HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(0.71, 0.82, 1.0))

	# 7. 提示
	draw_string(font_default, Vector2(cx - 210, win_size.y - 22), "👉 点击模式或调音按钮 | 按 [1]/[2] 启动模式 | 按 [ESC] 退出程序", HORIZONTAL_ALIGNMENT_CENTER, -1, 13, Color(0.51, 0.59, 0.69))

func _draw_item_icon(rect: Rect2, world: int, scale: float) -> void:
	var w = rect.size.x
	var h = rect.size.y
	if w < 4.0 or h < 4.0:
		return
	var cx = rect.position.x + w * 0.5
	var cy = rect.position.y + h * 0.5

	if world == 1:
		var stem_w = maxf(2.0, w * 0.22)
		var stem_h = maxf(3.0, h * 0.35)
		var stem_rect = Rect2(cx - stem_w * 0.5, cy + h * 0.05, stem_w, stem_h)
		draw_rect(stem_rect, Color(0.94, 0.90, 0.82))

		var cap_r = maxf(4.0, w * 0.38)
		draw_circle(Vector2(cx, cy - h * 0.05), cap_r, Color(0.88, 0.18, 0.18))

		var dot_r = maxf(1.0, cap_r * 0.28)
		draw_circle(Vector2(cx - cap_r * 0.4, cy - h * 0.12), dot_r, Color(1, 1, 1))
		draw_circle(Vector2(cx + cap_r * 0.35, cy - h * 0.08), dot_r, Color(1, 1, 1))
		draw_circle(Vector2(cx, cy - h * 0.25), dot_r, Color(1, 1, 1))

	elif world == 2:
		var bone_w = maxf(3.0, w * 0.52)
		var bone_h = maxf(2.0, h * 0.18)
		draw_line(Vector2(cx - bone_w * 0.5, cy - h * 0.1), Vector2(cx + bone_w * 0.5, cy + h * 0.1), Color(0.94, 0.92, 0.86), bone_h)
		draw_circle(Vector2(cx - bone_w * 0.5, cy - h * 0.1), maxf(2.0, bone_h), Color(0.94, 0.92, 0.86))
		draw_circle(Vector2(cx + bone_w * 0.5, cy + h * 0.1), maxf(2.0, bone_h), Color(0.94, 0.92, 0.86))

		var meat_r = maxf(4.0, w * 0.32)
		draw_circle(Vector2(cx - w * 0.05, cy), meat_r, Color(0.70, 0.16, 0.20))
		draw_circle(Vector2(cx - w * 0.05, cy), maxf(2.0, meat_r * 0.5), Color(0.86, 0.35, 0.39))

	elif world == 3:
		var key_r = maxf(3.0, w * 0.22)
		var key_x = cx - w * 0.15
		var key_y = cy - h * 0.12
		draw_circle(Vector2(key_x, key_y), key_r, Color(1.0, 0.84, 0.0), false, maxf(1.0, key_r * 0.4))

		var stem_len = maxf(5.0, w * 0.42)
		draw_line(Vector2(key_x, key_y), Vector2(key_x + stem_len, key_y + stem_len), Color(1.0, 0.84, 0.0), maxf(2.0, scale * 2.2))
		var tx = key_x + stem_len * 0.7
		var ty = key_y + stem_len * 0.7
		draw_line(Vector2(tx, ty), Vector2(tx + w * 0.15, ty - h * 0.15), Color(1.0, 0.84, 0.0), maxf(2.0, scale * 1.8))

	elif world == 4:
		var pts = PackedVector2Array([
			Vector2(cx, cy - h * 0.38),
			Vector2(cx + w * 0.32, cy - h * 0.05),
			Vector2(cx, cy + h * 0.38),
			Vector2(cx - w * 0.32, cy - h * 0.05)
		])
		draw_colored_polygon(pts, Color(0.0, 0.86, 1.0))
		draw_polyline(pts, Color(0.78, 0.98, 1.0), 1.0)
		draw_line(Vector2(cx, cy - h * 0.38), Vector2(cx, cy + h * 0.38), Color(1, 1, 1), 1.0)

	elif world == 5:
		var r_outer = maxf(4.0, w * 0.36)
		draw_circle(Vector2(cx, cy), r_outer, Color(1.0, 0.16, 0.63), false, maxf(1.0, scale * 2.0))
		draw_circle(Vector2(cx, cy), maxf(3.0, r_outer * 0.65), Color(0.0, 0.94, 1.0))
		draw_circle(Vector2(cx, cy), maxf(1.0, r_outer * 0.3), Color(1.0, 1.0, 0.86))

func _draw_tile_marker(tile: Vector2i, color: Color, type: String) -> void:
	var p1 = offset_pos + Vector2(tile.x * CELL_SIZE, tile.y * CELL_SIZE) * camera_scale
	var p2 = offset_pos + Vector2((tile.x + 1) * CELL_SIZE, (tile.y + 1) * CELL_SIZE) * camera_scale
	var rect = Rect2(p1, p2 - p1)
	var is_locked = (type == "house" and not item_tiles.is_empty())
	var tile_color = Color(0.48, 0.16, 0.20) if is_locked else color
	draw_rect(rect, tile_color)

	if type == "house":
		var border_c = Color(0.88, 0.18, 0.22) if is_locked else Color(0.30, 0.95, 0.45)
		draw_rect(rect, border_c, false, max(1.0, camera_scale * 2.2))
	elif type == "tree":
		draw_rect(rect, Color(0.40, 0.90, 0.40), false, max(1.0, camera_scale * 1.8))
	elif type == "flag":
		draw_rect(rect, Color(1.0, 0.90, 0.20), false, max(1.0, camera_scale * 1.8))

	if rect.size.x >= 6.0:
		if type == "house":
			_draw_mini_house(rect)
			var font_default = ThemeDB.fallback_font
			if font_default != null and rect.size.x >= 10.0:
				var lock_str = "🔒" if is_locked else "🔓"
				var f_sz = max(9, int(rect.size.x * 0.35))
				draw_string(font_default, Vector2(rect.position.x + rect.size.x * 0.1, rect.position.y + rect.size.y * 0.35), lock_str, HORIZONTAL_ALIGNMENT_CENTER, -1, f_sz, Color(1, 1, 1))
		elif type == "tree":
			_draw_mini_tree(rect)
		elif type == "flag":
			_draw_mini_flag(rect)

func _draw_ramp_slope(rect: Rect2, scale: float, direction: String) -> void:
	if rect.size.x < 6.0 or rect.size.y < 6.0:
		return
	var bw = maxf(4.0, rect.size.x * 0.68)
	var bx = rect.position.x + (rect.size.x - bw) / 2.0
	var h_steps = int(rect.size.y)
	for i in range(h_steps):
		var factor = float(i) / maxf(1.0, float(h_steps)) if direction == "south" else float(h_steps - 1 - i) / maxf(1.0, float(h_steps))
		var r = 0.10 + factor * 0.15
		var g = 0.35 + factor * 0.22
		var b = 0.43 + factor * 0.30
		draw_line(Vector2(bx, rect.position.y + i), Vector2(bx + bw, rect.position.y + i), Color(r, g, b), 1.0)
	var rail_w = maxf(1.0, scale * 1.5)
	draw_line(Vector2(bx, rect.position.y), Vector2(bx, rect.position.y + rect.size.y), Color(0.39, 0.78, 0.94), rail_w)
	draw_line(Vector2(bx + bw, rect.position.y), Vector2(bx + bw, rect.position.y + rect.size.y), Color(0.39, 0.78, 0.94), rail_w)

func _draw_overpass_underpass(rect: Rect2, scale: float, cur_path: Color, cur_wall: Color) -> void:
	# 1. 地下隧道底色
	var tunnel_bg = Color(maxf(0.0, cur_path.r - 0.04), maxf(0.0, cur_path.g - 0.08), maxf(0.0, cur_path.b - 0.10))
	draw_rect(rect, tunnel_bg)

	# 2. 上下洞口混凝土墙线
	var line_w = maxf(1.0, scale * 1.5)
	draw_line(rect.position, Vector2(rect.position.x + rect.size.x, rect.position.y), cur_wall, line_w)
	draw_line(Vector2(rect.position.x, rect.position.y + rect.size.y - 1.0), rect.position + rect.size, cur_wall, line_w)

	# 3. 隧道内部暗光阴影
	draw_rect(rect, Color(0.01, 0.02, 0.05, 0.40))

func _draw_overpass_bridge_deck(rect: Rect2, scale: float, cur_wall: Color) -> void:
	var bw = maxf(4.0, rect.size.x * 0.70)
	var bx = rect.position.x + (rect.size.x - bw) / 2.0

	# 1. 3D 投射阴影
	var shadow_off_x = maxf(2.0, scale * 3.5)
	var shadow_off_y = maxf(1.0, scale * 2.0)
	var shadow_rect = Rect2(Vector2(bx + shadow_off_x, rect.position.y + shadow_off_y), Vector2(bw, rect.size.y))
	draw_rect(shadow_rect, Color(0.01, 0.02, 0.05, 0.55))

	# 2. 南北高架桥纯净路面
	var bridge_deck = Rect2(Vector2(bx, rect.position.y), Vector2(bw, rect.size.y))
	draw_rect(bridge_deck, Color(0.96, 0.97, 1.0))

	# 3. 左右 3D 黑色桥壁框线
	var line_w = maxf(1.0, scale * 1.5)
	draw_line(Vector2(bx, rect.position.y), Vector2(bx, rect.position.y + rect.size.y), cur_wall, line_w)
	draw_line(Vector2(bx + bw - 1.0, rect.position.y), Vector2(bx + bw - 1.0, rect.position.y + rect.size.y), cur_wall, line_w)

	# 4. 桥内两侧红线护栏
	if rect.size.x >= 8.0:
		draw_line(Vector2(bx + 2.0, rect.position.y), Vector2(bx + 2.0, rect.position.y + rect.size.y), Color(0.86, 0.16, 0.16), 1.0)
		draw_line(Vector2(bx + bw - 3.0, rect.position.y), Vector2(bx + bw - 3.0, rect.position.y + rect.size.y), Color(0.86, 0.16, 0.16), 1.0)

func _draw_overpass_ew_underpass(rect: Rect2, scale: float, cur_path: Color, cur_wall: Color) -> void:
	var tunnel_bg = Color(maxf(0.0, cur_path.r - 0.04), maxf(0.0, cur_path.g - 0.08), maxf(0.0, cur_path.b - 0.10))
	draw_rect(rect, tunnel_bg)

	var line_w = maxf(1.0, scale * 1.5)
	draw_line(rect.position, Vector2(rect.position.x, rect.position.y + rect.size.y), cur_wall, line_w)
	draw_line(Vector2(rect.position.x + rect.size.x - 1.0, rect.position.y), Vector2(rect.position.x + rect.size.x - 1.0, rect.position.y + rect.size.y), cur_wall, line_w)

	draw_rect(rect, Color(0.01, 0.02, 0.05, 0.40))

func _draw_overpass_ew_bridge_deck(rect: Rect2, scale: float, cur_wall: Color) -> void:
	var bh = maxf(4.0, rect.size.y * 0.70)
	var by = rect.position.y + (rect.size.y - bh) / 2.0

	var shadow_off_x = maxf(2.0, scale * 3.5)
	var shadow_off_y = maxf(1.0, scale * 2.0)
	var shadow_rect = Rect2(Vector2(rect.position.x + shadow_off_x, by + shadow_off_y), Vector2(rect.size.x, bh))
	draw_rect(shadow_rect, Color(0.01, 0.02, 0.05, 0.55))

	var bridge_deck = Rect2(Vector2(rect.position.x, by), Vector2(rect.size.x, bh))
	draw_rect(bridge_deck, Color(0.96, 0.97, 1.0))

	var line_w = maxf(1.0, scale * 1.5)
	draw_line(Vector2(rect.position.x, by), Vector2(rect.position.x + rect.size.x, by), cur_wall, line_w)
	draw_line(Vector2(rect.position.x, by + bh - 1.0), Vector2(rect.position.x + rect.size.x, by + bh - 1.0), cur_wall, line_w)

	if rect.size.y >= 8.0:
		draw_line(Vector2(rect.position.x, by + 2.0), Vector2(rect.position.x + rect.size.x, by + 2.0), Color(0.86, 0.16, 0.16), 1.0)
		draw_line(Vector2(rect.position.x, by + bh - 3.0), Vector2(rect.position.x + rect.size.x, by + bh - 3.0), Color(0.86, 0.16, 0.16), 1.0)

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
