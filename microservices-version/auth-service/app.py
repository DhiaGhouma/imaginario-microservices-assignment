"""
Authentication Microservice
Handles user registration, login, and API key management
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import jwt
import bcrypt
import uuid
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URI', 'sqlite:///../shared/database.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_ALGORITHM'] = 'HS256'

CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Service-Token"]
    }
})

db = SQLAlchemy(app)

# =====================
# MODELS
# =====================

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    api_keys = db.relationship('APIKey', backref='user', lazy=True)

class APIKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    key_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)

# =====================
# AUTHENTICATION HELPERS
# =====================

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
        return f(*args, **kwargs)
    return decorated_function

# =====================
# ROUTES
# =====================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'auth-service'
    }), 200

# USER REGISTRATION & LOGIN

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

# VERIFY TOKEN (FOR OTHER SERVICES)

@app.route('/api/v1/auth/verify', methods=['POST'])
def verify_token():
    """Verify JWT token or API key - for inter-service communication"""
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({'error': 'Token required'}), 400
    
    # Try JWT first
    user_id = verify_jwt_token(token)
    if user_id:
        user = User.query.get(user_id)
        if user:
            return jsonify({
                'valid': True,
                'user_id': user.id,
                'email': user.email,
                'name': user.name
            })
    
    # Try API key
    api_keys = APIKey.query.filter_by(is_active=True).all()
    for key in api_keys:
        if verify_api_key(token, key.key_hash):
            key.last_used_at = datetime.utcnow()
            db.session.commit()
            user = User.query.get(key.user_id)
            return jsonify({
                'valid': True,
                'user_id': user.id,
                'email': user.email,
                'name': user.name,
                'api_key_id': key.id
            })
    
    return jsonify({'valid': False, 'error': 'Invalid token'}), 401

# API KEY MANAGEMENT

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

# GET USER INFO (FOR OTHER SERVICES)

@app.route('/api/v1/auth/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user information - for inter-service communication"""
    # Verify service token
    service_token = request.headers.get('X-Service-Token')
    if service_token != os.getenv('SERVICE_TOKEN', 'service-secret-token'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'created_at': user.created_at.isoformat()
    })

# =====================
# RUN
# =====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    port = int(os.getenv('PORT', 5002))
    print(f"🚀 Auth Service running on port {port}")
    app.run(debug=True, port=port, host='0.0.0.0')