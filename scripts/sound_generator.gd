# GDScript: 声音合成器 (程序化合成 8-bit 复古音效)
class_name SoundGenerator
extends RefCounted

static func create_sound_step(sample_rate: int = 22050) -> AudioStreamWAV:
	var duration = 0.04
	var num_samples = int(sample_rate * duration)
	var pcm_bytes = PackedByteArray()
	pcm_bytes.resize(num_samples * 2)
	var freq = 160.0

	for i in range(num_samples):
		var t = float(i) / sample_rate
		var env = exp(-35.0 * t)
		var sine = sin(2.0 * PI * freq * t)
		var noise = (sin(2.0 * PI * freq * 3.7 * t) + sin(2.0 * PI * freq * 7.1 * t)) * 0.3
		var s = (sine * 0.7 + noise * 0.3) * env * 0.35
		var clamped = clamp(s, -1.0, 1.0)
		var val = int(clamped * 32767.0)
		pcm_bytes.encode_s16(i * 2, val)

	var stream = AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = sample_rate
	stream.stereo = false
	stream.data = pcm_bytes
	return stream

static func create_sound_start(sample_rate: int = 22050) -> AudioStreamWAV:
	var duration = 0.22
	var num_samples = int(sample_rate * duration)
	var pcm_bytes = PackedByteArray()
	pcm_bytes.resize(num_samples * 2)
	var notes = [
		{"st": 0.0, "ed": 0.07, "freq": 523.25},
		{"st": 0.07, "ed": 0.14, "freq": 659.25},
		{"st": 0.14, "ed": 0.22, "freq": 783.99}
	]

	for i in range(num_samples):
		var t = float(i) / sample_rate
		var val = 0.0
		for note in notes:
			if t >= note["st"] and t < note["ed"]:
				var local_t = t - note["st"]
				var dur = note["ed"] - note["st"]
				var env = pow(sin(PI * (local_t / dur)), 0.8)
				var sine = sin(2.0 * PI * note["freq"] * local_t)
				var square = 0.5 if sine >= 0 else -0.5
				val = (sine * 0.6 + square * 0.4) * env * 0.4
				break

		var clamped = clamp(val, -1.0, 1.0)
		var int_val = int(clamped * 32767.0)
		pcm_bytes.encode_s16(i * 2, int_val)

	var stream = AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = sample_rate
	stream.stereo = false
	stream.data = pcm_bytes
	return stream

static func create_sound_win(sample_rate: int = 22050) -> AudioStreamWAV:
	var duration = 0.55
	var num_samples = int(sample_rate * duration)
	var pcm_bytes = PackedByteArray()
	pcm_bytes.resize(num_samples * 2)
	var notes = [
		{"st": 0.00, "ed": 0.10, "freq": 783.99},
		{"st": 0.10, "ed": 0.20, "freq": 1046.50},
		{"st": 0.20, "ed": 0.30, "freq": 1318.51},
		{"st": 0.30, "ed": 0.55, "freq": 1567.98}
	]

	for i in range(num_samples):
		var t = float(i) / sample_rate
		var val = 0.0
		for note in notes:
			if t >= note["st"] and t < note["ed"]:
				var local_t = t - note["st"]
				var dur = note["ed"] - note["st"]
				var env = pow(sin(PI * (local_t / dur)), 0.8)
				var sine = sin(2.0 * PI * note["freq"] * local_t)
				var square = 0.5 if sine >= 0 else -0.5
				val = (sine * 0.6 + square * 0.4) * env * 0.4
				break

		var clamped = clamp(val, -1.0, 1.0)
		var int_val = int(clamped * 32767.0)
		pcm_bytes.encode_s16(i * 2, int_val)

	var stream = AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = sample_rate
	stream.stereo = false
	stream.data = pcm_bytes
	return stream

static func create_sound_wolf(sample_rate: int = 22050) -> AudioStreamWAV:
	var duration = 0.60
	var num_samples = int(sample_rate * duration)
	var pcm_bytes = PackedByteArray()
	pcm_bytes.resize(num_samples * 2)

	for i in range(num_samples):
		var t = float(i) / sample_rate
		var freq = 200.0 + (t / 0.3) * 250.0 if t < 0.3 else 450.0 - ((t - 0.3) / 0.3) * 200.0
		var env = pow(sin(PI * (t / duration)), 0.8)
		var vibrato = sin(2.0 * PI * 8.0 * t) * 0.15
		var wave = sin(2.0 * PI * (freq + vibrato * 50.0) * t)
		var clamped = clamp(wave * env * 0.50, -1.0, 1.0)
		var int_val = int(clamped * 32767.0)
		pcm_bytes.encode_s16(i * 2, int_val)

	var stream = AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = sample_rate
	stream.stereo = false
	stream.data = pcm_bytes
	return stream

static func create_sound_caught(sample_rate: int = 22050) -> AudioStreamWAV:
	var duration = 0.40
	var num_samples = int(sample_rate * duration)
	var pcm_bytes = PackedByteArray()
	pcm_bytes.resize(num_samples * 2)

	for i in range(num_samples):
		var t = float(i) / sample_rate
		var freq = 300.0 - (t / duration) * 180.0
		var env = exp(-6.0 * t)
		var sine = sin(2.0 * PI * freq * t)
		var saw = (2.0 * (t * freq - floor(0.5 + t * freq))) * 0.5
		var clamped = clamp((sine * 0.6 + saw * 0.4) * env * 0.5, -1.0, 1.0)
		var int_val = int(clamped * 32767.0)
		pcm_bytes.encode_s16(i * 2, int_val)

	var stream = AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = sample_rate
	stream.stereo = false
	stream.data = pcm_bytes
	return stream

static func _synthesize_nes_bgm(
	bpm: float,
	lead_pattern: Array,
	harm_pattern: Array,
	bass_pattern: Array,
	drum_pattern: Array,
	sample_rate: int = 22050,
	lead_duty: float = 0.25,
	harm_duty: float = 0.50,
	lead_vibrato: float = 6.0
) -> AudioStreamWAV:
	var step_dur = 60.0 / (bpm * 4.0)
	var total_steps = lead_pattern.size()
	var duration = total_steps * step_dur
	var num_samples = int(sample_rate * duration)
	var pcm_bytes = PackedByteArray()
	pcm_bytes.resize(num_samples * 2)

	var N = {
		"_": 0.0,
		"C1": 32.70, "CS1": 34.65, "D1": 36.71, "DS1": 38.89, "E1": 41.20, "F1": 43.65, "FS1": 46.25, "G1": 49.00, "GS1": 51.91, "A1": 55.00, "AS1": 58.27, "B1": 61.74,
		"C2": 65.41, "CS2": 69.30, "D2": 73.42, "DS2": 77.78, "E2": 82.41, "F2": 87.31, "FS2": 92.50, "G2": 98.00, "GS2": 103.83, "A2": 110.00, "AS2": 116.54, "B2": 123.47,
		"C3": 130.81, "CS3": 138.59, "D3": 146.83, "DS3": 155.56, "E3": 164.81, "F3": 174.61, "FS3": 185.00, "G3": 196.00, "GS3": 207.65, "A3": 220.00, "AS3": 233.08, "B3": 246.94,
		"C4": 261.63, "CS4": 277.18, "D4": 293.66, "DS4": 311.13, "E4": 329.63, "F4": 349.23, "FS4": 369.99, "G4": 392.00, "GS4": 415.30, "A4": 440.00, "AS4": 466.16, "B4": 493.88,
		"C5": 523.25, "CS5": 554.37, "D5": 587.33, "DS5": 622.25, "E5": 659.25, "F5": 698.46, "FS5": 739.99, "G5": 783.99, "GS5": 830.61, "A5": 880.00, "AS5": 932.33, "B5": 987.77,
		"C6": 1046.50, "CS6": 1108.73, "D6": 1174.66, "DS6": 1244.51, "E6": 1318.51, "F6": 1396.91, "FS6": 1479.98, "G6": 1567.98, "GS6": 1661.22, "A6": 1760.00
	}

	var lead_freqs: Array[float] = []
	var harm_freqs: Array[float] = []
	var bass_freqs: Array[float] = []
	for name in lead_pattern: lead_freqs.append(float(N[name]))
	for name in harm_pattern: harm_freqs.append(float(N[name]))
	for name in bass_pattern: bass_freqs.append(float(N[name]))

	var phase1: float = 0.0
	var phase2: float = 0.0
	var phase3: float = 0.0

	for i in range(num_samples):
		var t = float(i) / sample_rate
		var step = int(t / step_dur) % total_steps
		var step_t = fmod(t, step_dur)

		var f1 = lead_freqs[step]
		var f2 = harm_freqs[step]
		var f3 = bass_freqs[step]
		var d = drum_pattern[step]

		var lead_val = 0.0
		if f1 > 0.0:
			var vib = 1.0 + 0.006 * sin(2.0 * PI * lead_vibrato * step_t) if lead_vibrato > 0.0 else 1.0
			phase1 = fmod(phase1 + (f1 * vib) / sample_rate, 1.0)
			var square1 = 1.0 if phase1 < lead_duty else -1.0
			var env1 = exp(-5.0 * step_t) * 0.7 + 0.3
			lead_val = square1 * env1

		var harm_val = 0.0
		if f2 > 0.0:
			phase2 = fmod(phase2 + f2 / sample_rate, 1.0)
			var square2 = 1.0 if phase2 < harm_duty else -1.0
			var env2 = exp(-7.0 * step_t) * 0.8
			harm_val = square2 * env2

		var bass_val = 0.0
		if f3 > 0.0:
			phase3 = fmod(phase3 + f3 / sample_rate, 1.0)
			var tri = 2.0 * abs(2.0 * (phase3 - floor(phase3 + 0.5))) - 1.0
			var env3 = exp(-3.5 * step_t) * 0.9
			bass_val = tri * env3

		var drum_val = 0.0
		var rnd = (float((i * 1103515245 + 12345) & 0x7FFFFFFF) / 2147483648.0) * 2.0 - 1.0

		if d == "K":
			var freq_k = 120.0 * exp(-30.0 * step_t)
			var sine_k = sin(2.0 * PI * freq_k * step_t)
			drum_val = sine_k * exp(-15.0 * step_t) * 1.1 + rnd * exp(-50.0 * step_t) * 0.25
		elif d == "S":
			drum_val = rnd * exp(-20.0 * step_t) * 0.85 + sin(2.0 * PI * 170.0 * step_t) * exp(-25.0 * step_t) * 0.35
		elif d == "H":
			drum_val = rnd * exp(-70.0 * step_t) * 0.35

		var sample = (
			lead_val * 0.18 +
			harm_val * 0.11 +
			bass_val * 0.27 +
			drum_val * 0.15
		)
		var clamped = clamp(sample, -1.0, 1.0)
		var int_val = int(clamped * 32767.0)
		pcm_bytes.encode_s16(i * 2, int_val)

	var stream = AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = sample_rate
	stream.stereo = false
	stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
	stream.loop_end = num_samples
	stream.data = pcm_bytes
	return stream

static func create_sound_bgm_menu(sample_rate: int = 22050) -> AudioStreamWAV:
	var bpm = 102.0
	var lead = [
		"E4", "_", "G4", "_", "B4", "_", "E5", "_", "D5", "_", "B4", "_", "G4", "_", "A4", "B4",
		"C5", "_", "E4", "_", "A4", "_", "C5", "_", "B4", "_", "G4", "_", "E4", "_", "F4", "G4",
		"A4", "_", "C4", "_", "F4", "_", "A4", "_", "G4", "_", "E4", "_", "C4", "_", "D4", "E4",
		"F4", "A4", "C5", "F5", "E5", "D5", "C5", "B4", "A4", "G4", "F4", "E4", "D4", "C4", "B3", "D4",
		"E4", "_", "G4", "_", "B4", "_", "E5", "_", "G5", "E5", "B4", "G4", "E5", "B4", "G4", "E4",
		"A4", "_", "C5", "_", "E5", "_", "A5", "_", "G5", "E5", "C5", "A4", "F5", "D5", "B4", "G4",
		"F4", "A4", "C5", "F5", "E5", "C5", "A4", "F4", "G4", "B4", "D5", "G5", "F5", "D5", "B4", "G4",
		"E5", "_", "B4", "_", "G4", "_", "E4", "_", "E4", "F4", "G4", "A4", "B4", "C5", "D5", "DS5"
	]
	var harm = [
		"B3", "_", "E4", "_", "G4", "_", "B4", "_", "G4", "_", "E4", "_", "B3", "_", "F3", "G3",
		"A3", "_", "C4", "_", "E4", "_", "A4", "_", "E4", "_", "C4", "_", "B3", "_", "D4", "E4",
		"F3", "_", "A3", "_", "C4", "_", "F4", "_", "E4", "_", "C4", "_", "G3", "_", "B3", "C4",
		"D4", "F4", "A4", "D5", "C5", "B4", "A4", "G4", "F4", "E4", "D4", "C4", "B3", "A3", "G3", "B3",
		"B3", "_", "E4", "_", "G4", "_", "B4", "_", "E5", "B4", "G4", "E4", "B4", "G4", "E4", "B3",
		"C4", "_", "E4", "_", "A4", "_", "C5", "_", "E5", "C5", "A4", "E4", "D5", "B4", "G4", "D4",
		"D4", "F4", "A4", "D5", "C5", "A4", "F4", "D4", "E4", "G4", "B4", "E5", "D5", "B4", "G4", "E4",
		"G4", "_", "E4", "_", "B3", "_", "G3", "_", "B3", "C4", "D4", "E4", "F4", "FS4", "G4", "GS4"
	]
	var bass = [
		"E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3",
		"A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2",
		"F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
		"D2", "D3", "D2", "D3", "D2", "D3", "D2", "D3", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2",
		"E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3",
		"A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "F1", "F2", "F1", "F2", "G1", "G2", "G1", "G2",
		"F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2",
		"E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3"
	]
	var drum = [
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "S", "K", "S", "S", "_", "S", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S"
	]
	return _synthesize_nes_bgm(bpm, lead, harm, bass, drum, sample_rate, 0.50, 0.25, 4.0)

static func create_sound_bgm_free(sample_rate: int = 22050) -> AudioStreamWAV:
	var bpm = 114.0
	var lead = [
		"C5", "C5", "_", "C5", "_", "A4", "C5", "_", "G4", "_", "E4", "_", "G4", "_", "A4", "B4",
		"A4", "A4", "_", "C5", "_", "B4", "A4", "_", "G4", "_", "E4", "_", "C4", "D4", "E4", "G4",
		"F4", "F4", "A4", "C5", "B4", "A4", "G4", "F4", "E4", "E4", "G4", "C5", "A4", "G4", "F4", "E4",
		"D4", "F4", "A4", "D5", "C5", "B4", "A4", "G4", "G4", "A4", "B4", "C5", "D5", "E5", "F5", "FS5",
		"G5", "E5", "C5", "G4", "E5", "C5", "G4", "E4", "A5", "F5", "C5", "A4", "F5", "C5", "A4", "F4",
		"G5", "F5", "E5", "D5", "C5", "B4", "A4", "G4", "E5", "D5", "C5", "B4", "C5", "_", "G4", "_",
		"F4", "A4", "C5", "F5", "E5", "D5", "C5", "A4", "G4", "B4", "D5", "G5", "F5", "E5", "D5", "B4",
		"C5", "C5", "G4", "G4", "E4", "E4", "C4", "C4", "D4", "E4", "F4", "FS4", "G4", "G4", "B4", "D5"
	]
	var harm = [
		"E4", "E4", "_", "E4", "_", "F4", "A4", "_", "E4", "_", "C4", "_", "E4", "_", "F4", "G4",
		"F4", "F4", "_", "A4", "_", "G4", "F4", "_", "E4", "_", "C4", "_", "A3", "B3", "C4", "E4",
		"D4", "D4", "F4", "A4", "G4", "F4", "E4", "D4", "C4", "C4", "E4", "G4", "F4", "E4", "D4", "C4",
		"B3", "D4", "F4", "B4", "A4", "G4", "F4", "E4", "E4", "F4", "G4", "A4", "B4", "C5", "D5", "DS5",
		"E5", "C5", "G4", "E4", "C5", "G4", "E4", "C4", "F5", "C5", "A4", "F4", "C5", "A4", "F4", "C4",
		"E5", "D5", "C5", "B4", "A4", "G4", "F4", "E4", "C5", "B4", "A4", "G4", "E4", "_", "E4", "_",
		"D4", "F4", "A4", "D5", "C5", "B4", "A4", "F4", "E4", "G4", "B4", "E5", "D5", "C5", "B4", "G4",
		"E4", "E4", "C4", "C4", "G3", "G3", "E3", "E3", "B3", "C4", "D4", "DS4", "E4", "E4", "G4", "B4"
	]
	var bass = [
		"C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
		"F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
		"D2", "D3", "D2", "D3", "D2", "D3", "D2", "D3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
		"G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2",
		"C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2",
		"C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
		"F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2",
		"C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2"
	]
	var drum = [
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "S", "K", "S", "S", "S", "S", "S",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S"
	]
	return _synthesize_nes_bgm(bpm, lead, harm, bass, drum, sample_rate, 0.25, 0.50, 5.0)

static func create_sound_bgm_challenge(sample_rate: int = 22050) -> AudioStreamWAV:
	var bpm = 120.0
	var lead = [
		"A3", "_", "C4", "_", "E4", "_", "A4", "_", "E4", "_", "C4", "_", "A3", "C4", "D4", "DS4",
		"E4", "_", "G4", "_", "A4", "_", "C5", "_", "B4", "_", "A4", "_", "G4", "E4", "G4", "A4",
		"F4", "_", "A4", "_", "C5", "_", "F5", "_", "E5", "_", "D5", "_", "C5", "_", "A4", "_",
		"G4", "B4", "D5", "G5", "F5", "E5", "D5", "C5", "B4", "A4", "G4", "F4", "E4", "D4", "C4", "B3",
		"A4", "_", "C5", "_", "E5", "_", "A5", "_", "G5", "E5", "C5", "A4", "E5", "C5", "A4", "E4",
		"F5", "_", "C5", "_", "A4", "_", "F4", "_", "C5", "_", "A4", "_", "F4", "_", "A4", "C5",
		"G5", "_", "D5", "_", "B4", "_", "G4", "_", "D5", "_", "B4", "_", "G4", "_", "B4", "D5",
		"E5", "E5", "D5", "C5", "B4", "B4", "A4", "GS4", "B4", "C5", "D5", "DS5", "E5", "E5", "G5", "GS5"
	]
	var harm = [
		"E3", "_", "A3", "_", "C4", "_", "E4", "_", "C4", "_", "A3", "_", "E3", "A3", "B3", "C4",
		"C4", "_", "E4", "_", "E4", "_", "A4", "_", "G4", "_", "E4", "_", "D4", "C4", "D4", "E4",
		"C4", "_", "F4", "_", "A4", "_", "C5", "_", "C5", "_", "A4", "_", "F4", "_", "C4", "_",
		"D4", "G4", "B4", "D5", "D5", "C5", "B4", "A4", "G4", "F4", "E4", "D4", "C4", "B3", "A3", "G3",
		"E4", "_", "A4", "_", "C5", "_", "E5", "_", "E5", "C5", "A4", "E4", "C5", "A4", "E4", "C4",
		"C5", "_", "A4", "_", "F4", "_", "C4", "_", "A4", "_", "F4", "_", "C4", "_", "F4", "A4",
		"D5", "_", "B4", "_", "G4", "_", "D4", "_", "B4", "_", "G4", "_", "D4", "_", "G4", "B4",
		"GS4", "GS4", "F4", "E4", "D4", "D4", "C4", "B3", "D4", "E4", "F4", "FS4", "GS4", "GS4", "B4", "D5"
	]
	var bass = [
		"A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2",
		"A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2",
		"F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2",
		"G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2",
		"A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2",
		"F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2", "F1", "F2",
		"G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2",
		"E1", "E2", "E1", "E2", "E1", "E2", "E1", "E2", "E1", "E2", "E1", "E2", "E1", "E2", "E1", "E2"
	]
	var drum = [
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "S", "K", "S", "S", "S", "S", "S",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S"
	]
	return _synthesize_nes_bgm(bpm, lead, harm, bass, drum, sample_rate, 0.25, 0.50, 6.0)

static func create_sound_bgm_dungeon(sample_rate: int = 22050) -> AudioStreamWAV:
	var bpm = 108.0
	var lead = [
		"D4", "_", "F4", "GS4", "A4", "_", "D5", "_", "CS5", "_", "GS4", "F4", "D4", "_", "CS4", "_",
		"D4", "_", "F4", "GS4", "A4", "_", "F5", "_", "E5", "_", "CS5", "A4", "F4", "E4", "D4", "CS4",
		"G4", "_", "AS4", "CS5", "D5", "_", "G5", "_", "FS5", "_", "CS5", "AS4", "G4", "_", "FS4", "_",
		"A4", "CS5", "E5", "G5", "FS5", "F5", "E5", "DS5", "D5", "CS5", "C5", "B4", "AS4", "A4", "GS4", "G4",
		"D5", "_", "F5", "_", "GS5", "_", "D6", "_", "CS6", "GS5", "F5", "D5", "CS5", "GS4", "F4", "D4",
		"A4", "AS4", "D5", "F5", "A5", "GS5", "G5", "FS5", "F5", "E5", "DS5", "D5", "CS5", "C5", "B4", "A4",
		"G4", "AS4", "CS5", "E5", "G5", "CS5", "AS4", "G4", "A4", "CS5", "E5", "G5", "A5", "G5", "E5", "CS5",
		"D5", "D5", "CS5", "C5", "B4", "AS4", "A4", "GS4", "A4", "AS4", "C5", "CS5", "D5", "E5", "F5", "GS5"
	]
	var harm = [
		"F3", "_", "A3", "_", "D4", "_", "F4", "_", "E4", "_", "CS4", "_", "F3", "_", "E3", "_",
		"F3", "_", "A3", "_", "D4", "_", "D5", "_", "CS5", "_", "A4", "_", "D4", "_", "CS4", "_",
		"AS3", "_", "D4", "_", "G4", "_", "AS4", "_", "A4", "_", "E4", "_", "AS3", "_", "A3", "_",
		"CS4", "E4", "G4", "CS5", "C5", "B4", "AS4", "A4", "GS4", "G4", "FS4", "F4", "E4", "DS4", "D4", "CS4",
		"F4", "_", "A4", "_", "D5", "_", "F5", "_", "E5", "CS5", "A4", "F4", "E4", "CS4", "A3", "F3",
		"F4", "G4", "AS4", "D5", "F5", "E5", "DS5", "D5", "CS5", "C5", "B4", "AS4", "A4", "GS4", "G4", "FS4",
		"E4", "G4", "AS4", "CS5", "E5", "AS4", "G4", "E4", "CS4", "E4", "G4", "CS5", "E5", "CS5", "G4", "E4",
		"F4", "F4", "E4", "DS4", "D4", "CS4", "C4", "B3", "C4", "CS4", "D4", "DS4", "F4", "G4", "GS4", "A4"
	]
	var bass = [
		"D2", "D2", "CS2", "CS2", "C2", "C2", "B1", "B1", "AS1", "AS1", "A1", "A1", "GS1", "GS1", "A1", "CS2",
		"D2", "D2", "CS2", "CS2", "C2", "C2", "B1", "B1", "AS1", "AS1", "A1", "A1", "GS1", "GS1", "A1", "CS2",
		"G1", "G2", "FS1", "FS2", "F1", "F2", "E1", "E2", "DS1", "DS2", "D1", "D2", "CS1", "CS2", "D1", "FS1",
		"A1", "A2", "GS1", "GS2", "G1", "G2", "FS1", "FS2", "F1", "F2", "E1", "E2", "DS1", "DS2", "E1", "GS1",
		"D2", "D2", "CS2", "CS2", "C2", "C2", "B1", "B1", "AS1", "AS1", "A1", "A1", "GS1", "GS1", "A1", "CS2",
		"A1", "A2", "GS1", "GS2", "G1", "G2", "FS1", "FS2", "F1", "F2", "E1", "E2", "DS1", "DS2", "E1", "GS1",
		"G1", "G2", "FS1", "FS2", "F1", "F2", "E1", "E2", "A1", "A2", "GS1", "GS2", "G1", "G2", "FS1", "FS2",
		"D2", "D2", "CS2", "CS2", "C2", "C2", "B1", "B1", "AS1", "AS1", "A1", "A1", "GS1", "GS1", "A1", "CS2"
	]
	var drum = [
		"K", "_", "_", "_", "S", "_", "_", "_", "K", "_", "K", "_", "S", "_", "H", "_",
		"K", "_", "_", "_", "S", "_", "_", "_", "K", "_", "K", "_", "S", "S", "S", "S",
		"K", "_", "_", "_", "S", "_", "_", "_", "K", "_", "K", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S",
		"K", "_", "_", "_", "S", "_", "_", "_", "K", "_", "K", "_", "S", "_", "H", "_",
		"K", "_", "_", "_", "S", "_", "_", "_", "K", "_", "K", "_", "S", "S", "S", "S",
		"K", "_", "_", "_", "S", "_", "_", "_", "K", "_", "K", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S"
	]
	return _synthesize_nes_bgm(bpm, lead, harm, bass, drum, sample_rate, 0.125, 0.50, 8.0)

static func create_sound_bgm_pattern(sample_rate: int = 22050) -> AudioStreamWAV:
	var bpm = 132.0
	var lead = [
		"E5", "B4", "C5", "E5", "G5", "FS5", "E5", "D5", "C5", "G4", "A4", "C5", "E5", "D5", "C5", "B4",
		"E5", "B4", "C5", "E5", "A5", "G5", "FS5", "E5", "D5", "A4", "B4", "D5", "FS5", "E5", "D5", "CS5",
		"C5", "E5", "G5", "C6", "B5", "A5", "G5", "F5", "E5", "G5", "C6", "E6", "D6", "C6", "B5", "A5",
		"G5", "B5", "D6", "G6", "FS6", "E6", "D6", "C6", "B5", "G5", "A5", "B5", "C6", "D6", "E6", "FS6",
		"E5", "B4", "C5", "E5", "G5", "FS5", "E5", "D5", "C5", "G4", "A4", "C5", "E5", "D5", "C5", "B4",
		"E5", "B4", "C5", "E5", "A5", "G5", "FS5", "E5", "D5", "A4", "B4", "D5", "FS5", "E5", "D5", "CS5",
		"C5", "E5", "G5", "C6", "B5", "A5", "G5", "F5", "E5", "G5", "C6", "E6", "D6", "C6", "B5", "A5",
		"G5", "B5", "D6", "G6", "FS6", "E6", "D6", "C6", "B5", "G5", "A5", "B5", "C6", "D6", "E6", "FS6"
	]
	var harm = [
		"G4", "_", "E4", "_", "B4", "_", "G4", "_", "E4", "_", "C4", "_", "G4", "_", "E4", "_",
		"G4", "_", "E4", "_", "C5", "_", "A4", "_", "FS4", "_", "D4", "_", "A4", "_", "FS4", "_",
		"E4", "G4", "C5", "E5", "D5", "C5", "B4", "A4", "C4", "E4", "G4", "C5", "B4", "A4", "G4", "F4",
		"D4", "G4", "B4", "D5", "C5", "B4", "A4", "G4", "D4", "G4", "A4", "B4", "A4", "B4", "C5", "D5",
		"G4", "_", "E4", "_", "B4", "_", "G4", "_", "E4", "_", "C4", "_", "G4", "_", "E4", "_",
		"G4", "_", "E4", "_", "C5", "_", "A4", "_", "FS4", "_", "D4", "_", "A4", "_", "FS4", "_",
		"E4", "G4", "C5", "E5", "D5", "C5", "B4", "A4", "C4", "E4", "G4", "C5", "B4", "A4", "G4", "F4",
		"D4", "G4", "B4", "D5", "C5", "B4", "A4", "G4", "D4", "G4", "A4", "B4", "A4", "B4", "C5", "D5"
	]
	var bass = [
		"E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
		"A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "D2", "D3", "D2", "D3", "D2", "D3", "D2", "D3",
		"C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
		"G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2",
		"E2", "E3", "E2", "E3", "E2", "E3", "E2", "E3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
		"A1", "A2", "A1", "A2", "A1", "A2", "A1", "A2", "D2", "D3", "D2", "D3", "D2", "D3", "D2", "D3",
		"C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3", "C2", "C3",
		"G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2", "G1", "G2"
	]
	var drum = [
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "S", "S", "S",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "S", "S", "S",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S"
	]
	return _synthesize_nes_bgm(bpm, lead, harm, bass, drum, sample_rate, 0.25, 0.50, 5.0)

static func create_sound_bgm_shape(sample_rate: int = 22050) -> AudioStreamWAV:
	var bpm = 140.0
	var lead = [
		"C5", "E5", "G5", "C6", "A5", "F5", "C5", "F5", "B4", "D5", "G5", "B5", "C6", "G5", "E5", "C5",
		"C5", "E5", "G5", "C6", "D6", "B5", "G5", "D5", "C6", "A5", "F5", "D5", "B5", "G5", "E5", "D5",
		"E5", "GS5", "B5", "E6", "A5", "C6", "E6", "A6", "D5", "FS5", "A5", "D6", "G5", "B5", "D6", "G6",
		"C6", "G5", "E5", "C5", "A5", "F5", "D5", "A4", "B5", "G5", "F5", "D5", "C6", "G5", "E5", "C5",
		"C5", "E5", "G5", "C6", "A5", "F5", "C5", "F5", "B4", "D5", "G5", "B5", "C6", "G5", "E5", "C5",
		"C5", "E5", "G5", "C6", "D6", "B5", "G5", "D5", "C6", "A5", "F5", "D5", "B5", "G5", "E5", "D5",
		"E5", "GS5", "B5", "E6", "A5", "C6", "E6", "A6", "D5", "FS5", "A5", "D6", "G5", "B5", "D6", "G6",
		"C6", "G5", "E5", "C5", "A5", "F5", "D5", "A4", "B5", "G5", "F5", "D5", "C6", "G5", "E5", "C5"
	]
	var harm = [
		"G4", "_", "E4", "_", "F4", "_", "C4", "_", "G4", "_", "D4", "_", "E4", "_", "C4", "_",
		"G4", "_", "E4", "_", "B4", "_", "G4", "_", "A4", "_", "F4", "_", "G4", "_", "E4", "_",
		"B4", "_", "GS4", "_", "C5", "_", "A4", "_", "A4", "_", "FS4", "_", "B4", "_", "G4", "_",
		"G4", "_", "E4", "_", "F4", "_", "D4", "_", "G4", "_", "F4", "_", "E4", "_", "C4", "_",
		"G4", "_", "E4", "_", "F4", "_", "C4", "_", "G4", "_", "D4", "_", "E4", "_", "C4", "_",
		"G4", "_", "E4", "_", "B4", "_", "G4", "_", "A4", "_", "F4", "_", "G4", "_", "E4", "_",
		"B4", "_", "GS4", "_", "C5", "_", "A4", "_", "A4", "_", "FS4", "_", "B4", "_", "G4", "_",
		"G4", "_", "E4", "_", "F4", "_", "D4", "_", "G4", "_", "F4", "_", "E4", "_", "C4", "_"
	]
	var bass = [
		"C2", "C3", "C2", "C3", "F2", "F3", "F2", "F3", "G2", "G3", "G2", "G3", "C2", "C3", "C2", "C3",
		"C2", "C3", "C2", "C3", "G2", "G3", "G2", "G3", "F2", "F3", "F2", "F3", "G2", "G3", "G2", "G3",
		"E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
		"C2", "C3", "C2", "C3", "F2", "F3", "F2", "F3", "G2", "G3", "G2", "G3", "C2", "C3", "C2", "C3",
		"C2", "C3", "C2", "C3", "F2", "F3", "F2", "F3", "G2", "G3", "G2", "G3", "C2", "C3", "C2", "C3",
		"C2", "C3", "C2", "C3", "G2", "G3", "G2", "G3", "F2", "F3", "F2", "F3", "G2", "G3", "G2", "G3",
		"E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
		"C2", "C3", "C2", "C3", "F2", "F3", "F2", "F3", "G2", "G3", "G2", "G3", "C2", "C3", "C2", "C3"
	]
	var drum = [
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "S", "S", "S",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "S", "S", "S",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S"
	]
	return _synthesize_nes_bgm(bpm, lead, harm, bass, drum, sample_rate, 0.50, 0.25, 4.0)

static func create_sound_bgm_woven(sample_rate: int = 22050) -> AudioStreamWAV:
	var bpm = 148.0
	var lead = [
		"E5", "G5", "B5", "E6", "D6", "B5", "G5", "E5", "A5", "C6", "E6", "A6", "G6", "E6", "C6", "A5",
		"FS5", "A5", "C6", "FS6", "E6", "C6", "A5", "FS5", "G5", "B5", "D6", "G6", "FS6", "D6", "B5", "G5",
		"E5", "G5", "B5", "E6", "D6", "B5", "G5", "E5", "A5", "C6", "E6", "A6", "G6", "E6", "C6", "A5",
		"FS5", "A5", "C6", "FS6", "E6", "C6", "A5", "FS5", "G5", "B5", "D6", "G6", "FS6", "D6", "B5", "G5",
		"E5", "G5", "B5", "E6", "D6", "B5", "G5", "E5", "A5", "C6", "E6", "A6", "G6", "E6", "C6", "A5",
		"FS5", "A5", "C6", "FS6", "E6", "C6", "A5", "FS5", "G5", "B5", "D6", "G6", "FS6", "D6", "B5", "G5",
		"E5", "G5", "B5", "E6", "D6", "B5", "G5", "E5", "A5", "C6", "E6", "A6", "G6", "E6", "C6", "A5",
		"FS5", "A5", "C6", "FS6", "E6", "C6", "A5", "FS5", "G5", "B5", "D6", "G6", "FS6", "D6", "B5", "G5"
	]
	var harm = [
		"B4", "_", "G4", "_", "C5", "_", "A4", "_", "D5", "_", "A4", "_", "B4", "_", "G4", "_",
		"A4", "_", "FS4", "_", "B4", "_", "G4", "_", "C5", "_", "A4", "_", "B4", "_", "G4", "_",
		"B4", "_", "G4", "_", "C5", "_", "A4", "_", "D5", "_", "A4", "_", "B4", "_", "G4", "_",
		"A4", "_", "FS4", "_", "B4", "_", "G4", "_", "C5", "_", "A4", "_", "B4", "_", "G4", "_",
		"B4", "_", "G4", "_", "C5", "_", "A4", "_", "D5", "_", "A4", "_", "B4", "_", "G4", "_",
		"A4", "_", "FS4", "_", "B4", "_", "G4", "_", "C5", "_", "A4", "_", "B4", "_", "G4", "_",
		"B4", "_", "G4", "_", "C5", "_", "A4", "_", "D5", "_", "A4", "_", "B4", "_", "G4", "_",
		"A4", "_", "FS4", "_", "B4", "_", "G4", "_", "C5", "_", "A4", "_", "B4", "_", "G4", "_"
	]
	var bass = [
		"E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
		"E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
		"E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
		"E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
		"E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
		"E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
		"E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3",
		"E2", "E3", "E2", "E3", "A2", "A3", "A2", "A3", "D2", "D3", "D2", "D3", "G2", "G3", "G2", "G3"
	]
	var drum = [
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "S", "S", "S",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "S", "S", "S",
		"K", "_", "H", "_", "S", "_", "H", "_", "K", "_", "H", "_", "S", "_", "H", "_",
		"K", "_", "H", "_", "S", "_", "H", "_", "S", "S", "S", "S", "S", "S", "S", "S"
	]
	return _synthesize_nes_bgm(bpm, lead, harm, bass, drum, sample_rate, 0.25, 0.50, 4.5)

static func create_sound_bgm(sample_rate: int = 22050) -> AudioStreamWAV:
	return create_sound_bgm_menu(sample_rate)
