from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.research import ResearchProject, ResearchOutline
from app.models.content import ResearchContent
from app.services.content_service import ContentService
from app import db
from datetime import datetime

content_bp = Blueprint('content', __name__, url_prefix='/api/content')

@content_bp.route('/generate/<int:outline_id>/<section_title>', methods=['POST'])
@jwt_required()
def generate_content(outline_id, section_title):
    """Generate content for a specific section of an approved outline"""
    user_id = get_jwt_identity()
    
    # Get the outline and verify it belongs to the user
    outline = ResearchOutline.query.join(ResearchProject).filter(
        ResearchOutline.id == outline_id,
        ResearchProject.user_id == user_id
    ).first()
    
    if not outline:
        return jsonify({"error": "Outline not found"}), 404
    
    # Check if the outline is approved
    if not outline.is_approved:
        return jsonify({"error": "Outline must be approved before generating content"}), 400
    
    # Get the project
    project = ResearchProject.query.get(outline.project_id)
    
    # Get request data
    data = request.get_json() or {}
    subsection_titles = data.get('subsection_titles', [])
    
    # Generate content
    content_service = ContentService()
    content_data = content_service.generate_section_content(
        project=project,
        outline=outline,
        section_title=section_title,
        subsection_titles=subsection_titles,
        citation_style=project.citation_style,
        language=project.language
    )
    
    if "error" in content_data:
        return jsonify(content_data), 500
    
    # Check if content for this section already exists
    existing_content = ResearchContent.query.filter_by(
        project_id=project.id,
        outline_id=outline.id,
        section_title=section_title
    ).first()
    
    if existing_content:
        # Increment version and update content
        existing_content.content = content_data.get('content', '')
        existing_content.set_citations(content_data.get('citations', []))
        existing_content.version += 1
        existing_content.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            "message": "Content updated successfully",
            "content_id": existing_content.id,
            "section_title": section_title,
            "version": existing_content.version
        }), 200
    else:
        # Create new content
        new_content = ResearchContent(
            project_id=project.id,
            outline_id=outline.id,
            section_title=section_title,
            content=content_data.get('content', '')
        )
        new_content.set_citations(content_data.get('citations', []))
        
        db.session.add(new_content)
        db.session.commit()
        
        return jsonify({
            "message": "Content generated successfully",
            "content_id": new_content.id,
            "section_title": section_title,
            "version": new_content.version
        }), 201

@content_bp.route('/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project_content(project_id):
    """Get all content for a project"""
    user_id = get_jwt_identity()
    
    # Verify the project belongs to the user
    project = ResearchProject.query.filter_by(id=project_id, user_id=user_id).first()
    
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    # Get the latest approved outline
    latest_outline = ResearchOutline.query.filter_by(
        project_id=project.id,
        is_approved=True
    ).order_by(ResearchOutline.created_at.desc()).first()
    
    if not latest_outline:
        return jsonify({"error": "No approved outline found for this project"}), 404
    
    # Get all content for this outline
    content_sections = ResearchContent.query.filter_by(
        project_id=project.id,
        outline_id=latest_outline.id
    ).all()
    
    result = []
    for section in content_sections:
        result.append({
            "id": section.id,
            "section_title": section.section_title,
            "content": section.content,
            "citations": section.get_citations(),
            "version": section.version,
            "created_at": section.created_at.isoformat(),
            "updated_at": section.updated_at.isoformat()
        })
    
    return jsonify(result), 200

@content_bp.route('/<int:content_id>', methods=['GET'])
@jwt_required()
def get_content(content_id):
    """Get a specific content section"""
    user_id = get_jwt_identity()
    
    # Get the content and verify it belongs to the user
    content = ResearchContent.query.join(ResearchProject).filter(
        ResearchContent.id == content_id,
        ResearchProject.user_id == user_id
    ).first()
    
    if not content:
        return jsonify({"error": "Content not found"}), 404
    
    return jsonify({
        "id": content.id,
        "section_title": content.section_title,
        "content": content.content,
        "citations": content.get_citations(),
        "version": content.version,
        "created_at": content.created_at.isoformat(),
        "updated_at": content.updated_at.isoformat()
    }), 200