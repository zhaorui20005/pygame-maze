"""玩家移动与撞墙。像素级平滑移动，支持 dt 增量时间，XY 分开检测，贴墙滑行时不会斜着卡死。"""

from __future__ import annotations

import pygame

from maze import Maze


class Player:
    def __init__(self, pixel_x: float, pixel_y: float, size: int, speed: float = 192.0) -> None:
        # 逻辑坐标在迷宫瓦片空间里（不含 HUD 高度），绘制时再整体下移。
        self.x = float(pixel_x)
        self.y = float(pixel_y)
        self.size = size
        self.rect = pygame.Rect(int(round(self.x)), int(round(self.y)), size, size)
        self.speed = speed if speed > 10.0 else speed * 60.0  # 保证 speed 为像素/秒 (标准约 192px/s)
        self.facing = "down"  # 当前朝向: "down", "up", "left", "right"
        self.anim_frame = 0   # 0 或 1，走动动画帧
        self.is_moving = False
        self._step_counter = 0
        self.overpass_layer = "none"  # 立交桥层级: "none", "ns_bridge", "ew_tunnel", "ew_bridge", "ns_tunnel"

    def update(
        self,
        keys: pygame.key.ScancodeWrapper,
        maze: Maze,
        cell_size: int,
        dt: float = 1.0 / 60.0,
        sound_step: pygame.mixer.Sound | None = None,
    ) -> None:
        """读当前按住的键，根据 dt 增量计算平滑移动并更新方向、走动动画及脚步音效。"""
        dt = min(max(dt, 0.001), 0.05)

        move_x = 0.0
        move_y = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move_x -= 1.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move_x += 1.0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            move_y -= 1.0
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            move_y += 1.0

        if move_x != 0.0 and move_y != 0.0:
            move_x *= 0.7071
            move_y *= 0.7071

        dx = move_x * self.speed * dt
        dy = move_y * self.speed * dt

        old_x, old_y = self.x, self.y

        # 优先决定朝向
        if move_x < 0:
            self.facing = "left"
        elif move_x > 0:
            self.facing = "right"
        elif move_y < 0:
            self.facing = "up"
        elif move_y > 0:
            self.facing = "down"

        # 记录移动前中心格
        cx = int((self.x + self.size * 0.5) // cell_size)
        cy = int((self.y + self.size * 0.5) // cell_size)

        if dx != 0.0:
            self._move_axis(dx, 0.0, maze, cell_size)
        if dy != 0.0:
            self._move_axis(0.0, dy, maze, cell_size)

        moved = (self.x, self.y) != (old_x, old_y)
        self.is_moving = moved

        # 更新在 OVERPASS 瓦片上的层级状态
        new_cx = int((self.x + self.size * 0.5) // cell_size)
        new_cy = int((self.y + self.size * 0.5) // cell_size)

        if 0 <= new_cx < maze.cols and 0 <= new_cy < maze.rows:
            tile_val = maze.grid[new_cy][new_cx]
            if tile_val == 2:  # OVERPASS_NS (南北桥，东西隧道)
                if cx != new_cx:  # 从东西侧相邻格水平切入 -> 东西隧道
                    self.overpass_layer = "ew_tunnel"
                elif cy != new_cy:  # 从南北侧相邻格垂直切入 -> 南北高架桥
                    self.overpass_layer = "ns_bridge"
                elif self.overpass_layer == "none":
                    if self.facing in ("up", "down") or move_y != 0:
                        self.overpass_layer = "ns_bridge"
                    else:
                        self.overpass_layer = "ew_tunnel"
            elif tile_val == 3:  # OVERPASS_EW (东西桥，南北隧道)
                if cx != new_cx:  # 从东西侧相邻格水平切入 -> 东西高架桥
                    self.overpass_layer = "ew_bridge"
                elif cy != new_cy:  # 从南北侧相邻格垂直切入 -> 南北隧道
                    self.overpass_layer = "ns_tunnel"
                elif self.overpass_layer == "none":
                    if self.facing in ("left", "right") or move_x != 0:
                        self.overpass_layer = "ew_bridge"
                    else:
                        self.overpass_layer = "ns_tunnel"
            else:
                self.overpass_layer = "none"
        else:
            self.overpass_layer = "none"

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

    def _move_axis(self, dx: float, dy: float, maze: Maze, cell_size: int) -> None:
        """单轴尝试移动；浮点精确定位，碰撞取消。"""
        trial_x = self.x + dx
        trial_y = self.y + dy
        trial_rect = pygame.Rect(int(round(trial_x)), int(round(trial_y)), self.size, self.size)
        is_y_axis = (dy != 0.0)
        if not _hits_wall(trial_rect, maze, cell_size, is_y_axis=is_y_axis, player=self):
            self.x = trial_x
            self.y = trial_y
            self.rect = trial_rect

    def reached_exit(self, maze: Maze, cell_size: int) -> bool:
        """角色与出口格的内缩矩形相交即算到达（不必像素级对齐）。"""
        exit_rect = pygame.Rect(
            maze.exit[0] * cell_size,
            maze.exit[1] * cell_size,
            cell_size,
            cell_size,
        )
        return self.rect.colliderect(exit_rect.inflate(-cell_size // 4, -cell_size // 4))


def _hits_wall(
    rect: pygame.Rect,
    maze: Maze,
    cell_size: int,
    is_y_axis: bool = False,
    player: Player | None = None,
) -> bool:
    """用角色矩形覆盖到的瓦片范围做碰撞，比逐像素查表便宜。支持 OVERPASS 立交桥方向与护栏判定。"""
    left = rect.left // cell_size
    right = (rect.right - 1) // cell_size
    top = rect.top // cell_size
    bottom = (rect.bottom - 1) // cell_size
    px = rect.centerx
    py = rect.centery
    current_layer = player.overpass_layer if player else "none"

    for tile_y in range(top, bottom + 1):
        for tile_x in range(left, right + 1):
            if maze.is_wall(
                tile_x,
                tile_y,
                is_y_axis=is_y_axis,
                player_x=px,
                player_y=py,
                cell_size=cell_size,
                current_layer=current_layer,
            ):
                return True
    return False
