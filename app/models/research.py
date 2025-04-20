from app import db
from datetime import datetime
import json


class ResearchProject(db.Model):
    __tablename__ = "research_projects"
    """Research project model"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    language = db.Column(db.String(10), default="en")
    citation_style = db.Column(db.String(20), default="APA")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = db.relationship("User", backref=db.backref("research_projects", lazy=True))
    outlines = db.relationship("ResearchOutline", backref="project", lazy=True)

    def __repr__(self):
        return f"<ResearchProject {self.title}>"


class ResearchOutline(db.Model):
    """Research outline model"""

    __tablename__ = "research_outlines"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("research_projects.id"), nullable=False
    )
    outline_data = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    total_pages = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def calculate_section_pages(self):
        """Convert string page counts to numbers and validate"""
        structure = self.get_outline_structure()

        # Convert string page counts to float
        for section in structure.get("sections", []):
            if "pages" in section:
                try:
                    section["pages"] = float(section["pages"])
                except (ValueError, TypeError):
                    section["pages"] = 1.0

            for subsection in section.get("subsections", []):
                if "pages" in subsection:
                    try:
                        subsection["pages"] = float(subsection["pages"])
                    except (ValueError, TypeError):
                        subsection["pages"] = 1.0

        self.set_outline_structure(structure)
        return structure

    def generate_index(self, language="en"):
        """Generate index (فهرس) for the research"""
        structure = self.get_outline_structure()
        index = []
        current_page = 1

        title = structure.get("title", "Research Paper")
        index.append({"title": title, "page": current_page})
        current_page += 1

        if language == "en":
            index_title = "Table of Contents"
        else:
            index_title = "فهرس المحتويات"

        index.append({"title": index_title, "page": current_page})
        current_page += 1

        if language == "en":
            intro_title = "Introduction"
        else:
            intro_title = "المقدمة"

        intro_pages = structure.get("introduction_pages", 1)
        intro_page_range = structure.get(
            "introduction_page_range", {"start": current_page}
        )

        index.append(
            {"title": intro_title, "page": intro_page_range.get("start", current_page)}
        )
        current_page = intro_page_range.get("end", current_page + intro_pages) + 1

        for section in structure.get("sections", []):
            section_title = section.get("title")
            page_range = section.get("page_range", {"start": current_page})

            index.append(
                {"title": section_title, "page": page_range.get("start", current_page)}
            )

            for subsection in section.get("subsections", []):
                index.append(
                    {
                        "title": subsection.get("title"),
                        "page": page_range.get("start", current_page),
                        "indent": True,
                    }
                )

            current_page = (
                page_range.get("end", current_page + section.get("pages", 1)) + 1
            )

        if language == "en":
            conclusion_title = "Conclusion"
        else:
            conclusion_title = "الخاتمة"

        conclusion_page_range = structure.get(
            "conclusion_page_range", {"start": current_page}
        )

        index.append(
            {
                "title": conclusion_title,
                "page": conclusion_page_range.get("start", current_page),
            }
        )

        if language == "en":
            references_title = "References"
        else:
            references_title = "المراجع"

        current_page = conclusion_page_range.get("end", current_page) + 1

        index.append({"title": references_title, "page": current_page})

        return index

    def set_outline_structure(self, structure):
        """Set the outline structure from a Python object"""
        self.outline_data = json.dumps(structure)

    def get_outline_structure(self):
        """Get outline structure from JSON data"""
        return json.loads(self.outline_data) if self.outline_data else {}

    def get_ordered_sections(self):
        """
        Get all sections in the correct order for export

        Returns:
            List of section titles in order
        """
        structure = self.get_outline_structure()
        sections = []

        # Add main sections
        for section in structure.get("sections", []):
            sections.append(section.get("title"))

        return sections

    def __repr__(self):
        return f"<ResearchOutline for Project {self.project_id}>"
