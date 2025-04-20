from app import db
from datetime import datetime
import json
from app.models.research import ResearchProject, ResearchOutline


class ResearchContent(db.Model):
    __tablename__ = "research_content"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "research_projects.id",
            ondelete="CASCADE",
            name="fk_research_content_project",
        ),
        nullable=False,
    )
    outline_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "research_outlines.id",
            ondelete="CASCADE",
            name="fk_research_content_outline",
        ),
        nullable=False,
    )
    section_title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    citations = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Add relationships
    project = db.relationship("ResearchProject", backref="contents")
    outline = db.relationship("ResearchOutline", backref="contents")

    def get_citations(self):
        """Get citations as a list of dictionaries"""
        if not self.citations:
            return []

        try:
            return json.loads(self.citations)
        except json.JSONDecodeError:
            return []

    def set_citations(self, citations):
        """Set citations from a list of dictionaries or JSON string"""

        try:
            if isinstance(citations, list):
                self.citations = json.dumps(citations)
            elif isinstance(citations, str):
                # Check if it's already a JSON string
                try:
                    json.loads(citations)
                    self.citations = citations
                except json.JSONDecodeError:
                    # If not valid JSON, store as empty array
                    self.citations = "[]"
            elif isinstance(citations, dict):
                # If it's a dictionary (should be a single citation)
                self.citations = json.dumps([citations])
            else:
                self.citations = "[]"
        except Exception as e:
            # If anything goes wrong, default to empty array
            self.citations = "[]"
            print(f"Error setting citations: {str(e)}")

    def from_json_response(self, json_data):
        """
        Parse a complete JSON response from AI and update the content object

        Args:
            json_data: JSON data as string or dictionary
        """
        try:
            if isinstance(json_data, str):
                try:
                    data = json.loads(json_data)
                except json.JSONDecodeError:
                    # If it's not valid JSON, just use it as content
                    self.content = json_data
                    return
            else:
                data = json_data

            # Update fields from the JSON data
            if "section_title" in data and data["section_title"]:
                self.section_title = data["section_title"]

            if "content" in data and data["content"]:
                self.content = data["content"]

            if "citations" in data:
                self.set_citations(data["citations"])

            # Additional metadata can be stored if needed
            if "page_range" in data:
                # This could be extended to store in a separate column if needed
                pass
        except Exception as e:
            print(f"Error parsing JSON response: {str(e)}")
            # If parsing fails, at least store what we received
            if isinstance(json_data, str):
                self.content = json_data
            elif isinstance(json_data, dict) and "content" in json_data:
                self.content = json_data["content"]

    def get_formatted_content(self, include_citations=True):
        """
        Get formatted content with citations for export
        
        Args:
            include_citations: Whether to include citations at the end
            
        Returns:
            Formatted content string
        """
        formatted_content = self.content or ""
        
        if include_citations and self.citations:
            citations = self.get_citations()
            if citations:
                formatted_content += "\n\n"
                if any(citation.get('language') == 'ar' for citation in citations if isinstance(citation, dict)):
                    formatted_content += "المراجع:\n"
                else:
                    formatted_content += "References:\n"
                
                for i, citation in enumerate(citations):
                    if isinstance(citation, dict):
                        formatted_content += f"{i+1}. {citation.get('text', '')}\n"
        
        return formatted_content

    def __repr__(self):
        return f"<ResearchContent {self.section_title} for Project {self.project_id}>"
