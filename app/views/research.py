import datetime
import json
from flask import (
    Blueprint,
    Response,
    jsonify,
    render_template,
    redirect,
    send_file,
    stream_with_context,
    url_for,
    request,
    flash,
)
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.research import ResearchProject, ResearchOutline
from app.models.content import ResearchContent
from app.services.gemini_service import GeminiService
from app.services.content_service import ContentService
from app.services.export_service import ExportService
from app import db

research_views_bp = Blueprint("research_views", __name__)


def jwt_cookie_required(f):
    """Custom decorator for JWT cookie verification"""

    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request(locations=["cookies"])
            user_id = get_jwt_identity()
            if not user_id:
                return redirect(url_for("auth_views.login"))
            return f(*args, **kwargs)
        except Exception as e:
            print(f"JWT verification error: {str(e)}")
            flash("Login required", "error")
            return redirect(url_for("auth_views.login"))

    decorated_function.__name__ = f.__name__
    return decorated_function


def public_route(f):
    """Decorator for public routes that can handle optional JWT"""

    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request(optional=True, locations=["cookies"])
            return f(*args, **kwargs)
        except Exception as e:
            print(f"JWT verification error: {str(e)}")
            return f(*args, **kwargs)

    decorated_function.__name__ = f.__name__
    return decorated_function


@research_views_bp.route("/projects")
@jwt_cookie_required
def projects():
    """Render the projects page"""
    user_id = get_jwt_identity()
    projects = ResearchProject.query.filter_by(user_id=int(user_id)).all()

    return render_template("research/projects.html", projects=projects)


@research_views_bp.route("/projects/new", methods=["GET", "POST"])
def new_project():
    """Render the new project page and handle form submission"""
    try:
        verify_jwt_in_request(locations=["cookies"])
        user_id = get_jwt_identity()
        if not user_id:
            return redirect(url_for("auth_views.login"))

        if request.method == "POST":
            title = request.form.get("title")
            description = request.form.get("description", "")
            language = request.form.get("language", "en")
            citation_style = request.form.get("citation_style", "APA")

            if not title:
                flash("Title is required", "error")
                return render_template("research/new_project.html")
            verify_jwt_in_request(locations=["cookies"])
            user_id = get_jwt_identity()

            project = ResearchProject(
                title=title,
                description=description,
                user_id=int(user_id),
                language=language,
                citation_style=citation_style,
            )

            db.session.add(project)
            db.session.commit()

            flash("Project created successfully", "success")
            return redirect(
                url_for("research_views.project_detail", project_id=project.id)
            )
    except Exception as e:
        flash(f"Error creating project: {str(e)}", "error")
        return redirect(url_for("research_views.projects"))

    return render_template("research/new_project.html")


@research_views_bp.route("/projects/<int:project_id>")
@jwt_cookie_required
def project_detail(project_id):
    """Render the project detail page"""
    user_id = get_jwt_identity()
    project = ResearchProject.query.filter_by(id=project_id, user_id=user_id).first()

    if not project:
        flash("Project not found", "error")
        return redirect(url_for("research_views.projects"))

    # Get the latest outline
    latest_outline = (
        ResearchOutline.query.filter_by(project_id=project.id)
        .order_by(ResearchOutline.created_at.desc())
        .first()
    )

    # Get content sections if outline is approved
    content_sections = []
    if latest_outline and latest_outline.is_approved:
        content_sections = ResearchContent.query.filter_by(
            project_id=project.id, outline_id=latest_outline.id
        ).all()

        # Debug information
        print(f"Found {len(content_sections)} content sections")
        for section in content_sections:
            print(
                f"Section: {section.section_title}, Content length: {len(section.content or '')}"
            )

    return render_template(
        "research/project_detail.html",
        project=project,
        outline=latest_outline,
        content_sections=content_sections,
    )


@research_views_bp.route(
    "/projects/<int:project_id>/generate-outline", methods=["GET", "POST"]
)
def generate_outline(project_id):
    """Render the generate outline page and handle form submission"""
    try:
        verify_jwt_in_request(locations=["cookies"])
        user_id = get_jwt_identity()
        if not user_id:
            return redirect(url_for("auth_views.login"))

        project = ResearchProject.query.filter_by(
            id=project_id, user_id=user_id
        ).first()

        if not project:
            flash("Project not found", "error")
            return redirect(url_for("research_views.projects"))

        if request.method == "POST":
            complexity = request.form.get("complexity", "medium")
            total_pages = int(request.form.get("total_pages", 10))

            gemini_service = GeminiService()
            outline_structure = gemini_service.generate_research_outline(
                topic=project.title,
                complexity=complexity,
                language=project.language,
                total_pages=total_pages,
            )

            if "error" in outline_structure:
                flash(
                    f"Error generating outline: {outline_structure['error']}", "error"
                )
                return render_template(
                    "research/generate_outline.html", project=project
                )

            outline = ResearchOutline(project_id=project.id, total_pages=total_pages)
            outline.set_outline_structure(outline_structure)

            # Calculate pages for each section
            outline.calculate_section_pages()

            db.session.add(outline)
            db.session.commit()

            flash("Outline generated successfully", "success")
            return redirect(
                url_for("research_views.outline_detail", outline_id=outline.id)
            )

        return render_template("research/generate_outline.html", project=project)
    except Exception as e:
        print(f"JWT verification error: {str(e)}")
        flash("Login required", "error")
        return redirect(url_for("auth_views.login"))


@research_views_bp.route("/outlines/<int:outline_id>", methods=["GET", "POST"])
@jwt_cookie_required
def outline_detail(outline_id):
    """Render the outline detail page"""
    user_id = get_jwt_identity()
    outline = (
        ResearchOutline.query.join(ResearchProject)
        .filter(ResearchOutline.id == outline_id, ResearchProject.user_id == user_id)
        .first()
    )

    if not outline:
        flash("Outline not found", "error")
        return redirect(url_for("research_views.projects"))

    # Handle POST request for approving the outline
    if request.method == "POST":
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            try:
                outline.is_approved = True
                db.session.commit()
                return jsonify(
                    {"success": True, "message": "Outline approved successfully"}
                )
            except Exception as e:
                db.session.rollback()
                return jsonify({"success": False, "error": str(e)}), 500
        else:
            try:
                outline.is_approved = True
                db.session.commit()
                flash("Outline approved successfully", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Error approving outline: {str(e)}", "error")
            return redirect(
                url_for("research_views.project_detail", project_id=outline.project_id)
            )

    project = ResearchProject.query.get(outline.project_id)
    outline_structure = outline.get_outline_structure()

    if "introduction_page_range" not in outline_structure:
        outline_structure["introduction_page_range"] = {"start": 1, "end": 1}
    if "conclusion_page_range" not in outline_structure:
        outline_structure["conclusion_page_range"] = {"start": 1, "end": 1}

    # Get existing content sections
    content_sections = {}
    if outline.is_approved:
        sections = ResearchContent.query.filter_by(
            project_id=project.id, outline_id=outline.id
        ).all()

        for section in sections:
            content_sections[section.section_title] = section

    return render_template(
        "research/outline_detail.html",
        outline=outline,
        project=project,
        structure=outline_structure,
        content_sections=content_sections,
    )


@research_views_bp.route(
    "/projects/<int:project_id>/generate-content/<section_title>",
    methods=["GET", "POST"],
)
@jwt_cookie_required
def generate_content(project_id, section_title):
    """Generate content for a specific section"""
    try:
        user_id = get_jwt_identity()
        project = ResearchProject.query.filter_by(
            id=project_id, user_id=user_id
        ).first()

        if not project:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": "Project not found"}), 404
            flash("Project not found", "error")
            return redirect(url_for("research_views.projects"))

        # Get the latest approved outline
        outline = (
            ResearchOutline.query.filter_by(project_id=project.id, is_approved=True)
            .order_by(ResearchOutline.created_at.desc())
            .first()
        )

        if not outline:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": "No approved outline found"}), 400
            flash("No approved outline found", "error")
            return redirect(
                url_for("research_views.project_detail", project_id=project_id)
            )

        # Get page_by_page parameter
        page_by_page = request.args.get("page_by_page", "true").lower() == "true"

        # Handle AJAX POST request
        if (
            request.method == "POST"
            and request.headers.get("X-Requested-With") == "XMLHttpRequest"
        ):
            data = request.get_json()
            if data:
                section_title = data.get("section_title", section_title)
                page_by_page = data.get("page_by_page", True)
                subsection_titles = data.get("subsection_titles", [])
                json_content = data.get("json_content")

                if json_content:
                    content = ResearchContent.query.filter_by(
                        project_id=project.id,
                        outline_id=outline.id,
                        section_title=section_title,
                    ).first()

                    if not content:
                        content = ResearchContent(
                            project_id=project.id,
                            outline_id=outline.id,
                            section_title=section_title,
                        )

                    content.from_json_response(json_content)

                    db.session.add(content)
                    db.session.commit()

                    return jsonify(
                        {"success": True, "message": "Content saved successfully"}
                    )

                # Generate content for the section
                outline_structure = outline.get_outline_structure()

                # Find the section in the outline structure
                section_data = None
                if section_title == "Introduction" or section_title == "المقدمة":
                    section_data = {
                        "title": section_title,
                        "thesis_statement": outline_structure.get(
                            "thesis_statement", ""
                        ),
                        "research_questions": outline_structure.get(
                            "research_questions", []
                        ),
                    }
                elif section_title == "Conclusion" or section_title == "الخاتمة":
                    section_data = {"title": section_title}
                else:
                    for section in outline_structure.get("sections", []):
                        if section.get("title") == section_title:
                            section_data = section
                            break

                if not section_data:
                    return jsonify(
                        {
                            "success": False,
                            "error": f"Section '{section_title}' not found in outline",
                        }
                    )

                content_service = ContentService()
                content_data = content_service.generate_section_content(
                    project,
                    outline,
                    section_title,
                    subsection_titles,
                    project.citation_style,
                    project.language,
                    page_by_page=page_by_page,
                )

                if "error" in content_data:
                    return (
                        jsonify({"success": False, "error": content_data["error"]}),
                        400,
                    )

                content = ResearchContent.query.filter_by(
                    project_id=project.id,
                    outline_id=outline.id,
                    section_title=section_title,
                ).first()

                if not content:
                    content = ResearchContent(
                        project_id=project.id,
                        outline_id=outline.id,
                        section_title=section_title,
                    )

                content.from_json_response(content_data)
                db.session.add(content)
                db.session.commit()

                return jsonify(
                    {
                        "success": True,
                        "message": "Content generated successfully",
                        "content": content.content,
                        "citations": content.get_citations(),
                    }
                )

        # Handle regular GET request
        if request.method == "GET":
            # Generate content in the background
            content_service = ContentService()
            content_data = content_service.generate_section_content(
                project,
                outline,
                section_title,
                [],
                project.citation_style,
                project.language,
                page_by_page=page_by_page,
            )

            if "error" in content_data:
                flash(f"Error generating content: {content_data['error']}", "error")
                return redirect(
                    url_for("research_views.outline_detail", outline_id=outline.id)
                )

            content = ResearchContent.query.filter_by(
                project_id=project.id,
                outline_id=outline.id,
                section_title=section_title,
            ).first()

            if not content:
                content = ResearchContent(
                    project_id=project.id,
                    outline_id=outline.id,
                    section_title=section_title,
                )

            content.from_json_response(content_data)

            db.session.add(content)
            db.session.commit()

            flash(f"Content for '{section_title}' generated successfully", "success")
            return redirect(
                url_for("research_views.outline_detail", outline_id=outline.id)
            )

        # Handle regular POST request
        subsection_titles = request.json.get("subsection_titles", [])
        json_content = request.json.get("json_content")

        if json_content:
            content = ResearchContent.query.filter_by(
                project_id=project.id,
                outline_id=outline.id,
                section_title=section_title,
            ).first()

            if not content:
                content = ResearchContent(
                    project_id=project.id,
                    outline_id=outline.id,
                    section_title=section_title,
                )

            content.from_json_response(json_content)

            db.session.add(content)
            db.session.commit()

            return jsonify({"success": True, "message": "Content saved successfully"})

        content_service = ContentService()
        content_data = content_service.generate_section_content(
            project,
            outline,
            section_title,
            subsection_titles,
            project.citation_style,
            project.language,
            page_by_page=page_by_page,
        )

        if "error" in content_data:
            return jsonify(content_data), 400

        content = ResearchContent.query.filter_by(
            project_id=project.id,
            outline_id=outline.id,
            section_title=section_title,
        ).first()

        if not content:
            content = ResearchContent(
                project_id=project.id,
                outline_id=outline.id,
                section_title=section_title,
            )

        content.from_json_response(content_data)

        print(f"Saving content for section: {section_title}")
        print(f"Content length: {len(content.content)}")
        print(f"Citations count: {len(content.get_citations())}")

        db.session.add(content)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Content generated successfully",
                "content": content.content,
                "citations": content.get_citations(),
            }
        )

    except Exception as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": str(e)}), 500
        print(f"Error generating content: {str(e)}")
        flash(f"Error generating content: {str(e)}", "error")
        return redirect(url_for("research_views.projects"))


@research_views_bp.route("/projects/<int:project_id>/export", methods=["GET", "POST"])
@jwt_cookie_required
def export_paper(project_id):
    """Preview the full research paper"""
    user_id = get_jwt_identity()
    project = ResearchProject.query.filter_by(id=project_id, user_id=user_id).first()

    if not project:
        flash("Project not found", "error")
        return redirect(url_for("research_views.projects"))

    # Get the latest approved outline
    outline = (
        ResearchOutline.query.filter_by(project_id=project.id, is_approved=True)
        .order_by(ResearchOutline.created_at.desc())
        .first()
    )

    if not outline:
        flash("No approved outline found for this project", "error")
        return redirect(url_for("research_views.project_detail", project_id=project_id))

    # Get all content sections
    content_sections = ResearchContent.query.filter_by(
        project_id=project.id, outline_id=outline.id
    ).all()

    # Create a dictionary to organize content by section title
    sections_with_content = {}
    for section in content_sections:
        sections_with_content[section.section_title] = section

    # Get the ordered sections
    ordered_sections = outline.get_ordered_sections()

    # Get the outline structure
    outline_structure = outline.get_outline_structure()

    # Generate index
    index = outline.generate_index(language=project.language)

    return render_template(
        "research/preview_paper.html",
        project=project,
        outline=outline,
        outline_structure=outline_structure,
        sections_with_content=sections_with_content,
        ordered_sections=ordered_sections,
        index=index,
        now=datetime.datetime.now(),
    )


@research_views_bp.route("/projects/<int:project_id>/export-pdf", methods=["GET"])
@jwt_cookie_required
def export_pdf(project_id):
    """Export the research paper as PDF"""
    try:
        user_id = get_jwt_identity()
        project = ResearchProject.query.filter_by(
            id=project_id, user_id=user_id
        ).first()

        if not project:
            flash("Project not found", "error")
            return redirect(url_for("research_views.projects"))

        # Get the latest approved outline
        outline = (
            ResearchOutline.query.filter_by(project_id=project.id, is_approved=True)
            .order_by(ResearchOutline.created_at.desc())
            .first()
        )

        if not outline:
            flash("No approved outline found for this project", "error")
            return redirect(
                url_for("research_views.project_detail", project_id=project_id)
            )

        # Use the export service to generate PDF
        export_service = ExportService()
        result = export_service.generate_pdf(project_id)

        if "error" in result:
            flash(f"Error generating PDF: {result['error']}", "error")
            return redirect(
                url_for("research_views.project_detail", project_id=project_id)
            )

        # Return the PDF file
        return send_file(
            result["filepath"],
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{project.title}.pdf",
        )

    except Exception as e:
        flash(f"Error exporting PDF: {str(e)}", "error")
        return redirect(url_for("research_views.project_detail", project_id=project_id))


@research_views_bp.route("/projects/<int:project_id>/export-docx", methods=["GET"])
@jwt_cookie_required
def export_docx(project_id):
    """Export the research paper as DOCX"""
    try:
        user_id = get_jwt_identity()
        project = ResearchProject.query.filter_by(
            id=project_id, user_id=user_id
        ).first()

        if not project:
            flash("Project not found", "error")
            return redirect(url_for("research_views.projects"))

        # Get the latest approved outline
        outline = (
            ResearchOutline.query.filter_by(project_id=project.id, is_approved=True)
            .order_by(ResearchOutline.created_at.desc())
            .first()
        )

        if not outline:
            flash("No approved outline found for this project", "error")
            return redirect(
                url_for("research_views.project_detail", project_id=project_id)
            )

        # Use the export service to generate DOCX
        export_service = ExportService()
        result = export_service.generate_docx(project_id)

        if "error" in result:
            flash(f"Error generating DOCX: {result['error']}", "error")
            return redirect(
                url_for("research_views.project_detail", project_id=project_id)
            )

        # Return the DOCX file
        return send_file(
            result["filepath"],
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name=f"{project.title}.docx",
        )

    except Exception as e:
        flash(f"Error exporting DOCX: {str(e)}", "error")
        return redirect(url_for("research_views.project_detail", project_id=project_id))


@research_views_bp.route("/projects/delete/<int:project_id>", methods=["POST"])
@jwt_cookie_required
def delete_project(project_id):
    """Delete a research project"""
    try:
        user_id = get_jwt_identity()
        project = ResearchProject.query.filter_by(
            id=project_id, user_id=user_id
        ).first()

        if not project:
            flash("Project not found", "error")
            return redirect(url_for("research_views.projects"))

        # Delete associated outlines and content
        outlines = ResearchOutline.query.filter_by(project_id=project_id).all()
        for outline in outlines:
            # Delete content associated with this outline
            contents = ResearchContent.query.filter_by(outline_id=outline.id).all()
            for content in contents:
                db.session.delete(content)
            db.session.delete(outline)

        # Delete the project
        db.session.delete(project)
        db.session.commit()

        flash("Project deleted successfully", "success")
        return redirect(url_for("main.dashboard"))
    except Exception as e:
        flash(f"Error deleting project: {str(e)}", "error")
        return redirect(url_for("research_views.projects"))


@research_views_bp.route(
    "/projects/<int:project_id>/generate-all-content", methods=["POST"]
)
@jwt_cookie_required
def generate_all_content(project_id):
    """Generate content for all sections in the background"""
    try:
        user_id = get_jwt_identity()
        project = ResearchProject.query.filter_by(
            id=project_id, user_id=user_id
        ).first()

        if not project:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": "Project not found"}), 404
            flash("Project not found", "error")
            return redirect(url_for("research_views.projects"))

        # Get the latest approved outline
        outline = (
            ResearchOutline.query.filter_by(project_id=project.id, is_approved=True)
            .order_by(ResearchOutline.created_at.desc())
            .first()
        )

        if not outline:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": "No approved outline found"}), 400
            flash("No approved outline found", "error")
            return redirect(
                url_for("research_views.project_detail", project_id=project_id)
            )

        # Get the outline structure
        outline_structure = outline.get_outline_structure()

        # Prepare the list of sections to generate
        sections_to_generate = []

        # Add introduction
        intro_title = "المقدمة" if project.language == "ar" else "Introduction"
        sections_to_generate.append(intro_title)

        # Add main sections
        for section in outline_structure.get("sections", []):
            sections_to_generate.append(section.get("title"))

        # Add conclusion
        conclusion_title = "الخاتمة" if project.language == "ar" else "Conclusion"
        sections_to_generate.append(conclusion_title)

        # Get existing content sections to skip already generated ones
        existing_content = ResearchContent.query.filter_by(
            project_id=project.id, outline_id=outline.id
        ).all()

        existing_section_titles = [
            content.section_title for content in existing_content
        ]

        # Filter out sections that already have content
        sections_to_generate = [
            section
            for section in sections_to_generate
            if section not in existing_section_titles
        ]

        # Start generating the first section
        if sections_to_generate:
            section_title = sections_to_generate[0]
            content_service = ContentService()
            content_data = content_service.generate_section_content(
                project,
                outline,
                section_title,
                [],
                project.citation_style,
                project.language,
                page_by_page=True,
            )

            if "error" not in content_data:
                content = ResearchContent.query.filter_by(
                    project_id=project.id,
                    outline_id=outline.id,
                    section_title=section_title,
                ).first()

                if not content:
                    content = ResearchContent(
                        project_id=project.id,
                        outline_id=outline.id,
                        section_title=section_title,
                    )

                content.from_json_response(content_data)
                db.session.add(content)
                db.session.commit()

        # Return the list of sections to be generated
        return jsonify(
            {
                "success": True,
                "message": "Content generation started",
                "sections": sections_to_generate,
                "project_id": project_id,
                "total_sections": len(sections_to_generate),
                "completed_sections": 1 if sections_to_generate else 0,
            }
        )

    except Exception as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": str(e)}), 500
        print(f"Error starting content generation: {str(e)}")
        flash(f"Error starting content generation: {str(e)}", "error")
        return redirect(url_for("research_views.project_detail", project_id=project_id))


@research_views_bp.route("/projects/<int:project_id>/content-status", methods=["GET"])
@jwt_cookie_required
def content_status(project_id):
    """Get the status of content generation for a project"""
    try:
        user_id = get_jwt_identity()
        project = ResearchProject.query.filter_by(
            id=project_id, user_id=user_id
        ).first()

        if not project:
            return jsonify({"error": "Project not found"}), 404

        # Get the latest approved outline
        outline = (
            ResearchOutline.query.filter_by(project_id=project.id, is_approved=True)
            .order_by(ResearchOutline.created_at.desc())
            .first()
        )

        if not outline:
            return jsonify({"error": "No approved outline found"}), 400

        # Get the outline structure
        outline_structure = outline.get_outline_structure()

        # Count total sections
        total_sections = (
            len(outline_structure.get("sections", [])) + 2
        )  # +2 for intro and conclusion

        # Get existing content sections
        existing_content = ResearchContent.query.filter_by(
            project_id=project.id, outline_id=outline.id
        ).all()

        completed_sections = len(existing_content)

        # Calculate word count
        total_words = sum(
            len(content.content.split()) if content.content else 0
            for content in existing_content
        )
        target_words = outline.total_pages * 250  # Assuming 250 words per page

        # Calculate percentages
        progress_percentage = (
            (completed_sections / total_sections) * 100 if total_sections > 0 else 0
        )
        word_percentage = (total_words / target_words) * 100 if target_words > 0 else 0

        return jsonify(
            {
                "success": True,
                "total_sections": total_sections,
                "completed_sections": completed_sections,
                "progress_percentage": progress_percentage,
                "total_words": total_words,
                "target_words": target_words,
                "word_percentage": word_percentage,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
