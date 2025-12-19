from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# =====================
# Database Config
# =====================
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URI', 'sqlite:///C:/Users/DELL/Downloads/Internship-technical-assessment/Internship-technical-assessment/microservices-version/shared/database.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# =====================
# MODELS
# =====================
class ApiRequestLog(db.Model):
    __tablename__ = 'api_request_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    endpoint = db.Column(db.String(200), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    response_time = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# =====================
# ROUTES
# =====================
@app.route('/api/v1/analytics/overview', methods=['GET', 'OPTIONS'])
def overview():
    if request.method == 'OPTIONS':
        return '', 200

    user_id = request.args.get('user_id', default=1, type=int)
    logs = ApiRequestLog.query.filter_by(user_id=user_id).all()

    total_requests = len(logs)
    success_count = len([r for r in logs if 200 <= r.status_code < 300])
    success_rate = (success_count / total_requests * 100) if total_requests else 0
    avg_response_time = sum(r.response_time for r in logs) / max(total_requests, 1)

    endpoint_counts = {}
    for r in logs:
        endpoint_counts[r.endpoint] = endpoint_counts.get(r.endpoint, 0) + 1

    return jsonify({
        'total_requests': total_requests,
        'success_rate': round(success_rate, 2),
        'avg_response_time': round(avg_response_time, 4),
        'requests_by_endpoint': endpoint_counts
    }), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'analytics-service'}), 200

# =====================
# Helper: Log request (for other services to call)
# =====================
@app.route('/api/v1/analytics/log', methods=['POST'])
def log_request():
    data = request.json
    if not data:
        return jsonify({'error': 'Missing request data'}), 400

    log = ApiRequestLog(
        user_id=data.get('user_id', 1),
        endpoint=data.get('endpoint', '/unknown'),
        status_code=data.get('status_code', 200),
        response_time=data.get('response_time', 0.0)
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({'status': 'logged'}), 201

# =====================
# RUN
# =====================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    port = int(os.getenv('PORT', 5004))
    print(f"🚀 Analytics Service running on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
