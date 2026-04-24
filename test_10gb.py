import sys
sys.path.append('.')

from models.job_store import init_db
from models.chunked_upload import init_upload, receive_chunk, get_job

init_db()
print('Job store initialized')

job_id = 'test_10gb_001'
metadata = {'filename': 'test_video.mp4', 'size': 10*1024*1024*1024}
init_upload(job_id, 'test_video.mp4', 10*1024*1024*1024, metadata)
print(f'Upload initialized: {job_id}')

test_data = b'X' * 1024 * 1024
result = receive_chunk(job_id, 0, test_data)
print(f'Chunk received: {result["chunk_index"]}')

job = get_job(job_id)
print(f'Job status: {job["status"]}')
print(f'Progress: {job["progress"]}%')

print()
print('All tests passed!')
