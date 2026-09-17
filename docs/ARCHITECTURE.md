# Architecture

## Two layers, one direction

```
  physical device (ESP32)  ──USB serial, EVT: lines──▶  laptop (bridge.py → SQLite → app.py → browser)
```

The firmware is the whole product. It runs the state machine, validates every input, and drives every output; nothing on the laptop can send anything back to it. The dashboard is a read-only mirror for observers — the device has no screen by design, and the mirror exists so an audience can follow what an illiterate user is doing on it.

![System architecture](images/system-architecture.png)

---

## Firmware state machine

State lives in a handful of globals on the ESP32:

| Variable | Meaning |
|---|---|
| `deviceUnlocked` | keyfob has been presented this session |
| `selectedRecipient` | name string, `""` if none |
| `transferAmount` | running total in taka |
| `amountHistory[20]`, `historyCount` | stack of individual denomination taps, for undo |
| `accountBalance` | starts at 10 000, decremented on each successful transfer, **resets on power-cycle** |
| `amountInstructionPlayed`, `holdInstructionPlayed` | once-per-session guidance flags |
| `lastActivityTime` | for the 60 s idle timeout |

States and transitions are drawn in [images/interaction-flow.png](images/interaction-flow.png).

### Forcing functions (Norman)

| Guard | Where | Prevents |
|---|---|---|
| Everything ignored until keyfob | `handleRFID`, `loop` | any action on a device left on a table |
| Denomination refused if no recipient | `handleRFID` | composing an amount with nowhere to send it |
| Tap refused if it would exceed balance or 10 000 cap | `handleRFID` | overdraw, checked *before* the tap is added |
| Confirm button inert unless recipient **and** amount exist | `handleConfirmButton` | false "success" on an empty transaction |
| Hold must reach 2 000 ms; early release is a reminder, not a cancel | `handleConfirmButton` | accidental send from a brush or slip; also avoids the misleading "cancelled" message when nothing was lost |
| `awaitingRelease` after a confirm | `handleConfirmButton` | a held-down finger re-triggering a second transfer |
| 1 500 ms cooldown between reads | `handleRFID` | one physical tap being read as several |
| Software debounce, 40 ms | both buttons | contact bounce being read as multiple presses |

### Timing model

The sketch is intentionally `delay()`-based around audio so that spoken phrases never cut each other off (the DFPlayer plays one track at a time, and rapid back-to-back `play()` calls on clone boards are unreliable). The confirm-hold and idle-warning paths are non-blocking (`millis()`) so the ring animates smoothly and the serial stream keeps flowing.

### Audio strategy

Spoken numbers are **composed from building blocks**, not pre-recorded per value: thousands-word + hundreds-word + "taka". Twenty small clips cover every multiple of 100 from 100 to 10 000. See [../audio/AUDIO_MAP.md](../audio/AUDIO_MAP.md).

---

## Serial event protocol

Every state change prints one machine-readable line **in addition to** the human-readable log line that was already there. Format:

```
EVT:type=<name>;key=value;key=value
```

9600 baud. Lines not starting with `EVT:` are ordinary log text and are ignored by the bridge.

| `type` | Extra fields | When |
|---|---|---|
| `boot` | `balance` | end of `setup()` — forces the dashboard to a known locked state on every power-up |
| `unlocked` | `balance` | keyfob accepted while locked |
| `locked_attempt` | — | any other card while locked |
| `locked` | `reason` = `keyfob` \| `idle` | device locks |
| `recipient_selected` | `name` | photo card accepted |
| `blocked_no_recipient` | — | denomination before recipient |
| `rejected_limit` | — | tap would exceed balance / cap |
| `amount_updated` | `amount`, `last_token` | denomination accepted (`last_token` positive) **or** undo (`last_token` negative) |
| `transaction_cancelled` | — | undo reached zero, or pink button pressed mid-transaction |
| `undo_empty` | — | undo card with nothing to remove |
| `unknown_card` | — | UID not in any table |
| `confirm_not_ready` | — | yellow button with no recipient/amount |
| `confirm_progress` | `percent` (0–100, in twelfths) | during a hold, once per newly-lit LED |
| `confirm_released_early` | — | released before 2 s |
| `transfer_success` | `recipient`, `amount`, `balance` | hold completed; `balance` is the new post-transfer value |
| `balance_checked` | `balance` | pink button with nothing in progress |
| `idle_warning` | `seconds_left` | once per second during the final 5 s |
| `idle_warning_clear` | — | activity resumed, or lock fired |

**Balance is a single source of truth.** The dashboard never computes balance; it only displays the last value the device reported. This guarantees the screen can never disagree with what the speaker just said.

---

## Bridge (`dashboard/bridge.py`)

- Opens the serial port with `pyserial`; only one process may hold it, so Arduino's Serial Monitor must be closed.
- On start, **drops and recreates** both SQLite tables. State is session-only by design; a stale row can never survive a restart, and the firmware's `boot` event re-syncs everything the moment the device powers on.
- Parses each `EVT:` line into a dict and applies it to `current_state` (one row) and, for `transfer_success`, appends to `transactions`.
- Every user-visible outcome also writes a **banner** (`text`, `type`, ISO timestamp) that the page turns into a toast and a ring flash.

Schema, `current_state`:

```
session_status  selected_recipient  current_amount  current_balance  current_tokens
hold_active  hold_percent  idle_warning_active  idle_seconds_left
banner_text  banner_type  banner_timestamp
```

`current_tokens` is a comma-separated list rebuilt from `amount_updated` events (append on positive `last_token`, pop on negative), so the page can show every note in the order it was tapped.

---

## Dashboard (`dashboard/app.py`)

- Flask on port **5001** (5000 is AirPlay on macOS).
- `GET /api/state` — JSON snapshot. **When locked, session-sensitive fields are not sent at all** (recipient, amount, balance, tokens, history, hold, idle). This is a server-side privacy boundary, not a CSS `display:none`.
- `GET /photos/<file>` — serves `~/htm_photos/`.
- `GET /` — single-page dashboard; polls `/api/state` every 200 ms and updates the DOM in place (no page reloads).

The page is a **digital twin** of the device: a 12-segment SVG ring with the same `NUMPIXELS = 12` semantics as the firmware (`lit = round(percent × 12 / 100)`), a yellow button that breathes when `readyToConfirm` is true and depresses while held, green/red/amber ring flashes on the same events that trigger `feedback()` on the hardware, and a red 400 ms strobe during the idle warning matching `rapidFlashTick()`.
