from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Sample in-memory request logs (replace with real DB later)
api_requests_log = [
    {"user_id": 1, "endpoint": "/api/v1/videos", "status_code": 200, "response_time": 0.12},
    {"user_id": 1, "endpoint": "/api/v1/search/jobs", "status_code": 200, "response_time": 0.15},
]

@app.route('/api/v1/analytics/overview', methods=['GET', 'OPTIONS'])
def overview():
    if request.method == 'OPTIONS':
        return '', 200
    user_id = request.args.get('user_id', default=1, type=int)
    user_requests = [r for r in api_requests_log if r['user_id'] == user_id]

    total_requests = len(user_requests)
    success_count = len([r for r in user_requests if 200 <= r['status_code'] < 300])
    success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
    avg_response_time = sum(r['response_time'] for r in user_requests) / max(total_requests, 1)

    endpoint_counts = {}
    for r in user_requests:
        endpoint_counts[r['endpoint']] = endpoint_counts.get(r['endpoint'], 0) + 1

    return jsonify({
        'total_requests': total_requests,
        'success_rate': round(success_rate, 2),
        'avg_response_time': round(avg_response_time, 4),
        'requests_by_endpoint': endpoint_counts
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status':'healthy','service':'analytics-service'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5004)
