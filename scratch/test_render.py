import urllib.request
import json
import time

req = urllib.request.Request(
    'http://127.0.0.1:5000/api/projects/proj_1a0bfea5480_56bc6c80/render',
    data=json.dumps({'aspect_ratio': '16:9'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req)
data = json.loads(resp.read().decode('utf-8'))
print('Queue response:', data)
job_id = data['job_id']

for _ in range(25):
    time.sleep(1)
    status_req = urllib.request.urlopen(f'http://127.0.0.1:5000/api/jobs/{job_id}')
    res = json.loads(status_req.read().decode('utf-8'))
    j = res.get('job', {})
    print(f"Job {job_id}: status={j.get('status')}, progress={j.get('progress')}%, stage={j.get('stage')}")
    if j.get('status') in ('completed', 'failed'):
        if j.get('status') == 'failed':
            print("Error message:", j.get('error_message'))
        break
