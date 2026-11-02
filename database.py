
import sqlite3
from pathlib import Path

DB_NAME = Path(__file__).resolve().parent / "traffic.db"
TOTAL_SLOTS = 10


def connect_db():
    return sqlite3.connect(DB_NAME, timeout=10)


# =================================================
# INITIALIZE DATABASE
# =================================================

def init_db():
    with connect_db() as conn:

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS parking_slots (
                slot_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'Available'
            );

            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reservation_id TEXT UNIQUE NOT NULL,
                slot_id INTEGER NOT NULL,
                customer_name TEXT NOT NULL,
                vehicle_number TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'Active',
                FOREIGN KEY (slot_id) REFERENCES parking_slots(slot_id)
            );

            CREATE UNIQUE INDEX IF NOT EXISTS unique_active_reservation
            ON reservations(slot_id) WHERE status = 'Active';

            CREATE TABLE IF NOT EXISTS hazards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hazard_id TEXT UNIQUE NOT NULL,
                hazard_type TEXT NOT NULL,
                location TEXT NOT NULL,
                severity TEXT NOT NULL,
                traffic_level TEXT NOT NULL,
                description TEXT,
                priority INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Reported',
                photo_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS traffic_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_count INTEGER NOT NULL,
                traffic_level TEXT NOT NULL,
                signal_seconds INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.executemany(
            "INSERT OR IGNORE INTO parking_slots (slot_id) VALUES (?)",
            [(i,) for i in range(1, TOTAL_SLOTS + 1)]
        )


# =================================================
# TRAFFIC MANAGEMENT
# =================================================

def save_traffic(vehicle_count, traffic_level, signal_seconds):
    with connect_db() as conn:
        conn.execute("""
            INSERT INTO traffic_history
            (vehicle_count, traffic_level, signal_seconds)
            VALUES (?, ?, ?)
        """, (vehicle_count, traffic_level, signal_seconds))


def get_traffic_history():
    with connect_db() as conn:
        return conn.execute("""
            SELECT vehicle_count, traffic_level,
                   signal_seconds, created_at
            FROM traffic_history ORDER BY id DESC
        """).fetchall()


# =================================================
# SMART PARKING
# =================================================

def get_parking_slots():
    with connect_db() as conn:
        return conn.execute("""
            SELECT slot_id, status FROM parking_slots
            ORDER BY slot_id
        """).fetchall()


def get_parking_status():
    return get_parking_slots()


def update_parking_slot(slot_id, status):
    if status not in ("Available", "Occupied", "Reserved"):
        raise ValueError("Invalid parking status.")

    with connect_db() as conn:
        cur = conn.execute("""
            UPDATE parking_slots SET status = ?
            WHERE slot_id = ?
        """, (status, slot_id))
        return cur.rowcount > 0


def get_reservations():
    with connect_db() as conn:
        return conn.execute("""
            SELECT reservation_id, slot_id, customer_name,
                   vehicle_number, created_at, status
            FROM reservations ORDER BY id DESC
        """).fetchall()


def save_reservation(reservation_id, slot_id,
                     customer_name, vehicle_number):
    with connect_db() as conn:
        cur = conn.execute("""
            UPDATE parking_slots SET status = 'Reserved'
            WHERE slot_id = ? AND status = 'Available'
        """, (slot_id,))

        if cur.rowcount != 1:
            raise ValueError("This parking slot is not available.")

        conn.execute("""
            INSERT INTO reservations
            (reservation_id, slot_id, customer_name, vehicle_number)
            VALUES (?, ?, ?, ?)
        """, (reservation_id, slot_id, customer_name, vehicle_number))


def cancel_reservation(reservation_id):
    with connect_db() as conn:
        cur = conn.execute("""
            SELECT slot_id FROM reservations
            WHERE reservation_id = ? AND status = 'Active'
        """, (reservation_id,))

        result = cur.fetchone()
        if result is None:
            return False

        slot_id = result[0]

        conn.execute("""
            UPDATE reservations SET status = 'Cancelled'
            WHERE reservation_id = ?
        """, (reservation_id,))

        conn.execute("""
            UPDATE parking_slots SET status = 'Available'
            WHERE slot_id = ? AND status = 'Reserved'
        """, (slot_id,))

        return True


# =================================================
# ROAD SAFETY
# =================================================

def save_hazard(hazard_id, hazard_type, location,
                severity, traffic_level, description,
                priority, photo_path=None):
    with connect_db() as conn:
        conn.execute("""
            INSERT INTO hazards
            (hazard_id, hazard_type, location, severity,
             traffic_level, description, priority, photo_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (hazard_id, hazard_type, location, severity,
              traffic_level, description, priority, photo_path))


def get_hazards():
    with connect_db() as conn:
        return conn.execute("""
            SELECT hazard_id, hazard_type, location, severity,
                   traffic_level, description, priority,
                   status, photo_path, created_at
            FROM hazards ORDER BY id DESC
        """).fetchall()


def update_hazard_status(hazard_id, new_status):
    if new_status not in ("Reported", "Verified",
                          "In Progress", "Resolved"):
        raise ValueError("Invalid hazard status.")

    with connect_db() as conn:
        cur = conn.execute("""
            UPDATE hazards SET status = ?
            WHERE hazard_id = ?
        """, (new_status, hazard_id))
        return cur.rowcount > 0
def reset_parking_status():
    with connect_db() as conn:
        conn.execute("""
            UPDATE parking_slots
            SET status = 'Available'
        """)

        conn.execute("""
            UPDATE parking_slots
            SET status = 'Reserved'
            WHERE slot_id IN (
                SELECT slot_id
                FROM reservations
                WHERE status = 'Active'
            )
        """)
if __name__ == "__main__":
    reset_parking_status()
    print("Parking slots:")
    print(get_parking_slots())

    print("Reservations:")
    print(get_reservations())         