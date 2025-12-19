"""
API Gateway
Routes requests to Video, Search, Auth, and Analytics services with proper CORS handling.
"""
from flask import Flask, request, jsonify
import requests
import os
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# =====================
# CORS Setup
# =====================
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:3001"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# =====================
# SERVICE ENDPOINTS
# =====================
VIDEO_SERVICE_URL = os.getenv('VIDEO_SERVICE_URL', 'http://localhost:5003')
SEARCH_SERVICE_URL = os.getenv('SEARCH_SERVICE_URL', 'http://localhost:5001')
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://localhost:5002')
ANALYTICS_SERVICE_URL = os.getenv('ANALYTICS_SERVICE_URL', 'http://localhost:5004')

# =====================
# UTIL: Forward headers
# =====================
def forward_headers():
    """Forward only necessary headers to downstream services"""
    headers = {}
    if 'Authorization' in request.headers:
        headers['Authorization'] = request.headers['Authorization']
    headers['Content-Type'] = request.headers.get('Content-Type', 'application/json')
    return headers

# =====================
# VIDEO ROUTES
# =====================
@app.route('/api/v1/videos', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/v1/videos/<int:video_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def videos(video_id=None):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        url = f"{VIDEO_SERVICE_URL}/api/videos" + (f"/{video_id}" if video_id else "")
        if request.method == 'GET':
            resp = requests.get(url, params=request.args if not video_id else None, headers=forward_headers())
        elif request.method == 'POST':
            resp = requests.post(url, json=request.json, headers=forward_headers())
        elif request.method == 'PUT':
            resp = requests.put(url, json=request.json, headers=forward_headers())
        else:  # DELETE
            resp = requests.delete(url, headers=forward_headers())
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException:
        return jsonify({"error": "Video service unavailable"}), 503

@app.route('/api/v1/users/<int:user_id>/videos', methods=['GET', 'POST', 'OPTIONS'])
def user_videos(user_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        url = f"{VIDEO_SERVICE_URL}/api/users/{user_id}/videos"
        if request.method == 'GET':
            resp = requests.get(url, params=request.args, headers=forward_headers())
        else:  # POST
            resp = requests.post(url, json=request.json, headers=forward_headers())
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException:
        return jsonify({"error": "Video service unavailable"}), 503

@app.route('/api/v1/users/<int:user_id>/videos/<int:video_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def user_video_detail(user_id, video_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        url = f"{VIDEO_SERVICE_URL}/api/users/{user_id}/videos/{video_id}"
        if request.method == 'GET':
            resp = requests.get(url, headers=forward_headers())
        elif request.method == 'PUT':
            resp = requests.put(url, json=request.json, headers=forward_headers())
        else:  # DELETE
            resp = requests.delete(url, headers=forward_headers())
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException:
        return jsonify({"error": "Video service unavailable"}), 503

# =====================
# SEARCH ROUTES
# =====================
@app.route('/api/v1/search', methods=['POST', 'OPTIONS'])
def search():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        resp = requests.post(f"{SEARCH_SERVICE_URL}/api/v1/search", json=request.json, headers=forward_headers())
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException:
        return jsonify({"error": "Search service unavailable"}), 503

@app.route('/api/v1/search/<job_id>', methods=['GET', 'OPTIONS'])
def search_results(job_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        resp = requests.get(f"{SEARCH_SERVICE_URL}/api/v1/search/{job_id}", headers=forward_headers())
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException:
        return jsonify({"error": "Search service unavailable"}), 503

# =====================
# AUTH ROUTES
# =====================
@app.route('/api/v1/auth/<path:path>', methods=['GET', 'POST', 'DELETE', 'OPTIONS'])
def auth_proxy(path):
    if request.method == 'OPTIONS':
        return '', 200
    url = f"{AUTH_SERVICE_URL}/api/v1/auth/{path}"
    try:
        if request.method == 'POST':
            resp = requests.post(url, json=request.json, headers=forward_headers())
        elif request.method == 'GET':
            resp = requests.get(url, headers=forward_headers(), params=request.args)
        else:  # DELETE
            resp = requests.delete(url, headers=forward_headers())
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException:
        return jsonify({"error": "Auth service unavailable"}), 503

# =====================
# ANALYTICS ROUTES
# =====================
@app.route('/api/v1/analytics/overview', methods=['GET', 'OPTIONS'])
def analytics_overview():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        resp = requests.get(f"{ANALYTICS_SERVICE_URL}/api/v1/analytics/overview", headers=forward_headers(), params=request.args)
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException:
        return jsonify({"error": "Analytics service unavailable"}), 503

# =====================
# HEALTH CHECK
# =====================
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status':'healthy','service':'api-gateway'}), 200

# =====================
# RUN
# =====================
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 API Gateway running on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
