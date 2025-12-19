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
from flasgger import Swagger

load_dotenv()

app = Flask(__name__)
Swagger(app)

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
# AUTHENTICATION HELPER
# =====================
def validate_user_access(requested_user_id):
    """
    Validate that authenticated user matches requested user_id
    Returns: (is_valid, error_response)
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return False, (jsonify({'error': 'Unauthorized - No token provided'}), 401)
    
    token = auth_header[7:]  
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        authenticated_user_id = payload.get('user_id')
        
        if authenticated_user_id != requested_user_id:
            return False, (jsonify({'error': 'Forbidden - Cannot access other user\'s data'}), 403)
        
        return True, None  
        
    except jwt.ExpiredSignatureError:
        return False, (jsonify({'error': 'Token expired'}), 401)
    except jwt.InvalidTokenError:
        return False, (jsonify({'error': 'Invalid token'}), 401)
    except Exception as e:
        return False, (jsonify({'error': 'Authentication failed'}), 401)

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
# VIDEO ROUTES (No user validation - direct service access)
# =====================
@app.route('/api/v1/videos', methods=['GET', 'POST', 'OPTIONS'])
def videos_collection():
    """
    Proxy to Video Service (Collection)
    ---
    parameters:
      - name: body
        in: body
        required: false
        schema:
          type: object
    responses:
      200:
        description: Success
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        url = f"{VIDEO_SERVICE_URL}/api/v1/videos"
        
        def call_service():
            if request.method == 'GET':
                return requests.get(url, params=request.args, headers=forward_headers())
            elif request.method == 'POST':
                return requests.post(url, json=request.json, headers=forward_headers())

        resp = video_circuit.call(call_service)
        return jsonify(resp.json()), resp.status_code
    except CircuitBreakerOpenException:
        return jsonify({"error": "Video service temporarily unavailable", "fallback": True}), 503
    except requests.exceptions.RequestException:
        return jsonify({"error": "Video service unavailable"}), 503


@app.route('/api/v1/videos/<int:video_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def videos_item(video_id):
    """
    Proxy to Video Service (Item)
    ---
    parameters:
      - name: video_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Success
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        url = f"{VIDEO_SERVICE_URL}/api/v1/videos/{video_id}"
        
        def call_service():
            if request.method == 'GET':
                return requests.get(url, headers=forward_headers())
            elif request.method == 'PUT':
                return requests.put(url, json=request.json, headers=forward_headers())
            else: 
                return requests.delete(url, headers=forward_headers())

        resp = video_circuit.call(call_service)
        return jsonify(resp.json()), resp.status_code
    except CircuitBreakerOpenException:
        return jsonify({"error": "Video service temporarily unavailable", "fallback": True}), 503
    except requests.exceptions.RequestException:
        return jsonify({"error": "Video service unavailable"}), 503

# =====================
# USER VIDEO ROUTES (With user validation)
# =====================
@app.route('/api/v1/users/<int:user_id>/videos', methods=['GET', 'POST', 'OPTIONS'])
def user_videos_collection(user_id):
    """
    Handle /users/<id>/videos endpoint
    ---
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Success
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    is_valid, error_response = validate_user_access(user_id)
    if not is_valid:
        return error_response
    
    try:
        url = f"{VIDEO_SERVICE_URL}/api/v1/videos"
        
        def call_service():
            if request.method == 'GET':
                return requests.get(url, params=request.args, headers=forward_headers())
            elif request.method == 'POST':
                return requests.post(url, json=request.json, headers=forward_headers())
                
        resp = video_circuit.call(call_service)
        return jsonify(resp.json()), resp.status_code
    except CircuitBreakerOpenException:
        return jsonify({"error": "Video service temporarily unavailable", "fallback": True}), 503
    except requests.exceptions.RequestException:
        return jsonify({"error": "Video service unavailable"}), 503


@app.route('/api/v1/users/<int:user_id>/videos/<int:video_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def user_videos_item(user_id, video_id):
    """
    Handle /users/<id>/videos/<video_id> endpoint
    ---
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
      - name: video_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Success
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    is_valid, error_response = validate_user_access(user_id)
    if not is_valid:
        return error_response
    
    try:
        url = f"{VIDEO_SERVICE_URL}/api/v1/videos/{video_id}"
        
        def call_service():
            if request.method == 'GET':
                return requests.get(url, headers=forward_headers())
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
# SEARCH ROUTES (With user validation)
# =====================
@app.route('/api/v1/users/<int:user_id>/search', methods=['POST', 'OPTIONS'])
def user_search_submit(user_id):
    """
    Submit search for user
    ---
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Success
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    is_valid, error_response = validate_user_access(user_id)
    if not is_valid:
        return error_response
    
    try:
        data = request.get_json(silent=True) or {}
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
def user_search_results(user_id, job_id):
    """
    Get search results for user
    ---
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
      - name: job_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Success
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    is_valid, error_response = validate_user_access(user_id)
    if not is_valid:
        return error_response
    
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

# =====================
# DIRECT SEARCH ROUTES (No user validation)
# =====================
@app.route('/api/v1/search', methods=['POST', 'OPTIONS'])
def search():
    """
    Direct search endpoint
    ---
    responses:
      200:
        description: Success
    """
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
    """
    Direct search results endpoint
    ---
    parameters:
      - name: job_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Success
    """
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


@app.route('/api/v1/search/jobs', methods=['GET', 'OPTIONS'])
def search_jobs_list():
    """
    List search jobs (for developer dashboard)
    ---
    responses:
      200:
        description: Success
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        def call_service():
            return requests.get(
                f"{SEARCH_SERVICE_URL}/api/v1/search/jobs", 
                params=request.args,
                headers=forward_headers()
            )
            
        resp = search_circuit.call(call_service)
        return jsonify(resp.json()), resp.status_code
    except CircuitBreakerOpenException:
        return jsonify({"error": "Search service temporarily unavailable", "jobs": [], "total": 0}), 503
    except requests.exceptions.RequestException:
        return jsonify({"error": "Search service unavailable", "jobs": [], "total": 0}), 503

# =====================
# AUTH ROUTES
# =====================
@app.route('/api/v1/auth/<path:path>', methods=['GET', 'POST', 'DELETE', 'OPTIONS'])
def auth_proxy(path):
    """
    Proxy to Auth Service
    ---
    parameters:
      - name: path
        in: path
        type: string
        required: true
    responses:
      200:
        description: Success
    """
    if request.method == 'OPTIONS':
        return '', 200
    url = f"{AUTH_SERVICE_URL}/api/v1/auth/{path}"
    try:
        def call_service():
            if request.method == 'POST':
                return requests.post(url, json=request.json, headers=forward_headers())
            elif request.method == 'GET':
                return requests.get(url, headers=forward_headers(), params=request.args)
            else:  
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
    """
    Proxy to Analytics Service
    ---
    responses:
      200:
        description: Success
    """
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
    """
    Health check endpoint
    ---
    responses:
      200:
        description: Service is healthy
    """
    return jsonify({'status':'healthy','service':'api-gateway'}), 200

# =====================
# RUN
# =====================
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 API Gateway running on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)