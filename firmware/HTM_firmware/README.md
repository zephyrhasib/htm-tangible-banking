# Firmware

Place `HTM_firmware.ino` in this folder. Arduino IDE requires the sketch file name to match its enclosing folder name, which is why the extra `HTM_firmware/` directory exists.

Before uploading, replace the UIDs at the top of the sketch with your own cards' UIDs (see `docs/HARDWARE.md`, "Card UIDs"). Everything else — pin numbers, audio track numbers, timing — matches `docs/HARDWARE.md` and `audio/AUDIO_MAP.md` as-is.
