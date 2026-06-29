import sqlite3

DB_FILE = "lecture_lens.db"


def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # 1. Caching table for split chunks to track progress
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunk_cache (
                lecture_id TEXT,
                chunk_index INTEGER,
                file_path TEXT,
                status TEXT, -- 'pending', 'processing', 'completed'
                transcript TEXT,
                PRIMARY KEY (lecture_id, chunk_index)
            )
        """)

        # 2. Main structured output storage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lecture_results (
                lecture_id TEXT PRIMARY KEY,
                lecture_name TEXT,
                full_transcript TEXT,
                structured_json TEXT, -- Core study objects stored here
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def save_chunk_transcript(lecture_id, chunk_idx, text):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE chunk_cache 
            SET transcript = ?, status = 'completed'
            WHERE lecture_id = ? AND chunk_index = ?
        """,
            (text, lecture_id, chunk_idx),
        )
        conn.commit()


def get_lecture_progress(lecture_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM chunk_cache WHERE lecture_id = ?", (lecture_id,)
        )
        rows = cursor.fetchall()
        if not rows:
            return 0.0
        completed = sum(1 for r in rows if r[0] == "completed")
        return (completed / len(rows)) * 100
