import serial
import sqlite3
from datetime import datetime

SERIAL_PORT = "/dev/cu.usbserial-0001"
BAUD_RATE = 9600
DB_PATH = "/Users/hasib/htm_ledger.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Both tables are wiped and rebuilt fresh every script start.
    # This is a live session mirror, not a permanent ledger - no cross-restart history.
    cur.execute("DROP TABLE IF EXISTS transactions")
    cur.execute("DROP TABLE IF EXISTS current_state")

    cur.execute("""
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            recipient TEXT NOT NULL,
            amount INTEGER NOT NULL,
            balance_after INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE current_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            session_status TEXT DEFAULT 'locked',
            selected_recipient TEXT DEFAULT '',
            current_amount INTEGER DEFAULT 0,
            current_balance INTEGER DEFAULT 10000,
            current_tokens TEXT DEFAULT '',
            hold_active INTEGER DEFAULT 0,
            hold_percent INTEGER DEFAULT 0,
            idle_warning_active INTEGER DEFAULT 0,
            idle_seconds_left INTEGER DEFAULT 0,
            banner_text TEXT DEFAULT '',
            banner_type TEXT DEFAULT '',
            banner_timestamp TEXT DEFAULT ''
        )
    """)
    cur.execute("INSERT INTO current_state (id) VALUES (1)")
    conn.commit()
    return conn

def parse_event(line):
    payload = line[4:]
    fields = {}
    for pair in payload.split(";"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            fields[key] = value
    return fields

def update_state(conn, **kwargs):
    cur = conn.cursor()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values())
    cur.execute(f"UPDATE current_state SET {sets} WHERE id = 1", values)
    conn.commit()

def set_banner(conn, text, banner_type):
    update_state(conn, banner_text=text, banner_type=banner_type,
                 banner_timestamp=datetime.now().isoformat(timespec="milliseconds"))

def update_tokens(conn, last_token_str):
    cur = conn.cursor()
    cur.execute("SELECT current_tokens FROM current_state WHERE id = 1")
    current = cur.fetchone()[0] or ""
    tokens = [t for t in current.split(",") if t]
    value = int(last_token_str)
    if value > 0:
        tokens.append(str(value))
    else:
        if tokens:
            tokens.pop()
    cur.execute("UPDATE current_state SET current_tokens = ? WHERE id = 1", (",".join(tokens),))
    conn.commit()

def handle_event(conn, event):
    etype = event.get("type")

    if etype == "boot":
        update_state(conn, session_status="locked", selected_recipient="", current_amount=0,
                     current_balance=int(event["balance"]), current_tokens="",
                     hold_active=0, hold_percent=0, idle_warning_active=0, idle_seconds_left=0)

    elif etype == "unlocked":
        update_state(conn, session_status="unlocked", current_balance=int(event["balance"]))

    elif etype == "locked_attempt":
        set_banner(conn, "Locked - tap your keyfob first", "error")

    elif etype == "locked":
        reason = event.get("reason", "")
        update_state(conn, session_status="locked", selected_recipient="", current_amount=0,
                     current_tokens="", hold_active=0, hold_percent=0,
                     idle_warning_active=0, idle_seconds_left=0)
        set_banner(conn, "Session locked - idle timeout" if reason == "idle" else "Session locked", "warning" if reason == "idle" else "info")

    elif etype == "recipient_selected":
        update_state(conn, selected_recipient=event["name"], current_amount=0, current_tokens="")
        set_banner(conn, f"Recipient selected: {event['name']}", "success")

    elif etype == "blocked_no_recipient":
        set_banner(conn, "Blocked - select a recipient first", "error")

    elif etype == "rejected_limit":
        set_banner(conn, "Rejected - amount would exceed balance", "error")

    elif etype == "amount_updated":
        update_state(conn, current_amount=int(event["amount"]))
        update_tokens(conn, event["last_token"])
        if int(event["last_token"]) > 0:
            set_banner(conn, f"Added {event['last_token']} taka", "success")
        else:
            set_banner(conn, f"Removed {event['last_token'][1:]} taka", "info")

    elif etype == "transaction_cancelled":
        update_state(conn, selected_recipient="", current_amount=0, current_tokens="")
        set_banner(conn, "Transaction cancelled", "warning")

    elif etype == "undo_empty":
        set_banner(conn, "Nothing to undo", "error")

    elif etype == "unknown_card":
        set_banner(conn, "Unknown card - not recognized", "error")

    elif etype == "confirm_not_ready":
        set_banner(conn, "Select a recipient and amount first", "error")

    elif etype == "confirm_progress":
        update_state(conn, hold_active=1, hold_percent=int(event["percent"]))

    elif etype == "confirm_released_early":
        update_state(conn, hold_active=0, hold_percent=0)
        set_banner(conn, "Released early - hold to confirm", "warning")

    elif etype == "transfer_success":
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO transactions (timestamp, recipient, amount, balance_after)
            VALUES (?, ?, ?, ?)
        """, (
            datetime.now().strftime("%H:%M:%S"),
            event["recipient"], int(event["amount"]), int(event["balance"])
        ))
        conn.commit()
        update_state(conn, current_balance=int(event["balance"]), selected_recipient="",
                     current_amount=0, current_tokens="", hold_active=0, hold_percent=0)
        set_banner(conn, f"Sent {event['amount']} taka to {event['recipient']}", "success")

    elif etype == "balance_checked":
        set_banner(conn, f"Balance: {event['balance']} taka", "info")

    elif etype == "idle_warning":
        update_state(conn, idle_warning_active=1, idle_seconds_left=int(event["seconds_left"]))

    elif etype == "idle_warning_clear":
        update_state(conn, idle_warning_active=0, idle_seconds_left=0)

def main():
    conn = init_db()
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"Listening on {SERIAL_PORT}, session-only tracking in {DB_PATH}...\n")

    while True:
        try:
            raw = ser.readline().decode("utf-8", errors="ignore").strip()
        except Exception as e:
            print(f"Read error: {e}")
            continue
        if not raw:
            continue
        if raw.startswith("EVT:"):
            event = parse_event(raw)
            handle_event(conn, event)
            print(f"LOGGED -> {event}")
        else:
            print(f"(device log) {raw}")

if __name__ == "__main__":
    main()