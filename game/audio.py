from __future__ import annotations

import io
import math
import random
import wave
from array import array

import pygame


NOTE_INDEX = {
    "C": 0,
    "C#": 1,
    "D": 2,
    "D#": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "G": 7,
    "G#": 8,
    "A": 9,
    "A#": 10,
    "B": 11,
}


class MusicManager:
    def __init__(self) -> None:
        self.sample_rate = 22050
        self.available = False
        self.channel: pygame.mixer.Channel | None = None
        self.current_track: str | None = None
        self.tracks: dict[str, pygame.mixer.Sound] = {}

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=2, buffer=512)
            self.channel = pygame.mixer.Channel(0)
            self.available = True
        except pygame.error:
            self.available = False

    def play(self, track_name: str, volume: float = 0.42) -> None:
        if not self.available or not self.channel:
            return
        if self.current_track == track_name and self.channel.get_busy():
            return

        sound = self.tracks.get(track_name)
        if sound is None:
            builder = {
                "storm_siege_road": self._build_storm_siege_road,
                "blackfang_core": self._build_blackfang_core,
            }.get(track_name)
            if builder is None:
                return
            sound = builder()
            self.tracks[track_name] = sound

        self.channel.stop()
        self.channel.set_volume(volume)
        self.channel.play(sound, loops=-1, fade_ms=500)
        self.current_track = track_name

    def stop(self) -> None:
        if not self.available or not self.channel:
            return
        self.channel.fadeout(350)
        self.current_track = None

    def _note_frequency(self, note: str) -> float:
        if len(note) == 3:
            name = note[:2]
            octave = int(note[2])
        else:
            name = note[0]
            octave = int(note[1])
        midi = 12 * (octave + 1) + NOTE_INDEX[name]
        return 440.0 * (2 ** ((midi - 69) / 12))

    def _add_tone(
        self,
        left: list[float],
        right: list[float],
        start_beat: float,
        length_beats: float,
        freq: float,
        tempo: float,
        volume: float,
        waveform: str = "sine",
        pan: float = 0.5,
    ) -> None:
        beat_seconds = 60.0 / tempo
        start_frame = int(start_beat * beat_seconds * self.sample_rate)
        total_frames = int(length_beats * beat_seconds * self.sample_rate)
        if total_frames <= 0:
            return

        attack = max(1, int(total_frames * 0.06))
        release = max(1, int(total_frames * 0.18))
        for frame in range(total_frames):
            idx = start_frame + frame
            if idx >= len(left):
                break

            t = frame / self.sample_rate
            phase = freq * t
            if waveform == "triangle":
                wave_value = 2.0 * abs(2.0 * (phase % 1.0) - 1.0) - 1.0
            elif waveform == "saw":
                wave_value = 2.0 * (phase % 1.0) - 1.0
            elif waveform == "square":
                wave_value = 1.0 if math.sin(math.tau * phase) >= 0 else -1.0
            else:
                wave_value = math.sin(math.tau * phase)

            if frame < attack:
                envelope = frame / attack
            elif frame > total_frames - release:
                envelope = max(0.0, (total_frames - frame) / release)
            else:
                envelope = 1.0

            sample = wave_value * volume * envelope
            left[idx] += sample * (1.0 - pan)
            right[idx] += sample * pan

    def _add_kick(self, left: list[float], right: list[float], start_beat: float, tempo: float, volume: float) -> None:
        beat_seconds = 60.0 / tempo
        start_frame = int(start_beat * beat_seconds * self.sample_rate)
        frames = int(beat_seconds * 0.38 * self.sample_rate)
        for frame in range(frames):
            idx = start_frame + frame
            if idx >= len(left):
                break
            progress = frame / frames
            freq = 92.0 - progress * 54.0
            envelope = math.exp(-6.0 * progress)
            sample = math.sin(math.tau * freq * (frame / self.sample_rate)) * envelope * volume
            left[idx] += sample * 0.5
            right[idx] += sample * 0.5

    def _add_snare(self, left: list[float], right: list[float], start_beat: float, tempo: float, volume: float) -> None:
        beat_seconds = 60.0 / tempo
        start_frame = int(start_beat * beat_seconds * self.sample_rate)
        frames = int(beat_seconds * 0.28 * self.sample_rate)
        for frame in range(frames):
            idx = start_frame + frame
            if idx >= len(left):
                break
            progress = frame / frames
            envelope = math.exp(-10.0 * progress)
            noise = (random.random() * 2.0 - 1.0) * volume * envelope
            tone = math.sin(math.tau * 220.0 * (frame / self.sample_rate)) * volume * 0.22 * envelope
            sample = noise + tone
            left[idx] += sample * 0.5
            right[idx] += sample * 0.5

    def _add_hat(self, left: list[float], right: list[float], start_beat: float, tempo: float, volume: float) -> None:
        beat_seconds = 60.0 / tempo
        start_frame = int(start_beat * beat_seconds * self.sample_rate)
        frames = int(beat_seconds * 0.11 * self.sample_rate)
        for frame in range(frames):
            idx = start_frame + frame
            if idx >= len(left):
                break
            progress = frame / frames
            envelope = math.exp(-14.0 * progress)
            sample = (random.random() * 2.0 - 1.0) * volume * envelope
            left[idx] += sample * 0.42
            right[idx] += sample * 0.58

    def _sound_from_buffers(self, left: list[float], right: list[float]) -> pygame.mixer.Sound:
        peak = max(max(abs(sample) for sample in left), max(abs(sample) for sample in right), 1e-6)
        scale = 28000.0 / peak
        pcm = array("h")
        for left_sample, right_sample in zip(left, right):
            pcm.append(int(max(-32767, min(32767, left_sample * scale))))
            pcm.append(int(max(-32767, min(32767, right_sample * scale))))

        wav_bytes = io.BytesIO()
        with wave.open(wav_bytes, "wb") as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm.tobytes())
        wav_bytes.seek(0)
        return pygame.mixer.Sound(file=wav_bytes)

    def _build_storm_siege_road(self) -> pygame.mixer.Sound:
        tempo = 138.0
        total_beats = 32
        total_frames = int((total_beats * 60.0 / tempo) * self.sample_rate)
        left = [0.0] * total_frames
        right = [0.0] * total_frames

        pad_progression = [
            (0, "D3"), (4, "A#2"), (8, "F3"), (12, "C3"),
            (16, "D3"), (20, "A#2"), (24, "F3"), (28, "C3"),
        ]
        bass_line = [
            (0, "D2"), (2, "D2"), (4, "A#1"), (6, "A#1"),
            (8, "F2"), (10, "F2"), (12, "C2"), (14, "C2"),
            (16, "D2"), (18, "D2"), (20, "A#1"), (22, "A#1"),
            (24, "F2"), (26, "F2"), (28, "C2"), (30, "C2"),
        ]
        melody = [
            (0.0, "D4", 0.75), (1.0, "F4", 0.5), (2.0, "A4", 0.75), (3.0, "F4", 0.5),
            (4.0, "A#4", 0.75), (5.0, "A4", 0.5), (6.0, "F4", 0.75), (7.0, "D4", 0.5),
            (8.0, "F4", 0.75), (9.0, "G4", 0.5), (10.0, "A4", 0.75), (11.0, "F4", 0.5),
            (12.0, "E4", 0.75), (13.0, "D4", 0.5), (14.0, "C4", 0.75), (15.0, "A3", 0.5),
            (16.0, "D4", 0.75), (17.0, "F4", 0.5), (18.0, "A4", 0.75), (19.0, "C5", 0.5),
            (20.0, "A#4", 0.75), (21.0, "A4", 0.5), (22.0, "F4", 0.75), (23.0, "D4", 0.5),
            (24.0, "F4", 0.75), (25.0, "G4", 0.5), (26.0, "A4", 0.75), (27.0, "F4", 0.5),
            (28.0, "E4", 0.75), (29.0, "F4", 0.5), (30.0, "D4", 1.0),
        ]

        for start_beat, note in pad_progression:
            base_freq = self._note_frequency(note)
            self._add_tone(left, right, start_beat, 4.0, base_freq, tempo, 0.11, "triangle", 0.46)
            self._add_tone(left, right, start_beat, 4.0, base_freq * 1.5, tempo, 0.04, "sine", 0.54)

        for start_beat, note in bass_line:
            self._add_tone(left, right, start_beat, 1.5, self._note_frequency(note), tempo, 0.18, "saw", 0.50)

        for start_beat, note, length in melody:
            lead_freq = self._note_frequency(note)
            self._add_tone(left, right, start_beat, length, lead_freq, tempo, 0.14, "square", 0.62)
            self._add_tone(left, right, start_beat, length, lead_freq * 0.5, tempo, 0.04, "triangle", 0.38)

        for beat in range(0, total_beats, 2):
            self._add_kick(left, right, beat, tempo, 0.34)
        for beat in range(2, total_beats, 4):
            self._add_snare(left, right, beat, tempo, 0.20)
        for beat in range(1, total_beats * 2, 2):
            self._add_hat(left, right, beat / 2.0, tempo, 0.07)

        return self._sound_from_buffers(left, right)

    def _build_blackfang_core(self) -> pygame.mixer.Sound:
        tempo = 118.0
        total_beats = 32
        total_frames = int((total_beats * 60.0 / tempo) * self.sample_rate)
        left = [0.0] * total_frames
        right = [0.0] * total_frames

        pad_progression = [
            (0, "D2"), (8, "F2"), (16, "C2"), (24, "A#1"),
        ]
        bass_line = [
            (0, "D2"), (2, "D2"), (4, "F2"), (6, "D2"),
            (8, "F2"), (10, "F2"), (12, "G2"), (14, "F2"),
            (16, "C2"), (18, "C2"), (20, "D2"), (22, "F2"),
            (24, "A#1"), (26, "A#1"), (28, "C2"), (30, "D2"),
        ]
        pulse_line = [
            (0.0, "D4", 0.5), (1.5, "D4", 0.5), (3.0, "F4", 0.5),
            (4.0, "A3", 0.5), (5.5, "A3", 0.5), (7.0, "F4", 0.5),
            (8.0, "F4", 0.5), (9.5, "G4", 0.5), (11.0, "F4", 0.5),
            (12.0, "D4", 0.5), (13.5, "D4", 0.5), (15.0, "C4", 0.5),
            (16.0, "C4", 0.5), (17.5, "D4", 0.5), (19.0, "F4", 0.5),
            (20.0, "A#3", 0.5), (21.5, "A#3", 0.5), (23.0, "F4", 0.5),
            (24.0, "A#3", 0.5), (25.5, "C4", 0.5), (27.0, "D4", 0.5),
            (28.0, "F4", 0.5), (29.5, "D4", 0.5), (31.0, "C4", 0.75),
        ]
        alarm_hits = [(6.0, "A4"), (14.0, "G4"), (22.0, "A4"), (30.0, "F4")]

        for start_beat, note in pad_progression:
            base_freq = self._note_frequency(note)
            self._add_tone(left, right, start_beat, 8.0, base_freq, tempo, 0.11, "triangle", 0.50)
            self._add_tone(left, right, start_beat, 8.0, base_freq * 2.0, tempo, 0.03, "saw", 0.58)

        for start_beat, note in bass_line:
            self._add_tone(left, right, start_beat, 1.5, self._note_frequency(note), tempo, 0.20, "square", 0.50)

        for start_beat, note, length in pulse_line:
            freq = self._note_frequency(note)
            self._add_tone(left, right, start_beat, length, freq, tempo, 0.10, "saw", 0.62)
            self._add_tone(left, right, start_beat, length, freq * 0.5, tempo, 0.04, "triangle", 0.38)

        for start_beat, note in alarm_hits:
            freq = self._note_frequency(note)
            self._add_tone(left, right, start_beat, 0.75, freq, tempo, 0.12, "square", 0.72)
            self._add_tone(left, right, start_beat, 0.75, freq * 1.5, tempo, 0.03, "sine", 0.28)

        for beat in range(0, total_beats, 4):
            self._add_kick(left, right, beat, tempo, 0.36)
            self._add_kick(left, right, beat + 2, tempo, 0.24)
        for beat in range(2, total_beats, 4):
            self._add_snare(left, right, beat, tempo, 0.22)
        for beat in range(0, total_beats * 2, 2):
            self._add_hat(left, right, beat / 2.0 + 0.5, tempo, 0.05)

        return self._sound_from_buffers(left, right)
