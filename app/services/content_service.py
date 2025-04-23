import google.generativeai as genai
from flask import current_app
import logging
import json
from app.services.gemini_service import GeminiService
import gc
import time
import psutil
import os

logger = logging.getLogger(__name__)


class ContentService:
    """Service for generating research content"""

    def __init__(self):
        self.gemini_service = GeminiService()
        self.api_key = current_app.config.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning(
                "Gemini API key not found. Service will not function properly."
            )
            return

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash-lite")

    def generate_section_content(
        self,
        project,
        outline,
        section_title,
        subsection_titles,
        citation_style,
        language="en",
        page_by_page=True,
    ):
        """Generate content for a specific section"""
        try:
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            logger.info(f"Initial memory usage: {initial_memory:.2f} MB")
            outline_structure = outline.get_outline_structure()
            section = None
            for s in outline_structure.get("sections", []):
                if s.get("title") == section_title:
                    section = s
                    break

            if not section:
                return {"error": f"Section '{section_title}' not found in outline"}

            pages = section.get("pages", 1)
            words_per_page = 250
            target_words = int(pages * words_per_page)

            page_range = section.get("page_range", {"start": 1, "end": int(pages)})

            # If not generating page by page, use the original approach
            if not page_by_page:
                if language == "en":
                    prompt = self._create_english_content_prompt(
                        project.title,
                        outline_structure.get("thesis_statement", ""),
                        section_title,
                        section.get("subsections", []),
                        citation_style,
                        target_words,
                        page_range,
                    )
                elif language == "ar":
                    prompt = self._create_arabic_content_prompt(
                        project.title,
                        outline_structure.get("thesis_statement", ""),
                        section_title,
                        section.get("subsections", []),
                        citation_style,
                        target_words,
                        page_range,
                    )
                else:
                    return {"error": f"Unsupported language: {language}"}

                # Generate content with increased timeout
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.7,
                        "top_p": 0.8,
                        "top_k": 40,
                        "max_output_tokens": 2048,
                    },
                    safety_settings=[
                        {
                            "category": "HARM_CATEGORY_HARASSMENT",
                            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                        },
                        {
                            "category": "HARM_CATEGORY_HATE_SPEECH",
                            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                        },
                        {
                            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                        },
                        {
                            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                            "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                        },
                    ],
                )

                # Parse the response and include page range
                content_data = self._parse_content_response(
                    response.text, section_title, subsection_titles
                )

                return content_data

            # Page by page generation approach
            else:
                # Initialize the combined content data
                combined_content = {
                    "section_title": section_title,
                    "content": "",
                    "citations": [],
                    "page_range": page_range,
                }

                # Calculate the number of pages
                total_pages = page_range["end"] - page_range["start"] + 1
                
                # Reduce batch size for larger sections to prevent memory issues
                max_pages_per_batch = 2 if total_pages > 5 else 3
                
                logger.info(f"Processing {total_pages} pages in batches of {max_pages_per_batch}")
                
                for batch_start in range(
                    page_range["start"], page_range["end"] + 1, max_pages_per_batch
                ):
                    batch_end = min(
                        batch_start + max_pages_per_batch - 1, page_range["end"]
                    )
                    logger.info(f"Generating batch from page {batch_start} to {batch_end}")
                    
                    for page_num in range(batch_start, batch_end + 1):
                        current_page = {"start": page_num, "end": page_num}
                        # Words per page
                        page_target_words = words_per_page

                        # Create a prompt for this specific page
                        if language == "en":
                            prompt = self._create_english_page_prompt(
                                project.title,
                                outline_structure.get("thesis_statement", ""),
                                section_title,
                                section.get("subsections", []),
                                citation_style,
                                page_target_words,
                                current_page,
                                page_num - page_range["start"] + 1,
                                total_pages,
                                combined_content["content"],
                            )
                        elif language == "ar":
                            prompt = self._create_arabic_page_prompt(
                                project.title,
                                outline_structure.get("thesis_statement", ""),
                                section_title,
                                section.get("subsections", []),
                                citation_style,
                                page_target_words,
                                current_page,
                                page_num - page_range["start"] + 1,
                                total_pages,
                                combined_content["content"],
                            )
                        else:
                            return {"error": f"Unsupported language: {language}"}

                        try:
                            start_time = time.time()

                            response = self.model.generate_content(
                                prompt,
                                generation_config={
                                    "temperature": 0.7,
                                    "top_p": 0.8,
                                    "top_k": 40,
                                    "max_output_tokens": 2048,
                                },
                                safety_settings=[
                                    {
                                        "category": "HARM_CATEGORY_HARASSMENT",
                                        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                                    },
                                    {
                                        "category": "HARM_CATEGORY_HATE_SPEECH",
                                        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                                    },
                                    {
                                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                                    },
                                    {
                                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                                        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                                    },
                                ],
                            )

                            elapsed_time = time.time() - start_time
                            logger.info(f"Page generation took {elapsed_time:.2f} seconds")

                            page_content = self._parse_content_response(
                                response.text, section_title, subsection_titles
                            )

                            if page_num > page_range["start"]:
                                combined_content["content"] += "\n\n"
                            combined_content["content"] += page_content.get(
                                "content", ""
                            )

                            for citation in page_content.get("citations", []):
                                citation_exists = False
                                for existing_citation in combined_content["citations"]:
                                    if existing_citation.get("id") == citation.get(
                                        "id"
                                    ):
                                        citation_exists = True
                                        break

                                if not citation_exists:
                                    combined_content["citations"].append(citation)

                        except Exception as page_error:
                            logger.error(
                                f"Error generating page {page_num}: {str(page_error)}"
                            )
                            combined_content[
                                "content"
                            ] += f"\n\n[Content generation for page {page_num} failed: {str(page_error)}]\n\n"
                            continue
                    
                    # Force garbage collection after each batch
                    gc.collect()
                    
                    # Log memory usage after each batch
                    current_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_diff = current_memory - initial_memory
                    logger.info(
                        f"Memory after batch {batch_start}-{batch_end}: {current_memory:.2f} MB (change: {memory_diff:+.2f} MB)"
                    )
                    
                    # Add a small delay between batches to allow memory cleanup
                    time.sleep(1)
                
                # Final memory usage report
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_diff = current_memory - initial_memory
                logger.info(
                    f"Final memory usage: {current_memory:.2f} MB (change: {memory_diff:+.2f} MB)"
                )
                return combined_content
        except Exception as e:
            logger.error(f"Error generating section content: {str(e)}")
            return {"error": str(e)}

    def _create_english_page_prompt(
        self,
        title,
        thesis,
        section_title,
        subsections,
        citation_style,
        target_words,
        page_range,
        current_page_num,
        total_pages,
        previous_content="",
    ):
        """Create a prompt for English content generation for a single page"""
        subsection_text = ""
        for subsection in subsections:
            subsection_text += f"- {subsection.get('title')}\n"
            for point in subsection.get("key_points", []):
                subsection_text += f"  - {point}\n"

        context = ""
        if previous_content:
            context = f"""
            Previous content generated for this section:
            {previous_content[:1000]}... [truncated]
            
            Continue from where the previous content left off, maintaining consistency.
            """

        return f"""
        Generate academic content for page {current_page_num} of {total_pages} of the "{section_title}" section in a research paper titled "{title}".
        
        Thesis statement: {thesis}
        
        {context}
        
        The section should cover the following subsections and key points:
        {subsection_text}
        
        Requirements:
        1. Write in a formal academic style appropriate for scholarly publication
        2. Include at least 1-2 citations using {citation_style} format
        3. Ensure logical flow with previous content
        4. Use appropriate academic terminology
        5. Write approximately {target_words} words for this page
        6. This is page {page_range['start']} in the final document
        7. If this is not the first page, continue naturally from the previous content
        8. write the content in markdown format
        Format your response as a structured JSON object with the following schema:
        {{
            "section_title": "{section_title}",
            "content": "The content for this page with citations in {citation_style} format",
            "citations": [
                {{
                    "id": "citation1",
                    "text": "Full citation text in {citation_style} format", // (markdown)
                    "source_type": "journal/book/website/etc.",
                }},
                ...
            ],
            "page_number": {current_page_num}
        }}
        
        Ensure the JSON is valid and properly formatted.
        """

    def _create_arabic_page_prompt(
        self,
        title,
        thesis,
        section_title,
        subsections,
        citation_style,
        target_words,
        page_range,
        current_page_num,
        total_pages,
        previous_content="",
    ):
        """Create a prompt for Arabic content generation for a single page"""
        subsection_text = ""
        for subsection in subsections:
            subsection_text += f"- {subsection.get('title')}\n"
            for point in subsection.get("key_points", []):
                subsection_text += f"  - {point}\n"

        context = ""
        if previous_content:
            context = f"""
            المحتوى السابق المولد لهذا القسم:
            {previous_content[:1000]}... [مختصر]
            
            استمر من حيث انتهى المحتوى السابق، مع الحفاظ على الاتساق.
            """

        return f"""
        قم بإنشاء محتوى أكاديمي للصفحة {current_page_num} من {total_pages} من قسم "{section_title}" في ورقة بحثية بعنوان "{title}".
        
        بيان الأطروحة: {thesis}
        
        {context}
        
        يجب أن يغطي القسم النقاط الفرعية التالية:
        {subsection_text}
        
        المتطلبات:
        1. اكتب حوالي {target_words} كلمة لهذه الصفحة
        2. قم بتضمين 1-2 اقتباسات على الأقل
        3. استخدم تنسيق {citation_style} للمراجع
        4. اكتب بأسلوب أكاديمي رسمي
        5. قم بتنظيم المحتوى في فقرات واضحة
        6. هذه هي الصفحة {page_range['start']} في البحث النهائي
        7. إذا لم تكن هذه الصفحة الأولى، استمر بشكل طبيعي من المحتوى السابق
        8. قم بكنابة المحتوى باسلوب (markdown)
        قم بتنسيق الإجابة بتنسيق JSON كما يلي:
        {{
            "section_title": "{section_title}",
            "content": "محتوى هذه الصفحة مع المراجع بتنسيق {citation_style}", // (markdown)
            "citations": [
                {{
                    "id": "citation1",
                    "text": "نص المرجع بتنسيق {citation_style}",
                    "source_type": "نوع المصدر",
                }},
                ...
            ],
            "page_number": {current_page_num}
        }}
        
        تأكد من أن JSON صالح ومنسق بشكل صحيح.
        """

    def _parse_content_response(self, response_text, section_title, subsection_titles):
        """Parse the response from Gemini API into structured content"""
        try:
            # Clean up the response text
            response_text = response_text.strip()

            # Find JSON content - look for JSON blocks first
            json_text = None

            # Check for ```json blocks
            start_idx = response_text.find("```json")
            if start_idx >= 0:
                end_idx = response_text.find("```", start_idx + 6)
                if end_idx > start_idx:
                    json_text = response_text[start_idx + 7 : end_idx].strip()

            # If no JSON blocks found, look for just ``` blocks
            if json_text is None:
                start_idx = response_text.find("```")
                if start_idx >= 0:
                    end_idx = response_text.find("```", start_idx + 3)
                    if end_idx > start_idx:
                        json_text = response_text[start_idx + 3 : end_idx].strip()

            # If still no JSON blocks, check if the entire response is JSON
            if json_text is None:
                if response_text.strip().startswith(
                    "{"
                ) and response_text.strip().endswith("}"):
                    json_text = response_text.strip()

            # If we couldn't find any JSON content, create a basic structure
            if json_text is None:
                logger.warning(
                    f"No JSON found in response for section: {section_title}"
                )
                return {
                    "section_title": section_title,
                    "content": response_text,
                    "citations": [],
                }

            # Now try to parse the JSON
            try:
                content_data = json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.warning(f"Initial JSON parsing failed: {str(e)}")
                # Try fixing common JSON issues
                fixed_json = json_text

                # Replace single quotes with double quotes
                fixed_json = fixed_json.replace("'", '"')

                # Replace True/False/None with JavaScript equivalents
                fixed_json = fixed_json.replace("True", "true")
                fixed_json = fixed_json.replace("False", "false")
                fixed_json = fixed_json.replace("None", "null")

                # Try to fix unescaped quotes in strings
                fixed_json = self._fix_unescaped_quotes(fixed_json)

                # Additional fixes for Arabic text and newlines
                fixed_json = self._fix_arabic_json(fixed_json)

                # Try more aggressive JSON repair if still failing
                try:
                    content_data = json.loads(fixed_json)
                except json.JSONDecodeError as e2:
                    logger.warning(
                        f"Standard fixes failed: {str(e2)}, trying advanced repair"
                    )
                    try:
                        # Try manual extraction of key components
                        content_data = self._manual_json_extraction(
                            fixed_json, section_title
                        )
                    except Exception as e3:
                        logger.error(f"Failed to parse JSON after all fixes: {str(e3)}")
                        # If all parsing fails, return the raw text with proper structure
                        return {
                            "section_title": section_title,
                            "content": response_text,
                            "citations": [],
                        }

            # Validate the content structure
            if not isinstance(content_data, dict):
                logger.warning(
                    "Content data is not a dictionary, converting to proper format"
                )
                return {
                    "section_title": section_title,
                    "content": str(content_data),
                    "citations": [],
                }

            # Ensure required fields exist
            required_fields = ["section_title", "content", "citations"]
            for field in required_fields:
                if field not in content_data:
                    if field == "citations":
                        content_data[field] = []
                    else:
                        content_data[field] = (
                            "" if field == "content" else section_title
                        )

            # If section_title is empty, use the provided one
            if not content_data["section_title"]:
                content_data["section_title"] = section_title

            # Ensure citations is a list
            if not isinstance(content_data["citations"], list):
                logger.warning("Citations is not a list, converting to empty list")
                content_data["citations"] = []

            logger.info(f"Successfully parsed content for section: {section_title}")
            logger.info(f"Content length: {len(content_data.get('content', ''))}")
            logger.info(f"Citations count: {len(content_data.get('citations', []))}")

            return content_data

        except Exception as e:
            logger.error(f"Error parsing content response: {str(e)}")
            return {
                "section_title": section_title,
                "content": response_text,
                "citations": [],
            }

    def _fix_unescaped_quotes(self, json_text):
        """Try to fix unescaped quotes in JSON strings"""
        # This is a simplified approach - in a production environment, you might want
        # a more sophisticated JSON repair library
        result = ""
        in_string = False
        escape_next = False

        for char in json_text:
            if char == '"' and not escape_next:
                in_string = not in_string
            elif char == "\\" and not escape_next:
                escape_next = True
            else:
                escape_next = False

            # If we're in a string and encounter an unescaped quote, escape it
            if in_string and char == '"' and not escape_next:
                result += "\\"

            result += char

        return result

    def _fix_arabic_json(self, json_text):
        """Fix common issues with Arabic text in JSON"""
        # Replace problematic newlines within strings
        import re

        # First, try to normalize newlines
        json_text = json_text.replace("\r\n", "\\n").replace("\n", "\\n")

        # Fix newlines in content field
        content_pattern = re.compile(
            r'"content":\s*"(.*?)"(?=\s*,\s*"citations"|$)', re.DOTALL
        )
        match = content_pattern.search(json_text)
        if match:
            content = match.group(1)
            # Escape newlines properly
            fixed_content = content.replace("\n", "\\n")
            # Replace with fixed content
            json_text = (
                json_text[: match.start(1)] + fixed_content + json_text[match.end(1) :]
            )

        # Fix potential issues with Arabic quotes and special characters
        json_text = json_text.replace("،", ",")  # Arabic comma
        json_text = json_text.replace("؛", ";")  # Arabic semicolon
        json_text = json_text.replace("«", '"').replace("»", '"')  # Arabic quotes
        json_text = json_text.replace("؟", "?")  # Arabic question mark

        return json_text

    def _manual_json_extraction(self, json_text, section_title):
        """Manually extract JSON components when standard parsing fails"""
        import re

        # Initialize with default structure
        result = {"section_title": section_title, "content": "", "citations": []}

        # Try to extract section_title
        title_match = re.search(r'"section_title"\s*:\s*"([^"]+)"', json_text)
        if title_match:
            result["section_title"] = title_match.group(1)

        # Try to extract content
        content_match = re.search(
            r'"content"\s*:\s*"(.*?)(?:"|$)(?=\s*,\s*"citations"|$)',
            json_text,
            re.DOTALL,
        )
        if content_match:
            # Clean up content - replace escaped newlines and quotes
            content = content_match.group(1)
            content = content.replace("\\n", "\n").replace('\\"', '"')
            result["content"] = content
        else:
            # If no content match, use everything between content and citations as fallback
            content_start = json_text.find('"content"')
            citations_start = json_text.find('"citations"')
            if content_start > 0 and citations_start > content_start:
                content_text = json_text[content_start:citations_start].strip()
                # Remove the "content": part
                if ":" in content_text:
                    content_text = content_text.split(":", 1)[1].strip()
                # Remove trailing comma and quotes
                content_text = content_text.rstrip(",").strip('"')
                result["content"] = content_text

        # Try to extract citations
        citations_match = re.search(
            r'"citations"\s*:\s*(\[.*?\])', json_text, re.DOTALL
        )
        if citations_match:
            citations_text = citations_match.group(1)
            try:
                # Try to parse the citations array
                citations = json.loads(citations_text)
                result["citations"] = citations
            except json.JSONDecodeError:
                # If parsing fails, try to extract individual citations
                citation_matches = re.finditer(
                    r'\{\s*"id"\s*:\s*"([^"]+)"\s*,\s*"text"\s*:\s*"([^"]+)"\s*,\s*"source_type"\s*:\s*"([^"]+)"\s*\}',
                    citations_text,
                )
                for match in citation_matches:
                    citation = {
                        "id": match.group(1),
                        "text": match.group(2),
                        "source_type": match.group(3),
                    }
                    result["citations"].append(citation)

        return result

    def process_json_content(self, json_data, section_title):
        """
        Process JSON content directly

        Args:
            json_data: JSON data containing content and citations
            section_title: The title of the section

        Returns:
            dict: Processed content data
        """
        try:
            # If json_data is a string, parse it
            if isinstance(json_data, str):
                content_data = json.loads(json_data)
            else:
                content_data = json_data

            # Ensure required fields exist
            required_fields = ["section_title", "content", "citations"]
            for field in required_fields:
                if field not in content_data:
                    content_data[field] = "" if field != "citations" else []

            # Override section_title if provided
            if section_title:
                content_data["section_title"] = section_title

            return content_data

        except Exception as e:
            logger.error(f"Error processing JSON content: {str(e)}")
            return {
                "section_title": section_title,
                "content": str(json_data),
                "citations": [],
            }
