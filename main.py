"""可玩原型：生成迷宫、方向键/WASD 走动、撞墙停下。"""

from __future__ import annotations

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


def _font(size: int) -> pygame.font.Font:
    """优先用系统中文字体，避免 HUD 变成方框。"""
    for name in ("Microsoft YaHei", "Microsoft YaHei UI", "SimHei", "Segoe UI"):
        font = pygame.font.SysFont(name, size)
        if font is not None:
            return font
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
    return maze.cols * CELL_SIZE, maze.rows * CELL_SIZE + HUD_HEIGHT


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

    difficulty = "normal"
    maze = _make_maze(difficulty)
    screen = pygame.display.set_mode(_window_size(maze))
    player = _spawn_player(maze)
    won = False

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif _is_reroll_event(event):
                maze = _make_maze(difficulty)
                screen = pygame.display.set_mode(_window_size(maze))
                player = _spawn_player(maze)
                won = False
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                difficulty = {pygame.K_1: "easy", pygame.K_2: "normal", pygame.K_3: "hard"}[
                    event.key
                ]
                maze = _make_maze(difficulty)
                screen = pygame.display.set_mode(_window_size(maze))
                player = _spawn_player(maze)
                won = False

        # 通关后停步，但仍可按 R / 1 / 2 / 3 重开。
        if not won:
            keys = pygame.key.get_pressed()
            player.update(keys, maze, CELL_SIZE)
            if player.reached_exit(maze, CELL_SIZE):
                won = True

        _draw(screen, maze, player, font, big_font, won)
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
) -> None:
    screen.fill(COLOR_BG)
    origin_y = HUD_HEIGHT
    for y, row in enumerate(maze.grid):
        for x, tile in enumerate(row):
            rect = pygame.Rect(x * CELL_SIZE, origin_y + y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            if tile == 1:
                pygame.draw.rect(screen, COLOR_WALL, rect)
            else:
                pygame.draw.rect(screen, COLOR_PATH, rect)

    ex, ey = maze.entrance
    ox, oy = maze.exit
    pygame.draw.rect(
        screen,
        COLOR_ENTRANCE,
        pygame.Rect(ex * CELL_SIZE, origin_y + ey * CELL_SIZE, CELL_SIZE, CELL_SIZE),
    )
    pygame.draw.rect(
        screen,
        COLOR_EXIT,
        pygame.Rect(ox * CELL_SIZE, origin_y + oy * CELL_SIZE, CELL_SIZE, CELL_SIZE),
    )

    # 迷宫坐标原点在 HUD 下方，绘制时把角色整体下移。
    draw_rect = player.rect.move(0, origin_y)
    pygame.draw.rect(screen, COLOR_PLAYER, draw_rect, border_radius=4)

    m = maze.metrics
    hud = (
        f"难度 {m.label}  |  路径 {m.path_length}  死胡同 {m.dead_ends}  "
        f"岔路 {m.decision_cells}  岔深 {m.avg_dead_end_depth:.1f}  分数 {m.score:.0f}    "
        "方向键/WASD 移动   1易 2中 3难   R重随   Esc退出"
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
