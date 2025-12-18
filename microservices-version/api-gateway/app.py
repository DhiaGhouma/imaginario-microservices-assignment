"""
API Gateway
Routes requests and handles authentication
Backward compatible with original API
"""
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import jwt
import bcrypt
import uuid
import requests
import time
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///../shared/database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_ALGORITHM'] = 'HS256'

db = SQLAlchemy(app)
CORS(app)

# Service URLs
SEARCH_SERVICE_URL = os.getenv('SEARCH_SERVICE_URL', 'http://localhost:5001')

api_requests_log = []

# MODELS 

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    videos = db.relationship('Video', backref='user', lazy=True)
    api_keys = db.relationship('APIKey', backref='user', lazy=True)

class Video(db.Model):
    __tablename__ = 'videos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class APIKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    key_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)

class SearchJob(db.Model):
    __tablename__ = 'search_jobs'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    query = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='queued')
    results = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)


# AUTHENTICATION HELPERS (Same as your original)

def generate_jwt_token(user_id):
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow().timestamp() + 86400  # 24 hours
    }
    return jwt.encode(payload, app.config['JWT_SECRET'], algorithm=app.config['JWT_ALGORITHM'])

def verify_jwt_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def hash_password(password):
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def hash_api_key(api_key):
    """Hash API key for storage"""
    return bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_api_key(api_key, key_hash):
    """Verify API key against hash"""
    try:
        return bcrypt.checkpw(api_key.encode('utf-8'), key_hash.encode('utf-8'))
    except:
        return False

def get_auth_user():
    """Get authenticated user from JWT or API key"""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Try JWT first
    user_id = verify_jwt_token(token)
    if user_id:
        return User.query.get(user_id)
    
    # Try API key
    api_keys = APIKey.query.filter_by(is_active=True).all()
    for key in api_keys:
        if verify_api_key(token, key.key_hash):
            key.last_used_at = datetime.utcnow()
            db.session.commit()
            return User.query.get(key.user_id)
    
    return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_auth_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        kwargs['current_user'] = user
        
        # Store for analytics
        g.current_user_id = user.id
        g.api_key_id = None
        
        return f(*args, **kwargs)
    return decorated_function

# ANALYTICS LOGGING


def log_request(user_id, api_key_id, endpoint, method, status_code, response_time):
    """Log API request for analytics"""
    api_requests_log.append({
        'user_id': user_id,
        'api_key_id': api_key_id,
        'endpoint': endpoint,
        'method': method,
        'status_code': status_code,
        'response_time': response_time,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Keep only last 10000 requests
    if len(api_requests_log) > 10000:
        api_requests_log.pop(0)

# AUTH ENDPOINTS

@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    user = User(
        email=data['email'],
        name=data.get('name', ''),
        password_hash=hash_password(data['password'])
    )
    db.session.add(user)
    db.session.commit()
    
    token = generate_jwt_token(user.id)
    
    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name
        },
        'token': token
    }), 201

@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not verify_password(data['password'], user.password_hash):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    token = generate_jwt_token(user.id)
    
    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name
        },
        'token': token
    })

#
# API KEY ENDPOINTS

@app.route('/api/v1/auth/api-keys', methods=['POST'])
@require_auth
def create_api_key(current_user):
    """Create a new API key"""
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400
    
    key_uuid = str(uuid.uuid4())
    api_key = f"imaginario_live_{key_uuid}"
    
    key_id = str(uuid.uuid4())
    api_key_record = APIKey(
        id=key_id,
        user_id=current_user.id,
        name=data['name'],
        key_hash=hash_api_key(api_key),
        is_active=True
    )
    db.session.add(api_key_record)
    db.session.commit()
    
    return jsonify({
        'api_key': api_key,
        'api_key_id': key_id,
        'name': data['name'],
        'created_at': api_key_record.created_at.isoformat()
    }), 201

@app.route('/api/v1/auth/api-keys', methods=['GET'])
@require_auth
def list_api_keys(current_user):
    """List user's API keys"""
    api_keys = APIKey.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'api_keys': [{
            'id': key.id,
            'name': key.name,
            'is_active': key.is_active,
            'created_at': key.created_at.isoformat(),
            'last_used_at': key.last_used_at.isoformat() if key.last_used_at else None
        } for key in api_keys]
    })

@app.route('/api/v1/auth/api-keys/<key_id>', methods=['DELETE'])
@require_auth
def delete_api_key(current_user, key_id):
    """Delete/revoke an API key"""
    api_key = APIKey.query.filter_by(id=key_id, user_id=current_user.id).first()
    
    if not api_key:
        return jsonify({'error': 'API key not found'}), 404
    
    db.session.delete(api_key)
    db.session.commit()
    
    return jsonify({'message': 'API key deleted'}), 200

# VIDEO ENDPOINTS (Same as original)

@app.route('/api/v1/users/<int:user_id>/videos', methods=['GET'])
@require_auth
def list_videos(user_id, current_user):
    """List videos for a user"""
    start_time = time.time()
    
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    videos = Video.query.filter_by(user_id=user_id).all()
    
    response = jsonify({
        'videos': [{
            'id': v.id,
            'title': v.title,
            'description': v.description,
            'duration': v.duration,
            'created_at': v.created_at.isoformat()
        } for v in videos]
    })
    
    response_time = time.time() - start_time
    log_request(user_id, None, '/videos', 'GET', 200, response_time)
    
    return response

@app.route('/api/v1/users/<int:user_id>/videos', methods=['POST'])
@require_auth
def create_video(user_id, current_user):
    """Create a new video"""
    start_time = time.time()
    
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if not data or not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400
    
    video = Video(
        user_id=user_id,
        title=data['title'],
        description=data.get('description', ''),
        duration=data.get('duration', 0)
    )
    db.session.add(video)
    db.session.commit()
    
    response = jsonify({
        'id': video.id,
        'title': video.title,
        'description': video.description,
        'duration': video.duration,
        'created_at': video.created_at.isoformat()
    })
    
    response_time = time.time() - start_time
    log_request(user_id, None, '/videos', 'POST', 201, response_time)
    
    return response, 201

@app.route('/api/v1/users/<int:user_id>/videos/<int:video_id>', methods=['GET'])
@require_auth
def get_video(user_id, current_user, video_id):
    """Get video details"""
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    video = Video.query.filter_by(id=video_id, user_id=user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    return jsonify({
        'id': video.id,
        'title': video.title,
        'description': video.description,
        'duration': video.duration,
        'created_at': video.created_at.isoformat()
    })

@app.route('/api/v1/users/<int:user_id>/videos/<int:video_id>', methods=['PUT'])
@require_auth
def update_video(user_id, current_user, video_id):
    """Update video"""
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    video = Video.query.filter_by(id=video_id, user_id=user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    data = request.get_json()
    
    if data.get('title'):
        video.title = data['title']
    if data.get('description') is not None:
        video.description = data['description']
    if data.get('duration') is not None:
        video.duration = data['duration']
    
    video.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'id': video.id,
        'title': video.title,
        'description': video.description,
        'duration': video.duration,
        'updated_at': video.updated_at.isoformat()
    })

@app.route('/api/v1/users/<int:user_id>/videos/<int:video_id>', methods=['DELETE'])
@require_auth
def delete_video(user_id, current_user, video_id):
    """Delete video"""
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    video = Video.query.filter_by(id=video_id, user_id=user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    db.session.delete(video)
    db.session.commit()
    
    return jsonify({'message': 'Video deleted'}), 200


# SEARCH ENDPOINTS (Proxy to Search Service)

@app.route('/api/v1/users/<int:user_id>/search', methods=['POST'])
@require_auth
def submit_search(user_id, current_user):
    """Submit search query (proxy to search service)"""
    start_time = time.time()
    
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if not data or not data.get('query'):
        return jsonify({'error': 'Query is required'}), 400
    
    try:
        # Forward to search service
        response = requests.post(
            f'{SEARCH_SERVICE_URL}/search',
            json={
                'query': data['query'],
                'video_ids': data.get('video_ids'),
                'user_id': user_id
            },
            timeout=5
        )
        
        response_time = time.time() - start_time
        log_request(user_id, None, '/search', 'POST', response.status_code, response_time)
        
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.RequestException as e:
        print(f"Search service error: {e}")
        return jsonify({'error': 'Search service unavailable'}), 503

@app.route('/api/v1/users/<int:user_id>/search/<job_id>', methods=['GET'])
@require_auth
def get_search_results(user_id, current_user, job_id):
    """Get search results (proxy to search service)"""
    start_time = time.time()
    
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        response = requests.get(
            f'{SEARCH_SERVICE_URL}/search/{job_id}',
            timeout=5
        )
        
        response_time = time.time() - start_time
        log_request(user_id, None, f'/search/{job_id}', 'GET', response.status_code, response_time)
        
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.RequestException as e:
        print(f"Search service error: {e}")
        return jsonify({'error': 'Search service unavailable'}), 503


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

# HEALTH CHECK

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'api-gateway'
    }), 200
# RUN

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"🚀 API Gateway starting on port {port}")
    print(f"📡 Search service URL: {SEARCH_SERVICE_URL}")
    app.run(debug=True, port=port, host='0.0.0.0')