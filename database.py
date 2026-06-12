import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Create Interviews table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            transcript TEXT NOT NULL,
            communication_score INTEGER NOT NULL,
            confidence_score INTEGER NOT NULL,
            grammar_score INTEGER NOT NULL,
            speaking_speed_score INTEGER NOT NULL,
            answer_quality_score INTEGER NOT NULL,
            overall_score INTEGER NOT NULL,
            speaking_speed INTEGER NOT NULL,
            filler_words TEXT NOT NULL,
            feedback TEXT NOT NULL,
            recommendations TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

# Users Table Queries
def create_user(name, email, password_hash):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
            (name, email, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_email(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    user = cursor.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    user = cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user

# Interviews Table Queries
def create_interview(user_id, file_name, transcript, comm_score, conf_score, gram_score, speed_score, quality_score, overall_score, speed_wpm, filler_words_json, feedback_json, recs_json):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO interviews (
            user_id, file_name, transcript, communication_score, confidence_score, 
            grammar_score, speaking_speed_score, answer_quality_score, overall_score, 
            speaking_speed, filler_words, feedback, recommendations
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, file_name, transcript, comm_score, conf_score, 
        gram_score, speed_score, quality_score, overall_score, 
        speed_wpm, filler_words_json, feedback_json, recs_json
    ))
    conn.commit()
    interview_id = cursor.lastrowid
    conn.close()
    return interview_id

def get_interviews_by_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    interviews = cursor.execute(
        'SELECT * FROM interviews WHERE user_id = ? ORDER BY created_at DESC', 
        (user_id,)
    ).fetchall()
    conn.close()
    return interviews

def get_interview_by_id(interview_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    interview = cursor.execute('SELECT * FROM interviews WHERE id = ?', (interview_id,)).fetchone()
    conn.close()
    return interview

def update_interview_results(interview_id, transcript, comm_score, conf_score, gram_score, speed_score, quality_score, overall_score, speed_wpm, filler_words_json, feedback_json, recs_json):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE interviews SET
            transcript = ?,
            communication_score = ?,
            confidence_score = ?,
            grammar_score = ?,
            speaking_speed_score = ?,
            answer_quality_score = ?,
            overall_score = ?,
            speaking_speed = ?,
            filler_words = ?,
            feedback = ?,
            recommendations = ?
        WHERE id = ?
    ''', (
        transcript, comm_score, conf_score, gram_score, speed_score, 
        quality_score, overall_score, speed_wpm, filler_words_json, 
        feedback_json, recs_json, interview_id
    ))
    conn.commit()
    conn.close()

def delete_interview(interview_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM interviews WHERE id = ? AND user_id = ?', (interview_id, user_id))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
