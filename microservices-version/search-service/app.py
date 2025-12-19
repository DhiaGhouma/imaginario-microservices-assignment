from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import uuid
import threading
from queue import Queue
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URI', 'sqlite:///C:/Users/DELL/Downloads/Internship-technical-assessment/Internship-technical-assessment/microservices-version/shared/database.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:3001"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Service-Token"]
    }
})

db = SQLAlchemy(app)

job_queue = Queue()
search_jobs = {}

class Video(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def perform_search(query, user_id=None):
    if not query:
        return []

    query_lower = query.lower()
    query_words = query_lower.split()

    # EASIEST FIX: Search ALL videos, don't filter by user_id
    videos = Video.query.all()

    results = []

    for video in videos:
        score = 0.0
        matched_parts = []
        title_lower = (video.title or '').lower()
        
        if query_lower in title_lower:
            score += 0.7
            matched_parts.append(video.title)
        else:
            for word in query_words:
                if word in title_lower:
                    score += 0.3 / len(query_words)
                    matched_parts.append(video.title)

        description_lower = (video.description or '').lower()
        if query_lower in description_lower:
            score += 0.3
            idx = description_lower.find(query_lower)
            start = max(0, idx - 30)
            end = min(len(description_lower), idx + len(query_lower) + 30)
            snippet = video.description[start:end]
            matched_parts.append(snippet)
        else:
            for word in query_words:
                if word in description_lower:
                    score += 0.1 / len(query_words)

        if score > 0:
            results.append({
                'video_id': video.id,
                'title': video.title,
                'relevance_score': round(min(score, 1.0), 2),
                'matched_text': matched_parts[0] if matched_parts else video.title
            })

    results.sort(key=lambda x: x['relevance_score'], reverse=True)
    return results

def process_search_job(job_id):
    with app.app_context():
        try:
            job = search_jobs[job_id]
            job['status'] = 'processing'
            job['started_at'] = datetime.utcnow().isoformat()

            results = perform_search(job['query'], job.get('user_id'))

            job['status'] = 'completed'
            job['results'] = results
            job['completed_at'] = datetime.utcnow().isoformat()

        except Exception as e:
            job['status'] = 'failed'
            job['error'] = str(e)
            job['completed_at'] = datetime.utcnow().isoformat()

def job_worker():
    while True:
        job_id = job_queue.get()
        if job_id is None:
            break
        process_search_job(job_id)
        job_queue.task_done()

threading.Thread(target=job_worker, daemon=True).start()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'search-service',
        'jobs_pending': job_queue.qsize()
    })

@app.route('/api/v1/search', methods=['POST'])
def create_search():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data.get('query'):
        return jsonify({'error': 'Query required'}), 400

    job_id = str(uuid.uuid4())
    job = {
        'id': job_id,
        'query': data['query'],
        'user_id': data.get('user_id') or data.get('userId'),
        'video_ids': data.get('video_ids'),
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat(),
        'results': [],
        'error': None
    }

    search_jobs[job_id] = job
    job_queue.put(job_id)

    return jsonify({
        'job_id': job_id,
        'status': 'pending'
    }), 202

@app.route('/api/v1/search/<job_id>', methods=['GET'])
def get_search_results(job_id):
    if job_id not in search_jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = search_jobs[job_id]
    response = {
        'job_id': job['id'],
        'query': job['query'],
        'status': job['status'],
        'created_at': job['created_at'],
        'completed_at': job.get('completed_at')
    }

    if job['status'] == 'completed':
        response['results'] = job['results']
    elif job['status'] == 'failed':
        response['error'] = job.get('error')

    return jsonify(response)

@app.route('/api/v1/search/jobs', methods=['GET'])
def list_jobs():
    user_id = request.args.get('user_id') or request.args.get('userId')
    jobs = list(search_jobs.values())

    if user_id:
        jobs = [j for j in jobs if str(j.get('user_id')) == str(user_id)]

    jobs.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify({
        'jobs': jobs[:50],
        'total': len(jobs)
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    print(f"🚀 Search Service running on port {port}")
    app.run(debug=True, port=port, host='0.0.0.0')