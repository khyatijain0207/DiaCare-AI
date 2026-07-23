"""
Simple SQLite helper for DiaCare AI.
Two tables:
  users        -> login/signup accounts
  predictions  -> saved prediction history, linked to a user
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            patient_name TEXT,
            age REAL,
            gender TEXT,
            height REAL,
            weight REAL,
            bmi REAL,
            blood_glucose_level REAL,
            prediction INTEGER,
            confidence REAL,
            top_reasons TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prediction_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
        comment TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (prediction_id) REFERENCES predictions(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        sender TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
""")

    conn.commit()
    conn.close()


# ---------------- Users ----------------

def create_user(name, email, password_hash):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user


# ------------- Predictions -------------

def save_prediction(user_id, patient_name, age, gender, height, weight,
                     bmi, blood_glucose_level, prediction, confidence, top_reasons):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO predictions
        (user_id, patient_name, age, gender, height, weight, bmi,
         blood_glucose_level, prediction, confidence, top_reasons)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, patient_name, age, gender, height, weight, bmi,
          blood_glucose_level, prediction, confidence, top_reasons))
    conn.commit()
    pred_id = cur.lastrowid
    conn.close()
    return pred_id


def get_prediction_by_id(pred_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM predictions WHERE id = ?", (pred_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_predictions_for_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM predictions WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_latest_prediction_for_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM predictions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row

# ------------- Predictions -------------

def save_feedback(prediction_id, user_id, rating, comment):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO feedback (prediction_id, user_id, rating, comment)
        VALUES (?, ?, ?, ?)
    """, (prediction_id, user_id, rating, comment))
    conn.commit()
    feedback_id = cur.lastrowid
    conn.close()
    return feedback_id

def get_feedback_for_prediction(prediction_id, user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM feedback
        WHERE prediction_id = ? AND user_id = ?
    """, (prediction_id, user_id))

    row = cur.fetchone()

    conn.close()
    return row

 # ------------- chat messages -------------
def save_chat_message(user_id, sender, message):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO chat_messages (user_id, sender, message)
        VALUES (?, ?, ?)
    """, (user_id, sender, message))
    conn.commit()
    msg_id = cur.lastrowid
    conn.close()
    return msg_id


def get_chat_history(user_id, limit=50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM chat_messages WHERE user_id = ?
        ORDER BY id ASC LIMIT ?
    """, (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def clear_chat_history(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
