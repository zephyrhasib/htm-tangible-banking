# Hardware Reference

## Bill of materials

| # | Part | Spec / notes | Qty | Approx. BDT |
|---|---|---|---|---|
| 1 | ESP32-WROOM-32 DevKit | 30-pin, USB-C, CP2102 USB-serial. Any standard "ESP32 Dev Module" works. | 2 (1 spare) | 500–700 ea |
| 2 | MFRC522 RFID reader | 13.56 MHz, SPI, **3.3 V logic** — never feed it 5 V | 1 | 150–250 |
| 3 | Mifare Classic 1K cards | ISO 14443A, 13.56 MHz. 5 recipients + 4 denominations + 1 undo + spares | 12–14 | 15–32 ea |
| 4 | RFID keyfob | 13.56 MHz, RC522-compatible (confirm it is **not** 125 kHz) | 1–2 | ~50 |
| 5 | MP3-TF-16P / FN-M16P | DFPlayer Mini clone. Genuine DFRobot works identically but costs ~5× more | 1 | 150–300 |
| 6 | microSD card + adapter | 4–8 GB, **FAT32**. Larger cards work but gain nothing | 1 | 150–300 |
| 7 | Speaker | 3 W, 8 Ω (4 Ω also fine). JST-PH 2.0 connector can simply be cut off and the wires soldered/screwed to SPK1/SPK2 | 1 | 100–150 |
| 8 | WS2812B ring | 12 LEDs, 5 V, single data line, drivers built in — no separate driver board | 1 | 150–250 |
| 9 | 74HCT125 | Quad buffer, DIP-14. The **HCT** variant matters: it accepts 3.3 V as logic-high and outputs 5 V | 1 | 30–50 |
| 10 | Tactile push buttons | 12×12×7.3 mm, momentary, 4-pin. One yellow cap (confirm), one pink cap (balance) | 2 | 20–30 ea |
| 11 | Resistor | 1.2 kΩ (1 kΩ – 10 kΩ all fine) on DFPlayer RX line | 1 | — |
| 12 | Breadboard, jumpers (M-M, M-F, F-F), USB-C cable | | | 400–600 |

Power: the ESP32's USB-C connection from the laptop supplies everything. No separate supply is required; the ring at partial brightness plus DFPlayer plus ESP32 stay comfortably under 1 A.

**Do not use:** Arduino Uno (no WiFi, single UART, 2 KB RAM), Raspberry Pi (slow boot, needs safe shutdown, unnecessary), PN532 reader (extra NFC modes this project never uses), UHF RFID (read range of metres would make every tap ambiguous).

---

## GPIO map

| Function | ESP32 GPIO | Notes |
|---|---|---|
| RFID SDA / SS | 5 | SPI chip select |
| RFID SCK | 18 | SPI clock |
| RFID MOSI | 23 | |
| RFID MISO | 19 | |
| RFID RST | 22 | |
| DFPlayer RX (module) | 17 (ESP32 TX2) | via 1.2 kΩ series resistor |
| DFPlayer TX (module) | 16 (ESP32 RX2) | |
| WS2812B data | 4 → 74HCT125 → ring DI | never straight to the ring |
| Yellow confirm button | 15 | `INPUT_PULLUP`, other leg to GND |
| Pink balance/cancel button | 13 | `INPUT_PULLUP`, other leg to GND |

Avoid GPIO 0, 2, 12 for anything — they are boot-strapping pins on most DevKits.

The ESP32's **`TX0`/`RX0`** pins are the USB programming/serial link. Do not connect the DFPlayer there; it will fight with uploads and the dashboard. Use **`TX2`/`RX2`**.

---

## Wiring, module by module

### MFRC522 (RFID)

| MFRC522 pin | → ESP32 |
|---|---|
| SDA | GPIO 5 |
| SCK | GPIO 18 |
| MOSI | GPIO 23 |
| MISO | GPIO 19 |
| IRQ | not connected |
| GND | GND |
| RST | GPIO 22 |
| 3.3V | **3V3** |

Thin non-metallic layers (paper, tape, laminate, cardboard) over the reader or on the cards do not affect reading. Metal or foil-backed tape does.

### DFPlayer / MP3-TF-16P (audio)

The clone board has **no silkscreen**. Pin layout is the standard MP3-TF-16P 16-pin (8 per side) — match it against a pinout diagram for that board. Chips on the back: MH2024K-24SS (decoder) and 8002A (3 W amp) — both expected.

| Module pin | → |
|---|---|
| VCC | **5V / VIN** (not 3.3 V) |
| GND | GND |
| RX | ESP32 GPIO 17 (TX2), through 1.2 kΩ |
| TX | ESP32 GPIO 16 (RX2) |
| SPK1 | speaker + |
| SPK2 | speaker − |

The module's `readFileCounts()` query returns `-1` on this clone. That is a known quirk of the chip and does not affect playback — the firmware does not use it.

### WS2812B ring via 74HCT125

Hold the DIP-14 with the notch pointing left; pin 1 is bottom-left, numbering runs down the left side and up the right.

| 74HCT125 pin | → |
|---|---|
| 14 (VCC) | 5V / VIN |
| 7 (GND) | GND |
| **1 (1OE)** | **GND** — must be grounded or the buffer stays high-impedance and nothing passes |
| 2 (1A) | ESP32 GPIO 4 |
| 3 (1Y) | ring **DI** |
| 4–6, 8–13 | unused |

| Ring pad | → |
|---|---|
| 5V | 5V / VIN |
| GND | GND |
| DI | 74HCT125 pin 3 |
| DO | not connected (only used to chain a second ring) |

Solder three wires to the ring's pads (5V, GND, DI). `DO` stays empty.

Why the shifter: the ESP32 outputs 3.3 V logic; WS2812B expects a 5 V data signal. Short runs often work without it, but flicker or a dead first LED is the classic symptom when they don't. The shifter costs ~40 BDT and removes the guesswork.

### Buttons

Each 4-pin tactile button has two internally-connected pairs. Use one leg from each side:

| Button | Leg A | Leg B |
|---|---|---|
| Yellow (confirm) | GPIO 15 | GND |
| Pink (balance / cancel) | GPIO 13 | GND |

`pinMode(pin, INPUT_PULLUP)` in firmware — no external resistor. Pressed reads `LOW`. The sketch debounces in software (40 ms) — a hardware resistor does not fix bounce; the code does.

---

## Token set

| Token | Physical form | Label |
|---|---|---|
| Keyfob | RFID fob on a keyring | tap-zone icon only |
| Recipient ×5 | Mifare card, photo glued on front | photo front, tap icon back |
| Denomination ×4 | Mifare card, note image on front | 1000 / 500 / 200 / 100 |
| Undo | Mifare card, yellow wrap | large ✕ front and back |

Print sheets for the tap icons are in `assets/`. All icons are original line art, chosen so a first-time user can match "the small flat thing" to "the small flat hollow" without reading.

---

## Card UIDs used in this build

These are the UIDs of the specific cards in the reference build. **Yours will differ** — scan each card with the MFRC522 `DumpInfo` example and replace them in the sketch.

| Role | UID |
|---|---|
| Keyfob | `50 2F F3 53` |
| Shanto | `C0 71 5A 5C` |
| Tonmoy | `B1 4C 46 0A` |
| Kabir | `B0 56 3F 5C` |
| Puja | `B0 EB 9C 5C` |
| Hasib | `C0 BB AF 5C` |
| 1000 taka | `B0 66 57 5C` |
| 500 taka | `B0 80 96 5C` |
| 200 taka | `B0 9B 36 5C` |
| 100 taka | `C1 5B 59 0A` |
| Undo (✕) | `C0 5A 26 5C` |
