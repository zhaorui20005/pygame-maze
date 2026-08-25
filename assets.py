"""音效生成与精细图形绘制资产模块 (Procedural Assets & Synthesizer)。

包含：
1. 内存程序化合成 8-bit / 复古音效 (走路音效、新局开始音效、通关音效)。
2. 程序化绘制矢量/像素风格的精细 Surface：
   - 小房子 (起点/入口)
   - 胜利小旗子 (终点/出口)
   - 4方向 x 2帧 大头萌系 Q 版走动小人 (玩家角色)
"""

from __future__ import annotations

import math
import struct
import pygame

# --- 1. 程序化音效合成器 (Sound Synthesizer) ---

def _generate_wav_bytes(
    samples: list[float], sample_rate: int = 22050
) -> bytes:
    """把 [-1.0, 1.0] 的浮点采样列表转换成 16-bit PCM WAV format 的 bytes 数据。"""
    pcm_data = bytearray()
    for s in samples:
        clamped = max(-1.0, min(1.0, s))
        val = int(clamped * 32767)
        pcm_data.extend(struct.pack("<h", val))

    num_samples = len(samples)
    data_size = num_samples * 2
    file_size = 36 + data_size

    # 44 字节 standard WAV header
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        file_size,
        b"WAVE",
        b"fmt ",
        16,  # Subchunk1Size (16 for PCM)
        1,   # AudioFormat (1 for PCM)
        1,   # NumChannels (1 for Mono)
        sample_rate,
        sample_rate * 2,  # ByteRate
        2,   # BlockAlign
        16,  # BitsPerSample
        b"data",
        data_size,
    )
    return bytes(header) + bytes(pcm_data)


def create_sound_step(sample_rate: int = 22050) -> pygame.mixer.Sound | None:
    """生成脚踏/走路轻微音效。"""
    try:
        duration = 0.04
        num_samples = int(sample_rate * duration)
        samples = []
        freq = 160.0
        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-35.0 * t)  # 快衰减包络
            sine = math.sin(2.0 * math.pi * freq * t)
            noise = (math.sin(2.0 * math.pi * freq * 3.7 * t) + math.sin(2.0 * math.pi * freq * 7.1 * t)) * 0.3
            samples.append((sine * 0.7 + noise * 0.3) * env * 0.35)

        wav_bytes = _generate_wav_bytes(samples, sample_rate)
        import io
        return pygame.mixer.Sound(io.BytesIO(wav_bytes))
    except Exception as e:
        print(f"Warning: Failed to create step sound: {e}")
        return None


def create_sound_start(sample_rate: int = 22050) -> pygame.mixer.Sound | None:
    """生成新一局开始/重随的开场三连音 (Upward Arpeggio C5-E5-G5)。"""
    try:
        duration = 0.22
        num_samples = int(sample_rate * duration)
        samples = []
        notes = [(0.0, 0.07, 523.25), (0.07, 0.14, 659.25), (0.14, 0.22, 783.99)]  # C5, E5, G5
        for i in range(num_samples):
            t = i / sample_rate
            val = 0.0
            for st, ed, freq in notes:
                if st <= t < ed:
                    local_t = t - st
                    env = math.sin(math.pi * (local_t / (ed - st))) ** 0.8
                    sine = math.sin(2.0 * math.pi * freq * local_t)
                    square = 0.5 if (math.sin(2.0 * math.pi * freq * local_t) >= 0) else -0.5
                    val = (sine * 0.6 + square * 0.4) * env * 0.4
                    break
            samples.append(val)

        wav_bytes = _generate_wav_bytes(samples, sample_rate)
        import io
        return pygame.mixer.Sound(io.BytesIO(wav_bytes))
    except Exception as e:
        print(f"Warning: Failed to create start sound: {e}")
        return None


def create_sound_win(sample_rate: int = 22050) -> pygame.mixer.Sound | None:
    """生成胜利通关欢快和弦 (Fanfare G5-C6-E6-G6)。"""
    try:
        duration = 0.55
        num_samples = int(sample_rate * duration)
        samples = []
        notes = [
            (0.00, 0.10, 783.99),   # G5
            (0.10, 0.20, 1046.50),  # C6
            (0.20, 0.30, 1318.51),  # E6
            (0.30, 0.55, 1567.98),  # G6 (长音)
        ]
        for i in range(num_samples):
            t = i / sample_rate
            val = 0.0
            for st, ed, freq in notes:
                if st <= t < ed:
                    local_t = t - st
                    dur = ed - st
                    if freq == 1567.98:
                        env = math.exp(-4.0 * local_t)
                    else:
                        env = math.sin(math.pi * (local_t / dur)) ** 0.7
                    sine = math.sin(2.0 * math.pi * freq * local_t)
                    harm = math.sin(4.0 * math.pi * freq * local_t) * 0.3
                    val = (sine + harm) * env * 0.45
                    break
            samples.append(val)

        wav_bytes = _generate_wav_bytes(samples, sample_rate)
        import io
        return pygame.mixer.Sound(io.BytesIO(wav_bytes))
    except Exception as e:
        print(f"Warning: Failed to create win sound: {e}")
        return None


# --- 2. 程序化图形绘制 (Graphics / Sprites Generator) ---

def create_house_surface(size: int = 128) -> pygame.Surface:
    """生成入口小房子 Surface。"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    s = size

    # 墙体 (暖黄/木质)
    wall_rect = pygame.Rect(int(s * 0.18), int(s * 0.38), int(s * 0.64), int(s * 0.54))
    pygame.draw.rect(surf, (230, 190, 140), wall_rect, border_radius=int(s * 0.04))
    pygame.draw.rect(surf, (160, 120, 80), wall_rect, width=int(s * 0.035), border_radius=int(s * 0.04))

    # 屋顶 (鲜红/砖红 尖顶)
    roof_pts = [
        (int(s * 0.50), int(s * 0.06)),
        (int(s * 0.08), int(s * 0.42)),
        (int(s * 0.92), int(s * 0.42)),
    ]
    pygame.draw.polygon(surf, (220, 60, 50), roof_pts)
    pygame.draw.polygon(surf, (140, 30, 20), roof_pts, width=int(s * 0.035))

    # 烟囱
    chimney = pygame.Rect(int(s * 0.68), int(s * 0.14), int(s * 0.11), int(s * 0.20))
    pygame.draw.rect(surf, (150, 65, 55), chimney)
    pygame.draw.rect(surf, (90, 40, 30), chimney, width=int(s * 0.025))

    # 门 (拱形深棕色门)
    door_rect = pygame.Rect(int(s * 0.41), int(s * 0.60), int(s * 0.18), int(s * 0.32))
    pygame.draw.rect(surf, (110, 65, 35), door_rect, border_radius=int(s * 0.04))
    pygame.draw.circle(surf, (255, 215, 80), (int(s * 0.54), int(s * 0.76)), int(s * 0.03))

    # 窗户 (天空蓝+白十字窗格)
    win_rect = pygame.Rect(int(s * 0.24), int(s * 0.50), int(s * 0.13), int(s * 0.13))
    pygame.draw.rect(surf, (130, 210, 255), win_rect)
    pygame.draw.rect(surf, (255, 255, 255), win_rect, width=int(s * 0.025))
    pygame.draw.line(surf, (255, 255, 255), (win_rect.centerx, win_rect.top), (win_rect.centerx, win_rect.bottom), width=int(s * 0.02))
    pygame.draw.line(surf, (255, 255, 255), (win_rect.left, win_rect.centery), (win_rect.right, win_rect.centery), width=int(s * 0.02))

    return surf


def create_flag_surface(size: int = 128) -> pygame.Surface:
    """生成终点小旗子 Surface。"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    s = size

    # 底座 (灰石台阶)
    base_rect = pygame.Rect(int(s * 0.22), int(s * 0.82), int(s * 0.56), int(s * 0.13))
    pygame.draw.rect(surf, (120, 130, 140), base_rect, border_radius=int(s * 0.03))
    pygame.draw.rect(surf, (70, 80, 90), base_rect, width=int(s * 0.03), border_radius=int(s * 0.03))

    # 旗杆 (金黄/木色)
    pole_x = int(s * 0.36)
    pygame.draw.line(surf, (210, 180, 80), (pole_x, int(s * 0.10)), (pole_x, int(s * 0.85)), width=int(s * 0.06))

    # 旗杆顶端金球
    pygame.draw.circle(surf, (255, 230, 70), (pole_x, int(s * 0.09)), int(s * 0.055))

    # 飘扬的旗帜 (亮红色)
    flag_pts = [
        (pole_x, int(s * 0.12)),
        (int(s * 0.86), int(s * 0.27)),
        (pole_x, int(s * 0.46)),
    ]
    pygame.draw.polygon(surf, (240, 45, 55), flag_pts)
    pygame.draw.polygon(surf, (170, 20, 30), flag_pts, width=int(s * 0.03))

    # 旗子中间小金星
    star_center = (int(s * 0.52), int(s * 0.28))
    pygame.draw.circle(surf, (255, 235, 90), star_center, int(s * 0.06))

    return surf


def create_player_sprites(size: int = 128) -> dict[str, list[pygame.Surface]]:
    """生成大头萌系 Q 版小人角色的 4 个方向，每个方向 2 帧走动动画的 Surface。"""
    sprites = {}
    directions = ["down", "up", "left", "right"]

    for d in directions:
        sprites[d] = [
            _draw_cute_character(size, d, frame=0),
            _draw_cute_character(size, d, frame=1),
        ]

    return sprites


def _draw_cute_character(size: int, facing: str, frame: int) -> pygame.Surface:
    """绘制超萌大头 Q 版小人 (大头、水汪汪大眼睛、粉红腮红、帅气小帽子/发型、亮丽衣服与迈步小手小脚)。"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    s = size

    # 调色盘
    c_skin = (255, 224, 196)       # 萌系粉白肤色
    c_blush = (255, 140, 160)      # 萌萌粉红腮红
    c_hair = (60, 40, 30)          # 深栗色头发
    c_cap = (255, 80, 50)          # 鲜艳大红棒球帽/帽子
    c_cap_brim = (230, 50, 30)     # 帽檐
    c_shirt = (40, 160, 240)       # 亮红/亮蓝萌系卫衣
    c_pants = (50, 60, 85)         # 藏青裤子
    c_shoes = (255, 255, 255)      # 亮白运动小鞋
    c_eye_bg = (25, 25, 35)        # 大眼珠
    c_eye_sparkle = (255, 255, 255)# 水汪汪闪烁高光点

    # 比例结构 (Q版 1.5 头身：大头占绝大部分空间)
    center_x = s * 0.50
    head_y = s * 0.36              # 大头中心
    head_r = s * 0.28              # 超大圆形大头！

    body_top = s * 0.58
    body_h = s * 0.20
    body_w = s * 0.32

    leg_top = body_top + body_h
    leg_h = s * 0.16

    # 脚步摆动偏移
    leg_offset = (s * 0.08) if frame == 1 else (-s * 0.08)

    if facing == "down":
        # === 正面 (朝下) ===
        # 1. 裤子与小鞋子
        left_foot = pygame.Rect(int(center_x - s * 0.13), int(leg_top + leg_offset * 0.4), int(s * 0.10), int(leg_h))
        right_foot = pygame.Rect(int(center_x + s * 0.03), int(leg_top - leg_offset * 0.4), int(s * 0.10), int(leg_h))
        pygame.draw.rect(surf, c_pants, left_foot, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_pants, right_foot, border_radius=int(s * 0.03))
        # 亮白萌系小鞋
        pygame.draw.rect(surf, c_shoes, (left_foot.left - int(s * 0.01), left_foot.bottom - int(s * 0.06), left_foot.width + int(s * 0.02), int(s * 0.06)), border_radius=int(s * 0.02))
        pygame.draw.rect(surf, c_shoes, (right_foot.left - int(s * 0.01), right_foot.bottom - int(s * 0.06), right_foot.width + int(s * 0.02), int(s * 0.06)), border_radius=int(s * 0.02))

        # 2. 身体上衣
        body_rect = pygame.Rect(int(center_x - body_w / 2), int(body_top), int(body_w), int(body_h))
        pygame.draw.rect(surf, c_shirt, body_rect, border_radius=int(s * 0.04))

        # 小手臂
        arm_l = pygame.Rect(int(body_rect.left - s * 0.06), int(body_top + s * 0.02 - leg_offset * 0.5), int(s * 0.07), int(s * 0.14))
        arm_r = pygame.Rect(int(body_rect.right - s * 0.01), int(body_top + s * 0.02 + leg_offset * 0.5), int(s * 0.07), int(s * 0.14))
        pygame.draw.rect(surf, c_shirt, arm_l, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_shirt, arm_r, border_radius=int(s * 0.03))
        pygame.draw.circle(surf, c_skin, (arm_l.centerx, arm_l.bottom), int(s * 0.035))
        pygame.draw.circle(surf, c_skin, (arm_r.centerx, arm_r.bottom), int(s * 0.035))

        # 3. 超大头
        pygame.draw.circle(surf, c_skin, (int(center_x), int(head_y)), int(head_r))

        # 帽子 (鲜艳大红帽)
        cap_rect = pygame.Rect(int(center_x - head_r * 1.05), int(head_y - head_r * 1.05), int(head_r * 2.1), int(head_r * 1.1))
        pygame.draw.ellipse(surf, c_cap, cap_rect)
        # 帽檐
        brim_rect = pygame.Rect(int(center_x - head_r * 1.1), int(head_y - head_r * 0.15), int(head_r * 2.2), int(s * 0.08))
        pygame.draw.ellipse(surf, c_cap_brim, brim_rect)

        # 腮红 (粉红小圈)
        pygame.draw.circle(surf, c_blush, (int(center_x - s * 0.15), int(head_y + s * 0.10)), int(s * 0.045))
        pygame.draw.circle(surf, c_blush, (int(center_x + s * 0.15), int(head_y + s * 0.10)), int(s * 0.045))

        # 萌萌水汪汪大眼睛
        eye_l_center = (int(center_x - s * 0.10), int(head_y + s * 0.04))
        eye_r_center = (int(center_x + s * 0.10), int(head_y + s * 0.04))
        pygame.draw.circle(surf, c_eye_bg, eye_l_center, int(s * 0.045))
        pygame.draw.circle(surf, c_eye_bg, eye_r_center, int(s * 0.045))
        # 高光点
        pygame.draw.circle(surf, c_eye_sparkle, (eye_l_center[0] - int(s * 0.012), eye_l_center[1] - int(s * 0.012)), int(s * 0.018))
        pygame.draw.circle(surf, c_eye_sparkle, (eye_r_center[0] - int(s * 0.012), eye_r_center[1] - int(s * 0.012)), int(s * 0.018))

        # 萌可爱笑脸
        smile_rect = pygame.Rect(int(center_x - s * 0.04), int(head_y + s * 0.11), int(s * 0.08), int(s * 0.05))
        pygame.draw.arc(surf, (80, 50, 40), smile_rect, math.pi, 2 * math.pi, int(s * 0.025))

    elif facing == "up":
        # === 背面 (朝上) ===
        # 1. 裤子与鞋子
        left_foot = pygame.Rect(int(center_x - s * 0.13), int(leg_top - leg_offset * 0.4), int(s * 0.10), int(leg_h))
        right_foot = pygame.Rect(int(center_x + s * 0.03), int(leg_top + leg_offset * 0.4), int(s * 0.10), int(leg_h))
        pygame.draw.rect(surf, c_pants, left_foot, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_pants, right_foot, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_shoes, (left_foot.left - int(s * 0.01), left_foot.bottom - int(s * 0.06), left_foot.width + int(s * 0.02), int(s * 0.06)), border_radius=int(s * 0.02))
        pygame.draw.rect(surf, c_shoes, (right_foot.left - int(s * 0.01), right_foot.bottom - int(s * 0.06), right_foot.width + int(s * 0.02), int(s * 0.06)), border_radius=int(s * 0.02))

        # 2. 上衣
        body_rect = pygame.Rect(int(center_x - body_w / 2), int(body_top), int(body_w), int(body_h))
        pygame.draw.rect(surf, c_shirt, body_rect, border_radius=int(s * 0.04))

        # 手臂
        arm_l = pygame.Rect(int(body_rect.left - s * 0.06), int(body_top + s * 0.02 + leg_offset * 0.5), int(s * 0.07), int(s * 0.14))
        arm_r = pygame.Rect(int(body_rect.right - s * 0.01), int(body_top + s * 0.02 - leg_offset * 0.5), int(s * 0.07), int(s * 0.14))
        pygame.draw.rect(surf, c_shirt, arm_l, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_shirt, arm_r, border_radius=int(s * 0.03))

        # 3. 超大头背影（帽子完全盖住后脑勺）
        pygame.draw.circle(surf, c_skin, (int(center_x), int(head_y)), int(head_r))
        pygame.draw.circle(surf, c_hair, (int(center_x), int(head_y + s * 0.02)), int(head_r * 0.95))
        # 棒球帽后脑勺
        cap_rect = pygame.Rect(int(center_x - head_r * 1.05), int(head_y - head_r * 1.05), int(head_r * 2.1), int(head_r * 1.3))
        pygame.draw.ellipse(surf, c_cap, cap_rect)

    elif facing == "left":
        # === 侧面 (朝左) ===
        # 1. 裤子与鞋子 (前后交替迈步)
        l1 = pygame.Rect(int(center_x - s * 0.06 + leg_offset), int(leg_top), int(s * 0.12), int(leg_h))
        l2 = pygame.Rect(int(center_x - s * 0.06 - leg_offset), int(leg_top), int(s * 0.12), int(leg_h))
        pygame.draw.rect(surf, c_pants, l2, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_pants, l1, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_shoes, (l1.left - int(s * 0.04), l1.bottom - int(s * 0.06), int(s * 0.15), int(s * 0.06)), border_radius=int(s * 0.02))

        # 2. 身体
        body_rect = pygame.Rect(int(center_x - s * 0.12), int(body_top), int(s * 0.24), int(body_h))
        pygame.draw.rect(surf, c_shirt, body_rect, border_radius=int(s * 0.04))

        # 侧手臂
        arm = pygame.Rect(int(center_x - s * 0.04 - leg_offset * 0.6), int(body_top + s * 0.02), int(s * 0.08), int(s * 0.14))
        pygame.draw.rect(surf, c_shirt, arm, border_radius=int(s * 0.03))
        pygame.draw.circle(surf, c_skin, (arm.centerx, arm.bottom), int(s * 0.035))

        # 3. 超大侧头
        pygame.draw.circle(surf, c_skin, (int(center_x), int(head_y)), int(head_r))

        # 侧帽子
        cap_rect = pygame.Rect(int(center_x - head_r * 0.95), int(head_y - head_r * 1.05), int(head_r * 1.9), int(head_r * 1.1))
        pygame.draw.ellipse(surf, c_cap, cap_rect)
        # 向左突出的帽檐
        brim_rect = pygame.Rect(int(center_x - head_r * 1.25), int(head_y - head_r * 0.10), int(head_r * 1.1), int(s * 0.08))
        pygame.draw.ellipse(surf, c_cap_brim, brim_rect)

        # 侧粉红腮红
        pygame.draw.circle(surf, c_blush, (int(center_x - s * 0.14), int(head_y + s * 0.10)), int(s * 0.045))

        # 侧萌萌大眼睛
        eye_center = (int(center_x - s * 0.12), int(head_y + s * 0.04))
        pygame.draw.circle(surf, c_eye_bg, eye_center, int(s * 0.045))
        pygame.draw.circle(surf, c_eye_sparkle, (eye_center[0] - int(s * 0.012), eye_center[1] - int(s * 0.012)), int(s * 0.018))

    elif facing == "right":
        # === 侧面 (朝右) ===
        # 1. 裤子与鞋子
        l1 = pygame.Rect(int(center_x - s * 0.06 - leg_offset), int(leg_top), int(s * 0.12), int(leg_h))
        l2 = pygame.Rect(int(center_x - s * 0.06 + leg_offset), int(leg_top), int(s * 0.12), int(leg_h))
        pygame.draw.rect(surf, c_pants, l2, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_pants, l1, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_shoes, (l1.left - int(s * 0.01), l1.bottom - int(s * 0.06), int(s * 0.15), int(s * 0.06)), border_radius=int(s * 0.02))

        # 2. 身体
        body_rect = pygame.Rect(int(center_x - s * 0.12), int(body_top), int(s * 0.24), int(body_h))
        pygame.draw.rect(surf, c_shirt, body_rect, border_radius=int(s * 0.04))

        # 侧手臂
        arm = pygame.Rect(int(center_x - s * 0.04 + leg_offset * 0.6), int(body_top + s * 0.02), int(s * 0.08), int(s * 0.14))
        pygame.draw.rect(surf, c_shirt, arm, border_radius=int(s * 0.03))
        pygame.draw.circle(surf, c_skin, (arm.centerx, arm.bottom), int(s * 0.035))

        # 3. 超大侧头
        pygame.draw.circle(surf, c_skin, (int(center_x), int(head_y)), int(head_r))

        # 侧帽子
        cap_rect = pygame.Rect(int(center_x - head_r * 0.95), int(head_y - head_r * 1.05), int(head_r * 1.9), int(head_r * 1.1))
        pygame.draw.ellipse(surf, c_cap, cap_rect)
        # 向右突出的帽檐
        brim_rect = pygame.Rect(int(center_x + head_r * 0.15), int(head_y - head_r * 0.10), int(head_r * 1.1), int(s * 0.08))
        pygame.draw.ellipse(surf, c_cap_brim, brim_rect)

        # 侧粉红腮红
        pygame.draw.circle(surf, c_blush, (int(center_x + s * 0.14), int(head_y + s * 0.10)), int(s * 0.045))

        # 侧萌萌大眼睛
        eye_center = (int(center_x + s * 0.12), int(head_y + s * 0.04))
        pygame.draw.circle(surf, c_eye_bg, eye_center, int(s * 0.045))
        pygame.draw.circle(surf, c_eye_sparkle, (eye_center[0] - int(s * 0.012), eye_center[1] - int(s * 0.012)), int(s * 0.018))

    return surf
