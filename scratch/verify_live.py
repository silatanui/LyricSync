import urllib.request
import json

base_url = "http://127.0.0.1:5000"

# 1. Test templates endpoint
req = urllib.request.urlopen(f"{base_url}/api/projects/templates")
data = json.loads(req.read().decode())
print("1. Templates API:", data["success"], [t["id"] for t in data["templates"]])

# 2. Test switching background live on demo project
post_data = json.dumps({"template": "retrowave_sunset"}).encode()
req = urllib.request.Request(
    f"{base_url}/api/projects/proj_1a0bfea5480_56bc6c80/background",
    data=post_data,
    headers={"Content-Type": "application/json"}
)
res = urllib.request.urlopen(req)
data = json.loads(res.read().decode())
print("2. Switch to Retrowave Sunset:", data)

# 3. Switch back to burgundy_studio default
post_data = json.dumps({"template": "burgundy_studio"}).encode()
req = urllib.request.Request(
    f"{base_url}/api/projects/proj_1a0bfea5480_56bc6c80/background",
    data=post_data,
    headers={"Content-Type": "application/json"}
)
res = urllib.request.urlopen(req)
data = json.loads(res.read().decode())
print("3. Switch back to Burgundy Studio:", data)

# 4. Check upload page HTML contains template selector and NO math pattern
req = urllib.request.urlopen(f"{base_url}/upload")
html = req.read().decode()
assert "template-choice-card" in html, "Template cards missing in upload HTML"
assert "math_book" not in html and "mathematical" not in html.lower(), "Math pattern text still present in upload HTML!"
print("4. Upload Page verified: No math pattern, template cards present.")

# 5. Check editor page HTML contains theater and timeline toggles
req = urllib.request.urlopen(f"{base_url}/editor/proj_1a0bfea5480_56bc6c80")
html = req.read().decode()
assert "toggleTheaterBtn" in html, "Theater button missing in editor HTML"
assert "toggleTimelineBtn" in html, "Timeline toggle button missing in editor HTML"
assert "editorBackgroundTemplate" in html, "Background template dropdown missing in editor HTML"
print("5. Editor Page verified: Theater button, timeline toggle, and background switcher present.")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
