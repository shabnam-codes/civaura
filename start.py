import threading
import time
import os
import sys

sys.path.append('/content/backend')

# ═══════════════════════════════════════════════
# STEP 1 — SET NGROK TOKEN
# ═══════════════════════════════════════════════
NGROK_TOKEN = "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"  # ← get from ngrok.com → free signup
os.system(f"ngrok authtoken {NGROK_TOKEN}")

# ═══════════════════════════════════════════════
# STEP 2 — START FLASK IN BACKGROUND
# ═══════════════════════════════════════════════
def run_flask():
    os.chdir('/content/backend')
    exec(open('/content/backend/app.py').read(), {'__name__': '__main__'})

print("⏳ Starting Flask server...")
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# Wait for Flask to boot
time.sleep(5)
print("✅ Flask running on port 5000")

# ═══════════════════════════════════════════════
# STEP 3 — START NGROK TUNNEL
# ═══════════════════════════════════════════════
from pyngrok import ngrok

public_url = ngrok.connect(5000)
url        = public_url.public_url

# ═══════════════════════════════════════════════
# STEP 4 — PRINT ALL URLS
# ═══════════════════════════════════════════════
print("\n" + "=" * 55)
print("✅ ALL SYSTEMS RUNNING")
print("=" * 55)

print(f"\n🌐 Public URL     : {url}")

print(f"\n📄 Pages:")
print(f"   Home           : {url}/")
print(f"   File Complaint : {url}/file-complaint")
print(f"   Track Status   : {url}/track-status")
print(f"   Result         : {url}/result")
print(f"   Feedback       : {url}/feedback")
print(f"   Dashboard      : {url}/dashboard")

print(f"\n🔌 API Endpoints:")
print(f"   POST  {url}/chat")
print(f"   POST  {url}/chat/submit")
print(f"   POST  {url}/predict")
print(f"   POST  {url}/route")

print(f"\n⏳ Coming after FAISS:")
print(f"   POST  {url}/autocomplete")
print(f"   POST  {url}/classify")
print(f"   POST  {url}/feedback/submit")

print("\n" + "=" * 55)
print("⚠️  Copy the Public URL → paste into script.js as API base")
print("=" * 55)