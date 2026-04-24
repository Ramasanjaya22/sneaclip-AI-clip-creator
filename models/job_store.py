import sqlite3
import json
import time
import os

DB_PATH = os.path.abspath("./jobs.db")

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'INIT',
            progress REAL DEFAULT 0.0,
            message TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}',
            result TEXT DEFAULT '',
            error TEXT DEFAULT '',
            created_at REAL,
            updated_at REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS job_chunks (
            job_id TEXT,
            chunk_index INTEGER,
            offset INTEGER,
            size INTEGER,
            received_at REAL,
            PRIMARY KEY (job_id, chunk_index)
        )
    """)
    conn.commit()
    return conn


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def create_job(job_id, metadata=None):
    conn = get_connection()
    now = time.time()
    conn.execute("""
        INSERT OR REPLACE INTO jobs (job_id, status, progress, metadata, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (job_id, 'INIT', 0.0, json.dumps(metadata or {}), now, now))
    conn.commit()
    conn.close()
    return job_id


def update_job(job_id, status=None, progress=None, message=None, result=None, error=None, metadata=None):
    conn = get_connection()
    now = time.time()
    
    updates = ["updated_at = ?"]
    params = [now]
    
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if progress is not None:
        updates.append("progress = ?")
        params.append(progress)
    if message is not None:
        updates.append("message = ?")
        params.append(message)
    if result is not None:
        updates.append("result = ?")
        params.append(json.dumps(result))
    if error is not None:
        updates.append("error = ?")
        params.append(error)
    if metadata is not None:
        updates.append("metadata = ?")
        params.append(json.dumps(metadata))
    
    params.append(job_id)
    conn.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?", params)
    conn.commit()
    conn.close()


def get_job(job_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT job_id, status, progress, message, metadata, result, error, created_at, updated_at
        FROM jobs WHERE job_id = ?
    """, (job_id,)).fetchone()
    conn.close()
    
    if row:
        return {
            "job_id": row[0],
            "status": row[1],
            "progress": row[2],
            "message": row[3],
            "metadata": json.loads(row[4]) if row[4] else {},
            "result": json.loads(row[5]) if row[5] else None,
            "error": row[6],
            "created_at": row[7],
            "updated_at": row[8]
        }
    return None


def get_all_jobs():
    conn = get_connection()
    rows = conn.execute("""
        SELECT job_id, status, progress, message, created_at
        FROM jobs ORDER BY created_at DESC LIMIT 100
    """).fetchall()
    conn.close()
    
    return [{
        "job_id": r[0],
        "status": r[1],
        "progress": r[2],
        "message": r[3],
        "created_at": r[4]
    } for r in rows]


def add_chunk(job_id, chunk_index, offset, size):
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO job_chunks (job_id, chunk_index, offset, size, received_at)
        VALUES (?, ?, ?, ?, ?)
    """, (job_id, chunk_index, offset, size, time.time()))
    conn.commit()
    conn.close()


def get_chunks(job_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT chunk_index, offset, size FROM job_chunks
        WHERE job_id = ? ORDER BY chunk_index
    """, (job_id,)).fetchall()
    conn.close()
    
    return [{"index": r[0], "offset": r[1], "size": r[2]} for r in rows]


def get_total_received(job_id):
    conn = get_connection()
    row = conn.execute("""
        SELECT SUM(size) FROM job_chunks WHERE job_id = ?
    """, (job_id,)).fetchone()
    conn.close()
    return row[0] if row and row[0] else 0


JOB_STATES = [
    'INIT', 'UPLOADING', 'VALIDATING', 'SEGMENTING_AUDIO',
    'ANALYZING_FRAME_STREAM', 'TRIMMING_OUTPUT', 'COMPLETE', 'FAILED'
]


def transition_job(job_id, new_status, message=None, progress=None):
    job = get_job(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    if new_status not in JOB_STATES:
        raise ValueError(f"Invalid state: {new_status}")
    
    if progress is None:
        state_progress = {
            'INIT': 0, 'UPLOADING': 10, 'VALIDATING': 20,
            'SEGMENTING_AUDIO': 40, 'ANALYZING_FRAME_STREAM': 60,
            'TRIMMING_OUTPUT': 80, 'COMPLETE': 100,
            'FAILED': job.get('progress', 0)
        }
        progress = state_progress.get(new_status, 0)
    
    update_job(
        job_id,
        status=new_status,
        progress=progress,
        message=message or f"Transitioned to {new_status}"
    )
    
    return get_job(job_id)


def cleanup_old_jobs(max_age_hours=24):
    conn = get_connection()
    cutoff = time.time() - (max_age_hours * 3600)
    conn.execute("DELETE FROM jobs WHERE updated_at < ?", (cutoff,))
    conn.execute("""
        DELETE FROM job_chunks 
        WHERE job_id NOT IN (SELECT job_id FROM jobs)
    """)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    job_id = "test_123"
    create_job(job_id, {"filename": "test.mp4", "size": 1000000})
    transition_job(job_id, "UPLOADING", "Uploading...")
    print(get_job(job_id))
    print("DB initialized and tested.")
