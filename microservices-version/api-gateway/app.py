"""
API Gateway
Routes requests to Video, Search, Auth, and Analytics services with proper CORS handling.
"""
from flask import Flask, request, jsonify
import requests
import os
from flask_cors import CORS
from dotenv import load_dotenv
import jwt
import datetime
import time

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
JWT_SECRET = os.getenv('JWT_SECRET')

# =====================
# CUSTOM CIRCUIT BREAKER
# =====================
class CircuitBreakerOpenException(Exception):
    pass

class SimpleCircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"

    def call(self, func):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenException("Circuit is open")

        try:
            result = func()
            # If we succeed in HALF_OPEN, reset
            if self.state == "HALF_OPEN":
                self.reset()
            return result
        except requests.exceptions.RequestException as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
            raise e
    
    def reset(self):
        self.failures = 0
        self.state = "CLOSED"

# Initialize Breakers
video_circuit = SimpleCircuitBreaker(failure_threshold=5, recovery_timeout=30)
search_circuit = SimpleCircuitBreaker(failure_threshold=5, recovery_timeout=30)
auth_circuit = SimpleCircuitBreaker(failure_threshold=5, recovery_timeout=30)
analytics_circuit = SimpleCircuitBreaker(failure_threshold=5, recovery_timeout=30)

# =====================
# UTIL: Forward headers
# =====================
def forward_headers():
    headers = {"Content-Type": request.headers.get('Content-Type', 'application/json')}
    auth_header = request.headers.get('Authorization')
    
    if auth_header:
        headers['Authorization'] = auth_header
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
        url = f"{VIDEO_SERVICE_URL}/api/v1/videos" + (f"/{video_id}" if video_id else "")
        
        def call_service():
            if request.method == 'GET':
                return requests.get(url, params=request.args if not video_id else None, headers=forward_headers())
            elif request.method == 'POST':
                return requests.post(url, json=request.json, headers=forward_headers())
            elif request.method == 'PUT':
                return requests.put(url, json=request.json, headers=forward_headers())
            else:  # DELETE
                return requests.delete(url, headers=forward_headers())

        resp = video_circuit.call(call_service)
        return jsonify(resp.json()), resp.status_code
    except CircuitBreakerOpenException:
        return jsonify({"error": "Video service temporarily unavailable", "fallback": True}), 503
    except requests.exceptions.RequestException:
        return jsonify({"error": "Video service unavailable"}), 503

# =====================
# USER VIDEO ROUTES
# =====================
@app.route('/api/v1/users/<int:user_id>/videos', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/v1/users/<int:user_id>/videos/<int:video_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def user_videos_proxy(user_id, video_id=None):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        url = f"{VIDEO_SERVICE_URL}/api/v1/videos" + (f"/{video_id}" if video_id else "")
        
        def call_service():
            if request.method == 'GET':
                return requests.get(url, params=request.args if not video_id else None, headers=forward_headers())
            elif request.method == 'POST':
                return requests.post(url, json=request.json, headers=forward_headers())
            elif request.method == 'PUT':
                return requests.put(url, json=request.json, headers=forward_headers())
            elif request.method == 'DELETE':
                return requests.delete(url, headers=forward_headers())
                
        resp = video_circuit.call(call_service)
        return jsonify(resp.json()), resp.status_code
    except CircuitBreakerOpenException:
        return jsonify({"error": "Video service temporarily unavailable", "fallback": True}), 503
    except requests.exceptions.RequestException:
        return jsonify({"error": "Video service unavailable"}), 503

# =====================
# SEARCH ROUTES
# =====================
@app.route('/api/v1/users/<int:user_id>/search', methods=['POST', 'OPTIONS'])
def user_search_proxy(user_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json(silent=True) or {}
        # Explicitly set BOTH casing styles to ensure Search Service catches it
        data['user_id'] = user_id
        data['userId'] = user_id 
        
        def call_service():
            return requests.post(
                f"{SEARCH_SERVICE_URL}/api/v1/search", 
                json=data, 
                headers=forward_headers()
            )
            
        resp = search_circuit.call(call_service)
        return jsonify(resp.json()), resp.status_code
    except CircuitBreakerOpenException:
        return jsonify({"error": "Search service temporarily unavailable", "results": []}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 503

@app.route('/api/v1/users/<int:user_id>/search/<job_id>', methods=['GET', 'OPTIONS'])
def user_search_results_proxy(user_id, job_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        def call_service():
            return requests.get(
                f"{SEARCH_SERVICE_URL}/api/v1/search/{job_id}", 
                headers=forward_headers()
            )
            
        resp = search_circuit.call(call_service)
        return jsonify(resp.json()), resp.status_code
    except CircuitBreakerOpenException:
        return jsonify({"error": "Search service temporarily unavailable", "status": "failed"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 503

@app.route('/api/v1/search', methods=['POST', 'OPTIONS'])
def search():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        def call_service():
            return requests.post(f"{SEARCH_SERVICE_URL}/api/v1/search", json=request.json, headers=forward_headers())
            
        resp = search_circuit.call(call_service)
        return jsonify(resp.json()), resp.status_code
    except CircuitBreakerOpenException:
        return jsonify({"error": "Search service temporarily unavailable", "results": []}), 503
    except requests.exceptions.RequestException:
        return jsonify({"error": "Search service unavailable"}), 503

@app.route('/api/v1/search/<job_id>', methods=['GET', 'OPTIONS'])
def search_results(job_id):
    if request.method == 'OPTIONS':
        return '', 200
    try:
        def call_service():
            return requests.get(f"{SEARCH_SERVICE_URL}/api/v1/search/{job_id}", headers=forward_headers())
            
        resp = search_circuit.call(call_service)
        return jsonify(resp.json()), resp.status_code
    except CircuitBreakerOpenException:
        return jsonify({"error": "Search service temporarily unavailable", "status": "failed"}), 503
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
        def call_service():
            if request.method == 'POST':
                return requests.post(url, json=request.json, headers=forward_headers())
            elif request.method == 'GET':
                return requests.get(url, headers=forward_headers(), params=request.args)
            else:  # DELETE
                return requests.delete(url, headers=forward_headers())
                
        resp = auth_circuit.call(call_service)
        return jsonify(resp.json()), resp.status_code
    except CircuitBreakerOpenException:
        return jsonify({"error": "Auth service temporarily unavailable"}), 503
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
        def call_service():
            return requests.get(f"{ANALYTICS_SERVICE_URL}/api/v1/analytics/overview", headers=forward_headers(), params=request.args)
            
        resp = analytics_circuit.call(call_service)
        return jsonify(resp.json()), resp.status_code
    except CircuitBreakerOpenException:
        return jsonify({"error": "Analytics service temporarily unavailable", "stats": {}}), 503
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
