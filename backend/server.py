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
    notes: Optional[str] = None

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
    correct_marks: Optional[float] = None
    incorrect_marks: Optional[float] = None
    skipped_marks: Optional[float] = None
    time_minutes: Optional[float] = None

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
    notes: Optional[str] = None
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
    question_id: str
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

@api_router.get("/pyq-questions-without-solution/{topic_id}")
async def get_pyq_questions_without_solution(topic_id: str):
    """Get PYQ questions for a topic that don't have solutions yet"""
    try:
        result = supabase.table("questions_topic_wise").select("id, question_statement, options, answer, solution, question_type").eq("topic_id", topic_id).execute()

        # Filter questions without solution
        questions_without_solution = [
            q for q in result.data
            if not q.get('solution') or q.get('solution', '').strip() == ''
        ]

        return questions_without_solution
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching PYQ questions without solution: {str(e)}")

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
        except (ValueError, TypeError, AttributeError):
            return False
    elif question_type == "MSQ":
        # MSQ should have one or more correct answers
        try:
            answer_indices = [int(x.strip()) for x in answer.split(",") if x.strip().isdigit()]
            return len(answer_indices) >= 1 and all(0 <= idx < len(options) for idx in answer_indices)
        except (ValueError, TypeError, AttributeError):
            return False
    elif question_type == "NAT":
        # NAT should be a numerical value
        try:
            float(answer)
            return True
        except (ValueError, TypeError):
            return False
    elif question_type == "SUB":
        # SUB can be any text
        return len(answer.strip()) > 0
    return False

@api_router.get("/all-topics-with-weightage/{course_id}", response_model=List[TopicWithWeightage])
async def get_all_topics_with_weightage(course_id: str):
    """Get all topics with weightage information for a course"""
    try:
        # Get all subjects for the course
        subjects_result = supabase.table("subjects").select("*").eq("course_id", course_id).execute()
        all_topics = []
        
        for subject in subjects_result.data:
            # Get units for subject
            units_result = supabase.table("units").select("*").eq("subject_id", subject["id"]).execute()
            
            for unit in units_result.data:
                # Get chapters for unit
                chapters_result = supabase.table("chapters").select("*").eq("unit_id", unit["id"]).execute()
                
                for chapter in chapters_result.data:
                    # Get topics for chapter
                    topics_result = supabase.table("topics").select("*").eq("chapter_id", chapter["id"]).execute()
                    
                    for topic in topics_result.data:
                        all_topics.append(TopicWithWeightage(
                            id=topic["id"],
                            name=topic["name"],
                            weightage=topic.get("weightage", 0.0),
                            notes=topic.get("notes", ""),
                            chapter_id=chapter["id"],
                            chapter_name=chapter["name"],
                            unit_id=unit["id"],
                            unit_name=unit["name"],
                            subject_id=subject["id"],
                            subject_name=subject["name"]
                        ))
        
        return all_topics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching topics with weightage: {str(e)}")

@api_router.post("/auto-generation-session")
async def create_auto_generation_session(config: AutoGenerationConfig, exam_id: str, course_id: str, generation_mode: str = "new_questions"):
    """Create a new auto-generation session"""
    try:
        # Get all topics with weightage for the course
        topics = await get_all_topics_with_weightage(course_id)
        
        # Calculate questions per topic based on weightage
        total_weightage = sum(topic.weightage or 0 for topic in topics)
        if total_weightage == 0:
            # If no weightage, give at least 1 question to each topic
            for topic in topics:
                topic.estimated_questions = 1
        else:
            # Distribute based on weightage
            for topic in topics:
                weightage = topic.weightage or 0

                if weightage == 0:
                    # Topics with 0% weightage still get 1 good question
                    topic.estimated_questions = 1
                else:
                    # Calculate questions based on percentage of total
                    exact_questions = (weightage / 100) * config.total_questions
                    # Round up to ensure we generate enough questions (user is okay with generating more)
                    topic.estimated_questions = max(1, int(exact_questions + 0.5))
        
        session_id = str(uuid.uuid4())
        session = AutoGenerationSession(
            id=session_id,
            exam_id=exam_id,
            course_id=course_id,
            config=config,
            questions_target=config.total_questions,
            generation_mode=generation_mode,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # For now, we'll return the session. In a real implementation, you'd store this in a sessions table
        return {"session_id": session_id, "session": session, "topics": topics}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating auto-generation session: {str(e)}")

@api_router.post("/generate-pyq-solution", response_model=PYQSolutionResponse)
async def generate_pyq_solution(request: PYQSolutionRequest):
    """Generate answer and solution for a PYQ question"""
    try:
        # Get topic information for context
        topic_result = supabase.table("topics").select("*").eq("id", request.topic_id).execute()
        if not topic_result.data:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        topic = topic_result.data[0]
        
        # Get chapter and course information for better context
        chapter_result = supabase.table("chapters").select("*").eq("id", topic["chapter_id"]).execute()
        chapter = chapter_result.data[0] if chapter_result.data else {}

        # Get notes for the topic
        topic_notes = topic.get('notes', '')

        # Create prompt for Gemini to solve the PYQ using topic notes
        prompt = f"""
You are an expert educator and question solver. Analyze the following previous year question and provide the correct answer and detailed solution.

Topic: {topic['name']}
Chapter: {chapter.get('name', '')}
Question Type: {request.question_type}

IMPORTANT CONTEXT - Study Notes from this Chapter:
{topic_notes if topic_notes else "No specific notes available for this topic."}

Use the concepts from these notes to solve the question. Your solution should reference and apply the principles mentioned in the notes.

Question: {request.question_statement}

{f'Options: {request.options}' if request.options else ''}

Your task:
1. Carefully analyze the question using the concepts from the provided notes
2. Determine the correct answer based on the principles in the notes
3. Provide a step-by-step solution that references the relevant concepts from the notes
4. Double-check your work to ensure accuracy

Requirements:
- For MCQ: Provide the correct option index (0-3)
- For MSQ: Provide comma-separated correct option indices
- For NAT: Provide the numerical answer
- For SUB: Provide a comprehensive answer
- Always reference the relevant concepts from the notes in your solution

Respond in the following JSON format:
{{
    "answer": "Your answer here (following the format rules above)",
    "solution": "Detailed step-by-step solution with clear explanations, referencing concepts from the notes",
    "confidence_level": "High/Medium/Low - your confidence in this solution"
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
                    temperature=0.3  # Lower temperature for more accurate answers
                )
                
                # Generate content with structured output
                response = model.generate_content(prompt, generation_config=generation_config)
                break
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Check if it's a quota/authentication error
                if "quota" in error_str or "429" in error_str or "exceeded" in error_str or "invalid api key" in error_str:
                    failed_keys.add(current_api_key)
                    if attempt == max_retries - 1:
                        raise HTTPException(status_code=429, detail=f"All Gemini API keys exhausted. Last error: {str(e)}")
                    continue
                else:
                    raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")
        
        if last_error and 'response' not in locals():
            raise HTTPException(status_code=500, detail=f"Failed after all retries: {str(last_error)}")
        
        # Parse the JSON response
        try:
            response_text = response.text.strip()
            solution_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Error parsing AI response: {str(e)}")

        # Validate the solution
        if not isinstance(solution_data, dict):
            raise HTTPException(status_code=500, detail="AI response is not a valid object")
        
        # Create response
        pyq_solution = PYQSolutionResponse(
            question_statement=request.question_statement,
            answer=solution_data.get("answer", ""),
            solution=solution_data.get("solution", ""),
            confidence_level=solution_data.get("confidence_level", "Medium")
        )

        # Update the question in questions_topic_wise table with the generated solution
        try:
            update_data = {
                "answer": solution_data.get("answer", ""),
                "solution": solution_data.get("solution", ""),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            supabase.table("questions_topic_wise").update(update_data).eq("id", request.question_id).execute()
        except Exception as update_error:
            # Log the error but don't fail the entire request
            print(f"Warning: Failed to update question with solution: {str(update_error)}")

        return pyq_solution
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PYQ solution: {str(e)}")

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
        
        # Get unit information
        unit_result = supabase.table("units").select("*").eq("id", chapter.get("unit_id", "")).execute()
        unit = unit_result.data[0] if unit_result.data else {}
        
        # Get subject information
        subject_result = supabase.table("subjects").select("*").eq("id", unit.get("subject_id", "")).execute()
        subject = subject_result.data[0] if subject_result.data else {}
        
        # Get course information
        course_result = supabase.table("courses").select("*").eq("id", subject.get("course_id", "")).execute()
        course = course_result.data[0] if course_result.data else {}
        
        # Get exam information
        exam_result = supabase.table("exams").select("*").eq("id", course.get("exam_id", "")).execute()
        exam = exam_result.data[0] if exam_result.data else {}
        
        # Get existing questions for reference (but not to copy)
        existing_questions = supabase.table("questions_topic_wise").select("question_statement, options, question_type").eq("topic_id", request.topic_id).limit(5).execute()
        
        # Get previously generated questions to avoid repetition
        generated_questions = supabase.table("new_questions").select("question_statement").eq("topic_id", request.topic_id).limit(10).execute()
        
        # Create prompt for Gemini
        prompt = f"""
You are an expert question creator for educational content. Generate a {request.question_type} type question for the following topic:

EXAM CONTEXT:
- Exam: {exam.get('name', 'Unknown Exam')}
- Course: {course.get('name', 'Unknown Course')}
- Subject: {subject.get('name', 'Unknown Subject')}
- Unit: {unit.get('name', 'Unknown Unit')}
- Chapter: {chapter.get('name', 'Unknown Chapter')}
- Topic: {topic['name']}

IMPORTANT: Create questions appropriate for the {exam.get('name', 'exam')} difficulty level and {course.get('name', 'course')} standards. Keep the difficulty suitable for this specific exam and course context.

Topic Description: {topic.get('description', '')}

Question Type Rules:
- MCQ: Multiple Choice Question with exactly ONE correct answer (4 options)
- MSQ: Multiple Select Question with ONE OR MORE correct answers (4 options)
- NAT: Numerical Answer Type with a numerical answer (no options)
- SUB: Subjective question with descriptive answer (no options)

Context from existing questions (DO NOT COPY, use for inspiration only):
{json.dumps([q['question_statement'] for q in existing_questions.data[:3]], indent=2)}

Previously generated questions in this topic (AVOID similar content - generate something completely different):
{json.dumps([q['question_statement'] for q in generated_questions.data], indent=2)}

Requirements:
1. Generate a FRESH, ORIGINAL question that tests understanding of the topic
2. Make it educationally valuable and appropriately challenging for {exam.get('name', 'the exam')}
3. Ensure difficulty is suitable for {course.get('name', 'the course')} level
4. For MCQ/MSQ: Provide exactly 4 options with realistic distractors
5. Ensure the answer follows the question type rules strictly
6. Provide a detailed solution explanation with clear steps
7. AVOID any similarity with previously generated questions listed above

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
            except json.JSONDecodeError:
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
            "correct_marks": request.correct_marks,
            "incorrect_marks": request.incorrect_marks,
            "skipped_marks": request.skipped_marks,
            "time_minutes": request.time_minutes,
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

@api_router.post("/save-question-manually")
async def save_question_manually(question_data: dict):
    """Save a manually created/reviewed question to the database"""
    try:
        # Always generate a new UUID to avoid conflicts
        new_id = str(uuid.uuid4())
        question_data["id"] = new_id
        question_data["created_at"] = datetime.now(timezone.utc).isoformat()
        question_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Save to database
        result = supabase.table("new_questions").insert(question_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Error saving question to database")
        
        return {"message": "Question saved successfully", "question_id": new_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving question: {str(e)}")

@api_router.post("/start-auto-generation")
async def start_auto_generation(
    exam_id: str,
    course_id: str, 
    config: AutoGenerationConfig,
    generation_mode: str = "new_questions"
):
    """Start automatic question generation process"""
    try:
        # Create session
        session_response = await create_auto_generation_session(config, exam_id, course_id, generation_mode)
        session_id = session_response["session_id"]
        topics = session_response["topics"]
        
        # Store session state (in a real app, you'd use a proper database table)
        # For now, we'll return the initial state
        
        return {
            "session_id": session_id,
            "total_topics": len(topics),
            "total_questions_planned": config.total_questions,
            "status": "ready_to_start",
            "message": "Auto-generation session created. Ready to start generating questions."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting auto-generation: {str(e)}")

@api_router.post("/auto-generate-next-question/{session_id}")
async def auto_generate_next_question(session_id: str):
    """Generate the next question in an auto-generation session"""
    try:
        # In a real implementation, you'd load the session state from database
        # For now, we'll return a placeholder response
        return {
            "message": "Auto-generation logic will be implemented in frontend",
            "session_id": session_id,
            "status": "use_frontend_logic"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in auto-generation: {str(e)}")

@api_router.get("/auto-generation-progress/{session_id}")
async def get_auto_generation_progress(session_id: str):
    """Get progress of auto-generation session"""
    try:
        # In a real implementation, you'd load this from database
        return {
            "session_id": session_id,
            "message": "Progress tracking will be handled by frontend",
            "status": "use_frontend_logic"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting progress: {str(e)}")

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