"""
API Gateway
Routes requests to Video, Search, and Auth services
"""
from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# =====================
# SERVICE ENDPOINTS
# =====================
VIDEO_SERVICE_URL = os.getenv('VIDEO_SERVICE_URL', 'http://localhost:5003')
SEARCH_SERVICE_URL = os.getenv('SEARCH_SERVICE_URL', 'http://localhost:5001')
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://localhost:5002')

# =====================
# ROUTES
# =====================

@app.route('/api/videos', methods=['GET', 'POST'])
def videos():
    if request.method == 'GET':
        resp = requests.get(f"{VIDEO_SERVICE_URL}/api/videos", params=request.args)
    else:
        resp = requests.post(f"{VIDEO_SERVICE_URL}/api/videos", json=request.json)
    return jsonify(resp.json()), resp.status_code

@app.route('/api/videos/<int:video_id>', methods=['GET', 'PUT', 'DELETE'])
def video_detail(video_id):
    if request.method == 'GET':
        resp = requests.get(f"{VIDEO_SERVICE_URL}/api/videos/{video_id}")
    elif request.method == 'PUT':
        resp = requests.put(f"{VIDEO_SERVICE_URL}/api/videos/{video_id}", json=request.json)
    else:
        resp = requests.delete(f"{VIDEO_SERVICE_URL}/api/videos/{video_id}")
    return jsonify(resp.json()), resp.status_code

# Search proxy
@app.route('/api/search', methods=['POST'])
def search():
    resp = requests.post(f"{SEARCH_SERVICE_URL}/api/v1/search", json=request.json)
    return jsonify(resp.json()), resp.status_code

@app.route('/api/search/<job_id>', methods=['GET'])
def search_results(job_id):
    resp = requests.get(f"{SEARCH_SERVICE_URL}/api/v1/search/{job_id}")
    return jsonify(resp.json()), resp.status_code

# Auth proxy
@app.route('/api/auth/<path:path>', methods=['POST', 'GET', 'DELETE'])
def auth_proxy(path):
    url = f"{AUTH_SERVICE_URL}/api/v1/auth/{path}"
    if request.method == 'POST':
        resp = requests.post(url, json=request.json, headers=request.headers)
    elif request.method == 'GET':
        resp = requests.get(url, headers=request.headers, params=request.args)
    elif request.method == 'DELETE':
        resp = requests.delete(url, headers=request.headers)
    return jsonify(resp.json()), resp.status_code

# Health check for gateway
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
