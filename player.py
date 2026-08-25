"""玩家移动与撞墙。像素级移动，XY 分开检测，贴墙滑行时不会斜着卡死。"""

from __future__ import annotations

import pygame

from maze import Maze


class Player:
    def __init__(self, pixel_x: float, pixel_y: float, size: int, speed: float = 3.2) -> None:
        # 逻辑坐标在迷宫瓦片空间里（不含 HUD 高度），绘制时再整体下移。
        self.rect = pygame.Rect(int(pixel_x), int(pixel_y), size, size)
        self.speed = speed
        self.facing = "down"  # 当前朝向: "down", "up", "left", "right"
        self.anim_frame = 0   # 0 或 1，走动动画帧
        self.is_moving = False
        self._step_counter = 0

    def update(
        self,
        keys: pygame.key.ScancodeWrapper,
        maze: Maze,
        cell_size: int,
        sound_step: pygame.mixer.Sound | None = None,
    ) -> None:
        """读当前按住的键，合成速度后移动并更新方向、走动动画及脚步音效。"""
        dx = 0.0
        dy = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += self.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += self.speed

        moved = False
        old_pos = (self.rect.x, self.rect.y)

        # 优先决定朝向
        if dx < 0:
            self.facing = "left"
        elif dx > 0:
            self.facing = "right"
        elif dy < 0:
            self.facing = "up"
        elif dy > 0:
            self.facing = "down"

        if dx:
            self._move(dx, 0, maze, cell_size)
        if dy:
            self._move(0, dy, maze, cell_size)

        if (self.rect.x, self.rect.y) != old_pos:
            moved = True

        self.is_moving = moved

        if self.is_moving:
            self._step_counter += 1
            # 步频计时：每 12 帧交替动画帧并播放脚步声
            if self._step_counter % 12 == 0:
                self.anim_frame = 1 - self.anim_frame
                if sound_step:
                    sound_step.play()
        else:
            self.anim_frame = 0
            self._step_counter = 0

    def _move(self, dx: float, dy: float, maze: Maze, cell_size: int) -> None:
        """单轴尝试移动；新矩形只要盖到任何墙格就整段取消。"""
        trial = self.rect.move(round(dx), round(dy))
        if not _hits_wall(trial, maze, cell_size):
            self.rect = trial

    def reached_exit(self, maze: Maze, cell_size: int) -> bool:
        """角色与出口格的内缩矩形相交即算到达（不必像素级对齐）。"""
        exit_rect = pygame.Rect(
            maze.exit[0] * cell_size,
            maze.exit[1] * cell_size,
            cell_size,
            cell_size,
        )
        return self.rect.colliderect(exit_rect.inflate(-cell_size // 4, -cell_size // 4))


def _hits_wall(rect: pygame.Rect, maze: Maze, cell_size: int) -> bool:
    """用角色矩形覆盖到的瓦片范围做碰撞，比逐像素查表便宜。"""
    left = rect.left // cell_size
    right = (rect.right - 1) // cell_size
    top = rect.top // cell_size
    bottom = (rect.bottom - 1) // cell_size
    for tile_y in range(top, bottom + 1):
        for tile_x in range(left, right + 1):
            if maze.is_wall(tile_x, tile_y):
                return True
    return False
