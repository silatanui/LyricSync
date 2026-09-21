import urllib.request
import json
import time

with open('data/media/proj_1a0bff6f5b5_5fe7fc66/master_audio.mp3', 'rb') as f:
    audio_data = f.read()

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
lines = [
    f'--{boundary}'.encode('utf-8'),
    b'Content-Disposition: form-data; name="name"',
    b'',
    b'Test Upload Speed Project',
    f'--{boundary}'.encode('utf-8'),
    b'Content-Disposition: form-data; name="audio"; filename="vocal_song.mp3"',
    b'Content-Type: audio/mpeg',
    b'',
    audio_data,
    f'--{boundary}--'.encode('utf-8'),
    b''
]
body = b'\r\n'.join(lines)

req = urllib.request.Request(
    'http://127.0.0.1:5000/api/projects',
    data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)

t0 = time.time()
resp = urllib.request.urlopen(req)
t1 = time.time()
print('Status:', resp.status)
print('Total time taken:', round(t1 - t0, 2), 'seconds!')
data = json.loads(resp.read().decode('utf-8'))
print('Project ID:', data['project']['id'])
print('Status:', data['project']['status'])
