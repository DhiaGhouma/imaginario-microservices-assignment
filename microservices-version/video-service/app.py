from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
import jwt
from dotenv import load_dotenv
from flasgger import Swagger

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///../shared/database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:3001"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
Swagger(app)

db = SQLAlchemy(app)

JWT_SECRET = os.getenv('JWT_SECRET') or os.getenv('SECRET_KEY')
JWT_ALGORITHM = 'HS256'

def get_current_user_id():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get('user_id')
    except:
        return None

class Video(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@app.route('/api/v1/videos', methods=['GET', 'POST', 'OPTIONS'])
def videos():
    """
    Manage videos collection
    ---
    parameters:
      - name: title
        in: query
        type: string
        required: false
      - name: min_duration
        in: query
        type: integer
        required: false
      - name: max_duration
        in: query
        type: integer
        required: false
      - name: body
        in: body
        required: false
        schema:
          type: object
          properties:
            title:
              type: string
            description:
              type: string
            duration:
              type: integer
    responses:
      200:
        description: List of videos
      201:
        description: Video created
      400:
        description: Invalid input
      401:
        description: Unauthorized
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    if request.method == 'GET':
        query = Video.query.filter_by(user_id=user_id)
        title = request.args.get('title')
        min_dur = request.args.get('min_duration', type=int)
        max_dur = request.args.get('max_duration', type=int)

        if title:
            query = query.filter(Video.title.ilike(f"%{title}%"))
        if min_dur is not None:
            query = query.filter(Video.duration >= min_dur)
        if max_dur is not None:
            query = query.filter(Video.duration <= max_dur)

        results = query.all()
        return jsonify([{
            'id': v.id,
            'title': v.title,
            'description': v.description,
            'duration': v.duration,
            'created_at': v.created_at.isoformat(),
            'updated_at': v.updated_at.isoformat()
        } for v in results])

    elif request.method == 'POST':
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400

        video = Video(
            user_id=user_id,
            title=data['title'],
            description=data.get('description', ''),
            duration=int(data.get('duration', 0))
        )
        db.session.add(video)
        db.session.commit()
        return jsonify({
            'id': video.id,
            'title': video.title,
            'description': video.description,
            'duration': video.duration,
            'created_at': video.created_at.isoformat()
        }), 201

@app.route('/api/v1/videos/<int:video_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def video_detail(video_id):
    """
    Manage single video
    ---
    parameters:
      - name: video_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: false
        schema:
          type: object
          properties:
            title:
              type: string
            description:
              type: string
            duration:
              type: integer
    responses:
      200:
        description: Video details or updated
      401:
        description: Unauthorized
      404:
        description: Video not found
    """
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    video = Video.query.filter_by(id=video_id, user_id=user_id).first()
    if not video:
        return jsonify({'error': 'Video not found'}), 404

    if request.method == 'GET':
        return jsonify({
            'id': video.id,
            'title': video.title,
            'description': video.description,
            'duration': video.duration,
            'created_at': video.created_at.isoformat(),
            'updated_at': video.updated_at.isoformat()
        })

    elif request.method == 'PUT':
        data = request.get_json(silent=True) or {}
        video.title = data.get('title', video.title)
        video.description = data.get('description', video.description)
        video.duration = int(data.get('duration', video.duration))
        video.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'id': video.id,
            'title': video.title,
            'description': video.description,
            'duration': video.duration,
            'updated_at': video.updated_at.isoformat()
        })

    elif request.method == 'DELETE':
        db.session.delete(video)
        db.session.commit()
        return jsonify({'message': 'Video deleted'})

@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint
    ---
    responses:
      200:
        description: Service is healthy
    """
    return jsonify({'status': 'healthy', 'service': 'video-service'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.getenv('PORT', 5003))
    app.run(debug=True, host='0.0.0.0', port=port)