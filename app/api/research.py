from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.research import ResearchProject, ResearchOutline
from app.models.user import User
from app.services.gemini_service import GeminiService
from app import db
from datetime import datetime

research_bp = Blueprint('research', __name__, url_prefix='/api/research')

@research_bp.route('/projects', methods=['GET'])
@jwt_required()
def get_projects():
    """Get all research projects for the current user"""
    user_id = get_jwt_identity()
    projects = ResearchProject.query.filter_by(user_id=user_id).all()
    
    result = []
    for project in projects:
        result.append({
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "language": project.language,
            "citation_style": project.citation_style,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat()
        })
    
    return jsonify(result), 200

@research_bp.route('/projects', methods=['POST'])
@jwt_required()
def create_project():
    """Create a new research project"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    # Check if required fields are present
    if 'title' not in data:
        return jsonify({"error": "Title is required"}), 400
    
    # Create new project
    project = ResearchProject(
        title=data['title'],
        description=data.get('description', ''),
        user_id=user_id,
        language=data.get('language', 'en'),
        citation_style=data.get('citation_style', 'APA')
    )
    
    db.session.add(project)
    db.session.commit()
    
    return jsonify({
        "message": "Project created successfully",
        "project_id": project.id,
        "title": project.title
    }), 201

@research_bp.route('/projects/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    """Get a specific research project"""
    user_id = get_jwt_identity()
    project = ResearchProject.query.filter_by(id=project_id, user_id=user_id).first()
    
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    # Get the latest outline if it exists
    latest_outline = ResearchOutline.query.filter_by(project_id=project.id).order_by(ResearchOutline.created_at.desc()).first()
    outline_data = None
    
    if latest_outline:
        outline_data = {
            "id": latest_outline.id,
            "is_approved": latest_outline.is_approved,
            "created_at": latest_outline.created_at.isoformat(),
            "structure": latest_outline.get_outline_structure()
        }
    
    return jsonify({
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "language": project.language,
        "citation_style": project.citation_style,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "latest_outline": outline_data
    }), 200

@research_bp.route('/projects/<int:project_id>/outline', methods=['POST'])
@jwt_required()
def generate_outline(project_id):
    """Generate a research outline for a project"""
    user_id = get_jwt_identity()
    project = ResearchProject.query.filter_by(id=project_id, user_id=user_id).first()
    
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    data = request.get_json()
    complexity = data.get('complexity', 'medium')
    
    # Generate outline using Gemini service
    gemini_service = GeminiService()
    outline_structure = gemini_service.generate_research_outline(
        topic=project.title,
        complexity=complexity,
        language=project.language
    )
    
    if "error" in outline_structure:
        return jsonify(outline_structure), 500
    
    # Create new outline
    outline = ResearchOutline(project_id=project.id)
    outline.set_outline_structure(outline_structure)
    
    db.session.add(outline)
    db.session.commit()
    
    return jsonify({
        "message": "Outline generated successfully",
        "outline_id": outline.id,
        "structure": outline_structure
    }), 201

@research_bp.route('/outlines/<int:outline_id>/approve', methods=['POST'])
@jwt_required()
def approve_outline(outline_id):
    """Approve a research outline"""
    user_id = get_jwt_identity()
    outline = ResearchOutline.query.join(ResearchProject).filter(
        ResearchOutline.id == outline_id,
        ResearchProject.user_id == user_id
    ).first()
    
    if not outline:
        return jsonify({"error": "Outline not found"}), 404
    
    outline.is_approved = True
    db.session.commit()
    
    return jsonify({
        "message": "Outline approved successfully",
        "outline_id": outline.id
    }), 200