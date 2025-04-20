from flask import Blueprint, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.research import ResearchProject
from app.services.export_service import ExportService
import os

export_bp = Blueprint('export', __name__, url_prefix='/api/export')

@export_bp.route('/markdown/<int:project_id>', methods=['GET'])
@jwt_required()
def export_to_markdown(project_id):
    """Export a research paper to Markdown format"""
    user_id = get_jwt_identity()
    
    # Verify the project belongs to the user
    project = ResearchProject.query.filter_by(id=project_id, user_id=user_id).first()
    
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    # Export the paper
    export_service = ExportService()
    result = export_service.export_paper_to_markdown(project_id)
    
    if "error" in result:
        return jsonify(result), 500
    
    # Return the file
    return send_file(
        result["filepath"],
        as_attachment=True,
        download_name=result["filename"],
        mimetype='text/markdown'
    )