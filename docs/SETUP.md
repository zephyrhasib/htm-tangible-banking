# Setup Guide

This is the order that actually works. Every stage was tested in isolation before the next one was added — do the same, because when three untested parts are wired together at once, you cannot tell which one is broken.

Tested on macOS with an ESP32-WROOM-32 (30-pin, USB-C, CP2102). Linux and Windows differ only in the driver step and the serial port name.

---

## Part 1 — Toolchain

### 1.1 Install Arduino IDE

Download from arduino.cc and install.

### 1.2 Add the ESP32 board package

1. **Arduino IDE → Settings** → *Additional boards manager URLs* → paste:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
2. **Tools → Board → Boards Manager** → search `esp32` → install the package by **Espressif Systems** (not the Arduino-maintained one).
3. **Tools → Board → esp32 → ESP32 Dev Module**.

### 1.3 Install the USB driver (CP2102)

On macOS with Homebrew:
```bash
brew install --cask silicon-labs-vcp-driver
open "/opt/homebrew/Caskroom/silicon-labs-vcp-driver/6.0.2/Install CP210x VCP Driver.app"
```
Follow the installer. Then **System Settings → Privacy & Security** → *Allow* if prompted → **restart the Mac**.

If the installer freezes, force-quit it and restart anyway — the driver usually finishes registering on reboot.

### 1.4 Confirm the board is alive

1. Plug in the ESP32. **Tools → Port** should now list `/dev/cu.usbserial-XXXX`.
2. **File → Examples → 01.Basics → Blink** → Upload.
3. If upload fails with `termios.error` or "Connecting..." hangs: set **Tools → Upload Speed → 115200**, and if still stuck, hold the **BOOT** button on the board while it says *Connecting…*.

Onboard LED blinking = toolchain done.

### 1.5 Install libraries

**Sketch → Include Library → Manage Libraries**, install:

| Library | Author |
|---|---|
| MFRC522 | GithubCommunity |
| DFRobotDFPlayerMini | DFRobot |
| Adafruit NeoPixel | Adafruit |

---

## Part 2 — Wire and test each peripheral alone

Full pinout is in [HARDWARE.md](HARDWARE.md). Wire **one** peripheral, upload its test sketch, confirm it works, then add the next.

### 2.1 RFID reader (MFRC522)

Wire per HARDWARE.md. Upload **File → Examples → MFRC522 → DumpInfo**, edit `RST_PIN 22` and `SS_PIN 5` at the top if needed. Open Serial Monitor at **9600**. Tap a card — you should see `Card UID: XX XX XX XX`.

### 2.2 Record every card's UID

With DumpInfo still running, tap each card one at a time and write down its UID. Physically label each card with tape as you go — do this *before* gluing any photos on. You need:

```
Recipient 1–5 : ___ ___ ___ ___    (assign a name to each)
Denomination 1000 / 500 / 200 / 100
Undo card
Keyfob
```

### 2.3 Audio (DFPlayer + speaker)

Wire per HARDWARE.md. Before the test sketch runs you need at least one MP3 on the card — see Part 3. Upload a minimal `myDFPlayer.play(1)` test. If Serial says *DFPlayer not detected*: check VCC is on **5 V** (not 3.3 V), RX/TX are crossed correctly, and the card is FAT32.

### 2.4 LED ring (WS2812B via 74HCT125)

Wire per HARDWARE.md — the ring's data line goes **through** the level shifter, not straight from the ESP32. Test with the Adafruit NeoPixel `simple` example on pin 4, 12 pixels. If only the first LED lights or colours are wrong, the shifter's pin 1 (`1OE`) is probably not grounded.

### 2.5 Buttons

Wire each button between its GPIO and GND; use `INPUT_PULLUP` — no external resistor. Yellow = GPIO 15, pink = GPIO 13.

---

## Part 3 — Audio files

### 3.1 Generate the Bangla clips

Requires Python 3 and internet (edge-tts calls Microsoft's TTS service).

```bash
python3 -m venv htm_venv
source htm_venv/bin/activate
pip install edge-tts
python3 audio/generate_audio.py     # 38 spoken clips → 0001–0038.mp3
python3 audio/generate_sfx.py       # 5 tones → 0039–0043.mp3
```

Listen to a few — Bangla number pronunciation is where TTS most often sounds off. Track-by-track meaning is in [audio/AUDIO_MAP.md](../audio/AUDIO_MAP.md).

### 3.2 Load the microSD card — order matters

**The DFPlayer clone plays files in the order they were physically written to the card, not by filename.** Dragging in Finder can write them in reverse. Do it from the terminal so the order is guaranteed:

1. Format the card as **MS-DOS (FAT)** in Disk Utility (this is FAT32; do *not* pick ExFAT).
2. With the clips in one folder:
   ```bash
   cd /path/to/clips
   for i in $(seq -w 1 43); do cp "00${i}.mp3" /Volumes/YOUR_SD_CARD/; done
   ```
3. Eject, insert into the DFPlayer.

Verify with a small sketch that plays track numbers typed into Serial Monitor: `1` must say "tap your card", `3` must say "welcome". If `1` plays the *last* file instead, the card was written in reverse — reformat and redo step 2.

---

## Part 4 — Firmware

1. Open `firmware/HTM_firmware/HTM_firmware.ino`.
2. Paste your UIDs from step 2.2 into `keyfobUID`, `recipientUIDs[]`, `denominationUIDs[]`, and `cancelCardUID`. Keep the array order matched to `recipientNames[]` and `denominationValues[]`.
3. Upload.
4. Open Serial Monitor at **9600**. You should see `Device ready.` followed by `EVT:type=boot;balance=10000`.
5. Full run-through: tap a card while locked (rejected, red flash) → keyfob (welcome) → recipient (name spoken) → two denominations (totals spoken) → undo (last removed) → hold yellow 2 s (success, balance) → keyfob again (locked).

**Cold-boot note:** the sketch waits 1.5 s and retries the DFPlayer up to 5× on startup. This is deliberate — the DFPlayer needs time to mount the card, and without the delay the device works after a USB upload but not after a plain power-cycle.

---

## Part 5 — Dashboard (Mac)

### 5.1 Install

```bash
source htm_venv/bin/activate
pip install -r dashboard/requirements.txt
```

### 5.2 Photos

```bash
mkdir -p ~/htm_photos
```
Put these files in it, named exactly (lowercase):
```
account_holder.jpg
shanto.jpg  tonmoy.jpg  kabir.jpg  puja.jpg  hasib.jpg
1000.jpg  500.jpg  200.jpg  100.jpg
```
If your recipients have different names, change `recipientNames[]` in the firmware and `ALL_RECIPIENTS` in `app.py` together, and name the photos to match.

### 5.3 Set the serial port

In `dashboard/bridge.py`, set `SERIAL_PORT` to what Arduino IDE shows under **Tools → Port**.

### 5.4 Run

**Only one program can hold the serial port.** Close Arduino IDE's Serial Monitor first.

Terminal 1:
```bash
source htm_venv/bin/activate
python3 dashboard/bridge.py
```
Terminal 2:
```bash
source htm_venv/bin/activate
python3 dashboard/app.py
```
Browser: `http://localhost:5001` (port 5000 is taken by AirPlay Receiver on macOS).

The page should show the red **LOCKED** screen and nothing else. Tap the keyfob — the dashboard unlocks within 200 ms.

### 5.5 Restarting cleanly

`bridge.py` wipes and rebuilds its database every time it starts, so a stale state can never survive a restart. If the dashboard ever looks out of step with the device:

1. Stop both scripts (Ctrl+C).
2. Start `bridge.py`, then `app.py`.
3. **Hard-refresh** the browser (Cmd+Shift+R) — a normal reload can serve a cached page.

---

## Common problems

| Symptom | Cause | Fix |
|---|---|---|
| No serial port listed | Driver not installed / not restarted | Part 1.3; restart Mac; try a different USB-C cable (some are charge-only) |
| `Port is busy` | Serial Monitor open | Close it — one reader at a time |
| Works after upload, dead after power-cycle | DFPlayer not ready at boot | Already handled by the 1.5 s delay + retries in firmware |
| Wrong audio plays for a track | Files written to SD out of order | Part 3.2 |
| `DFPlayer not detected` | VCC on 3.3 V, or RX/TX not crossed | Use 5 V; module TX → ESP32 RX2 (16), module RX → ESP32 TX2 (17) |
| Ring: only first LED works | 74HCT125 `1OE` floating | Ground pin 1 |
| Dashboard shows data while locked | Old database / cached page | Part 5.5 |
| `Address already in use` on port 5000 | macOS AirPlay | App already uses 5001 |
