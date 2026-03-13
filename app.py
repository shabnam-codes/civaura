from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from groq import Groq
import json
import os
import random
import string
import sys
import pickle
import numpy as np

sys.path.append('/content/drive/MyDrive/Hackathon/BackEnd')

# ═══════════════════════════════════════════════
# FLASK SETUP
# ═══════════════════════════════════════════════
app = Flask(__name__, template_folder='/content/drive/MyDrive/Hackathon/templates', static_folder='/content/drive/MyDrive/Hackathon/static', static_url_path='/static')
CORS(app)

# ═══════════════════════════════════════════════
# GROQ SETUP
# ═══════════════════════════════════════════════
GROQ_KEY = "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"
client   = Groq(api_key=GROQ_KEY)

def ask_groq(prompt, max_tokens=200, temperature=0.1):
    try:
        response = client.chat.completions.create(
            model       = "llama-3.1-8b-instant",
            messages    = [{"role": "user", "content": prompt}],
            max_tokens  = max_tokens,
            temperature = temperature
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ Groq error: {e}")
        return ""

# ═══════════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════════
print("⏳ Loading data_loader...")
try:
    exec(open('/content/drive/MyDrive/Hackathon/BackEnd/data_loader.py').read())
    print("✅ Data loaded successfully")
except Exception as e:
    print(f"⚠️ Error loading data_loader: {e}")
    # Set defaults if data_loader fails
    org_list = ['GENERAL_DEPT']
    category_list = [['0', 'Uncategorized']]
    
    def get_resolution_days(category_code, org_code):
        return 7
    
    def get_routing(category_code, org_code):
        return 'GENERAL_DEPT'

# ═══════════════════════════════════════════════
# PAGE ROUTES
# ═══════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/file-complaint')
def file_complaint():
    return render_template('chat.html')

@app.route('/track-status')
def track_status():
    return render_template('track-status.html')

@app.route('/result')
def result():
    return render_template('result.html')

@app.route('/feedback')
def feedback():
    return render_template('feedback.html')

@app.route('/chat')
def chat_page():
    return render_template('chat.html')

# ═══════════════════════════════════════════════
# FEATURE 5 — CONVERSATIONAL FILING BOT
# ═══════════════════════════════════════════════

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Input  : { "messages": [ {"role": "user"|"assistant", "content": "..."} ] }
    Output : { "reply", "collected_data", "is_complete" }
    """
    try:
        messages = request.json.get('messages', [])
        history  = "\n".join([
            f"{m['role']}: {m['content']}"
            for m in messages
        ])

        # Count user messages
        user_msgs = [m for m in messages if m['role'] == 'user']
        num_user  = len(user_msgs)

        prompt = f"""
You are a grievance filing assistant. Collect exactly 3 details:
1. Problem description
2. District and pincode
3. Duration

STRICT RULES:
- Ask ONE question at a time
- Message 1 from user = problem description = ALREADY COLLECTED
- Message 2 from user = location = ALREADY COLLECTED
- Message 3 from user = duration = ALREADY COLLECTED
- If you have all 3 → IMMEDIATELY end with [COMPLETE]
- Do NOT ask clarifying questions
- Keep replies under 1 sentence

Current status:
- Problem : {user_msgs[0]['content'] if len(user_msgs) > 0 else 'NOT YET'}
- Location: {user_msgs[1]['content'] if len(user_msgs) > 1 else 'NOT YET'}
- Duration: {user_msgs[2]['content'] if len(user_msgs) > 2 else 'NOT YET'}

If num_user >= 3: reply with "Thank you! I have all the details." and add [COMPLETE] at end.
If num_user == 2: ask ONLY "How long has this been happening?"
If num_user == 1: ask ONLY "Which district and pincode?"
If num_user == 0: ask ONLY "What is your problem?"

Conversation:
{history}
assistant:"""

        reply       = ask_groq(prompt, max_tokens=150, temperature=0.7)
        is_complete = '[COMPLETE]' in reply
        collected   = {}

        if is_complete:
            reply = reply.split('[COMPLETE]')[0].strip()
            if len(user_msgs) >= 3:
                collected = {
                    "description": user_msgs[0]['content'],
                    "location": user_msgs[1]['content'],
                    "duration": user_msgs[2]['content'],
                    "history": history
                }

        return jsonify({
            "reply"         : reply,
            "collected_data": collected,
            "is_complete"   : is_complete
        })

    except Exception as e:
        print(f"⚠️ Chat error: {e}")
        return jsonify({
            "reply"         : "Sorry I could not process that. Please try again.",
            "collected_data": {},
            "is_complete"   : False
        })

# ═══════════════════════════════════════════════
# FEATURE 5 — CHAT SUBMIT
# ═══════════════════════════════════════════════

@app.route('/api/chat/submit', methods=['POST'])
def chat_submit():
    """
    Input  : { "collected_data": { ... } }
    Output : { "registration_no", "status" }
    """
    try:
        reg_no = (
            'GRIEV/'
            + ''.join(random.choices(string.ascii_uppercase, k=2))
            + '/'
            + ''.join(random.choices(string.digits, k=7))
        )
        return jsonify({
            "registration_no": reg_no,
            "status"         : "Successfully Submitted ✅"
        }), 200
    except Exception as e:
        print(f"⚠️ Submit error: {e}")
        return jsonify({"error": str(e)}), 500

# ═══════════════════════════════════════════════
# FEATURE 3 — PREDICT RESOLVING TIMES
# ═══════════════════════════════════════════════

@app.route('/api/predict', methods=['POST'])
def predict():
    """
    Input  : { "category_code": 11578, "org_code": "MORLY" }
    Output : { "estimated_days", "range", "confidence_band" }
    """
    try:
        category_code = request.json.get('category_code', 0)
        org_code      = request.json.get('org_code', org_list[0] if org_list else 'GENERAL_DEPT')
        days          = get_resolution_days(category_code, org_code)

        if days <= 3:
            band = "High certainty"
        elif days <= 10:
            band = "Medium certainty"
        else:
            band = "Low certainty"

        return jsonify({
            "estimated_days" : days,
            "range"          : f"{max(1, days - 1)}–{days + 2} days",
            "confidence_band": band
        }), 200

    except Exception as e:
        print(f"⚠️ Predict error: {e}")
        return jsonify({
            "estimated_days" : 7,
            "range"          : "5–9 days",
            "confidence_band": "Medium certainty"
        }), 200

# ═══════════════════════════════════════════════
# ROUTING
# ═══════════════════════════════════════════════

@app.route('/api/route', methods=['POST'])
def route():
    """
    Input  : { "category_code": 11578, "org_code": "MORLY" }
    Output : { "assigned_to", "queue_depth", "avg_resolution" }
    """
    try:
        category_code = request.json.get('category_code', 0)
        org_code      = request.json.get('org_code', '')
        dest          = get_routing(category_code, org_code)

        return jsonify({
            "assigned_to"    : dest,
            "queue_depth"    : random.randint(2, 8),
            "avg_resolution" : "3–5 days"
        }), 200

    except Exception as e:
        print(f"⚠️ Route error: {e}")
        return jsonify({
            "assigned_to"    : "GENERAL_DEPT",
            "queue_depth"    : 5,
            "avg_resolution" : "5–7 days"
        }), 200

# ═══════════════════════════════════════════════
# FEATURE 2 — SMART AUTOCOMPLETE
# ═══════════════════════════════════════════════

@app.route('/api/autocomplete', methods=['POST'])
def autocomplete():
    """
    Input  : { "query": "water supply" }
    Output : { "suggestions": [ {"code": 11578, "description": "..."}, ... ] }
    """
    try:
        from sentence_transformers import SentenceTransformer
        import faiss

        query = request.json.get('query', '').strip()
        if not query or len(query) < 2:
            return jsonify({"suggestions": []}), 200

        # Load FAISS index and metadata
        embedder = SentenceTransformer('all-MiniLM-L6-v2')
        index    = faiss.read_index('/content/drive/MyDrive/Hackathon/Data/faiss.index')

        with open('/content/drive/MyDrive/Hackathon/Data/category_meta.pkl', 'rb') as f:
            meta = pickle.load(f)

        # Encode query and search
        vec  = embedder.encode([query]).astype('float32')
        D, I = index.search(vec, 5)

        # Format results
        results = []
        for i in I[0]:
            if i < len(meta['descriptions']):
                results.append({
                    "code": int(meta['codes'][i]),
                    "description": meta['descriptions'][i]
                })

        return jsonify({"suggestions": results}), 200

    except Exception as e:
        print(f"⚠️ Autocomplete error: {e}")
        return jsonify({"suggestions": [], "error": str(e)}), 500

# ═══════════════════════════════════════════════
# FEATURE 1 — CLASSIFY + CONFIDENCE THRESHOLDING
# ═══════════════════════════════════════════════

@app.route('/api/classify', methods=['POST'])
def classify():
    """
    Input  : { "complaint_text": "...", "category_code": 11578 }
    Output : { "category_code", "category_name", "department", "priority", "confidence", "needs_review" }
    """
    try:
        text = request.json.get('complaint_text', '').strip()
        if not text:
            return jsonify({"error": "No complaint text"}), 400

        # Get sample categories for context
        sample = category_list[:20] if category_list else [['0', 'Uncategorized']]

        prompt = f"""
You are classifying Indian citizen grievances.
Return ONLY a valid JSON object. No explanation, no markdown.

{{
  "category_code" : <integer>,
  "category_name" : "<category name>",
  "department"    : "<department name>",
  "priority"      : "<Low|Medium|High|Critical>",
  "confidence"    : <float 0.0-1.0>
}}

Priority rules:
- Critical : health emergency, safety hazard, water contamination
- High     : no water supply, road blocked, power outage
- Medium   : delayed service, potholes, minor issues
- Low      : general inquiries, information requests

Complaint: "{text}"
Sample categories: {sample}

Return ONLY the JSON object, nothing else:
"""
        
        raw = ask_groq(prompt, max_tokens=300, temperature=0.3)
        
        # Extract JSON from response
        try:
            start = raw.find('{')
            end   = raw.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(raw[start:end])
            else:
                raise ValueError("No JSON found in response")
        except json.JSONDecodeError:
            # Fallback result
            result = {
                "category_code": 0,
                "category_name": "Uncategorized",
                "department": "General",
                "priority": "Medium",
                "confidence": 0.5
            }
        
        # Apply confidence thresholding
        confidence = float(result.get('confidence', 0.5))
        result['needs_review'] = confidence < 0.85

        return jsonify(result), 200

    except Exception as e:
        print(f"⚠️ Classify error: {e}")
        return jsonify({
            "category_code": 0,
            "category_name": "Uncategorized",
            "department": "General",
            "priority": "Medium",
            "confidence": 0.5,
            "needs_review": True,
            "error": str(e)
        }), 500

# ═══════════════════════════════════════════════
# FEATURE 4 — FEEDBACK SYSTEM
# ═══════════════════════════════════════════════

# In-memory feedback storage (for demo)
feedback_storage = []

@app.route('/api/feedback/submit', methods=['POST'])
def feedback_submit():
    """
    Input  : { "registration_no": "GRIEV/XX/1234567", "rating": 4, "text": "Good service" }
    Output : { "sentiment", "score", "flagged", "feedback_id" }
    """
    try:
        rating = request.json.get('rating', 3)
        text   = request.json.get('text', '')
        registration_no = request.json.get('registration_no', '')
        
        if not (1 <= rating <= 5):
            return jsonify({"error": "Rating must be 1-5"}), 400

        prompt = f"""Analyze this citizen feedback. Return ONLY JSON, nothing else.
{{"sentiment":"<Positive|Neutral|Negative>","score":<1-5>}}
Rating: {rating}/5
Text: "{text}"
JSON:"""
        
        raw = ask_groq(prompt, max_tokens=100, temperature=0.3)
        
        try:
            start = raw.find('{')
            end   = raw.rfind('}') + 1
            result = json.loads(raw[start:end])
        except:
            # Fallback based on rating
            if rating <= 2:
                result = {"sentiment": "Negative", "score": rating}
            elif rating <= 3:
                result = {"sentiment": "Neutral", "score": rating}
            else:
                result = {"sentiment": "Positive", "score": rating}
        
        # Apply flagging logic
        is_flagged = int(rating) < 3 or result.get('sentiment') == 'Negative'
        
        feedback_id = 'FB/' + ''.join(random.choices(string.digits, k=10))
        
        # Store feedback
        feedback_storage.append({
            'feedback_id': feedback_id,
            'registration_no': registration_no,
            'rating': rating,
            'text': text,
            'sentiment': result.get('sentiment', 'Neutral'),
            'score': result.get('score', 3),
            'flagged': is_flagged
        })
        
        return jsonify({
            "sentiment": result.get('sentiment', 'Neutral'),
            "score": result.get('score', 3),
            "flagged": is_flagged,
            "registration_no": registration_no,
            "feedback_id": feedback_id
        }), 200

    except Exception as e:
        print(f"⚠️ Feedback submit error: {e}")
        return jsonify({
            "sentiment": "Neutral",
            "score": 3,
            "flagged": False,
            "error": str(e)
        }), 500

@app.route('/api/feedback/summary', methods=['GET'])
def feedback_summary():
    """
    Output : { "avg_rating", "total_responses", "sentiment_breakdown" }
    """
    try:
        if not feedback_storage:
            return jsonify({
                "avg_rating": 0,
                "total_responses": 0,
                "sentiment_breakdown": {"Positive": 0, "Neutral": 0, "Negative": 0}
            }), 200

        total = len(feedback_storage)
        avg_rating = sum([f['rating'] for f in feedback_storage]) / total

        sentiment_counts = {
            'Positive': len([f for f in feedback_storage if f.get('sentiment') == 'Positive']),
            'Neutral': len([f for f in feedback_storage if f.get('sentiment') == 'Neutral']),
            'Negative': len([f for f in feedback_storage if f.get('sentiment') == 'Negative'])
        }

        return jsonify({
            "avg_rating": round(avg_rating, 2),
            "total_responses": total,
            "sentiment_breakdown": sentiment_counts
        }), 200

    except Exception as e:
        print(f"⚠️ Feedback summary error: {e}")
        return jsonify({
            "avg_rating": 0,
            "total_responses": 0,
            "sentiment_breakdown": {},
            "error": str(e)
        }), 500

# ═══════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("✅ CivAura API Server Starting")
    print("=" * 50)
    print("📁 Template folder: /content/drive/MyDrive/Hackathon/templates")
    print("📁 Static folder: /content/drive/MyDrive/Hackathon/static")
    print("=" * 50 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
