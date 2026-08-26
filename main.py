"""可玩原型：生成迷宫、方向键/WASD 走动、撞墙停下。"""

from __future__ import annotations

import json
import math
import os
import sys

RECORDS_FILE = "best_records.json"


def _load_best_records() -> tuple[dict[int, float], int]:
    records: dict[int, float] = {}
    total_score: int = 0
    if os.path.exists(RECORDS_FILE):
        try:
            with open(RECORDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if k == "total_score":
                        total_score = int(v)
                    else:
                        records[int(k)] = float(v)
        except Exception as e:
            print(f"Warning: failed to load best records: {e}")
    return records, total_score


def _save_best_records(records: dict[int, float], total_score: int) -> None:
    try:
        data = {str(k): v for k, v in records.items()}
        data["total_score"] = total_score
        with open(RECORDS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Warning: failed to save best records: {e}")


import pygame

from assets import (
    create_flag_surface,
    create_house_surface,
    create_player_sprites,
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
SIDEBAR_WIDTH = 260  # 右侧独立记分牌与状态面板宽度
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


def _make_maze(difficulty: str) -> Maze:
    maze = generate_maze(difficulty)
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

    difficulty_level = 5  # 默认 5 阶难度
    maze = _make_maze(str(difficulty_level))
    screen = pygame.display.set_mode(_window_size(maze), pygame.RESIZABLE)
    player = _spawn_player(maze)
    wolf = Wolf(CELL_SIZE)
    camera = Camera()
    camera.fit_maze(maze, screen)
    won = False
    caught_by_wolf = False

    # 计时器与纪录管理
    best_records, total_score = _load_best_records()
    last_round_score = 0
    score_doubled = False
    timer_started = False
    start_time_ms = 0
    current_time_sec = 0.0

    def reset_level_state():
        nonlocal maze, screen, player, wolf, camera, won, caught_by_wolf, timer_started, start_time_ms, current_time_sec
        maze = _make_maze(str(difficulty_level))
        screen = pygame.display.set_mode(_window_size(maze), pygame.RESIZABLE)
        player = _spawn_player(maze)
        wolf = Wolf(CELL_SIZE)
        camera.fit_maze(maze, screen)
        won = False
        caught_by_wolf = False
        timer_started = False
        start_time_ms = 0
        current_time_sec = 0.0
        if sound_start:
            sound_start.play()

    # 开局播放声音
    if sound_start:
        sound_start.play()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                if not camera.following_player:
                    camera.fit_maze(maze, screen)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
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
                elif event.key in (pygame.K_c, pygame.K_SPACE):
                    camera.toggle_view(maze, player, screen)
                elif event.key in NUM_KEY_TO_LEVEL:
                    difficulty_level = NUM_KEY_TO_LEVEL[event.key]
                    reset_level_state()
                elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                    if difficulty_level < 10:
                        difficulty_level += 1
                        reset_level_state()
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    if difficulty_level > 1:
                        difficulty_level -= 1
                        reset_level_state()
                elif _is_reroll_event(event):
                    reset_level_state()
            elif event.type != pygame.KEYDOWN and _is_reroll_event(event):
                reset_level_state()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.pos[0] < screen.get_width() - SIDEBAR_WIDTH and event.pos[1] > HUD_HEIGHT:
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
                if wolf.active:
                    wolf.crying = True

                if timer_started:
                    current_time_sec = (pygame.time.get_ticks() - start_time_ms) / 1000.0

                has_prev = difficulty_level in best_records
                prev_best = best_records.get(difficulty_level, 999999.0)
                is_new_record = False

                if not has_prev or current_time_sec < prev_best:
                    is_new_record = True
                    best_records[difficulty_level] = current_time_sec

                base_score = difficulty_level * 100
                if is_new_record:
                    last_round_score = base_score * 2
                    score_doubled = True
                else:
                    last_round_score = base_score
                    score_doubled = False

                total_score += last_round_score
                _save_best_records(best_records, total_score)

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
        elif won and wolf.active:
            wolf.crying = True
            wolf.update(dt, player.rect.center)

        _draw(
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
            difficulty_level,
            best_records,
            timer_started,
            current_time_sec,
            total_score,
            last_round_score,
            score_doubled,
        )
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)


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
    difficulty_level: int,
    best_records: dict[int, float],
    timer_started: bool,
    current_time_sec: float,
    total_score: int,
    last_round_score: int,
    score_doubled: bool,
) -> None:
    screen.fill(COLOR_BG)
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
            color = COLOR_WALL if tile == 1 else COLOR_PATH
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
    _draw_sidebar(
        screen,
        font,
        big_font,
        difficulty_level,
        best_records,
        timer_started,
        current_time_sec,
        won,
        caught_by_wolf,
        total_score,
        last_round_score,
        score_doubled,
    )


def _draw_sidebar(
    screen: pygame.Surface,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    difficulty_level: int,
    best_records: dict[int, float],
    timer_started: bool,
    current_time_sec: float,
    won: bool,
    caught_by_wolf: bool,
    total_score: int,
    last_round_score: int,
    score_doubled: bool,
) -> None:
    """右侧独立记分牌面板：包含总得分、关卡分值、计时纪录、通关/被抓提示卡片与快捷键指南。"""
    sw, sh = screen.get_size()
    sb_x = sw - SIDEBAR_WIDTH
    sb_w = SIDEBAR_WIDTH

    # 1. 侧边栏整体背景与左分隔线
    sidebar_rect = pygame.Rect(sb_x, 0, sb_w, sh)
    pygame.draw.rect(screen, (16, 22, 34), sidebar_rect)
    pygame.draw.line(screen, (38, 52, 74), (sb_x, 0), (sb_x, sh), 2)

    pad_x = sb_x + 12
    card_w = sb_w - 24
    cur_y = 12

    # --- 卡片 1: 🏆 记分牌 (Scoreboard) ---
    c1_rect = pygame.Rect(pad_x, cur_y, card_w, 88)
    pygame.draw.rect(screen, (24, 34, 52), c1_rect, border_radius=8)
    pygame.draw.rect(screen, (48, 68, 98), c1_rect, width=1, border_radius=8)

    t_title = big_font.render("🏆 记分牌", True, (255, 220, 80))
    screen.blit(t_title, (pad_x + 12, cur_y + 8))

    t_total = font.render(f"累计总分: {total_score:,} 分", True, (255, 240, 150))
    screen.blit(t_total, (pad_x + 12, cur_y + 38))

    if last_round_score > 0:
        d_str = " (破纪录翻倍!)" if score_doubled else ""
        t_last = font.render(f"本局得分: +{last_round_score:,}分{d_str}", True, (120, 240, 160))
    elif caught_by_wolf:
        t_last = font.render("本局得分: 0 分 (被狼抓)", True, (255, 120, 120))
    else:
        t_last = font.render("本局得分: --", True, (180, 190, 205))
    screen.blit(t_last, (pad_x + 12, cur_y + 60))

    cur_y += 98

    # --- 卡片 2: 📊 关卡分值 (Level Points Info) ---
    c2_rect = pygame.Rect(pad_x, cur_y, card_w, 72)
    pygame.draw.rect(screen, (24, 34, 52), c2_rect, border_radius=8)
    pygame.draw.rect(screen, (48, 68, 98), c2_rect, width=1, border_radius=8)

    base_pts = difficulty_level * 100
    rec_pts = base_pts * 2
    t_lvl = font.render(f"当前关卡: {difficulty_level} 阶", True, (220, 230, 245))
    t_pts = font.render(f"通关: +{base_pts} 分 | 破纪录: +{rec_pts} 分", True, (160, 210, 255))

    screen.blit(t_lvl, (pad_x + 12, cur_y + 10))
    screen.blit(t_pts, (pad_x + 12, cur_y + 38))

    cur_y += 82

    # --- 卡片 3: ⏱️ 计时 & 纪录 (Timer & Record) ---
    c3_rect = pygame.Rect(pad_x, cur_y, card_w, 72)
    pygame.draw.rect(screen, (24, 34, 52), c3_rect, border_radius=8)
    pygame.draw.rect(screen, (48, 68, 98), c3_rect, width=1, border_radius=8)

    time_str = f"{current_time_sec:.2f} 秒" if timer_started else "按方向键开始"
    best_sec = best_records.get(difficulty_level)
    best_str = f"{best_sec:.2f} 秒" if best_sec is not None else "无纪录"

    t_time = font.render(f"当前用时: {time_str}", True, (255, 230, 140) if timer_started else (170, 180, 195))
    t_best = font.render(f"最佳纪录: {best_str}", True, (180, 220, 255))

    screen.blit(t_time, (pad_x + 12, cur_y + 10))
    screen.blit(t_best, (pad_x + 12, cur_y + 38))

    cur_y += 82

    # --- 卡片 4: 💬 游戏状态与过关/被抓提示 (Status Banner - 侧边显示，完全不遮挡地图) ---
    c4_h = 135
    c4_rect = pygame.Rect(pad_x, cur_y, card_w, c4_h)

    if won:
        pygame.draw.rect(screen, (38, 78, 52), c4_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 180, 100), c4_rect, width=2, border_radius=8)

        st1 = big_font.render("🎉 成功通关！", True, (255, 255, 100))
        st2 = font.render(f"获得积分: +{last_round_score} 分", True, (220, 255, 220))
        if score_doubled:
            st3 = font.render("🏆 破纪录积分翻倍！", True, (255, 220, 100))
        else:
            st3 = font.render("再接再厉，挑战更快速度！", True, (200, 230, 210))
        st4 = font.render("👉 按 R 键继续下一局", True, (255, 240, 180))

        screen.blit(st1, (pad_x + 12, cur_y + 8))
        screen.blit(st2, (pad_x + 12, cur_y + 40))
        screen.blit(st3, (pad_x + 12, cur_y + 64))
        screen.blit(st4, (pad_x + 12, cur_y + 94))

    elif caught_by_wolf:
        pygame.draw.rect(screen, (110, 28, 36), c4_rect, border_radius=8)
        pygame.draw.rect(screen, (200, 60, 70), c4_rect, width=2, border_radius=8)

        st1 = big_font.render("😱 被狼抓住了！", True, (255, 220, 220))
        st2 = font.render("本局得分: 0 分", True, (255, 180, 180))
        st3 = font.render("被大灰狼追上了...", True, (230, 190, 190))
        st4 = font.render("👉 按 R 键重新开始", True, (255, 240, 180))

        screen.blit(st1, (pad_x + 12, cur_y + 8))
        screen.blit(st2, (pad_x + 12, cur_y + 40))
        screen.blit(st3, (pad_x + 12, cur_y + 64))
        screen.blit(st4, (pad_x + 12, cur_y + 94))

    else:
        pygame.draw.rect(screen, (24, 34, 52), c4_rect, border_radius=8)
        pygame.draw.rect(screen, (48, 68, 98), c4_rect, width=1, border_radius=8)

        st1 = font.render("🟢 正在闯关中...", True, (120, 230, 160))
        st2 = font.render("按 WASD / 方向键移动", True, (190, 200, 215))
        st3 = font.render("避开大灰狼，到达小屋", True, (190, 200, 215))
        st4 = font.render("挑战用时最快纪录！", True, (170, 180, 200))

        screen.blit(st1, (pad_x + 12, cur_y + 12))
        screen.blit(st2, (pad_x + 12, cur_y + 40))
        screen.blit(st3, (pad_x + 12, cur_y + 66))
        screen.blit(st4, (pad_x + 12, cur_y + 92))

    cur_y += c4_h + 10

    # --- 卡片 5: 🕹️ 操作快捷键 (Controls) ---
    c5_h = max(110, sh - cur_y - 12)
    c5_rect = pygame.Rect(pad_x, cur_y, card_w, c5_h)
    pygame.draw.rect(screen, (20, 28, 44), c5_rect, border_radius=8)
    pygame.draw.rect(screen, (38, 52, 78), c5_rect, width=1, border_radius=8)

    t_ctrl_title = font.render("🕹️ 快捷键指南", True, (180, 200, 220))
    screen.blit(t_ctrl_title, (pad_x + 10, cur_y + 8))

    ctrl_lines = [
        "WASD / 方向键 : 移动小人",
        "1-9 / 0 : 选阶  |  +/- : 调难度",
        "R : 重新生成  |  P : 切换外观",
        "F : 召唤大灰狼 |  C : 切换视角",
    ]
    for i, line in enumerate(ctrl_lines):
        t_l = font.render(line, True, (140, 155, 175))
        screen.blit(t_l, (pad_x + 10, cur_y + 32 + i * 22))


if __name__ == "__main__":
    main()
