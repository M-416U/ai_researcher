from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "AI Research Assistant API is running"})

@api_bp.route('/research/outline', methods=['POST'])
@jwt_required()
def generate_outline():
    """Generate research outline endpoint"""
    # This will be implemented with Gemini API integration
    data = request.get_json()
    # Placeholder response
    return jsonify({
        "message": "Outline generation endpoint (to be implemented)",
        "topic": data.get("topic", ""),
        "user_id": get_jwt_identity()
    })