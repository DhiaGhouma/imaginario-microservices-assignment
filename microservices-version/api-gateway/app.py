"""
API Gateway
Routes requests to Video, Search, and Auth services with proper CORS handling.
"""
from flask import Flask, request, jsonify, make_response
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
# ROUTES
# =====================
# ANALYTICS ENDPOINTS (For Developer Dashboard)

@app.route('/api/v1/analytics/overview', methods=['GET'])
@require_auth
def analytics_overview(current_user):
    """Get analytics overview for current user"""
    user_id = current_user.id
    
    user_requests = [r for r in api_requests_log if r['user_id'] == user_id]
    
    total_requests = len(user_requests)
    success_count = len([r for r in user_requests if 200 <= r['status_code'] < 300])
    success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
    
    avg_response_time = sum(r['response_time'] for r in user_requests) / max(total_requests, 1)
    
    endpoint_counts = {}
    for r in user_requests:
        endpoint = r['endpoint']
        endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
    
    return jsonify({
        'total_requests': total_requests,
        'success_rate': round(success_rate, 2),
        'avg_response_time': round(avg_response_time, 4),
        'requests_by_endpoint': endpoint_counts
    })

@app.route('/api/v1/analytics/timeline', methods=['GET'])
@require_auth
def analytics_timeline(current_user):
    """Get request timeline data"""
    user_id = current_user.id
    days = int(request.args.get('days', 7))
    
    user_requests = [r for r in api_requests_log if r['user_id'] == user_id]
    
    from collections import defaultdict
    daily_counts = defaultdict(int)
    
    for r in user_requests:
        date = r['timestamp'][:10]
        daily_counts[date] += 1
    
    timeline = [{'date': date, 'count': count} 
                for date, count in sorted(daily_counts.items())]
    
    return jsonify({'timeline': timeline[-days:]})

@app.route('/api/v1/analytics/api-keys', methods=['GET'])
@require_auth
def analytics_api_keys(current_user):
    """Get usage statistics per API key"""
    user_id = current_user.id
    
    api_keys = APIKey.query.filter_by(user_id=user_id, is_active=True).all()
    
    key_usage = {}
    for key in api_keys:
        key_requests = [r for r in api_requests_log if r['api_key_id'] == key.id]
        key_usage[key.id] = {
            'key_id': key.id,
            'name': key.name,
            'total_requests': len(key_requests),
            'success_count': len([r for r in key_requests if 200 <= r['status_code'] < 300])
        }
    
    return jsonify({'api_keys': list(key_usage.values())})
# Videos
@app.route('/api/v1/videos', methods=['GET', 'POST', 'OPTIONS'])
def videos():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if request.method == 'GET':
            resp = requests.get(f"{VIDEO_SERVICE_URL}/api/videos", params=request.args, headers=forward_headers())
        else:
            resp = requests.post(f"{VIDEO_SERVICE_URL}/api/videos", json=request.json, headers=forward_headers())
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException:
        return jsonify({"error": "Video service unavailable"}), 503

@app.route('/api/v1/videos/<int:video_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def video_detail(video_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        if request.method == 'GET':
            resp = requests.get(f"{VIDEO_SERVICE_URL}/api/videos/{video_id}", headers=forward_headers())
        elif request.method == 'PUT':
            resp = requests.put(f"{VIDEO_SERVICE_URL}/api/videos/{video_id}", json=request.json, headers=forward_headers())
        else:
            resp = requests.delete(f"{VIDEO_SERVICE_URL}/api/videos/{video_id}", headers=forward_headers())
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException:
        return jsonify({"error": "Video service unavailable"}), 503

# Search
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

# Auth
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
        elif request.method == 'DELETE':
            resp = requests.delete(url, headers=forward_headers())
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException:
        return jsonify({"error": "Auth service unavailable"}), 503

# Health check
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
