import google.generativeai as genai
from flask import current_app
import logging
import json

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for interacting with Google's Gemini API"""

    def __init__(self):
        self.api_key = current_app.config.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning(
                "Gemini API key not found. Service will not function properly."
            )
            return

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash-lite")

    def generate_research_outline(
        self, topic, complexity="medium", language="en", total_pages=10
    ):
        """
        Generate a research outline based on the given topic

        Args:
            topic (str): The research topic
            complexity (str): The complexity level (basic, medium, advanced)
            language (str): The language code (en, ar)
            total_pages (int): Total number of pages required

        Returns:
            dict: The generated outline structure
        """
        if not self.api_key:
            return {"error": "Gemini API key not configured"}

        try:
            # Add page count to prompt
            if language == "en":
                prompt = self._create_english_prompt(topic, complexity, total_pages)
            elif language == "ar":
                prompt = self._create_arabic_prompt(topic, complexity, total_pages)
            else:
                return {"error": f"Unsupported language: {language}"}

            response = self.model.generate_content(prompt)
            print(response.text)
            # Parse the response
            return self._parse_outline_response(response.text, topic)

        except Exception as e:
            logger.error(f"Error generating research outline: {str(e)}")
            return {"error": str(e)}

    def _create_english_prompt(self, topic, complexity, total_pages):
        """Create a prompt for English research outline"""
        complexity_descriptions = {
            "basic": "suitable for undergraduate level research",
            "medium": "suitable for graduate level research with moderate depth",
            "advanced": "suitable for doctoral level research with significant depth and complexity",
        }

        complexity_desc = complexity_descriptions.get(
            complexity, complexity_descriptions["medium"]
        )

        return f"""
        Create a detailed academic research outline for the topic: "{topic}"
        
        The outline should be {complexity_desc}.
        The research paper should be exactly {total_pages} pages in length.
        
        Format the outline as a hierarchical structure with:
        1. A clear thesis statement
        2. 3-5 research questions
        3. Main sections (Introduction, Literature Review, Methodology, Results, Discussion, Conclusion)
        4. Subsections for each main section (at least 3 per section)
        5. Key points to address in each subsection (at least 3 per subsection)
        6. Page count for each section and subsection, ensuring the total adds up to {total_pages} pages
        
        For the methodology section, include appropriate research methods based on the topic.
        
        Format your response as a structured JSON object with the following schema:
        {{
            "title": "Research Title",
            "thesis_statement": "The main argument or hypothesis",
            "research_questions": ["Question 1", "Question 2", ...],
            "total_pages": {total_pages},
            "sections": [
                {{
                    "title": "Section Title",
                    "pages": number_of_pages_for_this_section,
                    "page_range": {{
                        "start": starting_page_number,
                        "end": ending_page_number
                    }},
                    "subsections": [
                        {{
                            "title": "Subsection Title",
                            "pages": number_of_pages_for_this_subsection,
                            "key_points": ["Point 1", "Point 2", ...]
                        }},
                        ...
                    ]
                }},
                ...
            ]
        }}
        
        Ensure the JSON is valid and properly formatted.
        """

    def _create_arabic_prompt(self, topic, complexity, total_pages):
        """Create prompt in Arabic with the same JSON structure as the English one"""
        complexity_levels = {
            "basic": "مناسب لبحث في مرحلة البكالوريوس",
            "medium": "مناسب لبحث في مرحلة الماجستير وذو تعقيد متوسط",
            "advanced": "مناسب لبحث في مرحلة الدكتوراه وذو تعقيد عالٍ",
        }

        complexity_desc = complexity_levels.get(complexity, complexity_levels["medium"])

        return f"""
        أنشئ مخططًا تفصيليًا لورقة بحث أكاديمية حول الموضوع: "{topic}"
        
        يجب أن يكون المخطط {complexity_desc}.
        يجب أن يكون طول البحث حوالي {total_pages} صفحات.

        صِغ المخطط كبنية هرمية تحتوي على:
        1. عنوان واضح للبحث
        2. بيان الأطروحة (الفكرة أو الحجة الرئيسية)
        3. 3 إلى 5 أسئلة بحث
        4. أقسام رئيسية (المقدمة، مراجعة الأدبيات، المنهجية، النتائج، المناقشة، الخاتمة)
        5. 3 فروع فرعية على الأقل لكل قسم رئيسي
        6. 3 نقاط رئيسية على الأقل لكل فرع فرعي
        7. عدد الصفحات لكل قسم وفرع فرعي، مع التأكد من أن المجموع الكلي يساوي {total_pages} صفحات

        في قسم المنهجية، استخدم طرق البحث المناسبة بناءً على الموضوع.

        صيّغ الناتج ككائن JSON بالهيكل التالي:
        {{
            "title": "عنوان البحث",
            "thesis_statement": "بيان الأطروحة",
            "research_questions": ["سؤال 1", "سؤال 2", ...],
            "total_pages": {total_pages},
            "sections": [
                {{
                    "title": "عنوان القسم",
                    "pages": عدد_الصفحات_لهذا_القسم,
                    "page_range": {{
                        "start": رقم_الصفحة_البداية,
                        "end": رقم_الصفحة_النهاية
                    }},
                    "subsections": [
                        {{
                            "title": "عنوان الفرع الفرعي",
                            "pages": عدد_الصفحات_لهذا_الفرع_الفرعي,
                            "key_points": ["نقطة 1", "نقطة 2", ...]
                        }},
                        ...
                    ]
                }},
                ...
            ]
        }}

        تأكد من أن الناتج عبارة عن JSON صالح ومنسق بشكل صحيح.
        """

    def _parse_outline_response(self, response_text, topic):
        """Parse the response from Gemini API into a structured outline"""
        try:
            # Try to extract JSON from the response
            # First, look for JSON block in markdown
            if (
                "```json" in response_text
                and "```" in response_text.split("```json")[1]
            ):
                json_text = response_text.split("```json")[1].split("```")[0].strip()
                outline = json.loads(json_text)
            # If not found, try to parse the entire response as JSON
            else:
                try:
                    outline = json.loads(response_text)
                except:
                    # If that fails, try to extract anything that looks like JSON
                    start_idx = response_text.find("{")
                    end_idx = response_text.rfind("}") + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        json_text = response_text[start_idx:end_idx]
                        outline = json.loads(json_text)
                    else:
                        raise ValueError("Could not extract JSON from response")

            # Validate the outline structure
            if not all(
                k in outline
                for k in ("title", "thesis_statement", "research_questions", "sections")
            ):
                # If missing required fields, create a basic structure
                if "title" not in outline:
                    outline["title"] = topic
                if "thesis_statement" not in outline:
                    outline["thesis_statement"] = (
                        "Generated thesis statement placeholder"
                    )
                if "research_questions" not in outline:
                    outline["research_questions"] = [
                        "Generated research question placeholder"
                    ]
                if "sections" not in outline:
                    outline["sections"] = [
                        {
                            "title": "Introduction",
                            "subsections": [
                                {
                                    "title": "Background",
                                    "key_points": ["Generated key point placeholder"],
                                }
                            ],
                        }
                    ]

            return outline

        except Exception as e:
            logger.error(f"Error parsing outline response: {str(e)}")
            # Return a basic outline structure as fallback
            return {
                "title": topic,
                "thesis_statement": "Could not generate thesis statement due to parsing error",
                "research_questions": [
                    "Could not generate research questions due to parsing error"
                ],
                "sections": [
                    {
                        "title": "Introduction",
                        "subsections": [
                            {
                                "title": "Background",
                                "key_points": ["Please regenerate the outline"],
                            }
                        ],
                    }
                ],
                "parsing_error": str(e),
            }
