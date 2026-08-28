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


def create_sound_item(sample_rate: int = 22050) -> pygame.mixer.Sound | None:
    """生成拾取道具/吃宝物的清脆 8-bit 双连音效 (E6 -> A6)。"""
    try:
        duration = 0.15
        num_samples = int(sample_rate * duration)
        samples = []
        notes = [(0.0, 0.07, 1318.5), (0.07, 0.15, 1760.0)]
        for i in range(num_samples):
            t = i / sample_rate
            val = 0.0
            for st, ed, freq in notes:
                if st <= t < ed:
                    local_t = t - st
                    dur = ed - st
                    env = math.sin(math.pi * (local_t / dur)) ** 0.6
                    sine = math.sin(2.0 * math.pi * freq * local_t)
                    square = 0.4 if sine >= 0 else -0.4
                    val = (sine * 0.5 + square * 0.5) * env * 0.45
                    break
            samples.append(val)

        wav_bytes = _generate_wav_bytes(samples, sample_rate)
        import io
        return pygame.mixer.Sound(io.BytesIO(wav_bytes))
    except Exception as e:
        print(f"Warning: Failed to create item sound: {e}")
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


def create_sound_wolf(sample_rate: int = 22050) -> pygame.mixer.Sound | None:
    """生成大灰狼出现的狼嚎/紧急提示音 (Pitch slide Wolf Howl)。"""
    try:
        duration = 0.60
        num_samples = int(sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            if t < 0.3:
                freq = 200.0 + (t / 0.3) * 250.0
            else:
                freq = 450.0 - ((t - 0.3) / 0.3) * 200.0

            env = math.sin(math.pi * (t / duration)) ** 0.8
            vibrato = math.sin(2.0 * math.pi * 8.0 * t) * 0.15
            wave = math.sin(2.0 * math.pi * (freq + vibrato * 50.0) * t)
            samples.append(wave * env * 0.50)

        wav_bytes = _generate_wav_bytes(samples, sample_rate)
        import io
        return pygame.mixer.Sound(io.BytesIO(wav_bytes))
    except Exception as e:
        print(f"Warning: Failed to create wolf sound: {e}")
        return None


def create_sound_caught(sample_rate: int = 22050) -> pygame.mixer.Sound | None:
    """生成被大灰狼追上的提示音。"""
    try:
        duration = 0.40
        num_samples = int(sample_rate * duration)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            freq = 300.0 - (t / duration) * 180.0
            env = math.exp(-6.0 * t)
            sine = math.sin(2.0 * math.pi * freq * t)
            saw = (2.0 * (t * freq - math.floor(0.5 + t * freq))) * 0.5
            samples.append((sine * 0.6 + saw * 0.4) * env * 0.5)

        wav_bytes = _generate_wav_bytes(samples, sample_rate)
        import io
        return pygame.mixer.Sound(io.BytesIO(wav_bytes))
    except Exception as e:
        print(f"Warning: Failed to create caught sound: {e}")
        return None


def _synthesize_nes_bgm(
    bpm: float,
    lead_pattern: list[str],
    harm_pattern: list[str],
    bass_pattern: list[str],
    drum_pattern: list[str],
    sample_rate: int = 22050,
    lead_duty: float = 0.25,
    harm_duty: float = 0.50,
    lead_vibrato: float = 6.0,
) -> pygame.mixer.Sound | None:
    """NES 8-bit 通用合成编曲引擎。"""
    try:
        step_dur = 60.0 / (bpm * 4.0)
        total_steps = len(lead_pattern)
        duration = total_steps * step_dur
        num_samples = int(sample_rate * duration)

        N = {
            "_": 0.0,
            "C1": 32.70, "CS1": 34.65, "D1": 36.71, "DS1": 38.89, "E1": 41.20, "F1": 43.65, "FS1": 46.25, "G1": 49.00, "GS1": 51.91, "A1": 55.00, "AS1": 58.27, "B1": 61.74,
            "C2": 65.41, "CS2": 69.30, "D2": 73.42, "DS2": 77.78, "E2": 82.41, "F2": 87.31, "FS2": 92.50, "G2": 98.00, "GS2": 103.83, "A2": 110.00, "AS2": 116.54, "B2": 123.47,
            "C3": 130.81, "CS3": 138.59, "D3": 146.83, "DS3": 155.56, "E3": 164.81, "F3": 174.61, "FS3": 185.00, "G3": 196.00, "GS3": 207.65, "A3": 220.00, "AS3": 233.08, "B3": 246.94,
            "C4": 261.63, "CS4": 277.18, "D4": 293.66, "DS4": 311.13, "E4": 329.63, "F4": 349.23, "FS4": 369.99, "G4": 392.00, "GS4": 415.30, "A4": 440.00, "AS4": 466.16, "B4": 493.88,
            "C5": 523.25, "CS5": 554.37, "D5": 587.33, "DS5": 622.25, "E5": 659.25, "F5": 698.46, "FS5": 739.99, "G5": 783.99, "GS5": 830.61, "A5": 880.00, "AS5": 932.33, "B5": 987.77,
            "C6": 1046.50, "CS6": 1108.73, "D6": 1174.66, "DS6": 1244.51, "E6": 1318.51, "F6": 1396.91, "FS6": 1479.98, "G6": 1567.98, "GS6": 1661.22, "A6": 1760.00
        }

        lead_freqs = [N[name] for name in lead_pattern]
        harm_freqs = [N[name] for name in harm_pattern]
        bass_freqs = [N[name] for name in bass_pattern]

        samples = []
        phase1, phase2, phase3 = 0.0, 0.0, 0.0

        for i in range(num_samples):
            t = i / sample_rate
            step = int(t / step_dur) % total_steps
            step_t = t % step_dur

            f1 = lead_freqs[step]
            f2 = harm_freqs[step]
            f3 = bass_freqs[step]
            d = drum_pattern[step]

            # 1. Lead Pulse Wave
            lead_val = 0.0
            if f1 > 0.0:
                vib = 1.0 + 0.006 * math.sin(2.0 * math.pi * lead_vibrato * step_t) if lead_vibrato > 0 else 1.0
                phase1 = (phase1 + (f1 * vib) / sample_rate) % 1.0
                square1 = 1.0 if phase1 < lead_duty else -1.0
                env1 = math.exp(-5.0 * step_t) * 0.7 + 0.3
                lead_val = square1 * env1

            # 2. Harmony Pulse Wave
            harm_val = 0.0
            if f2 > 0.0:
                phase2 = (phase2 + f2 / sample_rate) % 1.0
                square2 = 1.0 if phase2 < harm_duty else -1.0
                env2 = math.exp(-7.0 * step_t) * 0.8
                harm_val = square2 * env2

            # 3. Bass Triangle Wave
            bass_val = 0.0
            if f3 > 0.0:
                phase3 = (phase3 + f3 / sample_rate) % 1.0
                tri = 2.0 * abs(2.0 * (phase3 - math.floor(phase3 + 0.5))) - 1.0
                env3 = math.exp(-3.5 * step_t) * 0.9
                bass_val = tri * env3

            # 4. Drum Noise Channel
            drum_val = 0.0
            rnd = (((i * 1103515245 + 12345) & 0x7FFFFFFF) / 2147483648.0) * 2.0 - 1.0

            if d == "K":
                freq_k = 120.0 * math.exp(-30.0 * step_t)
                sine_k = math.sin(2.0 * math.pi * freq_k * step_t)
                drum_val = sine_k * math.exp(-15.0 * step_t) * 1.1 + rnd * math.exp(-50.0 * step_t) * 0.25
            elif d == "S":
                drum_val = rnd * math.exp(-20.0 * step_t) * 0.85 + math.sin(2.0 * math.pi * 170.0 * step_t) * math.exp(-25.0 * step_t) * 0.35
            elif d == "H":
                drum_val = rnd * math.exp(-70.0 * step_t) * 0.35

            sample = (
                lead_val * 0.18 +
                harm_val * 0.11 +
                bass_val * 0.27 +
                drum_val * 0.15
            )
            samples.append(sample)

        wav_bytes = _generate_wav_bytes(samples, sample_rate)
        import io
        return pygame.mixer.Sound(io.BytesIO(wav_bytes))
    except Exception as e:
        print(f"Warning: Failed to create BGM sound: {e}")
        return None


def create_sound_bgm_menu(sample_rate: int = 22050) -> pygame.mixer.Sound | None:
    """生成主界面 BGM：102 BPM 温馨放松的 8-bit 小调玄想曲。"""
    bpm = 102.0
    lead = [
        "E4", "_", "G4", "_", "B4", "_", "E5", "_", "D5", "_", "B4", "_", "G4", "_", "A4", "B4",
        "C5", "_", "E4", "_", "A4", "_", "C5", "_", "B4", "_", "G4", "_", "E4", "_", "F4", "G4",
        "A4", "_", "C4", "_", "F4", "_", "A4", "_", "G4", "_", "E4", "_", "C4", "_", "D4", "E4",
        "F4", "A4", "C5", "F5", "E5", "D5", "C5", "B4", "A4", "G4", "F4", "E4", "D4", "C4", "B3", "D4",
        "E4", "_", "G4", "_", "B4", "_", "E5", "_", "G5", "E5", "B4", "G4", "E5", "B4", "G4", "E4",
        "A4", "_", "C5", "_", "E5", "_", "A5", "_", "G5", "E5", "C5", "A4", "F5", "D5", "B4", "G4",
        "F4", "A4", "C5", "F5", "E5", "C5", "A4", "F4", "G4", "B4", "D5", "G5", "F5", "D5", "B4", "G4",
        "E5", "_", "B4", "_", "G4", "_", "E4", "_", "E4", "F4", "G4", "A4", "B4", "C5", "D5", "DS5"
    ]
    harm = [
        "B3", "_", "E4", "_", "G4", "_", "B4", "_", "G4", "_", "E4", "_", "B3", "_", "F3", "G3",
        "A3", "_", "C4", "_", "E4", "_", "A4", "_", "E4", "_", "C4", "_", "B3", "_", "D4", "E4",
        "F3", "_", "A3", "_", "C4", "_", "F4", "_", "E4", "_", "C4", "_", "G3", "_", "B3", "C4",
        "D4", "F4", "A4", "D5", "C5", "B4", "A4", "G4", "F4", "E4", "D4", "C4", "B3", "A3", "G3", "B3",
        "B3", "_", "E4", "_", "G4", "_", "B4", "_", "E5", "B4", "G4", "E4", "B4", "G4", "E4", "B3",
        "C4", "_", "E4", "_", "A4", "_", "C5", "_", "E5", "C5", "A4", "E4", "D5", "B4", "G4", "D4",
        "D4", "F4", "A4", "D5", "C5", "A4", "F4", "D4", "E4", "G4", "B4", "E5", "D5", "B4", "G4", "E4",
        "G4", "_", "E4", "_", "B3", "_", "G3", "_", "B3", "C4", "D4", "E4", "F4", "FS4", "G4", "GS4"
    ]
    bass = [
        "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3",
        "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2",
        "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
        "D2", "D3", "D2", "D3", "D2", "D3", "D2", "D3", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2",
        "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3",
        "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "F1", "F2", "F1", "F2", "G1", "G2", "G1", "G2",
        "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2",
        "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3"
    ]
    drum = [
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "S", "K", "S", "S", "_", "S", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S"
    ]
    return _synthesize_nes_bgm(bpm, lead, harm, bass, drum, sample_rate, lead_duty=0.50, harm_duty=0.25, lead_vibrato=4.0)


def create_sound_bgm_free(sample_rate: int = 22050) -> pygame.mixer.Sound | None:
    """生成自由模式 BGM：114 BPM 欢快明轻的 FC 冒险探险曲 (超级玛丽 / 高桥名人风格)。"""
    bpm = 114.0
    lead = [
        "C5", "C5", "_", "C5", "_", "A4", "C5", "_", "G4", "_", "E4", "_", "G4", "_", "A4", "B4",
        "A4", "A4", "_", "C5", "_", "B4", "A4", "_", "G4", "_", "E4", "_", "C4", "D4", "E4", "G4",
        "F4", "F4", "A4", "C5", "B4", "A4", "G4", "F4", "E4", "E4", "G4", "C5", "A4", "G4", "F4", "E4",
        "D4", "F4", "A4", "D5", "C5", "B4", "A4", "G4", "G4", "A4", "B4", "C5", "D5", "E5", "F5", "FS5",
        "G5", "E5", "C5", "G4", "E5", "C5", "G4", "E4", "A5", "F5", "C5", "A4", "F5", "C5", "A4", "F4",
        "G5", "F5", "E5", "D5", "C5", "B4", "A4", "G4", "E5", "D5", "C5", "B4", "C5", "_", "G4", "_",
        "F4", "A4", "C5", "F5", "E5", "D5", "C5", "A4", "G4", "B4", "D5", "G5", "F5", "E5", "D5", "B4",
        "C5", "C5", "G4", "G4", "E4", "E4", "C4", "C4", "D4", "E4", "F4", "FS4", "G4", "G4", "B4", "D5"
    ]
    harm = [
        "E4", "E4", "_", "E4", "_", "F4", "A4", "_", "E4", "_", "C4", "_", "E4", "_", "F4", "G4",
        "F4", "F4", "_", "A4", "_", "G4", "F4", "_", "E4", "_", "C4", "_", "A3", "B3", "C4", "E4",
        "D4", "D4", "F4", "A4", "G4", "F4", "E4", "D4", "C4", "C4", "E4", "G4", "F4", "E4", "D4", "C4",
        "B3", "D4", "F4", "B4", "A4", "G4", "F4", "E4", "E4", "F4", "G4", "A4", "B4", "C5", "D5", "DS5",
        "E5", "C5", "G4", "E4", "C5", "G4", "E4", "C4", "F5", "C5", "A4", "F4", "C5", "A4", "F4", "C4",
        "E5", "D5", "C5", "B4", "A4", "G4", "F4", "E4", "C5", "B4", "A4", "G4", "E4", "_", "E4", "_",
        "D4", "F4", "A4", "D5", "C5", "B4", "A4", "F4", "E4", "G4", "B4", "E5", "D5", "C5", "B4", "G4",
        "E4", "E4", "C4", "C4", "G3", "G3", "E3", "E3", "B3", "C4", "D4", "DS4", "E4", "E4", "G4", "B4"
    ]
    bass = [
        "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
        "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
        "D2", "D3", "D2", "D3", "D2", "D3", "D2", "D3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
        "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2",
        "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2",
        "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
        "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2",
        "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2"
    ]
    drum = [
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "S", "K", "S", "S", "S", "S", "S",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S"
    ]
    return _synthesize_nes_bgm(bpm, lead, harm, bass, drum, sample_rate, lead_duty=0.25, harm_duty=0.50, lead_vibrato=5.0)


def create_sound_bgm_challenge(sample_rate: int = 22050) -> pygame.mixer.Sound | None:
    """生成闯关模式 BGM：120 BPM 热血英雄 8-bit FC 风格 (魂斗罗 / 赤色要塞，节奏放慢更舒适)。"""
    bpm = 120.0
    lead = [
        "A3", "_", "C4", "_", "E4", "_", "A4", "_", "E4", "_", "C4", "_", "A3", "C4", "D4", "DS4",
        "E4", "_", "G4", "_", "A4", "_", "C5", "_", "B4", "_", "A4", "_", "G4", "E4", "G4", "A4",
        "F4", "_", "A4", "_", "C5", "_", "F5", "_", "E5", "_", "D5", "_", "C5", "_", "A4", "_",
        "G4", "B4", "D5", "G5", "F5", "E5", "D5", "C5", "B4", "A4", "G4", "F4", "E4", "D4", "C4", "B3",
        "A4", "_", "C5", "_", "E5", "_", "A5", "_", "G5", "E5", "C5", "A4", "E5", "C5", "A4", "E4",
        "F5", "_", "C5", "_", "A4", "_", "F4", "_", "C5", "_", "A4", "_", "F4", "_", "A4", "C5",
        "G5", "_", "D5", "_", "B4", "_", "G4", "_", "D5", "_", "B4", "_", "G4", "_", "B4", "D5",
        "E5", "E5", "D5", "C5", "B4", "B4", "A4", "GS4", "B4", "C5", "D5", "DS5", "E5", "E5", "G5", "GS5"
    ]
    harm = [
        "E3", "_", "A3", "_", "C4", "_", "E4", "_", "C4", "_", "A3", "_", "E3", "A3", "B3", "C4",
        "C4", "_", "E4", "_", "E4", "_", "A4", "_", "G4", "_", "E4", "_", "D4", "C4", "D4", "E4",
        "C4", "_", "F4", "_", "A4", "_", "C5", "_", "C5", "_", "A4", "_", "F4", "_", "C4", "_",
        "D4", "G4", "B4", "D5", "D5", "C5", "B4", "A4", "G4", "F4", "E4", "D4", "C4", "B3", "A3", "G3",
        "E4", "_", "A4", "_", "C5", "_", "E5", "_", "E5", "C5", "A4", "E4", "C5", "A4", "E4", "C4",
        "C5", "_", "A4", "_", "F4", "_", "C4", "_", "A4", "_", "F4", "_", "C4", "_", "F4", "A4",
        "D5", "_", "B4", "_", "G4", "_", "D4", "_", "B4", "_", "G4", "_", "D4", "_", "G4", "B4",
        "GS4", "GS4", "F4", "E4", "D4", "D4", "C4", "B3", "D4", "E4", "F4", "FS4", "GS4", "GS4", "B4", "D5"
    ]
    bass = [
        "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2",
        "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2",
        "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2",
        "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2",
        "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2",
        "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2",
        "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2",
        "E1", "E2", "E1", "E2", "E1", "E2", "E1", "E2", "E1", "E2", "E1", "E2", "E1", "E2", "E1", "E2"
    ]
    drum = [
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "S", "K", "S", "S", "S", "S", "S",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S"
    ]
    return _synthesize_nes_bgm(bpm, lead, harm, bass, drum, sample_rate, lead_duty=0.25, harm_duty=0.50, lead_vibrato=6.0)


def create_sound_bgm_dungeon(sample_rate: int = 22050) -> pygame.mixer.Sound | None:
    """生成第二大关【狼穴地牢】BGM：108 BPM 诡异阴森的 FC 8-bit 地牢恶魔城/魔界村风格曲。"""
    bpm = 108.0
    lead = [
        "D4", "_", "F4", "GS4", "A4", "_", "D5", "_", "CS5", "_", "GS4", "F4", "D4", "_", "CS4", "_",
        "D4", "_", "F4", "GS4", "A4", "_", "F5", "_", "E5", "_", "CS5", "A4", "F4", "E4", "D4", "CS4",
        "G4", "_", "AS4", "CS5", "D5", "_", "G5", "_", "FS5", "_", "CS5", "AS4", "G4", "_", "FS4", "_",
        "A4", "CS5", "E5", "G5", "FS5", "F5", "E5", "DS5", "D5", "CS5", "C5", "B4", "AS4", "A4", "GS4", "G4",
        "D5", "_", "F5", "_", "GS5", "_", "D6", "_", "CS6", "GS5", "F5", "D5", "CS5", "GS4", "F4", "D4",
        "A4", "AS4", "D5", "F5", "A5", "GS5", "G5", "FS5", "F5", "E5", "DS5", "D5", "CS5", "C5", "B4", "A4",
        "G4", "AS4", "CS5", "E5", "G5", "CS5", "AS4", "G4", "A4", "CS5", "E5", "G5", "A5", "G5", "E5", "CS5",
        "D5", "D5", "CS5", "C5", "B4", "AS4", "A4", "GS4", "A4", "AS4", "C5", "CS5", "D5", "E5", "F5", "GS5"
    ]
    harm = [
        "F3", "_", "A3", "_", "D4", "_", "F4", "_", "E4", "_", "CS4", "_", "F3", "_", "E3", "_",
        "F3", "_", "A3", "_", "D4", "_", "D5", "_", "CS5", "_", "A4", "_", "D4", "_", "CS4", "_",
        "AS3", "_", "D4", "_", "G4", "_", "AS4", "_", "A4", "_", "E4", "_", "AS3", "_", "A3", "_",
        "CS4", "E4", "G4", "CS5", "C5", "B4", "AS4", "A4", "GS4", "G4", "FS4", "F4", "E4", "DS4", "D4", "CS4",
        "F4", "_", "A4", "_", "D5", "_", "F5", "_", "E5", "CS5", "A4", "F4", "E4", "CS4", "A3", "F3",
        "F4", "G4", "AS4", "D5", "F5", "E5", "DS5", "D5", "CS5", "C5", "B4", "AS4", "A4", "GS4", "G4", "FS4",
        "E4", "G4", "AS4", "CS5", "E5", "AS4", "G4", "E4", "CS4", "E4", "G4", "CS5", "E5", "CS5", "G4", "E4",
        "F4", "F4", "E4", "DS4", "D4", "CS4", "C4", "B3", "C4", "CS4", "D4", "DS4", "F4", "G4", "GS4", "A4"
    ]
    bass = [
        "D2", "D2", "CS2", "CS2", "C2", "C2", "B1", "B1", "AS1", "AS1", "A1", "A1", "GS1", "GS1", "A1", "CS2",
        "D2", "D2", "CS2", "CS2", "C2", "C2", "B1", "B1", "AS1", "AS1", "A1", "A1", "GS1", "GS1", "A1", "CS2",
        "G1", "G2", "FS1", "FS2", "F1", "F2", "E1", "E2", "DS1", "DS2", "D1", "D2", "CS1", "CS2", "D1", "FS1",
        "A1", "A2", "GS1", "GS2", "G1", "G2", "FS1", "FS2", "F1", "F2", "E1", "E2", "DS1", "DS2", "E1", "GS1",
        "D2", "D2", "CS2", "CS2", "C2", "C2", "B1", "B1", "AS1", "AS1", "A1", "A1", "GS1", "GS1", "A1", "CS2",
        "A1", "A2", "GS1", "GS2", "G1", "G2", "FS1", "FS2", "F1", "F2", "E1", "E2", "DS1", "DS2", "E1", "GS1",
        "G1", "G2", "FS1", "FS2", "F1", "F2", "E1", "E2", "A1", "A2", "GS1", "GS2", "G1", "G2", "FS1", "FS2",
        "D2", "D2", "CS2", "CS2", "C2", "C2", "B1", "B1", "AS1", "AS1", "A1", "A1", "GS1", "GS1", "A1", "CS2"
    ]
    drum = [
        "K", "_", "_", "_", "S", "_", "_", "_", "K", "_", "K", "_", "S", "_", "H", "_",
        "K", "_", "_", "_", "S", "_", "_", "_", "K", "_", "K", "_", "S", "S", "S", "S",
        "K", "_", "_", "_", "S", "_", "_", "_", "K", "_", "K", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S",
        "K", "_", "_", "_", "S", "_", "_", "_", "K", "_", "K", "_", "S", "_", "H", "_",
        "K", "_", "_", "_", "S", "_", "_", "_", "K", "_", "K", "_", "S", "S", "S", "S",
        "K", "_", "_", "_", "S", "_", "_", "_", "K", "_", "K", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S"
    ]
    return _synthesize_nes_bgm(bpm, lead, harm, bass, drum, sample_rate, lead_duty=0.125, harm_duty=0.50, lead_vibrato=8.0)


def create_sound_bgm_pattern(sample_rate: int = 22050) -> pygame.mixer.Sound | None:
    """生成第三大关【图案秘境】BGM：132 BPM 梦幻空灵的 FC 8-bit 魔法星空与秘境风格曲。"""
    bpm = 132.0
    lead = [
        "E5", "B4", "C5", "E5", "G5", "FS5", "E5", "D5", "C5", "G4", "A4", "C5", "E5", "D5", "C5", "B4",
        "E5", "B4", "C5", "E5", "A5", "G5", "FS5", "E5", "D5", "A4", "B4", "D5", "FS5", "E5", "D5", "CS5",
        "C5", "E5", "G5", "C6", "B5", "A5", "G5", "F5", "E5", "G5", "C6", "E6", "D6", "C6", "B5", "A5",
        "G5", "B5", "D6", "G6", "FS6", "E6", "D6", "C6", "B5", "G5", "A5", "B5", "C6", "D6", "E6", "FS6",
        "E5", "B4", "C5", "E5", "G5", "FS5", "E5", "D5", "C5", "G4", "A4", "C5", "E5", "D5", "C5", "B4",
        "E5", "B4", "C5", "E5", "A5", "G5", "FS5", "E5", "D5", "A4", "B4", "D5", "FS5", "E5", "D5", "CS5",
        "C5", "E5", "G5", "C6", "B5", "A5", "G5", "F5", "E5", "G5", "C6", "E6", "D6", "C6", "B5", "A5",
        "G5", "B5", "D6", "G6", "FS6", "E6", "D6", "C6", "B5", "G5", "A5", "B5", "C6", "D6", "E6", "FS6"
    ]
    harm = [
        "G4", "_", "E4", "_", "B4", "_", "G4", "_", "E4", "_", "C4", "_", "G4", "_", "E4", "_",
        "G4", "_", "E4", "_", "C5", "_", "A4", "_", "FS4", "_", "D4", "_", "A4", "_", "FS4", "_",
        "E4", "G4", "C5", "E5", "D5", "C5", "B4", "A4", "C4", "E4", "G4", "C5", "B4", "A4", "G4", "F4",
        "D4", "G4", "B4", "D5", "C5", "B4", "A4", "G4", "D4", "G4", "A4", "B4", "A4", "B4", "C5", "D5",
        "G4", "_", "E4", "_", "B4", "_", "G4", "_", "E4", "_", "C4", "_", "G4", "_", "E4", "_",
        "G4", "_", "E4", "_", "C5", "_", "A4", "_", "FS4", "_", "D4", "_", "A4", "_", "FS4", "_",
        "E4", "G4", "C5", "E5", "D5", "C5", "B4", "A4", "C4", "E4", "G4", "C5", "B4", "A4", "G4", "F4",
        "D4", "G4", "B4", "D5", "C5", "B4", "A4", "G4", "D4", "G4", "A4", "B4", "A4", "B4", "C5", "D5"
    ]
    bass = [
        "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
        "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "D2", "D3", "D2", "D3", "D2", "D3", "D2", "D3",
        "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
        "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2",
        "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
        "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "D2", "D3", "D2", "D3", "D2", "D3", "D2", "D3",
        "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
        "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2"
    ]
    drum = [
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "S", "S", "S",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "S", "S", "S",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S"
    ]
    return _synthesize_nes_bgm(bpm, lead, harm, bass, drum, sample_rate, lead_duty=0.25, harm_duty=0.50, lead_vibrato=5.0)


def create_sound_bgm_shape(sample_rate: int = 22050) -> pygame.mixer.Sound | None:
    """生成第四大关【异形几何秘境】BGM：140 BPM 律动欢快且富有科技几何感的 FC 8-bit 欢快曲。"""
    bpm = 140.0
    lead = [
        "C5", "E5", "G5", "C6", "A5", "F5", "C5", "F5", "B4", "D5", "G5", "B5", "C6", "G5", "E5", "C5",
        "C5", "E5", "G5", "C6", "D6", "B5", "G5", "D5", "C6", "A5", "F5", "D5", "B5", "G5", "E5", "D5",
        "E5", "GS5", "B5", "E6", "A5", "C6", "E6", "A6", "D5", "FS5", "A5", "D6", "G5", "B5", "D6", "G6",
        "C6", "G5", "E5", "C5", "A5", "F5", "D5", "A4", "B5", "G5", "F5", "D5", "C6", "G5", "E5", "C5",
        "C5", "E5", "G5", "C6", "A5", "F5", "C5", "F5", "B4", "D5", "G5", "B5", "C6", "G5", "E5", "C5",
        "C5", "E5", "G5", "C6", "D6", "B5", "G5", "D5", "C6", "A5", "F5", "D5", "B5", "G5", "E5", "D5",
        "E5", "GS5", "B5", "E6", "A5", "C6", "E6", "A6", "D5", "FS5", "A5", "D6", "G5", "B5", "D6", "G6",
        "C6", "G5", "E5", "C5", "A5", "F5", "D5", "A4", "B5", "G5", "F5", "D5", "C6", "G5", "E5", "C5"
    ]
    harm = [
        "G4", "_", "E4", "_", "F4", "_", "C4", "_", "G4", "_", "D4", "_", "E4", "_", "C4", "_",
        "G4", "_", "E4", "_", "B4", "_", "G4", "_", "A4", "_", "F4", "_", "G4", "_", "E4", "_",
        "B4", "_", "GS4", "_", "C5", "_", "A4", "_", "A4", "_", "FS4", "_", "B4", "_", "G4", "_",
        "G4", "_", "E4", "_", "F4", "_", "D4", "_", "G4", "_", "F4", "_", "E4", "_", "C4", "_",
        "G4", "_", "E4", "_", "F4", "_", "C4", "_", "G4", "_", "D4", "_", "E4", "_", "C4", "_",
        "G4", "_", "E4", "_", "B4", "_", "G4", "_", "A4", "_", "F4", "_", "G4", "_", "E4", "_",
        "B4", "_", "GS4", "_", "C5", "_", "A4", "_", "A4", "_", "FS4", "_", "B4", "_", "G4", "_",
        "G4", "_", "E4", "_", "F4", "_", "D4", "_", "G4", "_", "F4", "_", "E4", "_", "C4", "_"
    ]
    bass = [
        "C2", "C3", "C2", "C3", "F2", "F3", "F2", "F3", "G2", "G3", "G2", "G3", "C2", "C3", "C2", "C3",
        "C2", "C3", "C2", "C3", "G2", "G3", "G2", "G3", "F2", "F3", "F2", "F3", "G2", "G3", "G2", "G3",
        "E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
        "C2", "C3", "C2", "C3", "F2", "F3", "F2", "F3", "G2", "G3", "G2", "G3", "C2", "C3", "C2", "C3",
        "C2", "C3", "C2", "C3", "F2", "F3", "F2", "F3", "G2", "G3", "G2", "G3", "C2", "C3", "C2", "C3",
        "C2", "C3", "C2", "C3", "G2", "G3", "G2", "G3", "F2", "F3", "F2", "F3", "G2", "G3", "G2", "G3",
        "E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
        "C2", "C3", "C2", "C3", "F2", "F3", "F2", "F3", "G2", "G3", "G2", "G3", "C2", "C3", "C2", "C3"
    ]
    drum = [
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "S", "S", "S",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "S", "S", "S",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S"
    ]
    return _synthesize_nes_bgm(bpm, lead, harm, bass, drum, sample_rate, lead_duty=0.50, harm_duty=0.25, lead_vibrato=4.0)


def create_sound_bgm_woven(sample_rate: int = 22050) -> pygame.mixer.Sound | None:
    """生成第五大关【立交编织秘境】BGM：148 BPM 都市科技快节奏三维立交穿梭曲。"""
    bpm = 148.0
    lead = [
        "E5", "G5", "B5", "E6", "D6", "B5", "G5", "E5", "A5", "C6", "E6", "A6", "G6", "E6", "C6", "A5",
        "FS5", "A5", "C6", "FS6", "E6", "C6", "A5", "FS5", "G5", "B5", "D6", "G6", "FS6", "D6", "B5", "G5",
        "E5", "G5", "B5", "E6", "D6", "B5", "G5", "E5", "A5", "C6", "E6", "A6", "G6", "E6", "C6", "A5",
        "FS5", "A5", "C6", "FS6", "E6", "C6", "A5", "FS5", "G5", "B5", "D6", "G6", "FS6", "D6", "B5", "G5",
        "E5", "G5", "B5", "E6", "D6", "B5", "G5", "E5", "A5", "C6", "E6", "A6", "G6", "E6", "C6", "A5",
        "FS5", "A5", "C6", "FS6", "E6", "C6", "A5", "FS5", "G5", "B5", "D6", "G6", "FS6", "D6", "B5", "G5",
        "E5", "G5", "B5", "E6", "D6", "B5", "G5", "E5", "A5", "C6", "E6", "A6", "G6", "E6", "C6", "A5",
        "FS5", "A5", "C6", "FS6", "E6", "C6", "A5", "FS5", "G5", "B5", "D6", "G6", "FS6", "D6", "B5", "G5"
    ]
    harm = [
        "B4", "_", "G4", "_", "C5", "_", "A4", "_", "D5", "_", "A4", "_", "B4", "_", "G4", "_",
        "A4", "_", "FS4", "_", "B4", "_", "G4", "_", "C5", "_", "A4", "_", "B4", "_", "G4", "_",
        "B4", "_", "G4", "_", "C5", "_", "A4", "_", "D5", "_", "A4", "_", "B4", "_", "G4", "_",
        "A4", "_", "FS4", "_", "B4", "_", "G4", "_", "C5", "_", "A4", "_", "B4", "_", "G4", "_",
        "B4", "_", "G4", "_", "C5", "_", "A4", "_", "D5", "_", "A4", "_", "B4", "_", "G4", "_",
        "A4", "_", "FS4", "_", "B4", "_", "G4", "_", "C5", "_", "A4", "_", "B4", "_", "G4", "_",
        "B4", "_", "G4", "_", "C5", "_", "A4", "_", "D5", "_", "A4", "_", "B4", "_", "G4", "_",
        "A4", "_", "FS4", "_", "B4", "_", "G4", "_", "C5", "_", "A4", "_", "B4", "_", "G4", "_"
    ]
    bass = [
        "E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
        "E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
        "E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
        "E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
        "E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
        "E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
        "E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
        "E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3"
    ]
    drum = [
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "S", "S", "S",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "S", "S", "S",
        "K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
        "K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S"
    ]
    return _synthesize_nes_bgm(bpm, lead, harm, bass, drum, sample_rate, lead_duty=0.25, harm_duty=0.50, lead_vibrato=4.5)


def create_sound_bgm(sample_rate: int = 22050) -> pygame.mixer.Sound | None:
    """兼容性别名，默认返回主界面 BGM。"""
    return create_sound_bgm_menu(sample_rate)


# --- 2. 程序化图形绘制 (Graphics / Sprites Generator) ---

def create_tree_surface(size: int = 128) -> pygame.Surface:
    """生成起点小树 Surface (深棕树干 + 茂密森林绿树冠 + 红苹果点缀)。"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    s = size

    # 树干
    trunk = pygame.Rect(int(s * 0.40), int(s * 0.55), int(s * 0.20), int(s * 0.38))
    pygame.draw.rect(surf, (120, 75, 40), trunk, border_radius=int(s * 0.03))
    pygame.draw.rect(surf, (80, 48, 25), trunk, width=int(s * 0.03), border_radius=int(s * 0.03))

    # 树冠 (圆润茂密三重叶)
    pygame.draw.circle(surf, (30, 140, 50), (int(s * 0.50), int(s * 0.38)), int(s * 0.28))
    pygame.draw.circle(surf, (45, 165, 65), (int(s * 0.34), int(s * 0.42)), int(s * 0.22))
    pygame.draw.circle(surf, (45, 165, 65), (int(s * 0.66), int(s * 0.42)), int(s * 0.22))
    # 顶部亮绿高光
    pygame.draw.circle(surf, (80, 200, 95), (int(s * 0.45), int(s * 0.28)), int(s * 0.16))

    # 可爱红色果实
    for fx, fy in ((0.36, 0.38), (0.62, 0.32), (0.48, 0.48)):
        pygame.draw.circle(surf, (230, 55, 55), (int(s * fx), int(s * fy)), int(s * 0.055))
        pygame.draw.circle(surf, (255, 200, 200), (int(s * fx - 0.015), int(s * fy - 0.015)), int(s * 0.02))

    return surf


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
    """生成终点小旗子 Surface (鲜艳大红旗帜 + 浅色底高对比)。"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    s = size

    # 底座 (暖光石阶)
    base_rect = pygame.Rect(int(s * 0.20), int(s * 0.80), int(s * 0.60), int(s * 0.15))
    pygame.draw.rect(surf, (220, 180, 100), base_rect, border_radius=int(s * 0.03))

    # 旗杆 (金黄色)
    pole_x = int(s * 0.36)
    pygame.draw.line(surf, (210, 170, 40), (pole_x, int(s * 0.08)), (pole_x, int(s * 0.85)), width=int(s * 0.08))

    # 旗杆顶端金球
    pygame.draw.circle(surf, (245, 200, 50), (pole_x, int(s * 0.08)), int(s * 0.07))

    # 飘扬的鲜艳大红旗帜
    flag_pts = [
        (pole_x, int(s * 0.10)),
        (int(s * 0.88), int(s * 0.28)),
        (pole_x, int(s * 0.48)),
    ]
    pygame.draw.polygon(surf, (240, 45, 55), flag_pts)
    pygame.draw.polygon(surf, (160, 20, 30), flag_pts, width=int(s * 0.04))

    # 旗子中间小金星
    star_center = (int(s * 0.52), int(s * 0.28))
    pygame.draw.circle(surf, (255, 230, 60), star_center, int(s * 0.07))

    return surf


import os

def load_player_skin(skin_name: str = "red_hood", size: int = 128) -> dict[str, list[pygame.Surface]]:
    """根据皮肤名称 ("red_hood" 或 "mochi") 加载玩家角色的 4 方向走动动画 Surface。"""
    folder_name = "red_hood_frames" if skin_name == "red_hood" else "mochi_frames"
    frames_dir = os.path.join(os.path.dirname(__file__), "assets", folder_name)
    if not os.path.exists(frames_dir):
        frames_dir = f"assets/{folder_name}"

    if os.path.exists(frames_dir):
        try:
            sprites = {}
            for d in ["down", "up", "left", "right"]:
                frame_list = []
                for idx in ["0", "1"]:
                    path = os.path.join(frames_dir, f"{d}_{idx}.png")
                    if os.path.exists(path):
                        img = pygame.image.load(path)
                        if pygame.display.get_surface() is not None:
                            img = img.convert_alpha()
                        scaled = pygame.transform.smoothscale(img, (size, size))
                        frame_list.append(scaled)
                if frame_list:
                    sprites[d] = frame_list
            if len(sprites) == 4:
                return sprites
        except Exception as e:
            print(f"Warning: Failed to load {folder_name}: {e}")

    sprites = {}
    directions = ["down", "up", "left", "right"]
    for d in directions:
        sprites[d] = [
            _draw_cute_character(size, d, frame=0),
            _draw_cute_character(size, d, frame=1),
        ]
    return sprites


def create_player_sprites(size: int = 128, skin_name: str = "red_hood") -> dict[str, list[pygame.Surface]]:
    return load_player_skin(skin_name, size)


def load_all_player_skins(size: int = 128) -> dict[str, dict[str, list[pygame.Surface]]]:
    return {
        "red_hood": load_player_skin("red_hood", size),
        "mochi": load_player_skin("mochi", size),
    }


def create_wolf_sprites(size: int = 128) -> dict[str, list[pygame.Surface]]:
    """加载大灰狼角色的 4 个方向走动贴图及哭泣/趴地贴图 (cry_0, cry_1)。"""
    frames_dir = os.path.join(os.path.dirname(__file__), "assets", "wolf_frames")
    if not os.path.exists(frames_dir):
        frames_dir = "assets/wolf_frames"

    sprites: dict[str, list[pygame.Surface]] = {}
    if os.path.exists(frames_dir):
        try:
            # 4 方向走动动画
            for d in ["down", "up", "left", "right", "cry"]:
                frame_list = []
                for idx in ["0", "1"]:
                    path = os.path.join(frames_dir, f"{d}_{idx}.png")
                    if os.path.exists(path):
                        img = pygame.image.load(path)
                        if pygame.display.get_surface() is not None:
                            img = img.convert_alpha()
                        scaled = pygame.transform.smoothscale(img, (size, size))
                        frame_list.append(scaled)
                if frame_list:
                    sprites[d] = frame_list
            if len(sprites) >= 4:
                return sprites
        except Exception as e:
            print(f"Warning: Failed to load wolf frames: {e}")

    return sprites


def _draw_cute_character(size: int, facing: str, frame: int) -> pygame.Surface:
    """绘制超萌大头 Q 版小人 (大头、水汪汪大眼睛、粉红腮红、帅气小帽子/发型、亮丽衣服与迈步小手小脚)。"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    s = size

    # 调色盘
    c_skin = (255, 230, 210)       # 嫩粉肤色
    c_blush = (255, 140, 175)      # 萌萌红润腮红
    c_hair = (90, 55, 45)          # 栗棕色头发
    c_cap = (250, 82, 115)         # 草莓甜心帽子
    c_cap_brim = (215, 55, 90)     # 帽檐
    c_cap_ear = (215, 55, 90)      # 帽子猫耳/球球
    c_shirt = (64, 173, 250)       # 晴空蓝小卫衣
    c_pants = (50, 60, 95)         # 藏青裤子
    c_shoes = (255, 250, 245)      # 亮白萌系鞋子
    c_eye_bg = (20, 20, 40)        # 动漫大眼眶深色
    c_eye_iris = (45, 148, 250)    # 水蓝色彩瞳
    c_eye_sparkle = (255, 255, 255)# 双重闪烁高光

    # 比例结构 (Q版 1.5 头身：大头占绝大部分空间)
    center_x = s * 0.50
    head_y = s * 0.37              # 大头中心
    head_r = s * 0.30              # 超大圆形大头！

    body_top = s * 0.60
    body_h = s * 0.18
    body_w = s * 0.28

    leg_top = body_top + body_h
    leg_h = s * 0.14

    # 脚步摆动偏移
    leg_offset = (s * 0.07) if frame == 1 else (-s * 0.07)

    if facing == "down":
        # === 正面 (朝下) ===
        # 1. 裤子与小鞋子
        left_foot = pygame.Rect(int(center_x - s * 0.12), int(leg_top + leg_offset * 0.4), int(s * 0.09), int(leg_h))
        right_foot = pygame.Rect(int(center_x + s * 0.03), int(leg_top - leg_offset * 0.4), int(s * 0.09), int(leg_h))
        pygame.draw.rect(surf, c_pants, left_foot, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_pants, right_foot, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_shoes, (left_foot.left - int(s * 0.01), left_foot.bottom - int(s * 0.04), left_foot.width + int(s * 0.02), int(s * 0.05)), border_radius=int(s * 0.02))
        pygame.draw.rect(surf, c_shoes, (right_foot.left - int(s * 0.01), right_foot.bottom - int(s * 0.04), right_foot.width + int(s * 0.02), int(s * 0.05)), border_radius=int(s * 0.02))

        # 2. 身体上衣与小手臂
        body_rect = pygame.Rect(int(center_x - body_w / 2), int(body_top), int(body_w), int(body_h))
        pygame.draw.rect(surf, c_shirt, body_rect, border_radius=int(s * 0.04))

        arm_l = pygame.Rect(int(body_rect.left - s * 0.05), int(body_top + s * 0.01 - leg_offset * 0.4), int(s * 0.06), int(s * 0.12))
        arm_r = pygame.Rect(int(body_rect.right - s * 0.01), int(body_top + s * 0.01 + leg_offset * 0.4), int(s * 0.06), int(s * 0.12))
        pygame.draw.rect(surf, c_shirt, arm_l, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_shirt, arm_r, border_radius=int(s * 0.03))
        pygame.draw.circle(surf, c_skin, (arm_l.centerx, arm_l.bottom), int(s * 0.03))
        pygame.draw.circle(surf, c_skin, (arm_r.centerx, arm_r.bottom), int(s * 0.03))

        # 3. 超大萌萌头
        pygame.draw.circle(surf, c_skin, (int(center_x), int(head_y)), int(head_r))

        # 刘海
        hair_l_pts = [(int(center_x - head_r * 0.9), int(head_y - head_r * 0.1)), (int(center_x - head_r * 0.3), int(head_y - head_r * 0.2)), (int(center_x - head_r * 0.6), int(head_y + head_r * 0.15))]
        hair_r_pts = [(int(center_x + head_r * 0.9), int(head_y - head_r * 0.1)), (int(center_x + head_r * 0.3), int(head_y - head_r * 0.2)), (int(center_x + head_r * 0.6), int(head_y + head_r * 0.15))]
        pygame.draw.polygon(surf, c_hair, hair_l_pts)
        pygame.draw.polygon(surf, c_hair, hair_r_pts)

        # 帽子与猫耳球球
        pygame.draw.circle(surf, c_cap, (int(center_x), int(head_y - head_r * 0.35)), int(head_r * 0.88))
        pygame.draw.circle(surf, c_cap_ear, (int(center_x - head_r * 0.6), int(head_y - head_r * 0.9)), int(s * 0.07))
        pygame.draw.circle(surf, c_cap_ear, (int(center_x + head_r * 0.6), int(head_y - head_r * 0.9)), int(s * 0.07))

        # 腮红 (粉红小圈)
        pygame.draw.circle(surf, c_blush, (int(center_x - s * 0.16), int(head_y + s * 0.09)), int(s * 0.05))
        pygame.draw.circle(surf, c_blush, (int(center_x + s * 0.16), int(head_y + s * 0.09)), int(s * 0.05))

        # 动漫超级水汪汪大眼睛 (大框架 + 蓝彩瞳 + 主/副双重闪烁高光)
        eye_lw = pygame.Rect(int(center_x - s * 0.165), int(head_y - s * 0.01), int(s * 0.13), int(s * 0.085))
        eye_rw = pygame.Rect(int(center_x + s * 0.035), int(head_y - s * 0.01), int(s * 0.13), int(s * 0.085))
        pygame.draw.rect(surf, c_eye_bg, eye_lw, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_eye_bg, eye_rw, border_radius=int(s * 0.03))

        # 彩瞳
        pygame.draw.rect(surf, c_eye_iris, (eye_lw.left + int(s * 0.015), eye_lw.top + int(s * 0.02), int(s * 0.10), int(s * 0.05)), border_radius=int(s * 0.02))
        pygame.draw.rect(surf, c_eye_iris, (eye_rw.left + int(s * 0.015), eye_rw.top + int(s * 0.02), int(s * 0.10), int(s * 0.05)), border_radius=int(s * 0.02))

        # 主高光
        pygame.draw.circle(surf, c_eye_sparkle, (eye_lw.left + int(s * 0.035), eye_lw.top + int(s * 0.02)), int(s * 0.024))
        pygame.draw.circle(surf, c_eye_sparkle, (eye_rw.left + int(s * 0.035), eye_rw.top + int(s * 0.02)), int(s * 0.024))
        # 副高光
        pygame.draw.circle(surf, c_eye_sparkle, (eye_lw.right - int(s * 0.035), eye_lw.bottom - int(s * 0.02)), int(s * 0.013))
        pygame.draw.circle(surf, c_eye_sparkle, (eye_rw.right - int(s * 0.035), eye_rw.bottom - int(s * 0.02)), int(s * 0.013))

        # 萌可爱笑脸
        smile_rect = pygame.Rect(int(center_x - s * 0.04), int(head_y + s * 0.10), int(s * 0.08), int(s * 0.05))
        pygame.draw.arc(surf, (110, 50, 60), smile_rect, math.pi, 2 * math.pi, int(s * 0.025))

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
        pygame.draw.circle(surf, c_blush, (int(center_x - s * 0.14), int(head_y + s * 0.09)), int(s * 0.05))

        # 侧萌萌水汪汪大眼睛
        eye_w = pygame.Rect(int(center_x - s * 0.165), int(head_y - s * 0.01), int(s * 0.13), int(s * 0.085))
        pygame.draw.rect(surf, c_eye_bg, eye_w, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_eye_iris, (eye_w.left + int(s * 0.015), eye_w.top + int(s * 0.02), int(s * 0.10), int(s * 0.05)), border_radius=int(s * 0.02))
        pygame.draw.circle(surf, c_eye_sparkle, (eye_w.left + int(s * 0.035), eye_w.top + int(s * 0.02)), int(s * 0.024))
        pygame.draw.circle(surf, c_eye_sparkle, (eye_w.right - int(s * 0.035), eye_w.bottom - int(s * 0.02)), int(s * 0.013))

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
        pygame.draw.circle(surf, c_blush, (int(center_x + s * 0.14), int(head_y + s * 0.09)), int(s * 0.05))

        # 侧萌萌水汪汪大眼睛
        eye_w = pygame.Rect(int(center_x + s * 0.035), int(head_y - s * 0.01), int(s * 0.13), int(s * 0.085))
        pygame.draw.rect(surf, c_eye_bg, eye_w, border_radius=int(s * 0.03))
        pygame.draw.rect(surf, c_eye_iris, (eye_w.left + int(s * 0.015), eye_w.top + int(s * 0.02), int(s * 0.10), int(s * 0.05)), border_radius=int(s * 0.02))
        pygame.draw.circle(surf, c_eye_sparkle, (eye_w.left + int(s * 0.035), eye_w.top + int(s * 0.02)), int(s * 0.024))
        pygame.draw.circle(surf, c_eye_sparkle, (eye_w.right - int(s * 0.035), eye_w.bottom - int(s * 0.02)), int(s * 0.013))

    return surf
