import urllib.request
import json
import time

project_id = 'proj_1a0c01b574c_be8ad532'

print(f"Triggering transcription for {project_id}...")
req = urllib.request.Request(
    f'http://127.0.0.1:5000/api/projects/{project_id}/transcribe',
    data=b'{}',
    headers={'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read().decode('utf-8'))
print("Trigger response:", data)
job_id = data['job_id']

t0 = time.time()
for i in range(40):
    time.sleep(1)
    status_req = urllib.request.urlopen(f'http://127.0.0.1:5000/api/jobs/{job_id}')
    res = json.loads(status_req.read().decode('utf-8'))
    j = res.get('job', {})
    print(f"[{round(time.time() - t0, 1)}s] Job {job_id}: status={j.get('status')}, progress={j.get('progress')}%, stage={j.get('stage')}")
    if j.get('status') in ('completed', 'failed'):
        if j.get('status') == 'failed':
            print("Failed with error:", j.get('error_message'))
        break

# Verify canonical lyrics
lyrics_req = urllib.request.urlopen(f'http://127.0.0.1:5000/api/projects/{project_id}/lyrics')
lyr_data = json.loads(lyrics_req.read().decode('utf-8'))
print("Final lyrics count:", len(lyr_data.get('lyrics', [])))
if lyr_data.get('lyrics'):
    print("Line 1 words:", len(lyr_data['lyrics'][0].get('words', [])))
