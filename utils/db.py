import sqlite3
import datetime

def get_db_connection():
    """Returns a new in-memory SQLite connection."""
    # check_same_thread=False is needed for Streamlit if we share connection across threads (though typically st runs script in one thread, but interactions might differ)
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    return conn

def init_db(conn):
    """Initializes the database schema."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            level TEXT,
            message TEXT
        )
    """)
    conn.commit()

def log_message(conn, level, message):
    """Logs a message to the database."""
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (level, message) VALUES (?, ?)", (level, message))
        conn.commit()
    except Exception as e:
        print(f"Error logging to DB: {e}")

def get_logs(conn):
    """Retrieves all logs."""
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, level, message FROM logs ORDER BY id DESC")
    return cursor.fetchall()
