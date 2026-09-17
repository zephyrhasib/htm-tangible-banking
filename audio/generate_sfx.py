import os
os.makedirs("out", exist_ok=True)
import numpy as np
from scipy.io import wavfile
import subprocess
import os

SR = 44100

def tone(freq, duration, vol=0.4, fade=0.01):
    t = np.linspace(0, duration, int(SR * duration), False)
    wave = np.sin(freq * t * 2 * np.pi)
    # fade in/out to avoid clicks
    fade_samples = int(SR * fade)
    envelope = np.ones_like(wave)
    envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
    envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
    return wave * envelope * vol

def silence(duration):
    return np.zeros(int(SR * duration))

def save_wav_and_mp3(filename_base, audio):
    audio = np.clip(audio, -1, 1)
    audio_int16 = (audio * 32767).astype(np.int16)
    wav_path = f"out/{filename_base}.wav"
    mp3_path = f"out/{filename_base}.mp3"
    wavfile.write(wav_path, SR, audio_int16)
    subprocess.run(["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame",
                     "-qscale:a", "2", mp3_path],
                    capture_output=True)
    print(f"Saved {filename_base}.mp3")

# 0039 - short single high beep (card recognized)
audio_39 = tone(1800, 0.10, vol=0.5)
save_wav_and_mp3("0039", audio_39)

# 0040 - two-note descending buzz (error/rejected)
audio_40 = np.concatenate([
    tone(500, 0.14, vol=0.45),
    silence(0.03),
    tone(320, 0.20, vol=0.45)
])
save_wav_and_mp3("0040", audio_40)

# 0041 - rising three-note chime (success)
audio_41 = np.concatenate([
    tone(880, 0.10, vol=0.4),
    silence(0.02),
    tone(1100, 0.10, vol=0.4),
    silence(0.02),
    tone(1320, 0.18, vol=0.45)
])
save_wav_and_mp3("0041", audio_41)

# 0042 - soft short click (balance check)
audio_42 = tone(1000, 0.06, vol=0.35, fade=0.005)
save_wav_and_mp3("0042", audio_42)

# 0043 - low double beep (idle warning tick)
audio_43 = np.concatenate([
    tone(400, 0.08, vol=0.4),
    silence(0.05),
    tone(400, 0.08, vol=0.4)
])
save_wav_and_mp3("0043", audio_43)

print("All sound effects generated.")
