import requests
import os
import threading
import time
from werkzeug.serving import make_server
from main import app

class ServerThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self)
        self.server = make_server('127.0.0.1', 5001, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        print("Starting test server...")
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()
        print("Test server shutdown.")

def run_tests():
    base_url = "http://127.0.0.1:5001"

    # Test 1: Upload invalid music file extension
    try:
        with open('test_invalid.txt', 'w') as f:
            f.write("This is a text file")

        files = {'music': ('test_invalid.txt', open('test_invalid.txt', 'rb'), 'text/plain')}
        resp = requests.post(f"{base_url}/upload-music", files=files)
        assert resp.status_code == 400
        data = resp.json()
        assert not data['success']
        assert "Format file music tidak didukung" in data['error']
        print("✅ Test invalid music upload passed.")
    except Exception as e:
        print(f"❌ Test invalid music upload failed: {e}")
    finally:
        os.remove('test_invalid.txt')

    # Test 2: Upload valid music file extension
    try:
        with open('test_valid.mp3', 'wb') as f:
            f.write(b"fake mp3 data")

        files = {'music': ('test_valid.mp3', open('test_valid.mp3', 'rb'), 'audio/mpeg')}
        resp = requests.post(f"{base_url}/upload-music", files=files)
        # Note: it will fail eventually during upload-music logic or succeed returning a path depending on what exists, but we want to ensure it isn't blocked by the extension check.
        assert resp.status_code == 200
        data = resp.json()
        assert data['success']
        print("✅ Test valid music upload passed.")
    except Exception as e:
        print(f"❌ Test valid music upload failed: {e}")
    finally:
        os.remove('test_valid.mp3')


if __name__ == '__main__':
    server = ServerThread(app)
    server.start()
    time.sleep(2) # let the server start
    try:
        run_tests()
    finally:
        server.shutdown()
        server.join()
