"""可玩原型：生成迷宫、方向键/WASD 走动、撞墙停下。"""

from __future__ import annotations

import math
import sys

import pygame

from maze import Maze, assert_perfect_maze, generate_maze
from player import Player

CELL_SIZE = 26  # 房间变大后略缩小格子，尽量仍能在常见分辨率下完整显示
HUD_HEIGHT = 52
FPS = 60
PLAYER_INSET = 6  # 角色比格子小一圈，转弯时不容易被墙角卡住

COLOR_BG = (18, 18, 24)
COLOR_WALL = (42, 48, 72)
COLOR_PATH = (214, 214, 222)
COLOR_ENTRANCE = (80, 160, 90)
COLOR_EXIT = (200, 90, 70)
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
        """根据当前窗口尺寸，计算自动缩放比例，使地图紧贴 HUD 正下方且完整显示。"""
        sw, sh = screen.get_size()
        avail_w = sw
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

        # 水平居中，垂直紧贴 HUD 正下方对齐
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
        avail_h = max(1, sh - HUD_HEIGHT)
        vc_x = sw / 2.0
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

    desired_w = max(maze.cols * CELL_SIZE + 16, 880)
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


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Maze Game")
    # 关掉 SDL 文本输入，减少输入法把 R 吃掉的情况。
    if hasattr(pygame.key, "stop_text_input"):
        pygame.key.stop_text_input()

    clock = pygame.time.Clock()
    font = _font(18)
    big_font = _font(36)

    difficulty_level = 5  # 默认 5 阶难度
    maze = _make_maze(str(difficulty_level))
    screen = pygame.display.set_mode(_window_size(maze), pygame.RESIZABLE)
    player = _spawn_player(maze)
    camera = Camera()
    camera.fit_maze(maze, screen)
    won = False

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
                elif event.key in (pygame.K_c, pygame.K_SPACE):
                    camera.toggle_view(maze, player, screen)
                elif event.key in NUM_KEY_TO_LEVEL:
                    difficulty_level = NUM_KEY_TO_LEVEL[event.key]
                    maze = _make_maze(str(difficulty_level))
                    screen = pygame.display.set_mode(_window_size(maze), pygame.RESIZABLE)
                    player = _spawn_player(maze)
                    camera.fit_maze(maze, screen)
                    won = False
                elif event.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                    if difficulty_level < 10:
                        difficulty_level += 1
                        maze = _make_maze(str(difficulty_level))
                        screen = pygame.display.set_mode(_window_size(maze), pygame.RESIZABLE)
                        player = _spawn_player(maze)
                        camera.fit_maze(maze, screen)
                        won = False
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    if difficulty_level > 1:
                        difficulty_level -= 1
                        maze = _make_maze(str(difficulty_level))
                        screen = pygame.display.set_mode(_window_size(maze), pygame.RESIZABLE)
                        player = _spawn_player(maze)
                        camera.fit_maze(maze, screen)
                        won = False
                elif _is_reroll_event(event):
                    maze = _make_maze(str(difficulty_level))
                    screen = pygame.display.set_mode(_window_size(maze), pygame.RESIZABLE)
                    player = _spawn_player(maze)
                    camera.fit_maze(maze, screen)
                    won = False
            elif event.type != pygame.KEYDOWN and _is_reroll_event(event):
                maze = _make_maze(str(difficulty_level))
                screen = pygame.display.set_mode(_window_size(maze), pygame.RESIZABLE)
                player = _spawn_player(maze)
                camera.fit_maze(maze, screen)
                won = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.pos[1] > HUD_HEIGHT:
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
                if my > HUD_HEIGHT:
                    factor = 1.15 if event.y > 0 else (1 / 1.15 if event.y < 0 else 1.0)
                    if factor != 1.0:
                        camera.zoom(factor, (mx, my))

        # 通关后停步，但仍可按 R / 数字键 重开。
        if not won:
            keys = pygame.key.get_pressed()
            player.update(keys, maze, CELL_SIZE)
            if player.reached_exit(maze, CELL_SIZE):
                won = True

            if camera.following_player:
                camera.update_player_focus(player, screen)
            else:
                # 检查玩家坐标是否离开视口区域
                sw, sh = screen.get_size()
                psx, psy = camera.world_to_screen(player.rect.centerx, player.rect.centery)
                if not (0 <= psx <= sw and HUD_HEIGHT <= psy <= sh):
                    if camera.scale <= camera.fit_scale * 1.05:
                        camera.fit_maze(maze, screen)
                    else:
                        camera.focus_player(player, screen)

        _draw(screen, maze, player, font, big_font, won, camera)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)


def _draw(
    screen: pygame.Surface,
    maze: Maze,
    player: Player,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
    won: bool,
    camera: Camera,
) -> None:
    screen.fill(COLOR_BG)
    screen_w, screen_h = screen.get_size()

    scale = camera.scale

    # 计算视口覆盖的世界坐标范围，进行视口裁剪
    min_wx = (0 - camera.offset_x) / scale
    max_wx = (screen_w - camera.offset_x) / scale
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

    # 入口与出口瓦片
    for (tx, ty), color in ((maze.entrance, COLOR_ENTRANCE), (maze.exit, COLOR_EXIT)):
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

    # 玩家
    px1, py1 = camera.world_to_screen(player.rect.left, player.rect.top)
    px2, py2 = camera.world_to_screen(player.rect.right, player.rect.bottom)
    player_rect = pygame.Rect(
        int(px1),
        int(py1),
        max(1, int(px2 - px1)),
        max(1, int(py2 - py1)),
    )
    radius = max(0, int(4 * scale))
    pygame.draw.rect(screen, COLOR_PLAYER, player_rect, border_radius=radius)

    # HUD 区域 (覆盖在迷宫顶部)
    pygame.draw.rect(screen, COLOR_BG, (0, 0, screen_w, HUD_HEIGHT))
    m = maze.metrics
    hud = (
        f"难度 {m.label}  |  路径 {m.path_length}  死胡同 {m.dead_ends}  "
        f"岔路 {m.decision_cells}  岔深 {m.avg_dead_end_depth:.1f}  分数 {m.score:.0f}    "
        "WASD/方向键移动  1-9/0选1-10阶  +/-切换  R重随  拖拽平移/滚轮缩放  C/Space视角  Esc退出"
    )
    screen.blit(font.render(hud, True, COLOR_HUD), (10, 16))

    if won:
        _draw_win_banner(screen, big_font)


def _draw_win_banner(screen: pygame.Surface, big_font: pygame.font.Font) -> None:
    """通关提示：深红底 + 亮黄字，铺在迷宫上方居中，避免和浅色路面糊在一起。"""
    msg = big_font.render("到达出口！按 R 再来一局", True, COLOR_WIN)
    box = msg.get_rect(center=(screen.get_width() // 2, HUD_HEIGHT + 48))
    banner = box.inflate(36, 20)
    pygame.draw.rect(screen, COLOR_WIN_OUTLINE, banner.inflate(8, 8), border_radius=8)
    pygame.draw.rect(screen, COLOR_WIN_BANNER, banner, border_radius=6)
    screen.blit(msg, box)


if __name__ == "__main__":
    main()
