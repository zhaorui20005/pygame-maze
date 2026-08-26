"""可玩原型：生成迷宫、方向键/WASD 走动、撞墙停下。"""

from __future__ import annotations

import json
import math
import os
import sys

RECORDS_FILE = "best_records.json"


def _load_best_records() -> tuple[dict[int, float], int, float | None, int, float, float, float]:
    records: dict[int, float] = {}
    total_score: int = 0
    challenge_best_time: float | None = None
    challenge_best_score: int = 0
    vol_walk: float = 0.7
    vol_sfx: float = 0.8
    vol_bgm: float = 0.6
    if os.path.exists(RECORDS_FILE):
        try:
            with open(RECORDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if k == "total_score":
                        total_score = int(v)
                    elif k == "challenge_best_time":
                        challenge_best_time = float(v)
                    elif k == "challenge_best_score":
                        challenge_best_score = int(v)
                    elif k == "vol_walk":
                        vol_walk = float(v)
                    elif k == "vol_sfx":
                        vol_sfx = float(v)
                    elif k == "vol_bgm":
                        vol_bgm = float(v)
                    else:
                        try:
                            records[int(k)] = float(v)
                        except ValueError:
                            pass
        except Exception as e:
            print(f"Warning: failed to load best records: {e}")
    return (
        records,
        total_score,
        challenge_best_time,
        challenge_best_score,
        vol_walk,
        vol_sfx,
        vol_bgm,
    )


def _save_best_records(
    records: dict[int, float],
    total_score: int,
    challenge_best_time: float | None = None,
    challenge_best_score: int = 0,
    vol_walk: float = 0.7,
    vol_sfx: float = 0.8,
    vol_bgm: float = 0.6,
) -> None:
    try:
        data = {str(k): v for k, v in records.items()}
        data["total_score"] = total_score
        if challenge_best_time is not None:
            data["challenge_best_time"] = challenge_best_time
        data["challenge_best_score"] = challenge_best_score
        data["vol_walk"] = round(vol_walk, 2)
        data["vol_sfx"] = round(vol_sfx, 2)
        data["vol_bgm"] = round(vol_bgm, 2)
        with open(RECORDS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Warning: failed to save best records: {e}")


import pygame

from assets import (
    create_flag_surface,
    create_house_surface,
    create_player_sprites,
    create_sound_bgm_challenge,
    create_sound_bgm_dungeon,
    create_sound_bgm_free,
    create_sound_bgm_menu,
    create_sound_caught,
    create_sound_start,
    create_sound_step,
    create_sound_win,
    create_sound_wolf,
    create_tree_surface,
    create_wolf_sprites,
    load_all_player_skins,
)
from maze import Maze, assert_perfect_maze, generate_maze
from player import Player

CELL_SIZE = 26  # 房间变大后略缩小格子，尽量仍能在常见分辨率下完整显示
HUD_HEIGHT = 48
SIDEBAR_WIDTH = 280  # 右侧独立记分牌与状态面板宽度
FPS = 60
PLAYER_INSET = 6  # 角色比格子小一圈，转弯时不容易被墙角卡住

# 护眼高对比度颜色配置 (森林苔绿道路 + 沉稳深蓝石墙壁 + 超醒目白糯米团子 + 浅金亮底)
COLOR_BG = (12, 15, 22)
COLOR_WALL = (24, 32, 46)
COLOR_PATH = (42, 82, 60)
COLOR_ENTRANCE = (225, 160, 50)
COLOR_EXIT = (245, 235, 198)
COLOR_PLAYER = (70, 140, 230)
COLOR_HUD = (236, 236, 240)
# 通关字：浅色路面上浅黄几乎看不见，改成黄字 + 深红底条。
COLOR_WIN = (255, 255, 80)
COLOR_WIN_BANNER = (176, 16, 32)
COLOR_WIN_OUTLINE = (40, 0, 0)

FONT_CANDIDATES = (
    # Windows
    "Microsoft YaHei",
    "Microsoft YaHei UI",
    "SimHei",
    "SimSun",
    # macOS
    "STHeiti",
    "STHeiti Medium",
    "STHeiti Light",
    "Songti SC",
    "Songti",
    "Hiragino Sans GB",
    "PingFang SC",
    "Arial Unicode MS",
    # Linux
    "wqy-microhei",
    "wqy-zenhei",
    "Noto Sans CJK SC",
    "Noto Sans CJK",
    "Droid Sans Fallback",
)

NUM_KEY_TO_LEVEL = {
    pygame.K_1: 1,
    pygame.K_2: 2,
    pygame.K_3: 3,
    pygame.K_4: 4,
    pygame.K_5: 5,
    pygame.K_6: 6,
    pygame.K_7: 7,
    pygame.K_8: 8,
    pygame.K_9: 9,
    pygame.K_0: 10,
    pygame.K_KP1: 1,
    pygame.K_KP2: 2,
    pygame.K_KP3: 3,
    pygame.K_KP4: 4,
    pygame.K_KP5: 5,
    pygame.K_KP6: 6,
    pygame.K_KP7: 7,
    pygame.K_KP8: 8,
    pygame.K_KP9: 9,
    pygame.K_KP0: 10,
}


class Camera:
    """视角摄像机：支持按视口紧贴适应、自动缩放、拖拽平移与滚轮缩放。"""

    def __init__(self) -> None:
        self.scale = 1.0
        self.fit_scale = 1.0
        self.offset_x = 0.0
        self.offset_y = float(HUD_HEIGHT)
        self.following_player = False
        self.is_dragging = False
        self.drag_start_pos = (0, 0)
        self.drag_start_offset = (0.0, 0.0)

    def fit_maze(self, maze: Maze, screen: pygame.Surface) -> None:
        """根据当前窗口尺寸，计算自动缩放比例，使地图紧贴 HUD 正下方且在左侧区域完整显示。"""
        sw, sh = screen.get_size()
        avail_w = max(1, sw - SIDEBAR_WIDTH)
        avail_h = max(1, sh - HUD_HEIGHT)
        mw = maze.cols * CELL_SIZE
        mh = maze.rows * CELL_SIZE

        # 计算自适应缩放比例（留 16px 间距）
        scale_w = (avail_w - 16) / mw
        scale_h = (avail_h - 16) / mh
        self.fit_scale = min(1.0, scale_w, scale_h)
        self.scale = self.fit_scale

        scaled_w = mw * self.scale
        scaled_h = mh * self.scale

        # 左侧视口内居中，垂直紧贴 HUD 正下方对齐
        self.offset_x = max(8.0, (avail_w - scaled_w) / 2.0)
        self.offset_y = HUD_HEIGHT + max(8.0, (avail_h - scaled_h) / 2.0) if avail_h > scaled_h else float(HUD_HEIGHT)
        self.following_player = False

    def focus_player(self, player: Player, screen: pygame.Surface) -> None:
        """聚焦玩家视角。"""
        self.scale = max(1.0, self.fit_scale)
        self.following_player = True
        self.update_player_focus(player, screen)

    def update_player_focus(self, player: Player, screen: pygame.Surface) -> None:
        if not self.following_player:
            return
        sw, sh = screen.get_size()
        avail_w = max(1, sw - SIDEBAR_WIDTH)
        avail_h = max(1, sh - HUD_HEIGHT)
        vc_x = avail_w / 2.0
        vc_y = HUD_HEIGHT + avail_h / 2.0
        self.offset_x = vc_x - player.rect.centerx * self.scale
        self.offset_y = vc_y - player.rect.centery * self.scale

    def toggle_view(self, maze: Maze, player: Player, screen: pygame.Surface) -> None:
        """按 C / Space 键：在全景自适应与玩家跟随视角之间切换。"""
        if not self.following_player:
            self.focus_player(player, screen)
        else:
            self.fit_maze(maze, screen)

    def zoom(self, factor: float, mouse_pos: tuple[int, int]) -> None:
        old_scale = self.scale
        min_s = min(0.2, self.fit_scale * 0.5)
        new_scale = max(min_s, min(3.5, self.scale * factor))
        if new_scale == old_scale:
            return

        mx, my = mouse_pos
        wx = (mx - self.offset_x) / old_scale
        wy = (my - self.offset_y) / old_scale

        self.scale = new_scale
        self.offset_x = mx - wx * new_scale
        self.offset_y = my - wy * new_scale
        self.following_player = False

    def start_drag(self, mouse_pos: tuple[int, int]) -> None:
        self.is_dragging = True
        self.drag_start_pos = mouse_pos
        self.drag_start_offset = (self.offset_x, self.offset_y)
        self.following_player = False

    def update_drag(self, mouse_pos: tuple[int, int]) -> None:
        if not self.is_dragging:
            return
        dx = mouse_pos[0] - self.drag_start_pos[0]
        dy = mouse_pos[1] - self.drag_start_pos[1]
        self.offset_x = self.drag_start_offset[0] + dx
        self.offset_y = self.drag_start_offset[1] + dy

    def stop_drag(self) -> None:
        self.is_dragging = False

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        return self.offset_x + wx * self.scale, self.offset_y + wy * self.scale


def _font(size: int) -> pygame.font.Font:
    """优先用系统中文字体，跨平台（Windows / macOS / Linux）支持中文字体。"""
    for name in FONT_CANDIDATES:
        path = pygame.font.match_font(name)
        if path:
            try:
                return pygame.font.Font(path, size)
            except Exception:
                pass
    try:
        return pygame.font.SysFont("stheitimedium,microsoftyahei,simhei,sans-serif", size)
    except Exception:
        return pygame.font.Font(None, size)


def _spawn_player(maze: Maze) -> Player:
    """把角色放在入口格子正中（留出 PLAYER_INSET）。"""
    size = CELL_SIZE - PLAYER_INSET * 2
    px = maze.entrance[0] * CELL_SIZE + PLAYER_INSET
    py = maze.entrance[1] * CELL_SIZE + PLAYER_INSET
    return Player(px, py, size)


def _make_maze(world: int = 1, level: int = 1) -> Maze:
    maze = generate_maze(world=world, level=level)
    assert_perfect_maze(maze)
    return maze


def _window_size(maze: Maze) -> tuple[int, int]:
    """根据地图大小动态计算合适的窗口物理尺寸，不超过桌面允许的最大范围。"""
    try:
        sizes = pygame.display.get_desktop_sizes()
        if sizes and sizes[0][0] >= 640 and sizes[0][1] >= 480:
            screen_w, screen_h = sizes[0]
        else:
            info = pygame.display.Info()
            screen_w = info.current_w if info.current_w >= 640 else 1280
            screen_h = info.current_h if info.current_h >= 480 else 800
    except Exception:
        screen_w, screen_h = 1280, 800

    desired_w = max(maze.cols * CELL_SIZE + SIDEBAR_WIDTH + 16, 880)
    desired_h = maze.rows * CELL_SIZE + HUD_HEIGHT + 16

    # 限制窗口最大宽高，留出桌面任务栏/菜单栏空间
    max_w = int(screen_w * 0.92)
    max_h = int(screen_h * 0.88)

    win_w = min(desired_w, max_w)
    win_h = min(desired_h, max_h)
    return win_w, win_h


def _is_reroll_event(event: pygame.event.Event) -> bool:
    """R 重随。中文输入法开启时，字母往往进组合框，pygame.K_r 不会出现；

    数字键 1/2/3 不受影响，所以会表现为「R 没反应、按难度键却能刷新」。
    这里同时认：键值、键盘扫描码、unicode、TEXTINPUT。
    """
    if event.type == pygame.TEXTINPUT:
        return event.text.lower() == "r"

    if event.type != pygame.KEYDOWN:
        return False

    if event.key == pygame.K_r:
        return True

    # SDL_SCANCODE_R = 21；不依赖当前键盘布局 / 输入法字符。
    scancode_r = getattr(pygame, "KSCAN_R", 21)
    if getattr(event, "scancode", None) == scancode_r:
        return True

    if event.unicode and event.unicode.lower() == "r":
        return True

    return False


class Wolf:
    """追赶玩家的大灰狼角色，追随玩家步迹路线移动。"""

    def __init__(self, cell_size: int = CELL_SIZE) -> None:
        self.cell_size = cell_size
        self.x = 0.0
        self.y = 0.0
        self.speed = 1.8  # 速度慢于玩家
        self.facing = "down"
        self.anim_frame = 0
        self.step_timer = 0.0
        self.active = False
        self.trail: list[tuple[float, float]] = []
        self.crying = False

    def spawn(self, entrance_tile: tuple[int, int]) -> None:
        self.x = entrance_tile[0] * self.cell_size + self.cell_size / 2.0
        self.y = entrance_tile[1] * self.cell_size + self.cell_size / 2.0
        self.facing = "down"
        self.anim_frame = 0
        self.step_timer = 0.0
        self.active = True
        self.trail = []
        self.crying = False

    def record_trail(self, p_center: tuple[float, float]) -> None:
        if not self.trail:
            self.trail.append(p_center)
        else:
            lx, ly = self.trail[-1]
            px, py = p_center
            if math.hypot(px - lx, py - ly) >= 8.0:
                self.trail.append(p_center)

    def update(self, dt: float, p_center: tuple[float, float]) -> None:
        if not self.active:
            return

        if self.crying:
            # 玩家通关到达后大灰狼躺地上哭
            self.step_timer += dt
            if self.step_timer >= 0.25:
                self.step_timer = 0.0
                self.anim_frame = (self.anim_frame + 1) % 2
            return

        target = self.trail[0] if self.trail else p_center
        tx, ty = target
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)

        if dist < 6.0 and self.trail:
            self.trail.pop(0)
            if self.trail:
                target = self.trail[0]
                tx, ty = target
                dx = tx - self.x
                dy = ty - self.y
                dist = math.hypot(dx, dy)

        if dist > 0.001:
            move_step = min(self.speed * 60.0 * dt, dist)
            self.x += (dx / dist) * move_step
            self.y += (dy / dist) * move_step

            if abs(dx) > abs(dy):
                self.facing = "right" if dx > 0 else "left"
            else:
                self.facing = "down" if dy > 0 else "up"

            self.step_timer += dt
            if self.step_timer >= 0.15:
                self.step_timer = 0.0
                self.anim_frame = (self.anim_frame + 1) % 2


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Maze Game")
    # 关掉 SDL 文本输入，减少输入法把 R 吃掉的情况。
    if hasattr(pygame.key, "stop_text_input"):
        pygame.key.stop_text_input()

    # 初始化 mixer 及音频资产
    if pygame.mixer.get_init() is None:
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        except Exception as e:
            print(f"Warning: mixer init failed: {e}")

    sound_step = create_sound_step()
    sound_start = create_sound_start()
    sound_win = create_sound_win()
    sound_wolf = create_sound_wolf()
    sound_caught = create_sound_caught()

    sound_bgm_menu = create_sound_bgm_menu()
    sound_bgm_free = create_sound_bgm_free()
    sound_bgm_challenge = create_sound_bgm_challenge()
    sound_bgm_dungeon = create_sound_bgm_dungeon()
    current_bgm_key: str | None = None

    # 生成图形资产
    tree_surf = create_tree_surface(128)
    house_surf = create_house_surface(128)
    player_skins = load_all_player_skins(128)
    skin_list = ["red_hood", "mochi"]
    current_skin_idx = 0
    player_sprites = player_skins[skin_list[current_skin_idx]]
    wolf_sprites = create_wolf_sprites(128)

    clock = pygame.time.Clock()
    font = _font(18)
    big_font = _font(36)

    current_world = 1  # 1: 第一大关 (绿野森林), 2: 第二大关 (狼穴地牢)
    difficulty_level = 1  # 1-10 阶难度
    maze = _make_maze(current_world, difficulty_level)
    screen = pygame.display.set_mode(_window_size(maze), pygame.RESIZABLE)
    player = _spawn_player(maze)
    wolf = Wolf(CELL_SIZE)
    camera = Camera()
    camera.fit_maze(maze, screen)
    won = False
    caught_by_wolf = False

    # 计时器、纪录与音量管理
    (
        best_records,
        total_score,
        challenge_best_time,
        challenge_best_score,
        vol_walk,
        vol_sfx,
        vol_bgm,
    ) = _load_best_records()

    def apply_volumes():
        if sound_step:
            sound_step.set_volume(vol_walk)
        if sound_start:
            sound_start.set_volume(vol_sfx)
        if sound_win:
            sound_win.set_volume(vol_sfx)
        if sound_wolf:
            sound_wolf.set_volume(vol_sfx)
        if sound_caught:
            sound_caught.set_volume(vol_sfx)
        if sound_bgm_menu:
            sound_bgm_menu.set_volume(vol_bgm)
        if sound_bgm_free:
            sound_bgm_free.set_volume(vol_bgm)
        if sound_bgm_challenge:
            sound_bgm_challenge.set_volume(vol_bgm)
        if sound_bgm_dungeon:
            sound_bgm_dungeon.set_volume(vol_bgm)

    def switch_bgm(key: str):
        nonlocal current_bgm_key
        if current_bgm_key == key:
            return
        if sound_bgm_menu:
            sound_bgm_menu.stop()
        if sound_bgm_free:
            sound_bgm_free.stop()
        if sound_bgm_challenge:
            sound_bgm_challenge.stop()
        if sound_bgm_dungeon:
            sound_bgm_dungeon.stop()

        current_bgm_key = key
        target = None
        if key == "menu":
            target = sound_bgm_menu
        elif key == "free":
            target = sound_bgm_free
        elif key == "challenge":
            target = sound_bgm_challenge
        elif key == "dungeon":
            target = sound_bgm_dungeon

        if target:
            target.set_volume(vol_bgm)
            try:
                target.play(loops=-1)
            except Exception as e:
                print(f"Warning: failed to play BGM {key}: {e}")

    apply_volumes()
    switch_bgm("menu")

    in_menu = True
    game_mode = "free"  # "free" 或 "challenge"
    challenge_total_time = 0.0
    challenge_total_score = 0
    challenge_completed = False
    dragging_slider = None

    last_round_score = 0
    score_doubled = False
    timer_started = False
    start_time_ms = 0
    current_time_sec = 0.0
    show_auto_path = False
    auto_visited_order: list[tuple[int, int]] = []
    auto_path: list[tuple[int, int]] = []
    auto_parent_map: dict[tuple[int, int], tuple[int, int] | None] = {}
    auto_search_idx: float = 0.0
    auto_path_idx: float = 0.0
    auto_path_phase = "idle"  # "idle", "search", "path", "complete"

    auto_advance_timer: float = -1.0

    def trigger_auto_path():
        nonlocal show_auto_path, auto_visited_order, auto_path, auto_parent_map, auto_search_idx, auto_path_idx, auto_path_phase
        show_auto_path = not show_auto_path
        if show_auto_path and maze:
            auto_visited_order, auto_path, auto_parent_map = maze.solve_path_with_visited()
            auto_search_idx = 0.0
            auto_path_idx = 0.0
            auto_path_phase = "search"
        else:
            auto_path_phase = "idle"

    def reset_level_state():
        nonlocal maze, screen, player, wolf, camera, won, caught_by_wolf, timer_started, start_time_ms, current_time_sec, auto_advance_timer
        nonlocal auto_visited_order, auto_path, auto_parent_map, auto_search_idx, auto_path_idx, auto_path_phase
        maze = _make_maze(current_world, difficulty_level)
        screen = pygame.display.set_mode(_window_size(maze), pygame.RESIZABLE)
        player = _spawn_player(maze)
        wolf = Wolf(CELL_SIZE)
        camera.fit_maze(maze, screen)
        won = False
        caught_by_wolf = False
        timer_started = False
        start_time_ms = 0
        current_time_sec = 0.0
        auto_advance_timer = -1.0

        if show_auto_path and maze:
            auto_visited_order, auto_path, auto_parent_map = maze.solve_path_with_visited()
            auto_search_idx = 0.0
            auto_path_idx = 0.0
            auto_path_phase = "search"
        else:
            auto_visited_order = []
            auto_path = []
            auto_parent_map = {}
            auto_search_idx = 0.0
            auto_path_idx = 0.0
            auto_path_phase = "idle"

        if current_world == 2:
            switch_bgm("dungeon")
        elif game_mode == "challenge":
            switch_bgm("challenge")
        else:
            switch_bgm("free")

        if sound_start:
            sound_start.play()

    def start_free_mode(world: int = 1, level: int = 1):
        nonlocal in_menu, game_mode, current_world, difficulty_level
        in_menu = False
        game_mode = "free"
        current_world = world
        difficulty_level = level
        reset_level_state()

    def start_challenge_mode():
        nonlocal in_menu, game_mode, current_world, difficulty_level, challenge_total_time, challenge_total_score, challenge_completed
        in_menu = False
        game_mode = "challenge"
        current_world = 1
        difficulty_level = 1
        challenge_total_time = 0.0
        challenge_total_score = 0
        challenge_completed = False
        reset_level_state()

    def advance_next_level():
        nonlocal current_world, difficulty_level, challenge_completed
        if game_mode == "challenge":
            if current_world == 1:
                if difficulty_level < 10:
                    difficulty_level += 1
                else:
                    current_world = 2
                    difficulty_level = 1
                reset_level_state()
            elif current_world == 2:
                if difficulty_level < 10:
                    difficulty_level += 1
                    reset_level_state()
                else:
                    start_challenge_mode()
        else:
            if difficulty_level < 10:
                difficulty_level += 1
            else:
                if current_world == 1:
                    current_world = 2
                    difficulty_level = 1
                else:
                    current_world = 1
                    difficulty_level = 1
            reset_level_state()

    def prev_level():
        nonlocal current_world, difficulty_level
        if difficulty_level > 1:
            difficulty_level -= 1
        else:
            if current_world == 2:
                current_world = 1
                difficulty_level = 10
            else:
                current_world = 2
                difficulty_level = 10
        reset_level_state()

    # 开局播放声音
    if sound_start:
        sound_start.play()

    sidebar_level_rects: dict[int, pygame.Rect] = {}
    btn_auto_path_rect: pygame.Rect | None = None
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()

        if in_menu:
            switch_bgm("menu")
            btn_free_rect, btn_challenge_rect, sound_rects, menu_level_rects = _draw_main_menu(
                screen,
                font,
                big_font,
                mouse_pos,
                total_score,
                challenge_best_time,
                challenge_best_score,
                vol_walk,
                vol_sfx,
                vol_bgm,
            )
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_1, pygame.K_KP1):
                        start_free_mode(1, 1)
                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        start_challenge_mode()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    clicked_lvl = False
                    for (w, lvl), brect in menu_level_rects.items():
                        if brect.collidepoint(event.pos):
                            start_free_mode(w, lvl)
                            clicked_lvl = True
                            break
                    if clicked_lvl:
                        continue
                    if btn_free_rect.collidepoint(event.pos):
                        start_free_mode(1, 1)
                    elif btn_challenge_rect.collidepoint(event.pos):
                        start_challenge_mode()
                    elif sound_rects["walk_minus"].collidepoint(event.pos):
                        vol_walk = max(0.0, round((vol_walk - 0.05) * 20.0) / 20.0)
                        apply_volumes()
                        if sound_step:
                            sound_step.play()
                        _save_best_records(best_records, total_score, challenge_best_time, challenge_best_score, vol_walk, vol_sfx, vol_bgm)
                    elif sound_rects["walk_plus"].collidepoint(event.pos):
                        vol_walk = min(1.0, round((vol_walk + 0.05) * 20.0) / 20.0)
                        apply_volumes()
                        if sound_step:
                            sound_step.play()
                        _save_best_records(best_records, total_score, challenge_best_time, challenge_best_score, vol_walk, vol_sfx, vol_bgm)
                    elif sound_rects["walk_track"].collidepoint(event.pos):
                        dragging_slider = "walk"
                        vol_walk = max(0.0, min(1.0, round(((event.pos[0] - sound_rects["walk_track"].x) / sound_rects["walk_track"].w) * 20.0) / 20.0))
                        apply_volumes()
                        if sound_step:
                            sound_step.play()
                        _save_best_records(best_records, total_score, challenge_best_time, challenge_best_score, vol_walk, vol_sfx, vol_bgm)
                    elif sound_rects["sfx_minus"].collidepoint(event.pos):
                        vol_sfx = max(0.0, round((vol_sfx - 0.05) * 20.0) / 20.0)
                        apply_volumes()
                        if sound_start:
                            sound_start.play()
                        _save_best_records(best_records, total_score, challenge_best_time, challenge_best_score, vol_walk, vol_sfx, vol_bgm)
                    elif sound_rects["sfx_plus"].collidepoint(event.pos):
                        vol_sfx = min(1.0, round((vol_sfx + 0.05) * 20.0) / 20.0)
                        apply_volumes()
                        if sound_start:
                            sound_start.play()
                        _save_best_records(best_records, total_score, challenge_best_time, challenge_best_score, vol_walk, vol_sfx, vol_bgm)
                    elif sound_rects["sfx_track"].collidepoint(event.pos):
                        dragging_slider = "sfx"
                        vol_sfx = max(0.0, min(1.0, round(((event.pos[0] - sound_rects["sfx_track"].x) / sound_rects["sfx_track"].w) * 20.0) / 20.0))
                        apply_volumes()
                        if sound_start:
                            sound_start.play()
                        _save_best_records(best_records, total_score, challenge_best_time, challenge_best_score, vol_walk, vol_sfx, vol_bgm)
                    elif sound_rects["bgm_minus"].collidepoint(event.pos):
                        vol_bgm = max(0.0, round((vol_bgm - 0.05) * 20.0) / 20.0)
                        apply_volumes()
                        _save_best_records(best_records, total_score, challenge_best_time, challenge_best_score, vol_walk, vol_sfx, vol_bgm)
                    elif sound_rects["bgm_plus"].collidepoint(event.pos):
                        vol_bgm = min(1.0, round((vol_bgm + 0.05) * 20.0) / 20.0)
                        apply_volumes()
                        _save_best_records(best_records, total_score, challenge_best_time, challenge_best_score, vol_walk, vol_sfx, vol_bgm)
                    elif sound_rects["bgm_track"].collidepoint(event.pos):
                        dragging_slider = "bgm"
                        vol_bgm = max(0.0, min(1.0, round(((event.pos[0] - sound_rects["bgm_track"].x) / sound_rects["bgm_track"].w) * 20.0) / 20.0))
                        apply_volumes()
                        _save_best_records(best_records, total_score, challenge_best_time, challenge_best_score, vol_walk, vol_sfx, vol_bgm)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    dragging_slider = None
                elif event.type == pygame.MOUSEMOTION and dragging_slider:
                    if dragging_slider == "walk":
                        vol_walk = max(0.0, min(1.0, round(((event.pos[0] - sound_rects["walk_track"].x) / sound_rects["walk_track"].w) * 20.0) / 20.0))
                    elif dragging_slider == "sfx":
                        vol_sfx = max(0.0, min(1.0, round(((event.pos[0] - sound_rects["sfx_track"].x) / sound_rects["sfx_track"].w) * 20.0) / 20.0))
                    elif dragging_slider == "bgm":
                        vol_bgm = max(0.0, min(1.0, round(((event.pos[0] - sound_rects["bgm_track"].x) / sound_rects["bgm_track"].w) * 20.0) / 20.0))
                    apply_volumes()
                    _save_best_records(best_records, total_score, challenge_best_time, challenge_best_score, vol_walk, vol_sfx, vol_bgm)
            clock.tick(FPS)
            continue

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                if not camera.following_player:
                    camera.fit_maze(maze, screen)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_m):
                    in_menu = True
                    switch_bgm("menu")
                elif event.key == pygame.K_f:
                    if wolf.active:
                        wolf.active = False
                    else:
                        wolf.spawn(maze.entrance)
                        if sound_wolf:
                            sound_wolf.play()
                elif event.key == pygame.K_p:
                    current_skin_idx = (current_skin_idx + 1) % len(skin_list)
                    player_sprites = player_skins[skin_list[current_skin_idx]]
                elif event.key == pygame.K_h:
                    trigger_auto_path()
                elif event.key in (pygame.K_c, pygame.K_SPACE):
                    if won:
                        auto_advance_timer = -1.0
                        if not (game_mode == "challenge" and challenge_completed):
                            advance_next_level()
                        else:
                            start_challenge_mode()
                    else:
                        camera.toggle_view(maze, player, screen)
                elif event.key in NUM_KEY_TO_LEVEL and game_mode == "free":
                    difficulty_level = NUM_KEY_TO_LEVEL[event.key]
                    reset_level_state()
                elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS, pygame.K_PAGEDOWN) and game_mode == "free":
                    advance_next_level()
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_PAGEUP) and game_mode == "free":
                    prev_level()
                elif _is_reroll_event(event):
                    if won:
                        auto_advance_timer = -1.0
                        if not (game_mode == "challenge" and challenge_completed):
                            advance_next_level()
                        else:
                            start_challenge_mode()
                    else:
                        reset_level_state()
            elif event.type != pygame.KEYDOWN and _is_reroll_event(event):
                reset_level_state()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if won:
                    auto_advance_timer = -1.0
                    if not (game_mode == "challenge" and challenge_completed):
                        advance_next_level()
                    else:
                        start_challenge_mode()
                elif event.pos[0] >= screen.get_width() - SIDEBAR_WIDTH:
                    if btn_auto_path_rect and btn_auto_path_rect.collidepoint(event.pos):
                        trigger_auto_path()
                    else:
                        clicked_lvl = False
                        for (w, lvl), brect in sidebar_level_rects.items():
                            if brect.collidepoint(event.pos):
                                current_world = w
                                difficulty_level = lvl
                                reset_level_state()
                                clicked_lvl = True
                                break
                        if not clicked_lvl and event.pos[1] >= screen.get_height() - 40:
                            in_menu = True
                            switch_bgm("menu")
                elif event.pos[1] > HUD_HEIGHT:
                    if event.button in (1, 2, 3):
                        camera.start_drag(event.pos)
                    elif event.button == 4:
                        camera.zoom(1.15, event.pos)
                    elif event.button == 5:
                        camera.zoom(1 / 1.15, event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (1, 2, 3):
                    camera.stop_drag()
            elif event.type == pygame.MOUSEMOTION:
                if camera.is_dragging:
                    camera.update_drag(event.pos)
            elif event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if mx < screen.get_width() - SIDEBAR_WIDTH and my > HUD_HEIGHT:
                    factor = 1.15 if event.y > 0 else (1 / 1.15 if event.y < 0 else 1.0)
                    if factor != 1.0:
                        camera.zoom(factor, (mx, my))

        # 通关/被抓后停步，但仍可按 R / 数字键 重开。
        dt = clock.get_time() / 1000.0
        if not won and not caught_by_wolf:
            keys = pygame.key.get_pressed()

            # 第一次按方向键后开启精确到 0.01s 的计时器
            if not timer_started:
                if any(keys[k] for k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s)):
                    timer_started = True
                    start_time_ms = pygame.time.get_ticks()

            if timer_started:
                current_time_sec = (pygame.time.get_ticks() - start_time_ms) / 1000.0

            player.update(keys, maze, CELL_SIZE, sound_step)

            # 更新大灰狼轨迹与追赶逻辑
            if wolf.active:
                wolf.record_trail(player.rect.center)
                wolf.update(dt, player.rect.center)

                # 检查大灰狼是否抓到玩家
                if math.hypot(wolf.x - player.rect.centerx, wolf.y - player.rect.centery) < CELL_SIZE * 0.65:
                    caught_by_wolf = True
                    last_round_score = 0
                    score_doubled = False
                    if sound_caught:
                        sound_caught.play()

            if player.reached_exit(maze, CELL_SIZE):
                won = True
                if not (game_mode == "challenge" and challenge_completed):
                    auto_advance_timer = 1.2
                if wolf.active:
                    wolf.crying = True

                if timer_started:
                    current_time_sec = (pygame.time.get_ticks() - start_time_ms) / 1000.0

                rec_key = f"{current_world}_{difficulty_level}"
                has_prev = rec_key in best_records
                prev_best = best_records.get(rec_key, 999999.0)
                is_new_record = False

                if not has_prev or current_time_sec < prev_best:
                    is_new_record = True
                    best_records[rec_key] = current_time_sec

                base_score = (current_world - 1) * 1000 + difficulty_level * 100
                if is_new_record:
                    last_round_score = base_score * 2
                    score_doubled = True
                else:
                    last_round_score = base_score
                    score_doubled = False

                if game_mode == "free":
                    total_score += last_round_score
                    _save_best_records(
                        best_records, total_score, challenge_best_time, challenge_best_score, vol_walk, vol_sfx, vol_bgm
                    )
                elif game_mode == "challenge":
                    challenge_total_time += current_time_sec
                    challenge_total_score += last_round_score
                    if current_world == 2 and difficulty_level == 10:
                        challenge_completed = True
                        total_score += challenge_total_score
                        if (
                            challenge_best_time is None
                            or challenge_total_time < challenge_best_time
                        ):
                            challenge_best_time = challenge_total_time
                        if challenge_total_score > challenge_best_score:
                            challenge_best_score = challenge_total_score
                        _save_best_records(
                            best_records, total_score, challenge_best_time, challenge_best_score, vol_walk, vol_sfx, vol_bgm
                        )
                    else:
                        _save_best_records(
                            best_records, total_score, challenge_best_time, challenge_best_score, vol_walk, vol_sfx, vol_bgm
                        )

                if sound_win:
                    sound_win.play()

            if camera.following_player:
                camera.update_player_focus(player, screen)
            else:
                # 检查玩家坐标是否离开左侧视口区域
                sw, sh = screen.get_size()
                maze_w = sw - SIDEBAR_WIDTH
                psx, psy = camera.world_to_screen(player.rect.centerx, player.rect.centery)
                if not (0 <= psx <= maze_w and HUD_HEIGHT <= psy <= sh):
                    if camera.scale <= camera.fit_scale * 1.05:
                        camera.fit_maze(maze, screen)
                    else:
                        camera.focus_player(player, screen)
        elif won:
            if wolf.active:
                wolf.crying = True
                wolf.update(dt, player.rect.center)
            if not (game_mode == "challenge" and challenge_completed):
                if auto_advance_timer > 0.0:
                    auto_advance_timer -= dt
                    if auto_advance_timer <= 0.0:
                        auto_advance_timer = -1.0
                        advance_next_level()

        if show_auto_path:
            if auto_path_phase == "search":
                search_speed = max(0.5, len(auto_visited_order) / 200.0)
                auto_search_idx += search_speed
                if auto_search_idx >= len(auto_visited_order):
                    auto_search_idx = float(len(auto_visited_order))
                    auto_path_phase = "path"
            elif auto_path_phase == "path":
                path_speed = max(0.25, len(auto_path) / 100.0)
                auto_path_idx += path_speed
                if auto_path_idx >= len(auto_path):
                    auto_path_idx = float(len(auto_path))
                    auto_path_phase = "complete"

        sidebar_level_rects, btn_auto_path_rect = _draw(
            screen,
            maze,
            player,
            wolf,
            font,
            big_font,
            won,
            caught_by_wolf,
            camera,
            tree_surf,
            house_surf,
            player_sprites,
            wolf_sprites,
            current_world,
            difficulty_level,
            best_records,
            timer_started,
            current_time_sec,
            total_score,
            last_round_score,
            score_doubled,
            game_mode,
            challenge_total_time,
            challenge_total_score,
            challenge_completed,
            show_auto_path,
            auto_visited_order,
            auto_path,
            auto_parent_map,
            auto_search_idx,
            auto_path_idx,
            auto_path_phase,
            auto_advance_timer,
        )
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)


def _draw_main_menu(
    screen: pygame.Surface,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    mouse_pos: tuple[int, int],
    total_score: int,
    challenge_best_time: float | None,
    challenge_best_score: int,
    vol_walk: float,
    vol_sfx: float,
    vol_bgm: float,
) -> tuple[pygame.Rect, pygame.Rect, dict[str, pygame.Rect], dict[tuple[int, int], pygame.Rect]]:
    """绘制美观的主界面模式选择菜单与音量控制，完全对齐 Godot 版本的 5 卡片布局。"""
    screen.fill((12, 16, 26))
    sw, sh = screen.get_size()
    cx, cy = sw // 2, sh // 2
    small_font = _font(14)

    # 1. 主标题与副标题
    title_surf = big_font.render("🎮 小红帽迷宫大冒险", True, (255, 225, 90))
    title_rect = title_surf.get_rect(center=(cx, cy - 235))
    screen.blit(title_surf, title_rect)

    sub_surf = font.render("—— 请选择游戏模式 & 调整声音设置 ——", True, (170, 190, 215))
    sub_rect = sub_surf.get_rect(center=(cx, cy - 198))
    screen.blit(sub_surf, sub_rect)

    card_w = 560

    # 2. 模式 1 按钮：自由模式 (Free Mode)
    btn1_h = 58
    btn1_rect = pygame.Rect(cx - card_w // 2, cy - 188, card_w, btn1_h)
    hover1 = btn1_rect.collidepoint(mouse_pos)

    bg_color1 = (32, 48, 74) if hover1 else (22, 32, 52)
    border_color1 = (100, 180, 255) if hover1 else (48, 72, 108)
    pygame.draw.rect(screen, bg_color1, btn1_rect, border_radius=10)
    pygame.draw.rect(screen, border_color1, btn1_rect, width=2 if hover1 else 1, border_radius=10)

    t1 = font.render("🌟 1. 自由模式 (Free Mode)", True, (255, 240, 150) if hover1 else (230, 235, 245))
    screen.blit(t1, (btn1_rect.x + 18, btn1_rect.y + 8))

    desc1 = font.render("按 [1] 键或点击 | 1~10 阶自由切换，无限切关与随心练习", True, (160, 180, 205))
    screen.blit(desc1, (btn1_rect.x + 18, btn1_rect.y + 32))

    # 3. 模式 2 按钮：闯关模式 (Challenge Mode)
    btn2_h = 58
    btn2_rect = pygame.Rect(cx - card_w // 2, cy - 122, card_w, btn2_h)
    hover2 = btn2_rect.collidepoint(mouse_pos)

    bg_color2 = (32, 48, 74) if hover2 else (22, 32, 52)
    border_color2 = (255, 210, 90) if hover2 else (48, 72, 108)
    pygame.draw.rect(screen, bg_color2, btn2_rect, border_radius=10)
    pygame.draw.rect(screen, border_color2, btn2_rect, width=2 if hover2 else 1, border_radius=10)

    t2 = font.render("🏆 2. 闯关模式 (Challenge Mode)", True, (255, 220, 90) if hover2 else (230, 235, 245))
    screen.blit(t2, (btn2_rect.x + 18, btn2_rect.y + 8))

    desc2 = font.render("按 [2] 键或点击 | 第一大关 (1~10阶) + 第二大关 (1~10阶) 共 20 关连续挑战", True, (160, 180, 205))
    screen.blit(desc2, (btn2_rect.x + 18, btn2_rect.y + 32))

    # 4. 卡片 3：🎯 调试/自由选关卡片 (与 Godot 完全对齐)
    lvl_card_h = 74
    lvl_card = pygame.Rect(cx - card_w // 2, cy - 56, card_w, lvl_card_h)
    pygame.draw.rect(screen, (22, 32, 50), lvl_card, border_radius=10)
    pygame.draw.rect(screen, (60, 90, 140), lvl_card, width=1, border_radius=10)

    menu_level_rects: dict[tuple[int, int], pygame.Rect] = {}

    # 第一大关选关 (1~10 阶)
    lbl1 = small_font.render("🌲 第一大关 (绿野森林):", True, (130, 230, 150))
    screen.blit(lbl1, (lvl_card.x + 14, lvl_card.y + 10))
    for i in range(1, 11):
        bx = lvl_card.x + 200 + (i - 1) * 34
        by = lvl_card.y + 8
        brect = pygame.Rect(bx, by, 30, 24)
        menu_level_rects[(1, i)] = brect
        h_l = brect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (38, 88, 56) if h_l else (22, 48, 34), brect, border_radius=4)
        pygame.draw.rect(screen, (130, 230, 150) if h_l else (60, 130, 80), brect, width=1, border_radius=4)
        ts = small_font.render(str(i), True, (255, 240, 150) if h_l else (210, 235, 220))
        screen.blit(ts, ts.get_rect(center=brect.center))

    # 第二大关选关 (1~10 阶)
    lbl2 = small_font.render("🏰 第二大关 (狼穴地牢):", True, (255, 130, 130))
    screen.blit(lbl2, (lvl_card.x + 14, lvl_card.y + 44))
    for i in range(1, 11):
        bx = lvl_card.x + 200 + (i - 1) * 34
        by = lvl_card.y + 42
        brect = pygame.Rect(bx, by, 30, 24)
        menu_level_rects[(2, i)] = brect
        h_l = brect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (98, 38, 52) if h_l else (56, 22, 32), brect, border_radius=4)
        pygame.draw.rect(screen, (255, 130, 130) if h_l else (180, 60, 80), brect, width=1, border_radius=4)
        ts = small_font.render(str(i), True, (255, 240, 150) if h_l else (235, 210, 220))
        screen.blit(ts, ts.get_rect(center=brect.center))

    # 5. 卡片 4：🎵 声音大小设置 (Sound Volume Settings)
    c3_h = 115
    c3_rect = pygame.Rect(cx - card_w // 2, cy + 24, card_w, c3_h)
    pygame.draw.rect(screen, (22, 32, 50), c3_rect, border_radius=10)
    pygame.draw.rect(screen, (60, 90, 140), c3_rect, width=1, border_radius=10)

    v_title = font.render("🎵 声音大小设置", True, (255, 220, 90))
    screen.blit(v_title, (c3_rect.x + 16, c3_rect.y + 8))

    def _draw_vol_row(
        label_text: str, y_pos: int, vol_val: float
    ) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        lbl = font.render(label_text, True, (220, 230, 245))
        screen.blit(lbl, (c3_rect.x + 16, y_pos))

        b_minus = pygame.Rect(c3_rect.x + 120, y_pos - 2, 28, 22)
        h_m = b_minus.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (48, 68, 98) if h_m else (32, 46, 68), b_minus, border_radius=4)
        pygame.draw.rect(screen, (100, 140, 190), b_minus, width=1, border_radius=4)
        t_m = font.render("-", True, (255, 255, 255))
        screen.blit(t_m, t_m.get_rect(center=b_minus.center))

        track = pygame.Rect(c3_rect.x + 158, y_pos + 5, 180, 8)
        pygame.draw.rect(screen, (40, 52, 74), track, border_radius=4)
        fill_w = int(vol_val * track.w)
        if fill_w > 0:
            pygame.draw.rect(
                screen,
                (100, 190, 255),
                (track.x, track.y, fill_w, track.h),
                border_radius=4,
            )
        knob_x = track.x + fill_w
        pygame.draw.circle(screen, (255, 235, 140), (knob_x, track.centery), 7)

        b_plus = pygame.Rect(c3_rect.x + 348, y_pos - 2, 28, 22)
        h_p = b_plus.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (48, 68, 98) if h_p else (32, 46, 68), b_plus, border_radius=4)
        pygame.draw.rect(screen, (100, 140, 190), b_plus, width=1, border_radius=4)
        t_p = font.render("+", True, (255, 255, 255))
        screen.blit(t_p, t_p.get_rect(center=b_plus.center))

        val_txt = font.render(f"{int(round(vol_val * 100))}%", True, (255, 235, 150))
        screen.blit(val_txt, (c3_rect.x + 388, y_pos))

        return b_minus, b_plus, track

    bm_w, bp_w, tr_w = _draw_vol_row("🚶 走路音效", c3_rect.y + 30, vol_walk)
    bm_s, bp_s, tr_s = _draw_vol_row("🔔 提示音效", c3_rect.y + 56, vol_sfx)
    bm_b, bp_b, tr_b = _draw_vol_row("🎵 背景音乐", c3_rect.y + 82, vol_bgm)

    sound_rects = {
        "walk_minus": bm_w,
        "walk_plus": bp_w,
        "walk_track": tr_w,
        "sfx_minus": bm_s,
        "sfx_plus": bp_s,
        "sfx_track": tr_s,
        "bgm_minus": bm_b,
        "bgm_plus": bp_b,
        "bgm_track": tr_b,
    }

    # 6. 卡片 5：底部荣耀纪录卡片 (Statistics Card)
    card4_h = 68
    card4_rect = pygame.Rect(cx - card_w // 2, cy + 147, card_w, card4_h)
    pygame.draw.rect(screen, (18, 26, 40), card4_rect, border_radius=10)
    pygame.draw.rect(screen, (40, 58, 88), card4_rect, width=1, border_radius=10)

    r_title = font.render("📊 荣耀排行榜纪录", True, (255, 215, 80))
    screen.blit(r_title, (card4_rect.x + 16, card4_rect.y + 8))

    t_score = font.render(f"累计总得分: {total_score:,} 分", True, (200, 225, 245))
    screen.blit(t_score, (card4_rect.x + 16, card4_rect.y + 28))

    c_best_t_str = f"{challenge_best_time:.2f} 秒" if challenge_best_time is not None else "暂无纪录"
    c_best_s_str = f"{challenge_best_score:,} 分" if challenge_best_score > 0 else "暂无纪录"
    t_chal = font.render(
        f"闯关模式最佳全通: {c_best_t_str} | 最高得分: {c_best_s_str}", True, (180, 210, 255)
    )
    screen.blit(t_chal, (card4_rect.x + 16, card4_rect.y + 46))

    # 7. 脚标提示
    hint_surf = font.render(
        "👉 点击模式或调音按钮 | 按 [1]/[2] 启动模式 | 按 [ESC] 退出程序",
        True,
        (130, 150, 175),
    )
    hint_rect = hint_surf.get_rect(center=(cx, sh - 22))
    screen.blit(hint_surf, hint_rect)

    return btn1_rect, btn2_rect, sound_rects, menu_level_rects


def _draw(
    screen: pygame.Surface,
    maze: Maze,
    player: Player,
    wolf: Wolf,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    won: bool,
    caught_by_wolf: bool,
    camera: Camera,
    tree_surf: pygame.Surface,
    house_surf: pygame.Surface,
    player_sprites: dict[str, list[pygame.Surface]],
    wolf_sprites: dict[str, list[pygame.Surface]],
    current_world: int,
    difficulty_level: int,
    best_records: dict[str, float],
    timer_started: bool,
    current_time_sec: float,
    total_score: int,
    last_round_score: int,
    score_doubled: bool,
    game_mode: str,
    challenge_total_time: float,
    challenge_total_score: int,
    challenge_completed: bool,
    show_auto_path: bool = False,
    auto_visited_order: list[tuple[int, int]] | None = None,
    auto_path: list[tuple[int, int]] | None = None,
    auto_parent_map: dict[tuple[int, int], tuple[int, int] | None] | None = None,
    auto_search_idx: float = 0.0,
    auto_path_idx: float = 0.0,
    auto_path_phase: str = "idle",
    auto_advance_timer: float = -1.0,
) -> tuple[dict[tuple[int, int], pygame.Rect], pygame.Rect]:
    if current_world == 2:
        # 第二大关：狼穴地牢暗黑绯红调
        cur_bg = (20, 10, 16)
        cur_wall = (42, 20, 32)
        cur_path = (75, 30, 40)
    else:
        # 第一大关：绿野森林苔绿调
        cur_bg = COLOR_BG
        cur_wall = COLOR_WALL
        cur_path = COLOR_PATH

    screen.fill(cur_bg)
    screen_w, screen_h = screen.get_size()
    maze_w = screen_w - SIDEBAR_WIDTH

    scale = camera.scale

    # 1. 计算左侧迷宫视口覆盖的世界坐标范围，进行视口裁剪
    min_wx = (0 - camera.offset_x) / scale
    max_wx = (maze_w - camera.offset_x) / scale
    min_wy = (HUD_HEIGHT - camera.offset_y) / scale
    max_wy = (screen_h - camera.offset_y) / scale

    min_tile_x = max(0, int(min_wx // CELL_SIZE))
    max_tile_x = min(maze.cols - 1, int(max_wx // CELL_SIZE))
    min_tile_y = max(0, int(min_wy // CELL_SIZE))
    max_tile_y = min(maze.rows - 1, int(max_wy // CELL_SIZE))

    for y in range(min_tile_y, max_tile_y + 1):
        row = maze.grid[y]
        for x in range(min_tile_x, max_tile_x + 1):
            tile = row[x]
            x1, y1 = camera.world_to_screen(x * CELL_SIZE, y * CELL_SIZE)
            x2, y2 = camera.world_to_screen((x + 1) * CELL_SIZE, (y + 1) * CELL_SIZE)
            rect = pygame.Rect(
                int(x1),
                int(y1),
                max(1, int(math.ceil(x2 - x1))),
                max(1, int(math.ceil(y2 - y1))),
            )
            color = cur_wall if tile == 1 else cur_path
            pygame.draw.rect(screen, color, rect)

    # 入口与出口瓦片及图案 (起点大树、终点小房子)
    for (tx, ty), color, surf in (
        (maze.entrance, COLOR_ENTRANCE, tree_surf),
        (maze.exit, COLOR_EXIT, house_surf),
    ):
        if min_tile_x <= tx <= max_tile_x and min_tile_y <= ty <= max_tile_y:
            x1, y1 = camera.world_to_screen(tx * CELL_SIZE, ty * CELL_SIZE)
            x2, y2 = camera.world_to_screen((tx + 1) * CELL_SIZE, (ty + 1) * CELL_SIZE)
            rect = pygame.Rect(
                int(x1),
                int(y1),
                max(1, int(math.ceil(x2 - x1))),
                max(1, int(math.ceil(y2 - y1))),
            )
            pygame.draw.rect(screen, color, rect)
            if rect.w >= 4 and rect.h >= 4:
                scaled_surf = pygame.transform.smoothscale(surf, (rect.w, rect.h))
                screen.blit(scaled_surf, rect.topleft)

    # 1.5 如果开启自动寻路，绘制 DFS 单线探索与最终路径动画
    if show_auto_path:
        search_idx_int = int(auto_search_idx)
        path_idx_int = int(auto_path_idx)

        # A) 深度优先单线探索演示
        if auto_visited_order and search_idx_int > 0:
            visible_visited = auto_visited_order[:search_idx_int]

            # 1. 绘制历史试错痕迹 (柔和深灰蓝/暗蓝色)
            for vx, vy in visible_visited:
                if min_tile_x <= vx <= max_tile_x and min_tile_y <= vy <= max_tile_y:
                    x1, y1 = camera.world_to_screen(vx * CELL_SIZE, vy * CELL_SIZE)
                    x2, y2 = camera.world_to_screen((vx + 1) * CELL_SIZE, (vy + 1) * CELL_SIZE)
                    rect = pygame.Rect(
                        int(x1), int(y1), max(1, int(math.ceil(x2 - x1))), max(1, int(math.ceil(y2 - y1)))
                    )
                    pygame.draw.rect(screen, (32, 55, 90), rect)

            # 2. 绘制当前唯一正在尝试的单线通路 (亮青色单轨，绝无分叉)
            if auto_path_phase == "search" and auto_parent_map:
                curr_node = auto_visited_order[min(search_idx_int - 1, len(auto_visited_order) - 1)]
                active_trail = []
                node: tuple[int, int] | None = curr_node
                while node is not None and node in auto_parent_map:
                    active_trail.append(node)
                    node = auto_parent_map[node]
                active_trail.reverse()

                trail_pts = []
                for tx, ty in active_trail:
                    cx = (tx + 0.5) * CELL_SIZE
                    cy = (ty + 0.5) * CELL_SIZE
                    sx, sy = camera.world_to_screen(cx, cy)
                    trail_pts.append((sx, sy))

                if len(trail_pts) >= 2:
                    glow_w = max(3, int(scale * 8))
                    core_w = max(1, int(scale * 3))
                    pygame.draw.lines(screen, (0, 230, 255), False, trail_pts, width=glow_w)
                    pygame.draw.lines(screen, (230, 255, 255), False, trail_pts, width=core_w)

                if trail_pts:
                    tip_x, tip_y = trail_pts[-1]
                    pygame.draw.circle(screen, (0, 255, 180), (int(tip_x), int(tip_y)), max(4, int(scale * 7)))

        # B) 找到终点后，绘制从起点延伸至终点的最终最优路径 (金黄色光轨)
        if auto_path and path_idx_int > 0 and auto_path_phase in ("path", "complete"):
            visible_path = auto_path[:path_idx_int]
            points = []
            for tx, ty in visible_path:
                cx = (tx + 0.5) * CELL_SIZE
                cy = (ty + 0.5) * CELL_SIZE
                sx, sy = camera.world_to_screen(cx, cy)
                points.append((sx, sy))

            if len(points) >= 2:
                glow_w = max(3, int(scale * 8))
                core_w = max(1, int(scale * 3))
                pygame.draw.lines(screen, (255, 200, 50), False, points, width=glow_w)
                pygame.draw.lines(screen, (255, 255, 220), False, points, width=core_w)
                r_dot = max(2, int(scale * 3))
                for px, py in points:
                    pygame.draw.circle(screen, (255, 220, 80), (int(px), int(py)), r_dot)

            if auto_path_phase == "path" and points:
                tip_x, tip_y = points[-1]
                pygame.draw.circle(screen, (255, 255, 120), (int(tip_x), int(tip_y)), max(4, int(scale * 7)))

    # 绘制玩家 (通关后一跳一跳的开心跳跃动画)
    center_wx, center_wy = player.rect.centerx, player.rect.centery
    draw_w = CELL_SIZE * 1.25
    draw_h = CELL_SIZE * 1.25
    px1, py1 = camera.world_to_screen(center_wx - draw_w / 2.0, center_wy - draw_h / 2.0)
    px2, py2 = camera.world_to_screen(center_wx + draw_w / 2.0, center_wy + draw_h / 2.0)
    player_draw_rect = pygame.Rect(
        int(px1),
        int(py1),
        max(1, int(px2 - px1)),
        max(1, int(py2 - py1)),
    )

    bounce_y = 0.0
    if won:
        bounce_y = abs(math.sin(pygame.time.get_ticks() * 0.012)) * (player_draw_rect.h * 0.25)

    player_render_rect = pygame.Rect(
        player_draw_rect.x,
        int(player_draw_rect.y - bounce_y),
        player_draw_rect.w,
        player_draw_rect.h,
    )

    if player_render_rect.w >= 4 and player_render_rect.h >= 4:
        facing_sprites = player_sprites.get(player.facing, player_sprites["down"])
        cur_sprite = facing_sprites[player.anim_frame % len(facing_sprites)]
        scaled_player = pygame.transform.smoothscale(cur_sprite, (player_render_rect.w, player_render_rect.h))
        screen.blit(scaled_player, player_render_rect.topleft)
    else:
        radius = max(0, int(4 * scale))
        pygame.draw.rect(screen, COLOR_PLAYER, player_render_rect, border_radius=radius)

    # 绘制追赶的大灰狼
    if wolf.active:
        w_draw_w = CELL_SIZE * 1.35
        w_draw_h = CELL_SIZE * 1.35
        w_px1, w_py1 = camera.world_to_screen(wolf.x - w_draw_w / 2.0, wolf.y - w_draw_h / 2.0)
        w_px2, w_py2 = camera.world_to_screen(wolf.x + w_draw_w / 2.0, wolf.y + w_draw_h / 2.0)
        wolf_draw_rect = pygame.Rect(
            int(w_px1),
            int(w_py1),
            max(1, int(w_px2 - w_px1)),
            max(1, int(w_py2 - w_py1)),
        )

        facing_key = "cry" if wolf.crying else wolf.facing
        w_frames = wolf_sprites.get(facing_key, wolf_sprites.get("down", []))
        if w_frames and wolf_draw_rect.w >= 4 and wolf_draw_rect.h >= 4:
            cur_w_sprite = w_frames[wolf.anim_frame % len(w_frames)]
            scaled_wolf = pygame.transform.smoothscale(cur_w_sprite, (wolf_draw_rect.w, wolf_draw_rect.h))
            screen.blit(scaled_wolf, wolf_draw_rect.topleft)

    # 2. 绘制顶部 HUD 栏
    pygame.draw.rect(screen, (14, 18, 28), (0, 0, maze_w, HUD_HEIGHT))
    pygame.draw.line(screen, (38, 52, 74), (0, HUD_HEIGHT), (maze_w, HUD_HEIGHT), 1)

    m = maze.metrics
    hud = f"🎮 迷宫大冒险 ({m.label}阶) | 路径 {m.path_length} 死胡同 {m.dead_ends}"
    screen.blit(font.render(hud, True, COLOR_HUD), (12, 14))

    # 3. 绘制右侧独立记分牌与状态面板 (提示字样在侧边显示，完全不遮挡地图)
    return _draw_sidebar(
        screen,
        font,
        big_font,
        current_world,
        difficulty_level,
        best_records,
        timer_started,
        current_time_sec,
        won,
        caught_by_wolf,
        total_score,
        last_round_score,
        score_doubled,
        game_mode,
        challenge_total_time,
        challenge_total_score,
        challenge_completed,
        show_auto_path,
        len(auto_visited_order) if auto_visited_order else 0,
        len(auto_path) if auto_path else 0,
        auto_search_idx,
        auto_path_idx,
        auto_path_phase,
        auto_advance_timer,
    )


def _draw_sidebar(
    screen: pygame.Surface,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    current_world: int,
    difficulty_level: int,
    best_records: dict[str, float],
    timer_started: bool,
    current_time_sec: float,
    won: bool,
    caught_by_wolf: bool,
    total_score: int,
    last_round_score: int,
    score_doubled: bool,
    game_mode: str,
    challenge_total_time: float,
    challenge_total_score: int,
    challenge_completed: bool,
    show_auto_path: bool = False,
    auto_visited_order_len: int = 0,
    auto_path_len: int = 0,
    auto_search_idx: float = 0.0,
    auto_path_idx: float = 0.0,
    auto_path_phase: str = "idle",
    auto_advance_timer: float = -1.0,
) -> tuple[dict[tuple[int, int], pygame.Rect], pygame.Rect]:
    """右侧独立记分牌面板：包含总得分、关卡分值、调试选关按钮、计时纪录与提示卡片。"""
    sw, sh = screen.get_size()
    sb_x = sw - SIDEBAR_WIDTH
    sb_w = SIDEBAR_WIDTH

    # 专门为侧边栏定义的精致字体大小，防止文字超出卡片边界
    f_title = _font(15)
    f_body = _font(14)
    f_small = _font(13)
    f_tiny = _font(12)
    f_banner = _font(19)

    # 1. 侧边栏整体背景与左分隔线
    sidebar_rect = pygame.Rect(sb_x, 0, sb_w, sh)
    pygame.draw.rect(screen, (16, 22, 34), sidebar_rect)
    pygame.draw.line(screen, (38, 52, 74), (sb_x, 0), (sb_x, sh), 2)

    pad_x = sb_x + 10
    card_w = sb_w - 20
    cur_y = 10

    # --- 卡片 1: 🏆 记分牌 (Scoreboard) ---
    c1_rect = pygame.Rect(pad_x, cur_y, card_w, 88)
    pygame.draw.rect(screen, (24, 34, 52), c1_rect, border_radius=8)
    pygame.draw.rect(screen, (48, 68, 98), c1_rect, width=1, border_radius=8)

    stage_idx = (current_world - 1) * 10 + difficulty_level
    t_mode_str = "🌟 自由模式" if game_mode == "free" else f"🏆 闯关模式 ({stage_idx}/20关)"
    t_title = f_title.render(f"模式: {t_mode_str}", True, (255, 220, 80))
    screen.blit(t_title, (pad_x + 10, cur_y + 8))

    t_total = f_body.render(f"累计总得分: {total_score:,} 分", True, (255, 240, 150))
    screen.blit(t_total, (pad_x + 10, cur_y + 34))

    if game_mode == "free":
        if last_round_score > 0:
            d_str = " (破纪录!)" if score_doubled else ""
            t_last = f_body.render(f"本局得分: +{last_round_score:,}分{d_str}", True, (120, 240, 160))
        elif caught_by_wolf:
            t_last = f_body.render("本局得分: 0 分 (被狼抓)", True, (255, 120, 120))
        else:
            t_last = f_body.render("本局得分: --", True, (180, 190, 205))
    else:
        t_last = f_body.render(f"闯关累计得分: {challenge_total_score:,} 分", True, (120, 240, 160))
    screen.blit(t_last, (pad_x + 10, cur_y + 58))

    cur_y += 96

    # --- 卡片 2: 📊 关卡分值与大关主题 (Level & World Info) ---
    c2_rect = pygame.Rect(pad_x, cur_y, card_w, 92)
    pygame.draw.rect(screen, (24, 34, 52), c2_rect, border_radius=8)
    pygame.draw.rect(screen, (48, 68, 98), c2_rect, width=1, border_radius=8)

    world_title = "🏰 第二大关：狼穴地牢" if current_world == 2 else "🌲 第一大关：绿野森林"
    t_world = f_title.render(world_title, True, (255, 130, 130) if current_world == 2 else (130, 230, 150))
    screen.blit(t_world, (pad_x + 10, cur_y + 8))

    base_pts = (current_world - 1) * 1000 + difficulty_level * 100
    rec_pts = base_pts * 2
    if game_mode == "free":
        t_lvl = f_body.render(f"当前关卡: 第{current_world}大关 {difficulty_level}阶", True, (220, 230, 245))
        t_pts = f_small.render(f"通关: +{base_pts} 分 | 破纪录: +{rec_pts} 分", True, (160, 210, 255))
    else:
        t_lvl = f_body.render(f"闯关进度: 第 {stage_idx} / 20 关", True, (220, 230, 245))
        t_pts = f_small.render(f"本阶得分: +{base_pts} 分 (破纪录加倍)", True, (160, 210, 255))

    screen.blit(t_lvl, (pad_x + 10, cur_y + 34))
    screen.blit(t_pts, (pad_x + 10, cur_y + 60))

    cur_y += 100

    # --- 卡片 3: 🎯 调试选关按钮 (Level Select Card) ---
    c3_rect = pygame.Rect(pad_x, cur_y, card_w, 88)
    pygame.draw.rect(screen, (24, 34, 52), c3_rect, border_radius=8)
    pygame.draw.rect(screen, (48, 68, 98), c3_rect, width=1, border_radius=8)

    t_sel_title = f_small.render("🎯 调试选关按钮 (点击直跳关卡):", True, (255, 220, 90))
    screen.blit(t_sel_title, (pad_x + 10, cur_y + 6))

    sidebar_level_rects: dict[tuple[int, int], pygame.Rect] = {}

    # 第一大关 1~10 🌲
    lbl_w1 = f_tiny.render("🌲W1", True, (130, 230, 150))
    screen.blit(lbl_w1, (pad_x + 6, cur_y + 30))
    for lvl in range(1, 11):
        bx = pad_x + 46 + (lvl - 1) * 20
        by = cur_y + 28
        brect = pygame.Rect(bx, by, 18, 22)
        sidebar_level_rects[(1, lvl)] = brect

        is_active = (current_world == 1 and lvl == difficulty_level)
        bg_c = (38, 88, 56) if is_active else (22, 48, 34)
        border_c = (255, 220, 80) if is_active else (60, 130, 80)

        pygame.draw.rect(screen, bg_c, brect, border_radius=3)
        pygame.draw.rect(screen, border_c, brect, width=2 if is_active else 1, border_radius=3)

        txt_s = f_tiny.render(str(lvl), True, (255, 240, 150) if is_active else (210, 225, 235))
        screen.blit(txt_s, txt_s.get_rect(center=brect.center))

    # 第二大关 1~10 🏰
    lbl_w2 = f_tiny.render("🏰W2", True, (255, 130, 130))
    screen.blit(lbl_w2, (pad_x + 6, cur_y + 58))
    for lvl in range(1, 11):
        bx = pad_x + 46 + (lvl - 1) * 20
        by = cur_y + 56
        brect = pygame.Rect(bx, by, 18, 22)
        sidebar_level_rects[(2, lvl)] = brect

        is_active = (current_world == 2 and lvl == difficulty_level)
        bg_c = (98, 38, 52) if is_active else (56, 22, 32)
        border_c = (255, 220, 80) if is_active else (180, 60, 80)

        pygame.draw.rect(screen, bg_c, brect, border_radius=3)
        pygame.draw.rect(screen, border_c, brect, width=2 if is_active else 1, border_radius=3)

        txt_s = f_tiny.render(str(lvl), True, (255, 240, 150) if is_active else (235, 210, 220))
        screen.blit(txt_s, txt_s.get_rect(center=brect.center))

    cur_y += 96

    # --- 🧭 自动寻路按钮 ---
    btn_auto_rect = pygame.Rect(pad_x, cur_y, card_w, 30)
    hover_auto = btn_auto_rect.collidepoint(pygame.mouse.get_pos())
    if show_auto_path:
        bg_a = (20, 80, 100) if hover_auto else (15, 60, 80)
        border_a = (0, 240, 255)
        if auto_path_phase == "search":
            progress = int(auto_search_idx / max(1, auto_visited_order_len) * 100)
            txt_str = f"🧭 寻路算法探索中... ({progress}%)"
        elif auto_path_phase == "path":
            progress = int(auto_path_idx / max(1, auto_path_len) * 100)
            txt_str = f"🧭 生成通关路线中... ({progress}%)"
        else:
            txt_str = "🧭 自动寻路：已开启 [点击隐藏路线]"
        txt_a = font.render(txt_str, True, (200, 250, 255))
    else:
        bg_a = (38, 52, 74) if hover_auto else (24, 34, 52)
        border_a = (100, 180, 255) if hover_auto else (48, 68, 98)
        txt_a = font.render("🧭 自动寻路：已关闭 [点击演示过程]", True, (220, 235, 245))

    pygame.draw.rect(screen, bg_a, btn_auto_rect, border_radius=6)
    pygame.draw.rect(screen, border_a, btn_auto_rect, width=2 if (hover_auto or show_auto_path) else 1, border_radius=6)
    screen.blit(txt_a, txt_a.get_rect(center=btn_auto_rect.center))

    cur_y += 38

    # --- 卡片 4: ⏱️ 计时 & 纪录 (Timer & Record) ---
    c3_rect = pygame.Rect(pad_x, cur_y, card_w, 72)
    pygame.draw.rect(screen, (24, 34, 52), c3_rect, border_radius=8)
    pygame.draw.rect(screen, (48, 68, 98), c3_rect, width=1, border_radius=8)

    time_str = f"{current_time_sec:.2f} 秒" if timer_started else "按方向键开始"
    rec_key = f"{current_world}_{difficulty_level}"
    best_sec = best_records.get(rec_key)
    best_str = f"{best_sec:.2f} 秒" if best_sec is not None else "无纪录"

    if game_mode == "free":
        t_time = f_body.render(f"当前用时: {time_str}", True, (255, 230, 140) if timer_started else (170, 180, 195))
        t_best = f_body.render(f"本关最佳纪录: {best_str}", True, (180, 220, 255))
    else:
        t_time = f_body.render(f"本关用时: {time_str}", True, (255, 230, 140) if timer_started else (170, 180, 195))
        t_best = f_body.render(f"闯关累计用时: {challenge_total_time:.2f} 秒", True, (180, 220, 255))

    screen.blit(t_time, (pad_x + 10, cur_y + 10))
    screen.blit(t_best, (pad_x + 10, cur_y + 38))

    cur_y += 82

    # --- 卡片 5: 💬 游戏状态与过关/被抓提示 (Status Banner) ---
    c4_h = 135
    c4_rect = pygame.Rect(pad_x, cur_y, card_w, c4_h)

    if game_mode == "challenge" and challenge_completed:
        pygame.draw.rect(screen, (38, 78, 52), c4_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 180, 100), c4_rect, width=2, border_radius=8)

        st1 = f_banner.render("🏆 大满贯全通关！", True, (255, 255, 100))
        st2 = f_body.render(f"1~20关总用时: {challenge_total_time:.2f} 秒", True, (220, 255, 220))
        st3 = f_body.render(f"获得全通总分: +{challenge_total_score:,} 分", True, (255, 220, 100))
        st4 = f_body.render("👉 按 R 重测，按 M 返回主菜单", True, (255, 240, 180))

        screen.blit(st1, (pad_x + 10, cur_y + 8))
        screen.blit(st2, (pad_x + 10, cur_y + 38))
        screen.blit(st3, (pad_x + 10, cur_y + 64))
        screen.blit(st4, (pad_x + 10, cur_y + 94))

    elif won:
        pygame.draw.rect(screen, (38, 78, 52), c4_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 180, 100), c4_rect, width=2, border_radius=8)

        st1 = f_banner.render("🎉 成功通关！", True, (255, 255, 100))
        st2 = f_body.render(f"获得积分: +{last_round_score} 分", True, (220, 255, 220))
        if score_doubled:
            st3 = f_body.render("🏆 破纪录积分翻倍！", True, (255, 220, 100))
        else:
            st3 = f_body.render("再接再厉，挑战更快速度！", True, (200, 230, 210))

        if auto_advance_timer > 0:
            st4 = f_body.render(f"👉 {auto_advance_timer:.1f}s后自动跳下关 (按空格加速)", True, (255, 240, 180))
        else:
            if current_world == 1:
                next_str = f"第1大关 {difficulty_level + 1}阶" if difficulty_level < 10 else "第2大关 1阶"
            else:
                next_str = f"第2大关 {difficulty_level + 1}阶" if difficulty_level < 10 else "第1大关 1阶"
            st4 = f_body.render(f"👉 按 R/空格/点击进入 {next_str}", True, (255, 240, 180))

        screen.blit(st1, (pad_x + 12, cur_y + 8))
        screen.blit(st2, (pad_x + 12, cur_y + 40))
        screen.blit(st3, (pad_x + 12, cur_y + 64))
        screen.blit(st4, (pad_x + 12, cur_y + 94))

    elif caught_by_wolf:
        pygame.draw.rect(screen, (110, 28, 36), c4_rect, border_radius=8)
        pygame.draw.rect(screen, (200, 60, 70), c4_rect, width=2, border_radius=8)

        st1 = f_banner.render("😱 被狼抓住了！", True, (255, 220, 220))
        st2 = f_body.render("本局得分: 0 分", True, (255, 180, 180))
        st3 = f_body.render("被大灰狼追上了...", True, (230, 190, 190))
        st4 = f_body.render("👉 按 R 重新尝试本关", True, (255, 240, 180))

        screen.blit(st1, (pad_x + 10, cur_y + 8))
        screen.blit(st2, (pad_x + 10, cur_y + 38))
        screen.blit(st3, (pad_x + 10, cur_y + 64))
        screen.blit(st4, (pad_x + 10, cur_y + 94))

    else:
        pygame.draw.rect(screen, (24, 34, 52), c4_rect, border_radius=8)
        pygame.draw.rect(screen, (48, 68, 98), c4_rect, width=1, border_radius=8)

        if game_mode == "free":
            st1 = f_body.render("🟢 正在自由模式练习...", True, (120, 230, 160))
            st2 = f_body.render("按 WASD / 方向键移动", True, (190, 200, 215))
            st3 = f_body.render("避开大灰狼到达小屋", True, (190, 200, 215))
            st4 = f_body.render("按 M 键可随时返回菜单", True, (170, 180, 200))
        else:
            st1 = f_body.render(f"🟢 闯关挑战中 ({stage_idx}/20关)", True, (120, 230, 160))
            st2 = f_body.render("按 WASD / 方向键移动", True, (190, 200, 215))
            st3 = f_body.render("顺序挑战 20 阶全部迷宫", True, (190, 200, 215))
            st4 = f_body.render("创造最快全通时间与高分！", True, (170, 180, 200))

        screen.blit(st1, (pad_x + 10, cur_y + 12))
        screen.blit(st2, (pad_x + 10, cur_y + 38))
        screen.blit(st3, (pad_x + 10, cur_y + 64))
        screen.blit(st4, (pad_x + 10, cur_y + 90))

    cur_y += c4_h + 10

    # --- 卡片 6: 🕹️ 操作快捷键 (Controls) ---
    c5_h = max(110, sh - cur_y - 10)
    c5_rect = pygame.Rect(pad_x, cur_y, card_w, c5_h)
    pygame.draw.rect(screen, (20, 28, 44), c5_rect, border_radius=8)
    pygame.draw.rect(screen, (38, 52, 78), c5_rect, width=1, border_radius=8)

    t_ctrl_title = f_title.render("🕹️ 快捷键指南", True, (180, 200, 220))
    screen.blit(t_ctrl_title, (pad_x + 10, cur_y + 8))

    ctrl_lines = [
        "M / ESC : 返回模式菜单",
        "WASD / 方向键 : 移动小人",
        "R : 重生成/下关 | P : 换外观",
        "F : 召唤狼 | H : 自动寻路",
        "C / Space : 切换视角",
    ]
    for i, line in enumerate(ctrl_lines):
        t_l = f_small.render(line, True, (140, 155, 175))
        screen.blit(t_l, (pad_x + 10, cur_y + 28 + i * 19))
        screen.blit(t_l, (pad_x + 10, cur_y + 28 + i * 20))

    return sidebar_level_rects, btn_auto_rect


if __name__ == "__main__":
    main()
