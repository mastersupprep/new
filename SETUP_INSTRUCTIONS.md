# Setup Instructions

## Prerequisites
- Python 3.9+
- Node.js 16+
- Supabase account

## Configuration

### 1. Backend Configuration

Edit `/backend/.env` and add your Gemini API keys:

```bash
SUPABASE_URL=https://xiamgdlvjelcsfcrpjna.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhpYW1nZGx2amVsY3NmY3Jwam5hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk1NTYxNDcsImV4cCI6MjA3NTEzMjE0N30.FdG6bhyzA3ylKg2hE-6VZHBp8aUBgowxnx47O4RCErU
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000
GEMINI_API_KEYS=your-key-1,your-key-2,your-key-3
```

**Important**: Add multiple Gemini API keys separated by commas. The system uses round-robin to distribute requests across keys.

### 2. Frontend Configuration

Edit `/frontend/.env`:

```bash
REACT_APP_BACKEND_URL=http://localhost:8000
```

## Installation

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## Features Implemented

### 1. Auto Question Generation
- Select exam and course
- System automatically traverses through all subjects → units → chapters → topics
- Generates questions based on topic weightage:
  - Topics with weightage get proportional questions (e.g., 2.44% = 3 questions for 1000 total)
  - Topics with 0% weightage still get 1 good question
  - Total questions may exceed target (e.g., 1001 or 1094 instead of 1000) to ensure complete coverage
- Questions are saved to `new_questions` table automatically
- Uses round-robin Gemini API keys to avoid quota limits

### 2. PYQ Solution Generation
- Select exam and course
- System automatically traverses all topics
- For each topic, finds questions without solutions in `questions_topic_wise` table
- Generates solutions using topic notes from `topics.notes` column
- Updates the `questions_topic_wise` table with answer and solution
- Uses round-robin Gemini API keys

### 3. Manual Mode
- Select all parameters manually (exam → course → subject → unit → chapter → topic)
- Generate individual questions
- Option to save or discard generated questions

## Database Structure Expected

### Tables Required:
- `exams` - Exam definitions
- `courses` - Courses linked to exams
- `subjects` - Subjects in each course
- `units` - Units in each subject
- `chapters` - Chapters in each unit
- `topics` - Topics in each chapter (must have `weightage` and `notes` columns)
- `parts` - Optional parts for questions
- `slots` - Optional slots for questions
- `new_questions` - Auto-generated new questions
- `questions_topic_wise` - Existing PYQ questions

### Topics Table Columns:
- `id` - UUID primary key
- `chapter_id` - Foreign key to chapters
- `name` - Topic name
- `description` - Optional description
- `weightage` - Percentage (e.g., 2.44, 5.50, 0)
- `notes` - Study notes for this topic (used for PYQ solution generation)

## Usage

### Auto Question Generation
1. Switch to "Auto Mode"
2. Select "Generate New Questions"
3. Choose exam and course
4. Set total questions to generate (e.g., 1000)
5. Configure marks and time settings
6. Select question type (MCQ, MSQ, NAT, SUB)
7. Click "Start Auto Question Generation"
8. System will generate questions automatically and save to `new_questions` table

### PYQ Solution Generation
1. Switch to "Auto Mode"
2. Select "Generate PYQ Solutions"
3. Choose exam and course
4. Set total number of solutions to generate
5. Click "Start Auto Solution Generation"
6. System will find questions without solutions and generate them using topic notes
7. Solutions are saved back to `questions_topic_wise` table

## Troubleshooting

### "[object Object]" Error
This was caused by error objects not being properly converted to strings. This has been fixed in the frontend error handling.

### "No Gemini API keys configured"
Add your Gemini API keys to `/backend/.env` file in the `GEMINI_API_KEYS` variable.

### Backend won't start
Make sure all Python dependencies are installed: `pip install -r requirements.txt`

### Frontend won't connect
Check that `REACT_APP_BACKEND_URL` in `/frontend/.env` points to your backend server.
