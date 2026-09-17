# Dashboard

Place `bridge.py` and `app.py` here. See `docs/SETUP.md` Part 5 for setup and `docs/ARCHITECTURE.md` for the serial protocol they consume.

Before running:
- set `SERIAL_PORT` in `bridge.py` to your board's port (Tools → Port in Arduino IDE)
- both scripts default `DB_PATH` to `~/htm_ledger.db`; change both together if you move it
- photos go in `~/htm_photos/` (not committed — see `.gitignore`)
