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
