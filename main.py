"""可玩原型：生成迷宫、方向键/WASD 走动、撞墙停下。"""

from __future__ import annotations

import functools
import json
import math
import os
import sys
import time

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
    create_sound_bgm_pattern,
    create_sound_bgm_shape,
    create_sound_bgm_woven,
    create_sound_caught,
    create_sound_item,
    create_sound_start,
    create_sound_step,
    create_sound_win,
    create_sound_wolf,
    create_tree_surface,
    create_wolf_sprites,
    load_all_player_skins,
)
from maze import Maze, assert_perfect_maze, generate_maze, get_keep_going_progress
from player import Player

CELL_SIZE = 26  # 房间变大后略缩小格子，尽量仍能在常见分辨率下完整显示
HUD_HEIGHT = 48
SIDEBAR_WIDTH = 290  # 右侧独立记分牌与状态面板宽度 (加宽至 290px，避免中文字体宽度挤压)
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


@functools.lru_cache(maxsize=128)
def _get_scaled_surf(surf: pygame.Surface, w: int, h: int) -> pygame.Surface:
    return pygame.transform.smoothscale(surf, (w, h))


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

    def focus_player(self, player: Player, screen: pygame.Surface, maze: Maze | None = None) -> None:
        """聚焦玩家视角（地图放大跟随模式）。"""
        if maze is not None:
            sw, sh = screen.get_size()
            avail_w = max(1, sw - SIDEBAR_WIDTH)
            avail_h = max(1, sh - HUD_HEIGHT)
            mw = maze.cols * CELL_SIZE
            mh = maze.rows * CELL_SIZE
            scale_w = (avail_w - 16) / mw
            scale_h = (avail_h - 16) / mh
            self.fit_scale = min(1.0, scale_w, scale_h)

        target_render_size = 30.0  # 保持与 Level 10 同等舒适的放大渲染尺寸
        self.scale = max(1.0, target_render_size / CELL_SIZE)
        self.following_player = True
        self.snap_player_focus(player, screen)

    def snap_player_focus(self, player: Player, screen: pygame.Surface) -> None:
        if not self.following_player:
            return
        sw, sh = screen.get_size()
        avail_w = max(1, sw - SIDEBAR_WIDTH)
        avail_h = max(1, sh - HUD_HEIGHT)
        vc_x = avail_w / 2.0
        vc_y = HUD_HEIGHT + avail_h / 2.0
        px = player.x + player.size * 0.5
        py = player.y + player.size * 0.5
        self.offset_x = vc_x - px * self.scale
        self.offset_y = vc_y - py * self.scale

    def update_player_focus(self, player: Player, screen: pygame.Surface, dt: float = 1.0 / 60.0) -> None:
        if not self.following_player:
            return
        sw, sh = screen.get_size()
        avail_w = max(1, sw - SIDEBAR_WIDTH)
        avail_h = max(1, sh - HUD_HEIGHT)
        vc_x = avail_w / 2.0
        vc_y = HUD_HEIGHT + avail_h / 2.0
        px = player.x + player.size * 0.5
        py = player.y + player.size * 0.5
        target_x = vc_x - px * self.scale
        target_y = vc_y - py * self.scale

        # 平滑缓动 (Lerp) 追随，彻底解决剧烈画面跳动与眩晕眼花感
        lerp_rate = min(1.0, 14.0 * dt)
        self.offset_x += (target_x - self.offset_x) * lerp_rate
        self.offset_y += (target_y - self.offset_y) * lerp_rate

    def toggle_view(self, maze: Maze, player: Player, screen: pygame.Surface) -> None:
        """按 C / Space / Z 键或点击侧边栏按钮：在全景还原与地图放大跟随视角之间切换。"""
        if not self.following_player:
            self.focus_player(player, screen, maze)
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


@functools.lru_cache(maxsize=1)
def _get_cjk_font_file_or_name() -> tuple[str | None, str | None]:
    """获取跨平台中文字体文件绝对路径或 SysFont 名称（优先绝对路径，100% 解决 Windows 乱码/豆腐块问题）。"""
    win_dir = os.environ.get("WINDIR", "C:\\Windows")
    win_font_paths = [
        os.path.join(win_dir, "Fonts", "msyh.ttc"),      # 微软雅黑
        os.path.join(win_dir, "Fonts", "msyh.ttf"),
        os.path.join(win_dir, "Fonts", "msyhbd.ttc"),
        os.path.join(win_dir, "Fonts", "simhei.ttf"),    # 黑体
        os.path.join(win_dir, "Fonts", "simsun.ttc"),    # 宋体
        os.path.join(win_dir, "Fonts", "deng.ttf"),      # 等线
        os.path.join(win_dir, "Fonts", "kaiti.ttf"),     # 楷体
    ]
    for path in win_font_paths:
        if os.path.exists(path):
            try:
                _test_font = pygame.font.Font(path, 16)
                return (path, None)
            except Exception:
                pass

    other_font_paths = [
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in other_font_paths:
        if os.path.exists(path):
            try:
                _test_font = pygame.font.Font(path, 16)
                return (path, None)
            except Exception:
                pass

    font_names = (
        "microsoftyahei", "msyh", "simhei", "simsun", "dengxian",
        "stheitimedium", "stheitilight", "stheiti", "hiraginosansgb", "pingfangsc",
        "wqy-microhei", "wqy-zenhei", "notosanscjksc", "arialunicode"
    )
    for name in font_names:
        matched_path = pygame.font.match_font(name)
        if matched_path and os.path.exists(matched_path):
            try:
                _test_font = pygame.font.Font(matched_path, 16)
                return (matched_path, None)
            except Exception:
                pass

    for name in font_names:
        try:
            sys_font = pygame.font.SysFont(name, 16)
            if sys_font:
                return (None, name)
        except Exception:
            pass

    return (None, None)


@functools.lru_cache(maxsize=128)
def _font(size: int) -> pygame.font.Font:
    """获取指定字号的 Font，带 LRU 缓存，彻底解决 Windows / macOS 逐帧匹配卡顿与字体无法显示问题。"""
    file_path, sys_name = _get_cjk_font_file_or_name()
    if file_path:
        try:
            return pygame.font.Font(file_path, size)
        except Exception:
            pass
    if sys_name:
        try:
            return pygame.font.SysFont(sys_name, size)
        except Exception:
            pass
    try:
        return pygame.font.SysFont("microsoftyahei", size)
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
    """根据地图大小动态计算合适的窗口物理尺寸，保证主界面菜单与地图完全显示。"""
    try:
        sizes = pygame.display.get_desktop_sizes()
        if sizes and sizes[0][0] >= 640 and sizes[0][1] >= 480:
            screen_w, screen_h = sizes[0]
        else:
            info = pygame.display.Info()
            screen_w = info.current_w if info.current_w >= 640 else 1280
            screen_h = info.current_h if info.current_h >= 800 else 800
    except Exception:
        screen_w, screen_h = 1280, 800

    desired_w = max(maze.cols * CELL_SIZE + SIDEBAR_WIDTH + 16, 980)
    desired_h = max(maze.rows * CELL_SIZE + HUD_HEIGHT + 16, 760)

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
    sound_item = create_sound_item()

    sound_bgm_menu = create_sound_bgm_menu()
    sound_bgm_free = create_sound_bgm_free()
    sound_bgm_challenge = create_sound_bgm_challenge()
    sound_bgm_dungeon = create_sound_bgm_dungeon()
    sound_bgm_pattern = create_sound_bgm_pattern()
    sound_bgm_shape = create_sound_bgm_shape()
    sound_bgm_woven = create_sound_bgm_woven()
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
    won = False
    win_path = []
    maze = _make_maze(current_world, difficulty_level)
    screen = pygame.display.set_mode(_window_size(maze), pygame.RESIZABLE)
    player = _spawn_player(maze)
    wolf = Wolf(CELL_SIZE)
    camera = Camera()
    camera.focus_player(player, screen, maze)
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
        if sound_item:
            sound_item.set_volume(vol_sfx)
        if sound_bgm_menu:
            sound_bgm_menu.set_volume(vol_bgm)
        if sound_bgm_free:
            sound_bgm_free.set_volume(vol_bgm)
        if sound_bgm_challenge:
            sound_bgm_challenge.set_volume(vol_bgm)
        if sound_bgm_dungeon:
            sound_bgm_dungeon.set_volume(vol_bgm)
        if sound_bgm_pattern:
            sound_bgm_pattern.set_volume(vol_bgm)
        if sound_bgm_shape:
            sound_bgm_shape.set_volume(vol_bgm)
        if sound_bgm_woven:
            sound_bgm_woven.set_volume(vol_bgm)

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
        if sound_bgm_pattern:
            sound_bgm_pattern.stop()
        if sound_bgm_shape:
            sound_bgm_shape.stop()
        if sound_bgm_woven:
            sound_bgm_woven.stop()

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
        elif key == "pattern":
            target = sound_bgm_pattern
        elif key == "shape":
            target = sound_bgm_shape
        elif key == "woven":
            target = sound_bgm_woven

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

    last_regen_time = 0.0
    REGEN_COOLDOWN = 0.30  # 秒，防连按连续重新生成

    def check_and_update_regen_cooldown() -> bool:
        nonlocal last_regen_time
        now = time.time()
        if now - last_regen_time < REGEN_COOLDOWN:
            return False
        last_regen_time = now
        return True

    item_tiles: set[tuple[int, int]] = set()
    total_items_count: int = 0
    gate_locked_tip_timer: float = 0.0
    sidebar_scroll_y: float = 0.0
    max_sidebar_scroll: float = 0.0

    def reset_level_state():
        nonlocal maze, screen, player, wolf, camera, won, win_path, caught_by_wolf, timer_started, start_time_ms, current_time_sec, auto_advance_timer, show_auto_path
        nonlocal auto_visited_order, auto_path, auto_parent_map, auto_search_idx, auto_path_idx, auto_path_phase
        nonlocal item_tiles, total_items_count, gate_locked_tip_timer, sidebar_scroll_y, max_sidebar_scroll
        if not check_and_update_regen_cooldown():
            return
        maze = _make_maze(current_world, difficulty_level)
        screen = pygame.display.set_mode(_window_size(maze), pygame.RESIZABLE)
        player = _spawn_player(maze)
        wolf = Wolf(CELL_SIZE)
        camera.focus_player(player, screen, maze)
        item_tiles = set(maze.item_tiles)
        total_items_count = len(item_tiles)
        gate_locked_tip_timer = 0.0
        sidebar_scroll_y = 0.0
        max_sidebar_scroll = 0.0
        show_auto_path = False
        win_path = []

        auto_visited_order = []
        auto_path = []
        auto_parent_map = {}
        auto_search_idx = 0.0
        auto_path_idx = 0.0
        auto_path_phase = "idle"

        if current_world == 5:
            switch_bgm("woven")
        elif current_world == 4:
            switch_bgm("shape")
        elif current_world == 3:
            switch_bgm("pattern")
        elif current_world == 2:
            switch_bgm("dungeon")
        elif game_mode == "challenge":
            switch_bgm("challenge")
        else:
            switch_bgm("free")

        if sound_start:
            sound_start.play()

        pygame.event.clear(pygame.KEYDOWN)
        pygame.event.clear(pygame.MOUSEBUTTONDOWN)

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
                else:
                    current_world = 3
                    difficulty_level = 1
                reset_level_state()
            elif current_world == 3:
                if difficulty_level < 10:
                    difficulty_level += 1
                else:
                    current_world = 4
                    difficulty_level = 1
                reset_level_state()
            elif current_world == 4:
                if difficulty_level < 10:
                    difficulty_level += 1
                else:
                    current_world = 5
                    difficulty_level = 1
                reset_level_state()
            elif current_world == 5:
                if difficulty_level < 10:
                    difficulty_level += 1
                    reset_level_state()
                else:
                    current_world = 6
                    difficulty_level = 1
                    reset_level_state()
            elif current_world == 6:
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
                elif current_world == 2:
                    current_world = 3
                    difficulty_level = 1
                elif current_world == 3:
                    current_world = 4
                    difficulty_level = 1
                elif current_world == 4:
                    current_world = 5
                    difficulty_level = 1
                elif current_world == 5:
                    current_world = 6
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
            if current_world == 6:
                current_world = 5
                difficulty_level = 10
            elif current_world == 5:
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
                current_world = 6
                difficulty_level = 10
        reset_level_state()

    # 开局播放声音
    if sound_start:
        sound_start.play()

    sidebar_level_rects: dict[int, pygame.Rect] = {}
    btn_auto_path_rect: pygame.Rect | None = None
    btn_view_rect: pygame.Rect | None = None
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
                    elif btn_view_rect and btn_view_rect.collidepoint(event.pos):
                        camera.toggle_view(maze, player, screen)
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
                elif mx >= screen.get_width() - SIDEBAR_WIDTH:
                    sidebar_scroll_y = max(0.0, min(max_sidebar_scroll, sidebar_scroll_y - event.y * 30.0))

        # 通关/被抓后停步，但仍可按 R / 数字键 重开。
        dt = clock.get_time() / 1000.0
        gate_locked_tip_timer = max(0.0, gate_locked_tip_timer - dt)
        if not won and not caught_by_wolf:
            keys = pygame.key.get_pressed()

            # 第一次按方向键后开启精确到 0.01s 的计时器
            if not timer_started:
                if any(keys[k] for k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s)):
                    timer_started = True
                    start_time_ms = pygame.time.get_ticks()

            if timer_started:
                current_time_sec = (pygame.time.get_ticks() - start_time_ms) / 1000.0

            player.update(keys, maze, CELL_SIZE, dt, sound_step)

            # 检查玩家是否踩到支线道具格并收集
            p_tile = (int(player.rect.centerx // CELL_SIZE), int(player.rect.centery // CELL_SIZE))
            if p_tile in item_tiles:
                item_tiles.remove(p_tile)
                if sound_item:
                    sound_item.play()

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
                if len(item_tiles) == 0:
                    won = True
                    if camera is not None and maze is not None:
                        camera.fit_maze(maze, screen)
                    if not (game_mode == "challenge" and challenge_completed):
                        auto_advance_timer = 5.0 if (current_world == 6 or getattr(maze, "word_prompt", "")) else 1.2
                    if maze:
                        win_path = maze.solve_path()
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
                        if current_world == 6 and difficulty_level == 10:
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
                else:
                    gate_locked_tip_timer = 2.0

            if camera.following_player:
                camera.update_player_focus(player, screen, dt)
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

        sidebar_level_rects, btn_auto_path_rect, btn_view_rect, max_sidebar_scroll = _draw(
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
            item_tiles,
            total_items_count,
            gate_locked_tip_timer,
            win_path,
            sidebar_scroll_y,
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
    title_rect = title_surf.get_rect(center=(cx, cy - 268))
    screen.blit(title_surf, title_rect)

    sub_surf = font.render("—— 请选择游戏模式 & 调整声音设置 ——", True, (170, 190, 215))
    sub_rect = sub_surf.get_rect(center=(cx, cy - 238))
    screen.blit(sub_surf, sub_rect)

    card_w = 560

    # 2. 模式 1 按钮：自由模式 (Free Mode)
    btn1_h = 48
    btn1_rect = pygame.Rect(cx - card_w // 2, cy - 222, card_w, btn1_h)
    hover1 = btn1_rect.collidepoint(mouse_pos)

    bg_color1 = (32, 48, 74) if hover1 else (22, 32, 52)
    border_color1 = (100, 180, 255) if hover1 else (48, 72, 108)
    pygame.draw.rect(screen, bg_color1, btn1_rect, border_radius=10)
    pygame.draw.rect(screen, border_color1, btn1_rect, width=2 if hover1 else 1, border_radius=10)

    t1 = font.render("🌟 1. 自由模式 (Free Mode)", True, (255, 240, 150) if hover1 else (230, 235, 245))
    screen.blit(t1, (btn1_rect.x + 18, btn1_rect.y + 4))

    desc1 = font.render("按 [1] 键或点击 | 1~10 阶自由切换，无限切关与随心练习", True, (160, 180, 205))
    screen.blit(desc1, (btn1_rect.x + 18, btn1_rect.y + 26))

    # 3. 模式 2 按钮：闯关模式 (Challenge Mode)
    btn2_h = 48
    btn2_rect = pygame.Rect(cx - card_w // 2, cy - 168, card_w, btn2_h)
    hover2 = btn2_rect.collidepoint(mouse_pos)

    bg_color2 = (32, 48, 74) if hover2 else (22, 32, 52)
    border_color2 = (255, 210, 90) if hover2 else (48, 72, 108)
    pygame.draw.rect(screen, bg_color2, btn2_rect, border_radius=10)
    pygame.draw.rect(screen, border_color2, btn2_rect, width=2 if hover2 else 1, border_radius=10)

    t2 = font.render("🏆 2. 闯关模式 (Challenge Mode)", True, (255, 220, 90) if hover2 else (230, 235, 245))
    screen.blit(t2, (btn2_rect.x + 18, btn2_rect.y + 4))

    desc2 = font.render("按 [2] 键或点击 | 森林 + 地牢 + 秘境 + 异形 + 立交 + 提示词 共 60 关连续大满贯", True, (160, 180, 205))
    screen.blit(desc2, (btn2_rect.x + 18, btn2_rect.y + 26))

    # 4. 卡片 3：🎯 调试/自由选关卡片 (六大关 60 阶)
    lvl_card_h = 192
    lvl_card = pygame.Rect(cx - card_w // 2, cy - 114, card_w, lvl_card_h)
    pygame.draw.rect(screen, (22, 32, 50), lvl_card, border_radius=10)
    pygame.draw.rect(screen, (60, 90, 140), lvl_card, width=1, border_radius=10)

    menu_level_rects: dict[tuple[int, int], pygame.Rect] = {}

    # 第一大关选关 (1~10 阶)
    lbl1 = small_font.render("🌲 第一大关 (绿野森林):", True, (130, 230, 150))
    screen.blit(lbl1, (lvl_card.x + 14, lvl_card.y + 8))
    for i in range(1, 11):
        bx = lvl_card.x + 200 + (i - 1) * 34
        by = lvl_card.y + 6
        brect = pygame.Rect(bx, by, 30, 24)
        menu_level_rects[(1, i)] = brect
        h_l = brect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (38, 88, 56) if h_l else (22, 48, 34), brect, border_radius=4)
        pygame.draw.rect(screen, (130, 230, 150) if h_l else (60, 130, 80), brect, width=1, border_radius=4)
        ts = small_font.render(str(i), True, (255, 240, 150) if h_l else (210, 235, 220))
        screen.blit(ts, ts.get_rect(center=brect.center))

    # 第二大关选关 (1~10 阶)
    lbl2 = small_font.render("🏰 第二大关 (狼穴地牢):", True, (255, 130, 130))
    screen.blit(lbl2, (lvl_card.x + 14, lvl_card.y + 39))
    for i in range(1, 11):
        bx = lvl_card.x + 200 + (i - 1) * 34
        by = lvl_card.y + 37
        brect = pygame.Rect(bx, by, 30, 24)
        menu_level_rects[(2, i)] = brect
        h_l = brect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (98, 38, 52) if h_l else (56, 22, 32), brect, border_radius=4)
        pygame.draw.rect(screen, (255, 130, 130) if h_l else (180, 60, 80), brect, width=1, border_radius=4)
        ts = small_font.render(str(i), True, (255, 240, 150) if h_l else (235, 210, 220))
        screen.blit(ts, ts.get_rect(center=brect.center))

    # 第三大关选关 (1~10 阶)
    lbl3 = small_font.render("🌟 第三大关 (图案秘境):", True, (210, 140, 255))
    screen.blit(lbl3, (lvl_card.x + 14, lvl_card.y + 70))
    for i in range(1, 11):
        bx = lvl_card.x + 200 + (i - 1) * 34
        by = lvl_card.y + 68
        brect = pygame.Rect(bx, by, 30, 24)
        menu_level_rects[(3, i)] = brect
        h_l = brect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (88, 38, 108) if h_l else (48, 22, 62), brect, border_radius=4)
        pygame.draw.rect(screen, (210, 140, 255) if h_l else (140, 60, 180), brect, width=1, border_radius=4)
        ts = small_font.render(str(i), True, (255, 240, 150) if h_l else (235, 210, 250))
        screen.blit(ts, ts.get_rect(center=brect.center))

    # 第四大关选关 (1~10 阶)
    lbl4 = small_font.render("🌀 第四大关 (异形几何):", True, (100, 230, 220))
    screen.blit(lbl4, (lvl_card.x + 14, lvl_card.y + 101))
    for i in range(1, 11):
        bx = lvl_card.x + 200 + (i - 1) * 34
        by = lvl_card.y + 99
        brect = pygame.Rect(bx, by, 30, 24)
        menu_level_rects[(4, i)] = brect
        h_l = brect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (38, 98, 98) if h_l else (22, 56, 56), brect, border_radius=4)
        pygame.draw.rect(screen, (100, 230, 220) if h_l else (60, 160, 150), brect, width=1, border_radius=4)
        ts = small_font.render(str(i), True, (255, 240, 150) if h_l else (210, 245, 240))
        screen.blit(ts, ts.get_rect(center=brect.center))

    # 第五大关选关 (1~10 阶)
    lbl5 = small_font.render("🌉 第五大关 (立交编织):", True, (120, 220, 255))
    screen.blit(lbl5, (lvl_card.x + 14, lvl_card.y + 132))
    for i in range(1, 11):
        bx = lvl_card.x + 200 + (i - 1) * 34
        by = lvl_card.y + 130
        brect = pygame.Rect(bx, by, 30, 24)
        menu_level_rects[(5, i)] = brect
        h_l = brect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (38, 78, 108) if h_l else (22, 44, 68), brect, border_radius=4)
        pygame.draw.rect(screen, (120, 220, 255) if h_l else (60, 140, 180), brect, width=1, border_radius=4)
        ts = small_font.render(str(i), True, (255, 240, 150) if h_l else (210, 235, 250))
        screen.blit(ts, ts.get_rect(center=brect.center))

    # 第六大关选关 (1~10 阶)
    lbl6 = small_font.render("🔤 第六大关 (提示词阵):", True, (100, 240, 255))
    screen.blit(lbl6, (lvl_card.x + 14, lvl_card.y + 163))
    for i in range(1, 11):
        bx = lvl_card.x + 200 + (i - 1) * 34
        by = lvl_card.y + 161
        brect = pygame.Rect(bx, by, 30, 24)
        menu_level_rects[(6, i)] = brect
        h_l = brect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (22, 60, 80) if h_l else (16, 40, 58), brect, border_radius=4)
        pygame.draw.rect(screen, (100, 240, 255) if h_l else (50, 150, 180), brect, width=1, border_radius=4)
        ts = small_font.render(str(i), True, (255, 240, 150) if h_l else (210, 245, 255))
        screen.blit(ts, ts.get_rect(center=brect.center))

    # 5. 卡片 4：🎵 声音大小设置 (Sound Volume Settings)
    c3_h = 106
    c3_rect = pygame.Rect(cx - card_w // 2, cy + 84, card_w, c3_h)
    pygame.draw.rect(screen, (22, 32, 50), c3_rect, border_radius=10)
    pygame.draw.rect(screen, (60, 90, 140), c3_rect, width=1, border_radius=10)

    v_title = font.render("🎵 声音大小设置", True, (255, 220, 90))
    screen.blit(v_title, (c3_rect.x + 16, c3_rect.y + 6))

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
    card4_h = 62
    card4_rect = pygame.Rect(cx - card_w // 2, cy + 196, card_w, card4_h)
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


def _draw_ramp_slope(screen: pygame.Surface, rect: pygame.Rect, scale: float, direction: str):
    """绘制靠近立交桥路格上的 3D 起伏坡道 (坡道纵深渐变与侧边挡板)"""
    if rect.w < 6 or rect.h < 6:
        return
    bw = max(4, int(rect.w * 0.68))
    bx = rect.centerx - bw // 2

    # 渐变坡道
    for i in range(rect.h):
        factor = i / float(rect.h) if direction == "south" else (rect.h - 1 - i) / float(rect.h)
        r = int(25 + factor * 35)
        g = int(90 + factor * 55)
        b = int(110 + factor * 75)
        pygame.draw.line(screen, (r, g, b), (bx, rect.top + i), (bx + bw, rect.top + i), width=1)

    # 两侧引桥护栏引导线
    rail_w = max(1, int(scale * 1.5))
    pygame.draw.line(screen, (100, 200, 240), (bx, rect.top), (bx, rect.bottom), width=rail_w)
    pygame.draw.line(screen, (100, 200, 240), (bx + bw, rect.top), (bx + bw, rect.bottom), width=rail_w)


def _draw_overpass_underpass(
    screen: pygame.Surface, rect: pygame.Rect, scale: float, cur_path: tuple[int, int, int], cur_wall: tuple[int, int, int]
):
    """绘制 2.5D 南北向立交桥 - 地下东西方向隧道底色与上下洞口黑框墙线"""
    # 1. 隧道底色 (稍深于普通路径，呈现地下深度)
    tunnel_bg = (max(0, cur_path[0] - 10), max(0, cur_path[1] - 15), max(0, cur_path[2] - 20))
    pygame.draw.rect(screen, tunnel_bg, rect)

    # 2. 上下洞口黑框墙线 (混凝土侧墙)
    line_w = max(1, int(scale * 1.5))
    pygame.draw.line(screen, cur_wall, (rect.left, rect.top), (rect.right, rect.top), width=line_w)
    pygame.draw.line(screen, cur_wall, (rect.left, rect.bottom - 1), (rect.right, rect.bottom - 1), width=line_w)

    # 3. 隧道暗部阴影 (使人在隧道下方时产生深景邃暗感)
    shadow_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    shadow_surf.fill((2, 5, 12, 100))
    screen.blit(shadow_surf, rect.topleft)


def _draw_overpass_bridge_deck(screen: pygame.Surface, rect: pygame.Rect, scale: float, cur_wall: tuple[int, int, int]):
    """绘制 2.5D 南北向高架桥面 - 南北方向立体桥面、两侧护栏与 3D 投射阴影"""
    bw = max(4, int(rect.w * 0.70))
    bx = rect.centerx - bw // 2

    # 1. 3D 投射阴影 (Drop Shadow 覆盖地面)
    shadow_off_x = max(2, int(scale * 3.5))
    shadow_off_y = max(1, int(scale * 2.0))
    shadow_rect = pygame.Rect(bx + shadow_off_x, rect.top + shadow_off_y, bw, rect.h)
    shadow_surf = pygame.Surface((shadow_rect.w, shadow_rect.h), pygame.SRCALPHA)
    shadow_surf.fill((2, 5, 12, 140))
    screen.blit(shadow_surf, shadow_rect.topleft)

    # 2. 南北高架桥纯净路面 (高出地面)
    bridge_deck = pygame.Rect(bx, rect.top, bw, rect.h)
    pygame.draw.rect(screen, (245, 248, 255), bridge_deck)

    # 3. 左右 3D 黑色桥壁框线
    line_w = max(1, int(scale * 1.5))
    pygame.draw.line(screen, cur_wall, (bx, rect.top), (bx, rect.bottom), width=line_w)
    pygame.draw.line(screen, cur_wall, (bx + bw - 1, rect.top), (bx + bw - 1, rect.bottom), width=line_w)

    # 4. 桥内两侧高对比红色彩线护栏
    if rect.w >= 8:
        pygame.draw.line(screen, (220, 40, 40), (bx + 2, rect.top), (bx + 2, rect.bottom), width=1)
        pygame.draw.line(screen, (220, 40, 40), (bx + bw - 3, rect.top), (bx + bw - 3, rect.bottom), width=1)


def _draw_overpass_ew_underpass(
    screen: pygame.Surface, rect: pygame.Rect, scale: float, cur_path: tuple[int, int, int], cur_wall: tuple[int, int, int]
):
    """绘制 2.5D 东西向立交桥 - 地下南北方向隧道底色与左右洞口黑框墙线"""
    tunnel_bg = (max(0, cur_path[0] - 10), max(0, cur_path[1] - 15), max(0, cur_path[2] - 20))
    pygame.draw.rect(screen, tunnel_bg, rect)

    line_w = max(1, int(scale * 1.5))
    pygame.draw.line(screen, cur_wall, (rect.left, rect.top), (rect.left, rect.bottom), width=line_w)
    pygame.draw.line(screen, cur_wall, (rect.right - 1, rect.top), (rect.right - 1, rect.bottom), width=line_w)

    shadow_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    shadow_surf.fill((2, 5, 12, 100))
    screen.blit(shadow_surf, rect.topleft)


def _draw_overpass_ew_bridge_deck(screen: pygame.Surface, rect: pygame.Rect, scale: float, cur_wall: tuple[int, int, int]):
    """绘制 2.5D 东西向高架桥面 - 东西方向立体桥面、上下护栏与 3D 投射阴影"""
    bh = max(4, int(rect.h * 0.70))
    by = rect.centery - bh // 2

    shadow_off_x = max(2, int(scale * 3.5))
    shadow_off_y = max(1, int(scale * 2.0))
    shadow_rect = pygame.Rect(rect.left + shadow_off_x, by + shadow_off_y, rect.w, bh)
    shadow_surf = pygame.Surface((shadow_rect.w, shadow_rect.h), pygame.SRCALPHA)
    shadow_surf.fill((2, 5, 12, 140))
    screen.blit(shadow_surf, shadow_rect.topleft)

    bridge_deck = pygame.Rect(rect.left, by, rect.w, bh)
    pygame.draw.rect(screen, (245, 248, 255), bridge_deck)

    line_w = max(1, int(scale * 1.5))
    pygame.draw.line(screen, cur_wall, (rect.left, by), (rect.right, by), width=line_w)
    pygame.draw.line(screen, cur_wall, (rect.left, by + bh - 1), (rect.right, by + bh - 1), width=line_w)

    if rect.h >= 8:
        pygame.draw.line(screen, (220, 40, 40), (rect.left, by + 2), (rect.right, by + 2), width=1)
        pygame.draw.line(screen, (220, 40, 40), (rect.left, by + bh - 3), (rect.right, by + bh - 3), width=1)


def _draw_player_sprite(
    screen: pygame.Surface,
    camera: Camera,
    player: Player,
    player_sprites: dict[str, list[pygame.Surface]],
    won: bool,
    scale: float,
):
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


def _draw_wolf_sprite(
    screen: pygame.Surface,
    camera: Camera,
    wolf: Wolf,
    wolf_sprites: dict[str, list[pygame.Surface]],
):
    if not wolf.active:
        return
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


WORLD_ITEM_INFO = {
    1: {"name": "蘑菇", "icon": "🍄", "unit": "朵"},
    2: {"name": "肉块", "icon": "🥩", "unit": "块"},
    3: {"name": "钥匙", "icon": "🔑", "unit": "把"},
    4: {"name": "宝石", "icon": "💎", "unit": "颗"},
    5: {"name": "能量核心", "icon": "⚡", "unit": "核"},
    6: {"name": "提示词卷轴", "icon": "📜", "unit": "卷"},
}


def _draw_item_icon(screen: pygame.Surface, rect: pygame.Rect, world: int, scale: float) -> None:
    """精细绘制各世界专属收集道具 (1:蘑菇 2:肉块 3:钥匙 4:宝石 5:能量核心)"""
    w = rect.w
    h = rect.h
    if w < 4 or h < 4:
        return
    cx, cy = rect.centerx, rect.centery

    if world == 1:
        stem_w = max(2, int(w * 0.22))
        stem_h = max(3, int(h * 0.35))
        stem_rect = pygame.Rect(cx - stem_w // 2, cy + int(h * 0.05), stem_w, stem_h)
        pygame.draw.rect(screen, (240, 230, 210), stem_rect, border_radius=2)

        cap_r = max(4, int(w * 0.38))
        pygame.draw.circle(screen, (225, 45, 45), (cx, cy - int(h * 0.05)), cap_r)

        dot_r = max(1, int(cap_r * 0.28))
        pygame.draw.circle(screen, (255, 255, 255), (cx - int(cap_r * 0.4), cy - int(h * 0.12)), dot_r)
        pygame.draw.circle(screen, (255, 255, 255), (cx + int(cap_r * 0.35), cy - int(h * 0.08)), dot_r)
        pygame.draw.circle(screen, (255, 255, 255), (cx, cy - int(h * 0.25)), dot_r)

    elif world == 2:
        bone_w = max(3, int(w * 0.52))
        bone_h = max(2, int(h * 0.18))
        pygame.draw.line(screen, (240, 235, 220), (cx - bone_w // 2, cy - int(h * 0.1)), (cx + bone_w // 2, cy + int(h * 0.1)), width=bone_h)
        pygame.draw.circle(screen, (240, 235, 220), (cx - bone_w // 2, cy - int(h * 0.1)), max(2, bone_h))
        pygame.draw.circle(screen, (240, 235, 220), (cx + bone_w // 2, cy + int(h * 0.1)), max(2, bone_h))

        meat_r = max(4, int(w * 0.32))
        pygame.draw.circle(screen, (180, 40, 50), (cx - int(w * 0.05), cy), meat_r)
        pygame.draw.circle(screen, (220, 90, 100), (cx - int(w * 0.05), cy), max(2, int(meat_r * 0.5)))

    elif world == 3:
        key_r = max(3, int(w * 0.22))
        key_x = cx - int(w * 0.15)
        key_y = cy - int(h * 0.12)
        pygame.draw.circle(screen, (255, 215, 0), (key_x, key_y), key_r, width=max(1, int(key_r * 0.4)))

        stem_len = max(5, int(w * 0.42))
        pygame.draw.line(screen, (255, 215, 0), (key_x, key_y), (key_x + stem_len, key_y + stem_len), width=max(2, int(scale * 2.2)))
        tx = key_x + int(stem_len * 0.7)
        ty = key_y + int(stem_len * 0.7)
        pygame.draw.line(screen, (255, 215, 0), (tx, ty), (tx + int(w * 0.15), ty - int(h * 0.15)), width=max(2, int(scale * 1.8)))

    elif world == 4:
        pts = [
            (cx, cy - int(h * 0.38)),
            (cx + int(w * 0.32), cy - int(h * 0.05)),
            (cx, cy + int(h * 0.38)),
            (cx - int(w * 0.32), cy - int(h * 0.05)),
        ]
        pygame.draw.polygon(screen, (0, 220, 255), pts)
        pygame.draw.polygon(screen, (200, 250, 255), pts, width=1)
        pygame.draw.line(screen, (255, 255, 255), (cx, cy - int(h * 0.38)), (cx, cy + int(h * 0.38)), width=1)

    elif world == 5:
        r_outer = max(4, int(w * 0.36))
        pygame.draw.circle(screen, (255, 40, 160), (cx, cy), r_outer, width=max(1, int(scale * 2.0)))
        pygame.draw.circle(screen, (0, 240, 255), (cx, cy), max(3, int(r_outer * 0.65)))
        pygame.draw.circle(screen, (255, 255, 220), (cx, cy), max(1, int(r_outer * 0.3)))

    elif world == 6:
        rw = max(4, int(w * 0.50))
        rh = max(3, int(h * 0.38))
        scroll_rect = pygame.Rect(cx - rw // 2, cy - rh // 2, rw, rh)
        pygame.draw.rect(screen, (245, 230, 180), scroll_rect)
        pygame.draw.rect(screen, (200, 150, 50), scroll_rect, width=max(1, int(scale * 1.5)))
        pygame.draw.line(screen, (100, 70, 20), (cx - int(rw * 0.3), cy - int(rh * 0.15)), (cx + int(rw * 0.3), cy - int(rh * 0.15)), width=max(1, int(scale * 1.2)))
        pygame.draw.line(screen, (100, 70, 20), (cx - int(rw * 0.3), cy + int(rh * 0.15)), (cx + int(rw * 0.2), cy + int(rh * 0.15)), width=max(1, int(scale * 1.2)))


def _draw_minimap(
    screen: pygame.Surface,
    maze: Maze,
    player: Player,
    wolf: Wolf,
    camera: Camera,
    show_auto_path: bool = False,
    auto_path: list[tuple[int, int]] | None = None,
    auto_path_idx: float = 0.0,
    item_tiles: set[tuple[int, int]] | None = None,
    current_world: int = 1,
) -> None:
    """在地图放大跟随模式下，于迷宫视口左侧（左上角）绘制全景小地图与视口定位框"""
    if not camera.following_player or maze is None:
        return

    screen_w, screen_h = screen.get_size()
    maze_w = screen_w - SIDEBAR_WIDTH
    avail_h = screen_h - HUD_HEIGHT

    # 小地图最大尺寸与左上角边缘留白
    max_mm_w = 160
    max_mm_h = 160
    mm_x = 16
    mm_y = HUD_HEIGHT + 16

    # 按照迷宫行列比例，等比计算小地图尺寸
    scale_w = max_mm_w / max(1, maze.cols * CELL_SIZE)
    scale_h = max_mm_h / max(1, maze.rows * CELL_SIZE)
    mm_scale = min(scale_w, scale_h)

    mm_w = max(70, int(maze.cols * CELL_SIZE * mm_scale))
    mm_h = max(70, int(maze.rows * CELL_SIZE * mm_scale))

    box_w = mm_w + 12
    box_h = mm_h + 26
    box_rect = pygame.Rect(mm_x, mm_y, box_w, box_h)

    # 1. 绘制半透明精致深色框底背板
    mm_surface = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    mm_surface.fill((12, 18, 30, 220))
    screen.blit(mm_surface, box_rect.topleft)
    pygame.draw.rect(screen, (60, 140, 200), box_rect, width=2)

    # 2. 标头说明文字
    f_mm = _font(12)
    lbl = f_mm.render("📍 小地图 (C/Space还原)", True, (200, 230, 255))
    screen.blit(lbl, (mm_x + 8, mm_y + 4))

    map_start_x = mm_x + 6
    map_start_y = mm_y + 20

    cw = mm_w / maze.cols
    ch = mm_h / maze.rows

    # 3. 绘制地图微缩点阵网格
    for y in range(maze.rows):
        row = maze.grid[y]
        for x in range(maze.cols):
            tile = row[x]
            tx = map_start_x + x * cw
            ty = map_start_y + y * ch
            t_rect = pygame.Rect(int(tx), int(ty), max(1, int(math.ceil(cw))), max(1, int(math.ceil(ch))))
            if tile == 1:
                pygame.draw.rect(screen, (28, 38, 56), t_rect)
            elif tile in (2, 3):
                pygame.draw.rect(screen, (80, 110, 160), t_rect)
            else:
                pygame.draw.rect(screen, (45, 80, 100), t_rect)

    # 起点 (树) & 终点 (小房子)
    ent_x = map_start_x + (maze.entrance[0] + 0.5) * cw
    ent_y = map_start_y + (maze.entrance[1] + 0.5) * ch
    pygame.draw.circle(screen, (40, 220, 100), (int(ent_x), int(ent_y)), max(2, int(min(cw, ch) * 1.2)))

    exit_x = map_start_x + (maze.exit[0] + 0.5) * cw
    exit_y = map_start_y + (maze.exit[1] + 0.5) * ch
    pygame.draw.circle(screen, (255, 60, 60), (int(exit_x), int(exit_y)), max(2, int(min(cw, ch) * 1.2)))

    # 待收集支线道具在小地图上的发光标记点
    if item_tiles:
        item_color = (255, 80, 80) if current_world == 1 else ((255, 120, 140) if current_world == 2 else ((255, 215, 0) if current_world == 3 else ((0, 230, 255) if current_world == 4 else ((255, 40, 200) if current_world == 5 else (0, 240, 255)))))
        for itx, ity in item_tiles:
            it_x = map_start_x + (itx + 0.5) * cw
            it_y = map_start_y + (ity + 0.5) * ch
            pygame.draw.circle(screen, item_color, (int(it_x), int(it_y)), max(2, int(min(cw, ch) * 1.3)))

    # 自动寻路线微缩轨迹
    if show_auto_path and auto_path and int(auto_path_idx) > 0:
        ap_pts = []
        for tx, ty in auto_path[:int(auto_path_idx)]:
            ap_x = map_start_x + (tx + 0.5) * cw
            ap_y = map_start_y + (ty + 0.5) * ch
            ap_pts.append((int(ap_x), int(ap_y)))
        if len(ap_pts) >= 2:
            pygame.draw.lines(screen, (255, 215, 0), False, ap_pts, width=max(1, int(min(cw, ch))))

    # 追赶的大灰狼
    if wolf.active:
        wx_cell = wolf.x / CELL_SIZE
        wy_cell = wolf.y / CELL_SIZE
        w_x = map_start_x + wx_cell * cw
        w_y = map_start_y + wy_cell * ch
        pygame.draw.circle(screen, (255, 50, 80), (int(w_x), int(w_y)), max(3, int(min(cw, ch) * 1.5)))

    # 玩家位置 (亮青色高亮发光点)
    px_cell = player.rect.centerx / CELL_SIZE
    py_cell = player.rect.centery / CELL_SIZE
    p_x = map_start_x + px_cell * cw
    p_y = map_start_y + py_cell * ch
    p_r = max(3, int(min(cw, ch) * 1.8))
    pygame.draw.circle(screen, (0, 255, 255), (int(p_x), int(p_y)), p_r)
    pygame.draw.circle(screen, (255, 255, 255), (int(p_x), int(p_y)), max(1, p_r - 2))

    # 4. 当前镜头视口框 (实时反映玩家屏幕所能看到的地图世界坐标)
    min_wx = max(0.0, (0 - camera.offset_x) / camera.scale)
    max_wx = min(maze.cols * CELL_SIZE, (maze_w - camera.offset_x) / camera.scale)
    min_wy = max(0.0, (HUD_HEIGHT - camera.offset_y) / camera.scale)
    max_wy = min(maze.rows * CELL_SIZE, (HUD_HEIGHT + avail_h - camera.offset_y) / camera.scale)

    vx1 = map_start_x + (min_wx / CELL_SIZE) * cw
    vy1 = map_start_y + (min_wy / CELL_SIZE) * ch
    vx2 = map_start_x + (max_wx / CELL_SIZE) * cw
    vy2 = map_start_y + (max_wy / CELL_SIZE) * ch

    v_rect = pygame.Rect(int(vx1), int(vy1), max(4, int(vx2 - vx1)), max(4, int(vy2 - vy1)))
    pygame.draw.rect(screen, (255, 230, 100), v_rect, width=1)


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
    item_tiles: set[tuple[int, int]] | None = None,
    total_items_count: int = 0,
    gate_locked_tip_timer: float = 0.0,
    win_path: list[tuple[int, int]] | None = None,
    sidebar_scroll_y: float = 0.0,
) -> tuple[dict[tuple[int, int], pygame.Rect], pygame.Rect, pygame.Rect, float]:
    if current_world == 6:
        # 第六大关：提示词隐语阵 (深邃青蓝底色、霓虹冰蓝墙体、高亮字形通路)
        cur_bg = (10, 20, 30)
        cur_wall = (30, 55, 80)
        cur_path = (30, 95, 120)
    elif current_world == 5:
        # 第五大关：立体立交赛博风 (深蓝地色、灰蓝墙体、天蓝高架通廊)
        cur_bg = (12, 16, 28)
        cur_wall = (35, 45, 65)
        cur_path = (25, 90, 110)
    elif current_world == 4:
        # 第四大关：异形几何科技青蓝调
        cur_bg = (10, 24, 32)
        cur_wall = (25, 75, 95)
        cur_path = (35, 120, 110)
    elif current_world == 3:
        # 第三大关：图案秘境梦幻星空紫调
        cur_bg = (18, 12, 32)
        cur_wall = (45, 30, 68)
        cur_path = (30, 80, 110)
    elif current_world == 2:
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

    # 计算角色与大灰狼是否位于东西或南北地下隧道内 (在桥下方)
    p_tx = int(player.rect.centerx // CELL_SIZE)
    p_ty = int(player.rect.centery // CELL_SIZE)
    p_in_tunnel = False
    if 0 <= p_tx < maze.cols and 0 <= p_ty < maze.rows:
        cur_t = maze.grid[p_ty][p_tx]
        if cur_t == 2 and player.overpass_layer == "ew_tunnel":
            p_in_tunnel = True
        elif cur_t == 3 and player.overpass_layer == "ns_tunnel":
            p_in_tunnel = True

    w_tx = int(wolf.x // CELL_SIZE) if wolf.active else -1
    w_ty = int(wolf.y // CELL_SIZE) if wolf.active else -1
    wolf_layer = getattr(wolf, "overpass_layer", "none") if wolf.active else "none"
    w_in_tunnel = False
    if wolf.active and 0 <= w_tx < maze.cols and 0 <= w_ty < maze.rows:
        cur_wt = maze.grid[w_ty][w_tx]
        if cur_wt == 2 and wolf_layer == "ew_tunnel":
            w_in_tunnel = True
        elif cur_wt == 3 and wolf_layer == "ns_tunnel":
            w_in_tunnel = True

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
            if tile == 1:
                pygame.draw.rect(screen, cur_wall, rect)
            elif tile == 0:
                color = cur_path
                is_pattern = (hasattr(maze, "pattern_cells") and (x, y) in maze.pattern_cells)
                is_shape = (current_world == 4 and hasattr(maze, "shape_cells") and (x, y) in maze.shape_cells)
                if is_pattern:
                    if won and current_world == 6:
                        pulse = (math.sin(time.time() * 10.0) + 1.0) * 0.5
                        r = int(25 + 30 * pulse)
                        g = int(170 + 75 * pulse)
                        b = int(220 + 35 * pulse)
                        color = (r, g, b)
                    else:
                        color = (45, 130, 160) if current_world == 6 else ((130, 45, 110) if current_world == 5 else (95, 45, 125))
                elif is_shape:
                    color = (30, 90, 110)
                pygame.draw.rect(screen, color, rect)

                # 3D 坡道起伏引桥渲染
                if y + 1 < maze.rows and maze.grid[y + 1][x] in (2, 3):
                    _draw_ramp_slope(screen, rect, scale, "south")
                elif y - 1 >= 0 and maze.grid[y - 1][x] in (2, 3):
                    _draw_ramp_slope(screen, rect, scale, "north")

                if is_pattern and current_world == 6 and rect.w >= 3:
                    if won:
                        pulse = (math.sin(time.time() * 12.0) + 1.0) * 0.5
                        bc = (int(140 + 115 * pulse), 255, 255)
                        border_w = max(2, int(scale * 3))
                        pygame.draw.rect(screen, bc, rect, width=border_w)
                    else:
                        pygame.draw.rect(screen, (80, 240, 255), rect, width=1)
                elif is_pattern and rect.w >= 4 and rect.h >= 4:
                    pygame.draw.rect(screen, (255, 120, 140) if current_world == 5 else (220, 160, 255), rect, width=1)
                elif is_shape and rect.w >= 4 and rect.h >= 4:
                    pygame.draw.rect(screen, (150, 240, 255), rect, width=1)

                # 绘制待收集过关支线道具
                if item_tiles and (x, y) in item_tiles:
                    _draw_item_icon(screen, rect, current_world, scale)

            elif tile == 2:
                # OVERPASS_NS: 南北高架桥，东西地下隧道
                _draw_overpass_underpass(screen, rect, scale, cur_path, cur_wall)
                if p_in_tunnel and (x, y) == (p_tx, p_ty):
                    _draw_player_sprite(screen, camera, player, player_sprites, won, scale)
                if w_in_tunnel and (x, y) == (w_tx, w_ty):
                    _draw_wolf_sprite(screen, camera, wolf, wolf_sprites)
                _draw_overpass_bridge_deck(screen, rect, scale, cur_wall)

            elif tile == 3:
                # OVERPASS_EW: 东西高架桥，南北地下隧道
                _draw_overpass_ew_underpass(screen, rect, scale, cur_path, cur_wall)
                if p_in_tunnel and (x, y) == (p_tx, p_ty):
                    _draw_player_sprite(screen, camera, player, player_sprites, won, scale)
                if w_in_tunnel and (x, y) == (w_tx, w_ty):
                    _draw_wolf_sprite(screen, camera, wolf, wolf_sprites)
                _draw_overpass_ew_bridge_deck(screen, rect, scale, cur_wall)

    # 入口与出口瓦片及图案 (起点大树、终点小房子)
    is_gate_locked = bool(item_tiles and len(item_tiles) > 0)
    for (tx, ty), color, surf in (
        (maze.entrance, COLOR_ENTRANCE, tree_surf),
        (maze.exit, (120, 40, 50) if is_gate_locked else COLOR_EXIT, house_surf),
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
                scaled_surf = _get_scaled_surf(surf, rect.w, rect.h)
                screen.blit(scaled_surf, rect.topleft)

            # 出口小屋锁头 🔒 / 通关光环 🔓 绘制
            if (tx, ty) == maze.exit and rect.w >= 6 and rect.h >= 6:
                if is_gate_locked:
                    lock_size = max(10, int(rect.w * 0.45))
                    lock_rect = pygame.Rect(rect.centerx - lock_size // 2, rect.top - lock_size // 2, lock_size, lock_size)
                    pygame.draw.rect(screen, (220, 30, 40), lock_rect, border_radius=4)
                    pygame.draw.rect(screen, (255, 215, 0), lock_rect, width=1, border_radius=4)
                    f_lock = _font(max(9, int(lock_size * 0.7)))
                    t_lock = f_lock.render("🔒", True, (255, 255, 255))
                    screen.blit(t_lock, t_lock.get_rect(center=lock_rect.center))
                else:
                    pygame.draw.rect(screen, (80, 255, 120), rect, width=max(2, int(scale * 3.0)))
                    f_lock = _font(max(9, int(rect.w * 0.3)))
                    t_lock = f_lock.render("🔓", True, (255, 255, 255))
                    screen.blit(t_lock, t_lock.get_rect(center=(rect.centerx, rect.top)))

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

        # B) 找到终点后，绘制通关路径或自动寻路全景路线
        active_draw_path = []
        if won and win_path:
            active_draw_path = win_path
        elif show_auto_path and auto_path and path_idx_int > 0 and auto_path_phase in ("path", "complete"):
            active_draw_path = auto_path[:path_idx_int]

        if active_draw_path:
            points = []
            for tx, ty in active_draw_path:
                cx = (tx + 0.5) * CELL_SIZE
                cy = (ty + 0.5) * CELL_SIZE
                sx, sy = camera.world_to_screen(cx, cy)
                points.append((sx, sy))

            if len(points) >= 2:
                if current_world == 6:
                    glow_w = max(5, int(scale * 10))
                    core_w = max(3, int(scale * 5))
                    pygame.draw.lines(screen, (0, 220, 255), False, points, width=glow_w)
                    pygame.draw.lines(screen, (230, 255, 255), False, points, width=core_w)
                    r_dot = max(2, int(scale * 3.5))
                    for px, py in points:
                        pygame.draw.circle(screen, (50, 230, 255), (int(px), int(py)), r_dot)
                elif current_world == 5:
                    glow_w = max(5, int(scale * 10))
                    core_w = max(3, int(scale * 5))
                    pygame.draw.lines(screen, (140, 15, 15), False, points, width=glow_w)
                    pygame.draw.lines(screen, (235, 40, 40), False, points, width=core_w)
                    r_dot = max(2, int(scale * 3.5))
                    for px, py in points:
                        pygame.draw.circle(screen, (235, 40, 40), (int(px), int(py)), r_dot)
                else:
                    glow_w = max(3, int(scale * 8))
                    core_w = max(1, int(scale * 3))
                    pygame.draw.lines(screen, (255, 200, 50), False, points, width=glow_w)
                    pygame.draw.lines(screen, (255, 255, 220), False, points, width=core_w)
                    r_dot = max(2, int(scale * 3))
                    for px, py in points:
                        pygame.draw.circle(screen, (255, 220, 80), (int(px), int(py)), r_dot)

    # 绘制玩家 (若不在地下隧道穿梭状态，在最上层绘制)
    if not p_in_tunnel:
        _draw_player_sprite(screen, camera, player, player_sprites, won, scale)

    # 绘制追赶的大灰狼 (若不在地下隧道穿梭状态，在最上层绘制)
    if not w_in_tunnel:
        _draw_wolf_sprite(screen, camera, wolf, wolf_sprites)

    # 绘制小地图 (仅在放大模式下显示于视口左侧)
    _draw_minimap(
        screen,
        maze,
        player,
        wolf,
        camera,
        show_auto_path,
        auto_path,
        auto_path_idx,
        item_tiles,
        current_world,
    )

    # 如果尝试未集齐道具进门，绘制醒目的顶部上锁警示横幅
    if gate_locked_tip_timer > 0.0 and item_tiles:
        item_info = WORLD_ITEM_INFO.get(current_world, WORLD_ITEM_INFO[1])
        rem_c = len(item_tiles)
        col_c = max(0, total_items_count - rem_c)
        tip_str = f"🔒 大门未开启！需集齐 7 个 {item_info['icon']}{item_info['name']} (已收集 {col_c} 个，还有 {rem_c} 个未收集)"
        f_tip = _font(15)
        tip_surf = f_tip.render(tip_str, True, (255, 235, 120))
        bg_w = tip_surf.get_width() + 28
        bg_h = 32
        bg_rect = pygame.Rect((maze_w - bg_w) // 2, HUD_HEIGHT + 10, bg_w, bg_h)
        pygame.draw.rect(screen, (160, 20, 35), bg_rect, border_radius=6)
        pygame.draw.rect(screen, (255, 215, 0), bg_rect, width=2, border_radius=6)
        screen.blit(tip_surf, tip_surf.get_rect(center=bg_rect.center))

    if won and current_world == 6:
        prog_str = get_keep_going_progress(difficulty_level)
        word_str = f"🎉 破译字母路径：【 {maze.word_prompt} 】   拼词进度：{prog_str}"
        f_word = _font(17)
        word_surf = f_word.render(word_str, True, (100, 240, 255))
        bg_w = word_surf.get_width() + 36
        bg_h = 38
        bg_rect = pygame.Rect((maze_w - bg_w) // 2, HUD_HEIGHT + 10, bg_w, bg_h)
        pygame.draw.rect(screen, (20, 40, 70), bg_rect, border_radius=6)
        pygame.draw.rect(screen, (0, 230, 255), bg_rect, width=2, border_radius=6)
        screen.blit(word_surf, word_surf.get_rect(center=bg_rect.center))
    elif won and getattr(maze, "word_prompt", ""):
        word_str = f"🎉 破译隐秘提示词：【 {maze.word_prompt} 】！"
        f_word = _font(18)
        word_surf = f_word.render(word_str, True, (100, 240, 255))
        bg_w = word_surf.get_width() + 36
        bg_h = 38
        bg_rect = pygame.Rect((maze_w - bg_w) // 2, HUD_HEIGHT + 10, bg_w, bg_h)
        pygame.draw.rect(screen, (20, 40, 70), bg_rect, border_radius=6)
        pygame.draw.rect(screen, (0, 230, 255), bg_rect, width=2, border_radius=6)
        screen.blit(word_surf, word_surf.get_rect(center=bg_rect.center))

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
        camera,
        item_tiles,
        total_items_count,
        gate_locked_tip_timer,
        win_path,
        sidebar_scroll_y,
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
    camera: Camera | None = None,
    item_tiles: set[tuple[int, int]] | None = None,
    total_items_count: int = 0,
    gate_locked_tip_timer: float = 0.0,
    win_path: list[tuple[int, int]] | None = None,
    sidebar_scroll_y: float = 0.0,
) -> tuple[dict[tuple[int, int], pygame.Rect], pygame.Rect, pygame.Rect, float]:
    """右侧独立记分牌面板：包含总得分、关卡分值、调试选关按钮、计时纪录与提示卡片。"""
    sw, sh = screen.get_size()
    sb_x = sw - SIDEBAR_WIDTH
    sb_w = SIDEBAR_WIDTH

    f_title = _font(14)
    f_body = _font(13)
    f_small = _font(12)
    f_tiny = _font(11)
    f_banner = _font(17)

    # 1. 侧边栏整体背景与左分隔线
    sidebar_rect = pygame.Rect(sb_x, 0, sb_w, sh)
    pygame.draw.rect(screen, (16, 22, 34), sidebar_rect)
    pygame.draw.line(screen, (38, 52, 74), (sb_x, 0), (sb_x, sh), 2)

    total_content_h = 710.0
    max_scroll_y = max(0.0, total_content_h - sh + 12.0)
    scroll_y = max(0.0, min(max_scroll_y, sidebar_scroll_y))

    pad_x = sb_x + 10
    card_w = sb_w - 20
    cur_y = 8 - int(scroll_y)

    # --- 卡片 1: 🏆 记分牌 (Scoreboard) ---
    c1_rect = pygame.Rect(pad_x, cur_y, card_w, 76)
    pygame.draw.rect(screen, (24, 34, 52), c1_rect, border_radius=8)
    pygame.draw.rect(screen, (48, 68, 98), c1_rect, width=1, border_radius=8)

    stage_idx = (current_world - 1) * 10 + difficulty_level
    t_mode_str = "🌟 自由模式" if game_mode == "free" else f"🏆 闯关模式 ({stage_idx}/60关)"
    t_title = f_title.render(f"模式: {t_mode_str}", True, (255, 220, 80))
    screen.blit(t_title, (pad_x + 10, cur_y + 6))

    t_total = f_body.render(f"累计总得分: {total_score:,} 分", True, (255, 240, 150))
    screen.blit(t_total, (pad_x + 10, cur_y + 28))

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
    screen.blit(t_last, (pad_x + 10, cur_y + 50))

    cur_y += 82

    # --- 卡片 2: 📊 关卡分值与大关主题 (Level & World Info) ---
    c2_rect = pygame.Rect(pad_x, cur_y, card_w, 70)
    pygame.draw.rect(screen, (24, 34, 52), c2_rect, border_radius=8)
    pygame.draw.rect(screen, (48, 68, 98), c2_rect, width=1, border_radius=8)

    if current_world == 6:
        world_title = "🔤 第六大关：提示词阵"
        world_color = (100, 240, 255)
    elif current_world == 5:
        world_title = "🌉 第五大关：立交编织"
        world_color = (120, 220, 255)
    elif current_world == 4:
        world_title = "🌀 第四大关：异形几何"
        world_color = (100, 230, 220)
    elif current_world == 3:
        world_title = "🌟 第三大关：图案秘境"
        world_color = (210, 140, 255)
    elif current_world == 2:
        world_title = "🏰 第二大关：狼穴地牢"
        world_color = (255, 130, 130)
    else:
        world_title = "🌲 第一大关：绿野森林"
        world_color = (130, 230, 150)

    t_world = f_title.render(world_title, True, world_color)
    screen.blit(t_world, (pad_x + 10, cur_y + 6))

    base_pts = (current_world - 1) * 1000 + difficulty_level * 100
    rec_pts = base_pts * 2
    if current_world == 6:
        prog_str = get_keep_going_progress(difficulty_level)
        t_lvl = f_body.render(f"提示词进度: {prog_str}", True, (100, 240, 255))
        t_pts = f_small.render(f"通关: +{base_pts} 分 | 字母解密", True, (160, 210, 255))
    elif game_mode == "free":
        t_lvl = f_body.render(f"当前关卡: 第{current_world}大关 {difficulty_level}阶", True, (220, 230, 245))
        t_pts = f_small.render(f"通关: +{base_pts} 分 | 破纪录: +{rec_pts} 分", True, (160, 210, 255))
    else:
        t_lvl = f_body.render(f"闯关进度: 第 {stage_idx} / 60 关", True, (220, 230, 245))
        t_pts = f_small.render(f"本阶得分: +{base_pts} 分 (破纪录加倍)", True, (160, 210, 255))

    screen.blit(t_lvl, (pad_x + 10, cur_y + 26))
    screen.blit(t_pts, (pad_x + 10, cur_y + 48))

    cur_y += 76

    # --- 卡片 2.5: 🎒 支线任务道具收集 (Item Quest Card) ---
    c_item_rect = pygame.Rect(pad_x, cur_y, card_w, 52)
    pygame.draw.rect(screen, (24, 34, 52), c_item_rect, border_radius=8)
    pygame.draw.rect(screen, (48, 68, 98), c_item_rect, width=1, border_radius=8)

    item_info = WORLD_ITEM_INFO.get(current_world, WORLD_ITEM_INFO[1])
    rem_count = len(item_tiles) if item_tiles is not None else 0
    col_count = max(0, total_items_count - rem_count)

    if rem_count == 0:
        t_q_title = f_title.render(f"🎒 支线: {item_info['icon']}{item_info['name']} (已集齐 7 个!)", True, (100, 255, 150))
        t_q_status = f_small.render(f"已收集: {col_count} 个 | 还有 0 个未收集 (🔓 门已解封)", True, (150, 255, 180))
    else:
        t_q_title = f_title.render(f"🎒 支线: {item_info['icon']}{item_info['name']} 收集 ({col_count}/{total_items_count})", True, (255, 220, 90))
        t_q_status = f_small.render(f"已收集: {col_count} 个 | 还有 {rem_count} 个未收集", True, (255, 200, 120))

    screen.blit(t_q_title, (pad_x + 10, cur_y + 5))
    screen.blit(t_q_status, (pad_x + 10, cur_y + 28))

    cur_y += 58

    # --- 卡片 3: 🎯 调试选关按钮 (Level Select Card - 60 关) ---
    c3_rect = pygame.Rect(pad_x, cur_y, card_w, 172)
    pygame.draw.rect(screen, (24, 34, 52), c3_rect, border_radius=8)
    pygame.draw.rect(screen, (48, 68, 98), c3_rect, width=1, border_radius=8)

    t_sel_title = f_small.render("🎯 调试选关按钮 (点击直跳关卡):", True, (255, 220, 90))
    screen.blit(t_sel_title, (pad_x + 10, cur_y + 4))

    sidebar_level_rects: dict[tuple[int, int], pygame.Rect] = {}

    world_rows = [
        (1, "🌲W1", (130, 230, 150), 24),
        (2, "🏰W2", (255, 130, 130), 48),
        (3, "🌟W3", (210, 140, 255), 72),
        (4, "🌀W4", (100, 230, 220), 96),
        (5, "🌉W5", (120, 220, 255), 120),
        (6, "🔤W6", (100, 240, 255), 144),
    ]

    w6_letters_short = ["K", "E", "E", "P", "G", "O", "I", "N", "G", "!"]

    for w_idx, tag, tag_color, offset_y_pos in world_rows:
        lbl = f_tiny.render(tag, True, tag_color)
        screen.blit(lbl, (pad_x + 6, cur_y + offset_y_pos + 2))
        for lvl in range(1, 11):
            bx = pad_x + 44 + (lvl - 1) * 21
            by = cur_y + offset_y_pos
            brect = pygame.Rect(bx, by, 19, 20)
            sidebar_level_rects[(w_idx, lvl)] = brect

            is_active = (current_world == w_idx and lvl == difficulty_level)
            is_cleared = (w_idx == 6 and (f"6_{lvl}" in best_records or (won and current_world == 6 and difficulty_level == lvl)))

            if is_active:
                bg_c = (38, 88, 56) if w_idx == 1 else ((98, 38, 52) if w_idx == 2 else ((88, 38, 108) if w_idx == 3 else ((38, 98, 98) if w_idx == 4 else ((38, 78, 108) if w_idx == 5 else (20, 90, 120)))))
                border_c = (255, 220, 80)
            elif is_cleared:
                bg_c = (24, 60, 85)
                border_c = (0, 220, 200)
            else:
                bg_c = (22, 48, 34) if w_idx == 1 else ((56, 22, 32) if w_idx == 2 else ((48, 22, 62) if w_idx == 3 else ((22, 56, 56) if w_idx == 4 else ((22, 44, 68) if w_idx == 5 else (14, 48, 68)))))
                border_c = (60, 130, 80) if w_idx == 1 else ((180, 60, 80) if w_idx == 2 else ((140, 60, 180) if w_idx == 3 else ((60, 160, 150) if w_idx == 4 else ((60, 140, 180) if w_idx == 5 else (40, 160, 200)))))

            pygame.draw.rect(screen, bg_c, brect, border_radius=3)
            pygame.draw.rect(screen, border_c, brect, width=2 if is_active else 1, border_radius=3)

            btn_str = w6_letters_short[lvl - 1] if (w_idx == 6 and is_cleared) else str(lvl)
            txt_s = f_tiny.render(btn_str, True, (255, 240, 150) if is_active else ((255, 230, 120) if is_cleared else (210, 230, 245)))
            screen.blit(txt_s, txt_s.get_rect(center=brect.center))

    cur_y += 178

    # --- 🧭 自动寻路按钮 ---
    btn_auto_rect = pygame.Rect(pad_x, cur_y, card_w, 26)
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
        txt_a = f_body.render(txt_str, True, (200, 250, 255))
    else:
        bg_a = (38, 52, 74) if hover_auto else (24, 34, 52)
        border_a = (100, 180, 255) if hover_auto else (48, 68, 98)
        txt_a = f_body.render("🧭 自动寻路：已关闭 [点击演示过程]", True, (220, 235, 245))

    pygame.draw.rect(screen, bg_a, btn_auto_rect, border_radius=6)
    pygame.draw.rect(screen, border_a, btn_auto_rect, width=2 if (hover_auto or show_auto_path) else 1, border_radius=6)
    screen.blit(txt_a, txt_a.get_rect(center=btn_auto_rect.center))

    cur_y += 31

    # --- 🔍 视角模式切换按钮 ---
    btn_view_rect = pygame.Rect(pad_x, cur_y, card_w, 26)
    hover_view = btn_view_rect.collidepoint(pygame.mouse.get_pos())
    is_following = camera.following_player if camera is not None else False
    if is_following:
        bg_v = (20, 80, 70) if hover_view else (15, 60, 52)
        border_v = (0, 240, 200)
        txt_v = f_body.render("🔍 视角: 地图放大 [点击还原全景]", True, (200, 250, 240))
    else:
        bg_v = (38, 52, 74) if hover_view else (24, 34, 52)
        border_v = (100, 180, 255) if hover_view else (48, 68, 98)
        txt_v = f_body.render("🔍 视角: 全景还原 [点击放大跟随]", True, (220, 235, 245))

    pygame.draw.rect(screen, bg_v, btn_view_rect, border_radius=6)
    pygame.draw.rect(screen, border_v, btn_view_rect, width=2 if (hover_view or is_following) else 1, border_radius=6)
    screen.blit(txt_v, txt_v.get_rect(center=btn_view_rect.center))

    cur_y += 32

    # --- 卡片 3.5: 📜 提示词集锦 (KEEP GOING!) ---
    w6_card_h = 60
    w6_rect = pygame.Rect(pad_x, cur_y, card_w, w6_card_h)
    pygame.draw.rect(screen, (20, 36, 52), w6_rect, border_radius=8)
    pygame.draw.rect(screen, (40, 120, 160), w6_rect, width=1, border_radius=8)

    lbl_w6_title = f_tiny.render("📜 提示词阵收集 [ KEEP GOING! ]", True, (100, 240, 255))
    screen.blit(lbl_w6_title, (pad_x + 8, cur_y + 4))

    w6_letters = ["K", "E", "E", "P", "G", "O", "I", "N", "G", "!"]
    slot_w = 19
    slot_h = 20
    slot_start_x = pad_x + 8
    slot_y = cur_y + 18

    collected_count = 0
    for idx in range(10):
        lvl_num = idx + 1
        char_str = w6_letters[idx]
        is_collected = f"6_{lvl_num}" in best_records or (won and current_world == 6 and difficulty_level == lvl_num)
        if is_collected:
            collected_count += 1

        bx = slot_start_x + idx * (slot_w + 4)
        srect = pygame.Rect(bx, slot_y, slot_w, slot_h)

        is_current = (current_world == 6 and difficulty_level == lvl_num)

        if is_collected:
            bg_s = (30, 110, 140) if is_current else (20, 70, 95)
            border_s = (255, 230, 100) if is_current else (60, 200, 240)
            pygame.draw.rect(screen, bg_s, srect, border_radius=4)
            pygame.draw.rect(screen, border_s, srect, width=2 if is_current else 1, border_radius=4)
            txt_char = f_body.render(char_str, True, (255, 240, 120))
        else:
            bg_s = (18, 26, 38)
            border_s = (40, 60, 80)
            pygame.draw.rect(screen, bg_s, srect, border_radius=4)
            pygame.draw.rect(screen, border_s, srect, width=1, border_radius=4)
            txt_char = f_tiny.render("·", True, (80, 100, 120))

        screen.blit(txt_char, txt_char.get_rect(center=srect.center))

    if collected_count == 10:
        prog_txt = f_tiny.render("✨ 10/10 全满贯拼齐! 永不放弃！", True, (255, 235, 100))
    else:
        prog_txt = f_tiny.render(f"收集进度: {collected_count}/10 关 (通关解锁)", True, (160, 210, 235))
    screen.blit(prog_txt, (pad_x + 8, cur_y + 42))

    cur_y += 66

    # --- 卡片 4: ⏱️ 计时 & 纪录 (Timer & Record) ---
    c3_rect = pygame.Rect(pad_x, cur_y, card_w, 56)
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

    screen.blit(t_time, (pad_x + 10, cur_y + 6))
    screen.blit(t_best, (pad_x + 10, cur_y + 28))

    cur_y += 62

    # --- 卡片 5: 💬 游戏状态与过关/被抓提示 (Status Banner) ---
    c4_h = 106
    c4_rect = pygame.Rect(pad_x, cur_y, card_w, c4_h)

    if game_mode == "challenge" and challenge_completed:
        pygame.draw.rect(screen, (38, 78, 52), c4_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 180, 100), c4_rect, width=2, border_radius=8)

        st1 = f_banner.render("🏆 大满贯全通关！", True, (255, 255, 100))
        st2 = f_body.render(f"1~50关总用时: {challenge_total_time:.2f} 秒", True, (220, 255, 220))
        st3 = f_body.render(f"获得全通总分: +{challenge_total_score:,} 分", True, (255, 220, 100))
        st4 = f_body.render("👉 按 R 重测，按 M 返回主菜单", True, (255, 240, 180))

        screen.blit(st1, (pad_x + 10, cur_y + 6))
        screen.blit(st2, (pad_x + 10, cur_y + 30))
        screen.blit(st3, (pad_x + 10, cur_y + 52))
        screen.blit(st4, (pad_x + 10, cur_y + 76))

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
            elif current_world == 2:
                next_str = f"第2大关 {difficulty_level + 1}阶" if difficulty_level < 10 else "第3大关 1阶"
            elif current_world == 3:
                next_str = f"第3大关 {difficulty_level + 1}阶" if difficulty_level < 10 else "第4大关 1阶"
            elif current_world == 4:
                next_str = f"第4大关 {difficulty_level + 1}阶" if difficulty_level < 10 else "第5大关 1阶"
            else:
                next_str = f"第5大关 {difficulty_level + 1}阶" if difficulty_level < 10 else "第1大关 1阶"
            st4 = f_body.render(f"👉 按 R/空格/点击进入 {next_str}", True, (255, 240, 180))

        screen.blit(st1, (pad_x + 10, cur_y + 6))
        screen.blit(st2, (pad_x + 10, cur_y + 30))
        screen.blit(st3, (pad_x + 10, cur_y + 52))
        screen.blit(st4, (pad_x + 10, cur_y + 76))

    elif caught_by_wolf:
        pygame.draw.rect(screen, (110, 28, 36), c4_rect, border_radius=8)
        pygame.draw.rect(screen, (200, 60, 70), c4_rect, width=2, border_radius=8)

        st1 = f_banner.render("😱 被狼抓住了！", True, (255, 220, 220))
        st2 = f_body.render("本局得分: 0 分", True, (255, 180, 180))
        st3 = f_body.render("被大灰狼追上了...", True, (230, 190, 190))
        st4 = f_body.render("👉 按 R 重新尝试本关", True, (255, 240, 180))

        screen.blit(st1, (pad_x + 10, cur_y + 6))
        screen.blit(st2, (pad_x + 10, cur_y + 30))
        screen.blit(st3, (pad_x + 10, cur_y + 52))
        screen.blit(st4, (pad_x + 10, cur_y + 76))

    else:
        pygame.draw.rect(screen, (24, 34, 52), c4_rect, border_radius=8)
        pygame.draw.rect(screen, (48, 68, 98), c4_rect, width=1, border_radius=8)

        if game_mode == "free":
            st1 = f_body.render("🟢 正在自由模式练习...", True, (120, 230, 160))
            st2 = f_body.render("按 WASD / 方向键移动", True, (190, 200, 215))
            st3 = f_body.render("避开大灰狼到达小屋", True, (190, 200, 215))
            st4 = f_body.render("按 M 键可随时返回菜单", True, (170, 180, 200))
        else:
            st1 = f_body.render(f"🟢 闯关挑战中 ({stage_idx}/50关)", True, (120, 230, 160))
            st2 = f_body.render("按 WASD / 方向键移动", True, (190, 200, 215))
            st3 = f_body.render("顺序挑战 50 阶全部迷宫", True, (190, 200, 215))
            st4 = f_body.render("创造最快全通时间与高分！", True, (170, 180, 200))

        screen.blit(st1, (pad_x + 10, cur_y + 6))
        screen.blit(st2, (pad_x + 10, cur_y + 30))
        screen.blit(st3, (pad_x + 10, cur_y + 52))
        screen.blit(st4, (pad_x + 10, cur_y + 76))

    cur_y += c4_h + 8

    # 滚动条指示器
    if max_scroll_y > 0.0:
        bar_x = sb_x + sb_w - 5
        bar_h = sh - 16
        thumb_h = max(24, int(bar_h * (sh / total_content_h)))
        thumb_y = 8 + int((bar_h - thumb_h) * (scroll_y / max_scroll_y))
        pygame.draw.rect(screen, (35, 50, 75), (bar_x, 8, 3, bar_h), border_radius=2)
        pygame.draw.rect(screen, (90, 170, 230), (bar_x, thumb_y, 3, thumb_h), border_radius=2)

    return sidebar_level_rects, btn_auto_rect, btn_view_rect, max_scroll_y


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
