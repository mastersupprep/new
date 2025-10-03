from fastapi import FastAPI, APIRouter, HTTPException, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from supabase import create_client, Client
import google.generativeai as genai
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Supabase connection
supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_ANON_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

# Gemini AI configuration with round-robin keys
GEMINI_API_KEYS = os.environ.get('GEMINI_API_KEYS', '').split(',')
GEMINI_API_KEYS = [key.strip() for key in GEMINI_API_KEYS if key.strip()]

# Track current key index and failed keys
current_key_index = 0
failed_keys = set()

def get_next_working_gemini_key():
    """Get the next working Gemini API key using round-robin"""
    global current_key_index
    
    if not GEMINI_API_KEYS:
        raise HTTPException(status_code=500, detail="No Gemini API keys configured")
    
    # Remove failed keys from available keys
    available_keys = [key for key in GEMINI_API_KEYS if key not in failed_keys]
    
    if not available_keys:
        # Reset failed keys if all keys have failed (maybe quotas reset)
        failed_keys.clear()
        available_keys = GEMINI_API_KEYS
    
    # Use round-robin to select next key
    key = available_keys[current_key_index % len(available_keys)]
    current_key_index = (current_key_index + 1) % len(available_keys)
    
    return key

def create_gemini_model_with_key(api_key: str):
    """Create a Gemini model with the specified API key"""
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.0-flash')

# Create the main app
app = FastAPI(title="Question Maker API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Pydantic models
class ExamResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

class CourseResponse(BaseModel):
    id: str
    exam_id: str
    name: str
    description: Optional[str] = None

class SubjectResponse(BaseModel):
    id: str
    course_id: str
    name: str
    description: Optional[str] = None

class UnitResponse(BaseModel):
    id: str
    subject_id: str
    name: str
    description: Optional[str] = None

class ChapterResponse(BaseModel):
    id: str
    unit_id: str
    name: str
    description: Optional[str] = None

class TopicResponse(BaseModel):
    id: str
    chapter_id: str
    name: str
    description: Optional[str] = None
    weightage: Optional[float] = None

class PartResponse(BaseModel):
    id: str
    part_name: str
    course_id: str

class SlotResponse(BaseModel):
    id: str
    slot_name: str
    course_id: str

class QuestionRequest(BaseModel):
    topic_id: str
    question_type: str  # MCQ, MSQ, NAT, SUB
    part_id: Optional[str] = None
    slot_id: Optional[str] = None

class GeneratedQuestion(BaseModel):
    id: str
    topic_id: str
    topic_name: str
    question_statement: str
    question_type: str
    options: Optional[List[str]] = None
    answer: str
    solution: str
    difficulty_level: str
    part_id: Optional[str] = None
    slot_id: Optional[str] = None
    created_at: datetime

# New models for enhanced functionality
class AutoGenerationConfig(BaseModel):
    correct_marks: float
    incorrect_marks: float
    skipped_marks: float
    time_minutes: float
    total_questions: int

class AutoGenerationSession(BaseModel):
    id: str
    exam_id: str
    course_id: str
    config: AutoGenerationConfig
    current_subject_idx: int = 0
    current_unit_idx: int = 0
    current_chapter_idx: int = 0
    current_topic_idx: int = 0
    questions_generated: int = 0
    questions_target: int
    is_paused: bool = False
    is_completed: bool = False
    generation_mode: str = "new_questions"  # "new_questions" or "pyq_solutions"
    created_at: datetime
    updated_at: datetime

class TopicWithWeightage(BaseModel):
    id: str
    name: str
    weightage: Optional[float] = None
    chapter_id: str
    chapter_name: str
    unit_id: str
    unit_name: str
    subject_id: str
    subject_name: str
    estimated_questions: int = 0

class AutoGenerationProgress(BaseModel):
    session_id: str
    progress_percentage: float
    current_topic: Optional[str] = None
    questions_generated: int
    questions_target: int
    estimated_time_remaining: Optional[float] = None
    can_pause: bool = True

class PYQSolutionRequest(BaseModel):
    topic_id: str
    question_statement: str
    options: Optional[List[str]] = None
    question_type: str

class PYQSolutionResponse(BaseModel):
    question_statement: str
    answer: str
    solution: str
    confidence_level: str

# API Routes

@api_router.get("/")
async def root():
    return {"message": "Question Maker API is running"}

@api_router.get("/exams", response_model=List[ExamResponse])
async def get_exams():
    """Get all available exams"""
    try:
        result = supabase.table("exams").select("*").execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching exams: {str(e)}")

@api_router.get("/courses/{exam_id}", response_model=List[CourseResponse])
async def get_courses(exam_id: str):
    """Get courses for a specific exam"""
    try:
        result = supabase.table("courses").select("*").eq("exam_id", exam_id).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching courses: {str(e)}")

@api_router.get("/subjects/{course_id}", response_model=List[SubjectResponse])
async def get_subjects(course_id: str):
    """Get subjects for a specific course"""
    try:
        result = supabase.table("subjects").select("*").eq("course_id", course_id).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching subjects: {str(e)}")

@api_router.get("/units/{subject_id}", response_model=List[UnitResponse])
async def get_units(subject_id: str):
    """Get units for a specific subject"""
    try:
        result = supabase.table("units").select("*").eq("subject_id", subject_id).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching units: {str(e)}")

@api_router.get("/chapters/{unit_id}", response_model=List[ChapterResponse])
async def get_chapters(unit_id: str):
    """Get chapters for a specific unit"""
    try:
        result = supabase.table("chapters").select("*").eq("unit_id", unit_id).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chapters: {str(e)}")

@api_router.get("/topics/{chapter_id}", response_model=List[TopicResponse])
async def get_topics(chapter_id: str):
    """Get topics for a specific chapter"""
    try:
        result = supabase.table("topics").select("*").eq("chapter_id", chapter_id).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching topics: {str(e)}")

@api_router.get("/parts/{course_id}", response_model=List[PartResponse])
async def get_parts(course_id: str):
    """Get parts for a specific course"""
    try:
        result = supabase.table("parts").select("*").eq("course_id", course_id).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching parts: {str(e)}")

@api_router.get("/slots/{course_id}", response_model=List[SlotResponse])
async def get_slots(course_id: str):
    """Get slots for a specific course"""
    try:
        result = supabase.table("slots").select("*").eq("course_id", course_id).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching slots: {str(e)}")

@api_router.get("/existing-questions/{topic_id}")
async def get_existing_questions(topic_id: str):
    """Get existing questions for a topic for reference"""
    try:
        result = supabase.table("questions_topic_wise").select("question_statement, options, answer, solution, question_type").eq("topic_id", topic_id).limit(5).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching existing questions: {str(e)}")

@api_router.get("/generated-questions/{topic_id}")
async def get_generated_questions(topic_id: str):
    """Get previously generated questions for a topic"""
    try:
        result = supabase.table("new_questions").select("*").eq("topic_id", topic_id).order("created_at", desc=True).limit(10).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching generated questions: {str(e)}")

def validate_question_answer(question_type: str, options: List[str], answer: str) -> bool:
    """Validate that the question answer follows the rules"""
    if question_type == "MCQ":
        # MCQ should have exactly one correct answer
        try:
            answer_indices = [int(x.strip()) for x in answer.split(",") if x.strip().isdigit()]
            return len(answer_indices) == 1 and all(0 <= idx < len(options) for idx in answer_indices)
        except:
            return False
    elif question_type == "MSQ":
        # MSQ should have one or more correct answers
        try:
            answer_indices = [int(x.strip()) for x in answer.split(",") if x.strip().isdigit()]
            return len(answer_indices) >= 1 and all(0 <= idx < len(options) for idx in answer_indices)
        except:
            return False
    elif question_type == "NAT":
        # NAT should be a numerical value
        try:
            float(answer)
            return True
        except:
            return False
    elif question_type == "SUB":
        # SUB can be any text
        return len(answer.strip()) > 0
    return False

@api_router.post("/generate-question", response_model=GeneratedQuestion)
async def generate_question(request: QuestionRequest):
    """Generate a new question using Gemini AI"""
    try:
        # Get topic information
        topic_result = supabase.table("topics").select("*").eq("id", request.topic_id).execute()
        if not topic_result.data:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        topic = topic_result.data[0]
        
        # Get chapter information for context
        chapter_result = supabase.table("chapters").select("*").eq("id", topic["chapter_id"]).execute()
        chapter = chapter_result.data[0] if chapter_result.data else {}
        
        # Get existing questions for reference (but not to copy)
        existing_questions = supabase.table("questions_topic_wise").select("question_statement, options, question_type").eq("topic_id", request.topic_id).limit(5).execute()
        
        # Get previously generated questions to avoid repetition
        generated_questions = supabase.table("new_questions").select("question_statement").eq("topic_id", request.topic_id).limit(10).execute()
        
        # Create prompt for Gemini
        prompt = f"""
You are an expert question creator for educational content. Generate a {request.question_type} type question for the following topic:

Topic: {topic['name']}
Description: {topic.get('description', '')}
Chapter: {chapter.get('name', '')}

Question Type Rules:
- MCQ: Multiple Choice Question with exactly ONE correct answer (4 options)
- MSQ: Multiple Select Question with ONE OR MORE correct answers (4 options)
- NAT: Numerical Answer Type with a numerical answer (no options)
- SUB: Subjective question with descriptive answer (no options)

Context from existing questions (DO NOT COPY, use for inspiration only):
{json.dumps([q['question_statement'] for q in existing_questions.data[:3]], indent=2)}

Previously generated questions (AVOID similar content):
{json.dumps([q['question_statement'] for q in generated_questions.data], indent=2)}

Requirements:
1. Generate a FRESH, ORIGINAL question that tests understanding of the topic
2. Make it educationally valuable and appropriately challenging
3. For MCQ/MSQ: Provide exactly 4 options
4. Ensure the answer follows the question type rules
5. Provide a detailed solution explanation

Please respond in the following JSON format:
{{
    "question_statement": "Your question here",
    "options": ["Option 1", "Option 2", "Option 3", "Option 4"] or null for NAT/SUB,
    "answer": "For MCQ: single number (0-3), for MSQ: comma-separated numbers (0,1,2), for NAT: numerical value, for SUB: descriptive answer",
    "solution": "Detailed step-by-step solution",
    "difficulty_level": "Easy/Medium/Hard"
}}
"""

        # Generate response from Gemini with round-robin key handling
        max_retries = len(GEMINI_API_KEYS)
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Get next working API key
                current_api_key = get_next_working_gemini_key()
                
                # Create model with current key
                model = create_gemini_model_with_key(current_api_key)
                
                # Configure generation for structured JSON output
                generation_config = genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.7
                )
                
                # Generate content with structured output
                response = model.generate_content(prompt, generation_config=generation_config)
                
                # If successful, break out of retry loop
                break
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Check if it's a quota/authentication error
                if "quota" in error_str or "429" in error_str or "exceeded" in error_str or "invalid api key" in error_str:
                    # Mark current key as failed
                    failed_keys.add(current_api_key)
                    print(f"API key failed (quota/auth error), marked as failed: {current_api_key[:10]}...")
                    
                    # If this was the last attempt, raise the error
                    if attempt == max_retries - 1:
                        raise HTTPException(status_code=429, detail=f"All Gemini API keys exhausted. Last error: {str(e)}")
                    
                    # Continue to next key
                    continue
                else:
                    # For other errors, don't retry
                    raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")
        
        if last_error and 'response' not in locals():
            raise HTTPException(status_code=500, detail=f"Failed after all retries: {str(last_error)}")
        
        # Parse the JSON response
        try:
            # Get response text
            response_text = response.text.strip()
            
            # Since we're using structured output (application/json), 
            # the response should be valid JSON directly
            try:
                generated_data = json.loads(response_text)
            except json.JSONDecodeError as json_error:
                # Fallback: try to extract and clean JSON manually
                import re
                
                # Remove control characters
                cleaned_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', response_text)
                
                # Find JSON object bounds
                start_idx = cleaned_text.find('{')
                end_idx = cleaned_text.rfind('}') + 1
                
                if start_idx == -1 or end_idx == 0:
                    raise ValueError(f"No JSON found in response. Raw response: {response_text[:200]}...")
                
                json_str = cleaned_text[start_idx:end_idx]
                
                # Try to fix common JSON formatting issues
                json_str = json_str.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r')
                
                # Try parsing again
                generated_data = json.loads(json_str)
            
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=500, detail=f"Error parsing AI response: {str(e)}")

        # Handle case where Gemini returns an array instead of a single object
        if isinstance(generated_data, list):
            if len(generated_data) > 0:
                generated_data = generated_data[0]  # Take the first item
            else:
                raise HTTPException(status_code=500, detail="AI returned empty array response")
        
        # Ensure generated_data is a dictionary
        if not isinstance(generated_data, dict):
            raise HTTPException(status_code=500, detail=f"AI response is not a valid object. Got: {type(generated_data)}")
        
        # Validate the generated question
        options = generated_data.get("options", [])
        answer = generated_data.get("answer", "")
        
        if not validate_question_answer(request.question_type, options, answer):
            raise HTTPException(status_code=400, detail=f"Generated question doesn't meet {request.question_type} validation rules")

        # Create new question record
        new_question = {
            "id": str(uuid.uuid4()),
            "topic_id": request.topic_id,
            "topic_name": topic["name"],
            "question_statement": generated_data["question_statement"],
            "question_type": request.question_type,
            "options": options if request.question_type in ["MCQ", "MSQ"] else None,
            "answer": answer,
            "solution": generated_data["solution"],
            "difficulty_level": generated_data.get("difficulty_level", "Medium"),
            "part_id": request.part_id,
            "slot_id": request.slot_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # Save to database
        result = supabase.table("new_questions").insert(new_question).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Error saving question to database")

        return GeneratedQuestion(**new_question)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating question: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)