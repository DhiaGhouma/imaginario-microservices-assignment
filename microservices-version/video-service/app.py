"""
Video Service
Handles CRUD, list, and filtering of videos
"""

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os


# =====================
# APP SETUP
# =====================
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///../shared/database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "http://localhost:3001"]}})
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

class Video(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# =====================
# VIDEO ENDPOINTS
# =====================

@app.route('/api/videos', methods=['GET'])
def list_videos():
    """List all videos with optional filtering"""
    query = Video.query

    # Filters
    title = request.args.get('title')
    min_duration = request.args.get('min_duration', type=int)
    max_duration = request.args.get('max_duration', type=int)

    if title:
        query = query.filter(Video.title.ilike(f"%{title}%"))
    if min_duration is not None:
        query = query.filter(Video.duration >= min_duration)
    if max_duration is not None:
        query = query.filter(Video.duration <= max_duration)

    videos = query.all()
    return jsonify([{
        'id': v.id,
        'title': v.title,
        'description': v.description,
        'duration': v.duration,
        'created_at': v.created_at.isoformat(),
        'updated_at': v.updated_at.isoformat()
    } for v in videos])

@app.route('/api/videos/<int:video_id>', methods=['GET'])
def get_video(video_id):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({'error':'Video not found'}), 404
    return jsonify({
        'id': video.id,
        'title': video.title,
        'description': video.description,
        'duration': video.duration,
        'created_at': video.created_at.isoformat(),
        'updated_at': video.updated_at.isoformat()
    })

@app.route('/api/videos', methods=['POST'])
def create_video():
    data = request.get_json()
    if not data or not data.get('title'):
        return jsonify({'error':'Title is required'}), 400

    video = Video(
        title=data['title'],
        description=data.get('description',''),
        duration=data.get('duration',0)
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

@app.route('/api/videos/<int:video_id>', methods=['PUT'])
def update_video(video_id):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({'error':'Video not found'}), 404

    data = request.get_json() or {}
    video.title = data.get('title', video.title)
    video.description = data.get('description', video.description)
    video.duration = data.get('duration', video.duration)
    video.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({
        'id': video.id,
        'title': video.title,
        'description': video.description,
        'duration': video.duration,
        'updated_at': video.updated_at.isoformat()
    })

@app.route('/api/videos/<int:video_id>', methods=['DELETE'])
def delete_video(video_id):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({'error':'Video not found'}), 404
    db.session.delete(video)
    db.session.commit()
    return jsonify({'message':'Video deleted'})

# =====================
# HEALTH CHECK
# =====================
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status':'healthy','service':'video-service'}), 200

# =====================
# RUN
# =====================
if __name__ == '__main__':
    port = int(os.getenv('PORT',5003))
    print(f"🚀 Video Service running on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
