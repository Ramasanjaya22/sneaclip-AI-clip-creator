import os
import json
import time

from models.job_store import (
    init_db, create_job, update_job, get_job, add_chunk, 
    get_chunks, get_total_received, transition_job
)

CHUNK_DIR = os.path.abspath("./static/uploads/.chunks")
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024


def init_upload(upload_id, filename, file_size, metadata=None):
    os.makedirs(CHUNK_DIR, exist_ok=True)
    
    upload_metadata = {
        "filename": filename,
        "original_size": file_size,
        "chunks_received": [],
        "started_at": time.time()
    }
    if metadata:
        upload_metadata.update(metadata)
    
    create_job(upload_id, upload_metadata)
    transition_job(upload_id, 'UPLOADING', f"Upload started: {filename}")
    
    return upload_id


def receive_chunk(upload_id, chunk_index, chunk_data):
    job = get_job(upload_id)
    if not job:
        raise ValueError(f"Upload {upload_id} not found")
    
    if job['status'] not in ['INIT', 'UPLOADING']:
        raise ValueError(f"Upload {upload_id} is in invalid state: {job['status']}")
    
    chunk_dir = os.path.join(CHUNK_DIR, upload_id)
    os.makedirs(chunk_dir, exist_ok=True)
    
    chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index:06d}")
    offset = 0
    
    with open(chunk_path, 'wb') as f:
        if chunk_data:
            f.write(chunk_data)
            offset = len(chunk_data)
    
    add_chunk(upload_id, chunk_index, offset, len(chunk_data))
    
    total_received = get_total_received(upload_id)
    metadata = job.get('metadata', {})
    file_size = metadata.get('original_size', 0)
    
    if file_size > 0:
        progress = min(10, (total_received / file_size) * 10)
        update_job(upload_id, progress=progress)
    
    return {
        "upload_id": upload_id,
        "chunk_index": chunk_index,
        "total_received": total_received,
        "progress": progress if file_size > 0 else 0
    }


def finalize_upload(upload_id):
    job = get_job(upload_id)
    if not job:
        raise ValueError(f"Upload {upload_id} not found")
    
    chunk_dir = os.path.join(CHUNK_DIR, upload_id)
    if not os.path.exists(chunk_dir):
        raise ValueError(f"No chunks found for upload {upload_id}")
    
    chunks = sorted(os.listdir(chunk_dir))
    if not chunks:
        raise ValueError(f"No chunks found for upload {upload_id}")
    
    metadata = job.get('metadata', {})
    filename = metadata.get('filename', 'video.mp4')
    final_path = os.path.join(os.path.dirname(CHUNK_DIR), filename)
    
    with open(final_path, 'wb') as outfile:
        for chunk_name in chunks:
            chunk_path = os.path.join(chunk_dir, chunk_name)
            with open(chunk_path, 'rb') as infile:
                while True:
                    data = infile.read(1024 * 1024)
                    if not data:
                        break
                    outfile.write(data)
    
    for chunk_name in chunks:
        os.remove(os.path.join(chunk_dir, chunk_name))
    os.rmdir(chunk_dir)
    
    file_size = os.path.getsize(final_path)
    transition_job(upload_id, 'VALIDATING', f"Upload complete: {filename}", progress=15)
    
    return {
        "upload_id": upload_id,
        "final_path": final_path,
        "file_size": file_size,
        "status": "VALIDATING"
    }


def get_upload_status(upload_id):
    return get_job(upload_id)


def cleanup_failed_uploads(max_age_hours=24):
    from models.job_store import cleanup_old_jobs
    cleanup_old_jobs(max_age_hours)
    
    for item in os.listdir(CHUNK_DIR):
        item_path = os.path.join(CHUNK_DIR, item)
        if os.path.isdir(item_path):
            job = get_job(item)
            if not job or job.get('status') == 'FAILED':
                import shutil
                shutil.rmtree(item_path, ignore_errors=True)
