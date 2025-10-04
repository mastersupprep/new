import React, { useState, useEffect } from "react";
import axios from "axios";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { Badge } from "./components/ui/badge";
import { Separator } from "./components/ui/separator";
import { Loader2, Sparkles, BookOpen, GraduationCap, Play, Pause, Square } from "lucide-react";
import { Toaster, toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  // State for dropdown selections
  const [selectedExam, setSelectedExam] = useState("");
  const [selectedCourse, setSelectedCourse] = useState("");
  const [selectedSubject, setSelectedSubject] = useState("");
  const [selectedUnit, setSelectedUnit] = useState("");
  const [selectedChapter, setSelectedChapter] = useState("");
  const [selectedTopic, setSelectedTopic] = useState("");
  const [selectedQuestionType, setSelectedQuestionType] = useState("");
  const [selectedPart, setSelectedPart] = useState("");
  const [selectedSlot, setSelectedSlot] = useState("");

  // State for dropdown options
  const [exams, setExams] = useState([]);
  const [courses, setCourses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [units, setUnits] = useState([]);
  const [chapters, setChapters] = useState([]);
  const [topics, setTopics] = useState([]);
  const [parts, setParts] = useState([]);
  const [slots, setSlots] = useState([]);

  // State for question generation
  const [generatedQuestion, setGeneratedQuestion] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [existingQuestions, setExistingQuestions] = useState([]);

  // State for auto-generation mode
  const [isAutoMode, setIsAutoMode] = useState(true);
  const [autoConfig, setAutoConfig] = useState({
    correctMarks: 4,
    incorrectMarks: -1,
    skippedMarks: 0,
    timeMinutes: 3,
    totalQuestions: 30
  });
  const [autoSession, setAutoSession] = useState(null);
  const [isAutoGenerating, setIsAutoGenerating] = useState(false);
  const [autoProgress, setAutoProgress] = useState({
    generated: 0,
    total: 0,
    currentTopic: null,
    percentage: 0
  });
  const [isPaused, setIsPaused] = useState(false);
  const [generationMode, setGenerationMode] = useState("new_questions"); // "new_questions" or "pyq_solutions"
  const [newQuestionsCount, setNewQuestionsCount] = useState(0);
  const [pyqSolutionsCount, setPyqSolutionsCount] = useState(0);

  const questionTypes = [
    { value: "MCQ", label: "MCQ - Multiple Choice (One Answer)", description: "Single correct answer from 4 options" },
    { value: "MSQ", label: "MSQ - Multiple Select (One or More)", description: "One or more correct answers" },
    { value: "NAT", label: "NAT - Numerical Answer", description: "Numerical value answer" },
    { value: "SUB", label: "SUB - Subjective", description: "Descriptive text answer" },
  ];

  // Load exams on component mount
  useEffect(() => {
    loadExams();
  }, []);

  const loadExams = async () => {
    try {
      const response = await axios.get(`${API}/exams`);
      setExams(response.data);
    } catch (error) {
      toast.error("Failed to load exams");
      console.error("Error loading exams:", error);
    }
  };

  const loadCourses = async (examId) => {
    try {
      const response = await axios.get(`${API}/courses/${examId}`);
      setCourses(response.data);
      resetSelections(['course', 'subject', 'unit', 'chapter', 'topic']);
    } catch (error) {
      toast.error("Failed to load courses");
    }
  };

  const loadSubjects = async (courseId) => {
    try {
      const response = await axios.get(`${API}/subjects/${courseId}`);
      setSubjects(response.data);
      resetSelections(['subject', 'unit', 'chapter', 'topic']);
      
      // Load parts and slots for the course
      loadParts(courseId);
      loadSlots(courseId);
    } catch (error) {
      toast.error("Failed to load subjects");
    }
  };

  const loadUnits = async (subjectId) => {
    try {
      const response = await axios.get(`${API}/units/${subjectId}`);
      setUnits(response.data);
      resetSelections(['unit', 'chapter', 'topic']);
    } catch (error) {
      toast.error("Failed to load units");
    }
  };

  const loadChapters = async (unitId) => {
    try {
      const response = await axios.get(`${API}/chapters/${unitId}`);
      setChapters(response.data);
      resetSelections(['chapter', 'topic']);
    } catch (error) {
      toast.error("Failed to load chapters");
    }
  };

  const loadTopics = async (chapterId) => {
    try {
      const response = await axios.get(`${API}/topics/${chapterId}`);
      setTopics(response.data);
      resetSelections(['topic']);
    } catch (error) {
      toast.error("Failed to load topics");
    }
  };

  const loadParts = async (courseId) => {
    try {
      const response = await axios.get(`${API}/parts/${courseId}`);
      setParts(response.data);
    } catch (error) {
      console.error("Error loading parts:", error);
    }
  };

  const loadSlots = async (courseId) => {
    try {
      const response = await axios.get(`${API}/slots/${courseId}`);
      setSlots(response.data);
    } catch (error) {
      console.error("Error loading slots:", error);
    }
  };

  const loadExistingQuestions = async (topicId) => {
    try {
      const response = await axios.get(`${API}/existing-questions/${topicId}`);
      setExistingQuestions(response.data);
    } catch (error) {
      console.error("Error loading existing questions:", error);
    }
  };

  const resetSelections = (selectionsToReset) => {
    if (selectionsToReset.includes('course')) setSelectedCourse("");
    if (selectionsToReset.includes('subject')) setSelectedSubject("");
    if (selectionsToReset.includes('unit')) setSelectedUnit("");
    if (selectionsToReset.includes('chapter')) setSelectedChapter("");
    if (selectionsToReset.includes('topic')) setSelectedTopic("");
  };

  const handleExamChange = (value) => {
    setSelectedExam(value);
    loadCourses(value);
  };

  const handleCourseChange = (value) => {
    setSelectedCourse(value);
    loadSubjects(value);
  };

  const handleSubjectChange = (value) => {
    setSelectedSubject(value);
    loadUnits(value);
  };

  const handleUnitChange = (value) => {
    setSelectedUnit(value);
    loadChapters(value);
  };

  const handleChapterChange = (value) => {
    setSelectedChapter(value);
    loadTopics(value);
  };

  const handleTopicChange = (value) => {
    setSelectedTopic(value);
    loadExistingQuestions(value);
  };

  const generateQuestion = async () => {
    if (!selectedTopic || !selectedQuestionType) {
      toast.error("Please select a topic and question type");
      return;
    }

    setIsGenerating(true);
    setGeneratedQuestion(null);

    try {
      const response = await axios.post(`${API}/generate-question`, {
        topic_id: selectedTopic,
        question_type: selectedQuestionType,
        part_id: selectedPart === "none" ? null : selectedPart || null,
        slot_id: selectedSlot === "none" ? null : selectedSlot || null,
      });

      setGeneratedQuestion(response.data);
      toast.success("Question generated successfully!");
      
      // Update counts
      if (generationMode === "new_questions") {
        setNewQuestionsCount(prev => prev + 1);
      }
    } catch (error) {
      toast.error(`Failed to generate question: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const saveQuestionManually = async () => {
    if (!generatedQuestion) {
      toast.error("No question to save");
      return;
    }

    try {
      await axios.post(`${API}/save-question-manually`, generatedQuestion);
      toast.success("Question saved to database successfully!");
    } catch (error) {
      toast.error(`Failed to save question: ${error.response?.data?.detail || error.message}`);
    }
  };

  const startAutoGeneration = async () => {
    if (!selectedExam || !selectedCourse) {
      toast.error("Please select an exam and course first");
      return;
    }
    
    if (!selectedQuestionType) {
      toast.error("Please select a question type for auto-generation");
      return;
    }

    setIsAutoGenerating(true);
    setAutoProgress({ generated: 0, total: autoConfig.totalQuestions, currentTopic: null, percentage: 0 });

    try {
      // Start auto-generation session
      const response = await axios.post(
        `${API}/start-auto-generation?exam_id=${selectedExam}&course_id=${selectedCourse}&generation_mode=${generationMode}`,
        autoConfig
      );

      setAutoSession(response.data);
      
      // Get all topics with weightage for this course
      const topicsResponse = await axios.get(`${API}/all-topics-with-weightage/${selectedCourse}`);
      const topics = topicsResponse.data;
      
      toast.success("Auto-generation started!");
      
      // Start the auto-generation process
      await processAutoGeneration(topics);
      
    } catch (error) {
      console.error("Auto-generation error:", error);
      let errorMessage = "Unknown error occurred";

      if (error.response?.data?.detail) {
        if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        } else if (Array.isArray(error.response.data.detail)) {
          errorMessage = error.response.data.detail.map(err =>
            typeof err === 'string' ? err : (err.msg || JSON.stringify(err))
          ).join(', ');
        } else {
          errorMessage = JSON.stringify(error.response.data.detail);
        }
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.message) {
        errorMessage = error.message;
      }

      toast.error(`Failed to start auto-generation: ${errorMessage}`);
      setIsAutoGenerating(false);
    }
  };

  const processAutoGeneration = async (topics) => {
    let totalGenerated = 0;
    const totalQuestions = autoConfig.totalQuestions;
    
    // Calculate questions per topic based on weightage
    const topicsWithCounts = calculateQuestionsPerTopic(topics, totalQuestions);
    
    for (let i = 0; i < topicsWithCounts.length && !isPaused; i++) {
      const topicInfo = topicsWithCounts[i];
      const questionsForTopic = topicInfo.estimated_questions;
      
      setAutoProgress(prev => ({
        ...prev,
        currentTopic: `${topicInfo.subject_name} > ${topicInfo.unit_name} > ${topicInfo.chapter_name} > ${topicInfo.name}`,
        percentage: Math.round((totalGenerated / totalQuestions) * 100)
      }));

      // Generate questions for this topic
      for (let q = 0; q < questionsForTopic && !isPaused; q++) {
        try {
          if (generationMode === "new_questions") {
            // Generate new questions using the selected question type
            await generateQuestionForTopic(topicInfo.id, selectedQuestionType);
          } else {
            // Generate PYQ solutions
            await generatePYQSolutionForTopic(topicInfo.id);
          }
          
          totalGenerated++;
          setAutoProgress(prev => ({
            ...prev,
            generated: totalGenerated,
            percentage: Math.round((totalGenerated / totalQuestions) * 100)
          }));

          if (generationMode === "new_questions") {
            setNewQuestionsCount(prev => prev + 1);
          } else {
            setPyqSolutionsCount(prev => prev + 1);
          }

          // Small delay to prevent rate limiting
          await new Promise(resolve => setTimeout(resolve, 1000));
          
        } catch (error) {
          console.error(`Error generating question for topic ${topicInfo.name}:`, error);
          toast.error(`Error generating question for ${topicInfo.name}`);
        }
      }
    }

    setIsAutoGenerating(false);
    if (!isPaused) {
      toast.success(`Auto-generation completed! Generated ${totalGenerated} ${generationMode === "new_questions" ? "questions" : "solutions"}.`);
    }
  };

  const calculateQuestionsPerTopic = (topics, totalQuestions) => {
    const totalWeightage = topics.reduce((sum, topic) => sum + (topic.weightage || 0), 0);

    if (totalWeightage === 0) {
      // If no weightage, give at least 1 question to each topic
      return topics.map(topic => ({
        ...topic,
        estimated_questions: 1
      }));
    }

    // Distribute based on weightage
    const result = topics.map((topic) => {
      const weightage = topic.weightage || 0;

      if (weightage === 0) {
        // Topics with 0% weightage still get 1 good question
        return { ...topic, estimated_questions: 1 };
      }

      // Calculate questions based on percentage of total
      const exactQuestions = (weightage / 100) * totalQuestions;
      // Round up to ensure we generate enough questions (user is okay with generating more)
      const topicQuestions = Math.ceil(exactQuestions);

      return { ...topic, estimated_questions: topicQuestions };
    });

    return result;
  };

  const generateQuestionForTopic = async (topicId, questionType = "MCQ") => {
    const response = await axios.post(`${API}/generate-question`, {
      topic_id: topicId,
      question_type: questionType,
      part_id: selectedPart === "none" ? null : selectedPart || null,
      slot_id: selectedSlot === "none" ? null : selectedSlot || null,
      correct_marks: isAutoGenerating ? autoConfig.correctMarks : null,
      incorrect_marks: isAutoGenerating ? autoConfig.incorrectMarks : null,
      skipped_marks: isAutoGenerating ? autoConfig.skippedMarks : null,
      time_minutes: isAutoGenerating ? autoConfig.timeMinutes : null,
    });
    
    return response.data;
  };

  const generatePYQSolutionForTopic = async (topicId) => {
    // Get existing PYQ questions for this topic from questions_topic_wise table
    const existingResponse = await axios.get(`${API}/pyq-questions-without-solution/${topicId}`);
    const questionsWithoutSolution = existingResponse.data;

    if (questionsWithoutSolution.length === 0) {
      return null; // Skip if no PYQ questions available without solution
    }

    // Pick the first question that doesn't have a solution
    const questionWithoutSolution = questionsWithoutSolution[0];

    // Generate solution for the PYQ
    const response = await axios.post(`${API}/generate-pyq-solution`, {
      question_id: questionWithoutSolution.id,
      topic_id: topicId,
      question_statement: questionWithoutSolution.question_statement,
      options: questionWithoutSolution.options,
      question_type: questionWithoutSolution.question_type || "MCQ"
    });

    return response.data;
  };

  const pauseAutoGeneration = () => {
    setIsPaused(true);
    toast.info("Auto-generation paused. You can resume anytime.");
  };

  const resumeAutoGeneration = async () => {
    setIsPaused(false);
    toast.info("Resuming auto-generation...");
    
    // Get current topics and continue from where we left off
    try {
      const topicsResponse = await axios.get(`${API}/all-topics-with-weightage/${selectedCourse}`);
      const topics = topicsResponse.data;
      await processAutoGeneration(topics);
    } catch (error) {
      toast.error("Failed to resume auto-generation");
      setIsAutoGenerating(false);
    }
  };

  const stopAutoGeneration = () => {
    setIsPaused(true);
    setIsAutoGenerating(false);
    setAutoProgress({ generated: 0, total: 0, currentTopic: null, percentage: 0 });
    toast.info("Auto-generation stopped.");
  };

  const renderOptions = (options, answer, questionType) => {
    if (!options) return null;

    let correctIndices = [];
    if (questionType === "MCQ" || questionType === "MSQ") {
      correctIndices = answer.split(",").map(i => parseInt(i.trim()));
    }

    return (
      <div className="space-y-2 mt-4">
        {options.map((option, index) => (
          <div 
            key={index} 
            className={`p-3 rounded-lg border-2 ${
              correctIndices.includes(index) 
                ? 'border-emerald-500 bg-emerald-50' 
                : 'border-slate-200 bg-slate-50'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="font-medium text-slate-700">({String.fromCharCode(65 + index)})</span>
              <span className="text-slate-900">{option}</span>
              {correctIndices.includes(index) && (
                <Badge variant="default" className="ml-auto bg-emerald-500">Correct</Badge>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="flex justify-center items-center gap-3 mb-4">
            <div className="p-3 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl">
              <GraduationCap className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-800 to-purple-800 bg-clip-text text-transparent">
              Question Maker AI
            </h1>
          </div>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Generate intelligent, exam-focused questions using advanced AI. Select your parameters and create fresh, educational content.
          </p>
          
          {/* Mode Selection */}
          <div className="flex justify-center gap-4 mt-6">
            <div className="flex items-center gap-2 bg-white/80 backdrop-blur-sm px-4 py-2 rounded-lg border">
              <input
                type="radio"
                id="new_questions"
                name="generation_mode"
                value="new_questions"
                checked={generationMode === "new_questions"}
                onChange={(e) => setGenerationMode(e.target.value)}
                className="text-purple-600"
              />
              <label htmlFor="new_questions" className="text-sm font-medium text-slate-700">Generate New Questions</label>
            </div>
            <div className="flex items-center gap-2 bg-white/80 backdrop-blur-sm px-4 py-2 rounded-lg border">
              <input
                type="radio"
                id="pyq_solutions"
                name="generation_mode"
                value="pyq_solutions"
                checked={generationMode === "pyq_solutions"}
                onChange={(e) => setGenerationMode(e.target.value)}
                className="text-purple-600"
              />
              <label htmlFor="pyq_solutions" className="text-sm font-medium text-slate-700">Generate PYQ Solutions</label>
            </div>
          </div>

          {/* Auto Mode Toggle */}
          <div className="flex justify-center mt-4">
            <div className="text-center">
              <Button
                onClick={() => setIsAutoMode(!isAutoMode)}
                variant={isAutoMode ? "default" : "outline"}
                className={isAutoMode ? "bg-gradient-to-r from-green-600 to-emerald-600 text-white" : ""}
              >
                {isAutoMode ? "Manual Mode" : "Auto Mode"}
              </Button>
              <p className="text-xs text-slate-500 mt-1">
                Auto Mode: {isAutoMode ? "ON" : "OFF"}
              </p>
            </div>
          </div>
        </div>

        {/* Auto Generation Configuration */}
        {isAutoMode && (
          <Card className="mb-8 border-0 shadow-xl bg-white/80 backdrop-blur-sm">
            <CardHeader className="bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-t-lg">
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                Auto Generation Configuration
              </CardTitle>
              <CardDescription className="text-green-100">
                Configure automatic {generationMode === "new_questions" ? "question generation" : "PYQ solution generation"} settings
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Correct Marks</label>
                  <input
                    type="number"
                    step="0.1"
                    value={autoConfig.correctMarks}
                    onChange={(e) => setAutoConfig(prev => ({...prev, correctMarks: parseFloat(e.target.value)}))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Incorrect Marks</label>
                  <input
                    type="number"
                    step="0.1"
                    value={autoConfig.incorrectMarks}
                    onChange={(e) => setAutoConfig(prev => ({...prev, incorrectMarks: parseFloat(e.target.value)}))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Skipped Marks</label>
                  <input
                    type="number"
                    step="0.1"
                    value={autoConfig.skippedMarks}
                    onChange={(e) => setAutoConfig(prev => ({...prev, skippedMarks: parseFloat(e.target.value)}))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Time (Minutes)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={autoConfig.timeMinutes}
                    onChange={(e) => setAutoConfig(prev => ({...prev, timeMinutes: parseFloat(e.target.value)}))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Total Questions</label>
                  <input
                    type="number"
                    value={autoConfig.totalQuestions}
                    onChange={(e) => setAutoConfig(prev => ({...prev, totalQuestions: parseInt(e.target.value)}))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>
              </div>

              {/* Auto Mode Question Configuration */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Question Type for Auto Generation</label>
                  <Select value={selectedQuestionType} onValueChange={setSelectedQuestionType}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select question type" />
                    </SelectTrigger>
                    <SelectContent>
                      {questionTypes.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          <div>
                            <div className="font-medium">{type.label}</div>
                            <div className="text-xs text-slate-500">{type.description}</div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Part (Optional)</label>
                  <Select value={selectedPart} onValueChange={setSelectedPart}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select part" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No Part Selected</SelectItem>
                      {parts.map((part) => (
                        <SelectItem key={part.id} value={part.id}>
                          {part.part_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">Slot (Optional)</label>
                  <Select value={selectedSlot} onValueChange={setSelectedSlot}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select slot" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">No Slot Selected</SelectItem>
                      {slots.map((slot) => (
                        <SelectItem key={slot.id} value={slot.id}>
                          {slot.slot_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Auto Generation Controls */}
              <div className="flex flex-wrap gap-4 justify-center">
                <Button
                  onClick={startAutoGeneration}
                  disabled={isAutoGenerating || !selectedExam || !selectedCourse}
                  className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white"
                >
                  {isAutoGenerating ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Generating...
                    </>
                  ) : (
                    `Start Auto ${generationMode === "new_questions" ? "Question" : "Solution"} Generation`
                  )}
                </Button>

                {isAutoGenerating && (
                  <>
                    <Button
                      onClick={isPaused ? resumeAutoGeneration : pauseAutoGeneration}
                      variant="outline"
                      className="border-yellow-500 text-yellow-600 hover:bg-yellow-50"
                    >
                      {isPaused ? "Resume" : "Pause"}
                    </Button>
                    <Button
                      onClick={stopAutoGeneration}
                      variant="outline"
                      className="border-red-500 text-red-600 hover:bg-red-50"
                    >
                      Stop
                    </Button>
                  </>
                )}
              </div>

              {/* Progress Bar */}
              {isAutoGenerating && autoProgress.total > 0 && (
                <div className="mt-6 space-y-2">
                  <div className="flex justify-between text-sm text-slate-600">
                    <span>Progress: {autoProgress.generated}/{autoProgress.total}</span>
                    <span>{autoProgress.percentage}%</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-green-600 to-emerald-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${autoProgress.percentage}%` }}
                    />
                  </div>
                  {autoProgress.currentTopic && (
                    <p className="text-xs text-slate-500">Current: {autoProgress.currentTopic}</p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Selection Panel */}
          <div className="lg:col-span-2 space-y-6">
            <Card className="border-0 shadow-xl bg-white/80 backdrop-blur-sm">
              <CardHeader className="bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-t-lg">
                <CardTitle className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5" />
                  Course Selection
                </CardTitle>
                <CardDescription className="text-blue-100">
                  Navigate through the academic hierarchy to select your topic
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                {/* First Row */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700">Exam</label>
                    <Select value={selectedExam} onValueChange={handleExamChange}>
                      <SelectTrigger data-testid="exam-select">
                        <SelectValue placeholder="Select an exam" />
                      </SelectTrigger>
                      <SelectContent>
                        {exams.map((exam) => (
                          <SelectItem key={exam.id} value={exam.id}>
                            {exam.name} - {exam.description}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700">Course</label>
                    <Select value={selectedCourse} onValueChange={handleCourseChange} disabled={!selectedExam}>
                      <SelectTrigger data-testid="course-select">
                        <SelectValue placeholder="Select a course" />
                      </SelectTrigger>
                      <SelectContent>
                        {courses.map((course) => (
                          <SelectItem key={course.id} value={course.id}>
                            {course.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Second Row */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700">Subject</label>
                    <Select value={selectedSubject} onValueChange={handleSubjectChange} disabled={!selectedCourse}>
                      <SelectTrigger data-testid="subject-select">
                        <SelectValue placeholder="Select a subject" />
                      </SelectTrigger>
                      <SelectContent>
                        {subjects.map((subject) => (
                          <SelectItem key={subject.id} value={subject.id}>
                            {subject.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700">Unit</label>
                    <Select value={selectedUnit} onValueChange={handleUnitChange} disabled={!selectedSubject}>
                      <SelectTrigger data-testid="unit-select">
                        <SelectValue placeholder="Select a unit" />
                      </SelectTrigger>
                      <SelectContent>
                        {units.map((unit) => (
                          <SelectItem key={unit.id} value={unit.id}>
                            {unit.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Third Row */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700">Chapter</label>
                    <Select value={selectedChapter} onValueChange={handleChapterChange} disabled={!selectedUnit}>
                      <SelectTrigger data-testid="chapter-select">
                        <SelectValue placeholder="Select a chapter" />
                      </SelectTrigger>
                      <SelectContent>
                        {chapters.map((chapter) => (
                          <SelectItem key={chapter.id} value={chapter.id}>
                            {chapter.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700">Topic</label>
                    <Select value={selectedTopic} onValueChange={handleTopicChange} disabled={!selectedChapter}>
                      <SelectTrigger data-testid="topic-select">
                        <SelectValue placeholder="Select a topic" />
                      </SelectTrigger>
                      <SelectContent>
                        {topics.map((topic) => (
                          <SelectItem key={topic.id} value={topic.id}>
                            {topic.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Question Configuration */}
            <Card className="border-0 shadow-xl bg-white/80 backdrop-blur-sm">
              <CardHeader className="bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-t-lg">
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5" />
                  Question Configuration
                </CardTitle>
                <CardDescription className="text-purple-100">
                  Configure the type and parameters for your question
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700">Question Type</label>
                    <Select value={selectedQuestionType} onValueChange={setSelectedQuestionType}>
                      <SelectTrigger data-testid="question-type-select">
                        <SelectValue placeholder="Select question type" />
                      </SelectTrigger>
                      <SelectContent>
                        {questionTypes.map((type) => (
                          <SelectItem key={type.value} value={type.value}>
                            <div>
                              <div className="font-medium">{type.label}</div>
                              <div className="text-xs text-slate-500">{type.description}</div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700">Part (Optional)</label>
                    <Select value={selectedPart} onValueChange={setSelectedPart}>
                      <SelectTrigger data-testid="part-select">
                        <SelectValue placeholder="Select part" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">No Part Selected</SelectItem>
                        {parts.map((part) => (
                          <SelectItem key={part.id} value={part.id}>
                            {part.part_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700">Slot (Optional)</label>
                    <Select value={selectedSlot} onValueChange={setSelectedSlot}>
                      <SelectTrigger data-testid="slot-select">
                        <SelectValue placeholder="Select slot" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">No Slot Selected</SelectItem>
                        {slots.map((slot) => (
                          <SelectItem key={slot.id} value={slot.id}>
                            {slot.slot_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <Separator className="my-6" />

                <div className="text-center">
                  <div className="flex flex-wrap gap-4 justify-center">
                    <Button 
                      onClick={generateQuestion}
                      disabled={!selectedTopic || !selectedQuestionType || isGenerating || isAutoMode}
                      size="lg"
                      className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white px-8 py-3"
                      data-testid="generate-question-btn"
                    >
                      {isGenerating ? (
                        <>
                          <Loader2 className="h-5 w-5 animate-spin mr-2" />
                          Generating Question...
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-5 w-5 mr-2" />
                          Generate Question
                        </>
                      )}
                    </Button>

                    {generatedQuestion && !isAutoMode && (
                      <Button
                        onClick={saveQuestionManually}
                        variant="outline"
                        size="lg"
                        className="border-green-500 text-green-600 hover:bg-green-50 px-8 py-3"
                      >
                        Save to Database
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Results Panel */}
          <div className="space-y-6">
            {/* Statistics Cards */}
            <div className="grid grid-cols-2 gap-4">
              <Card className="border-0 shadow-lg bg-gradient-to-br from-blue-50 to-blue-100">
                <CardContent className="p-4 text-center">
                  <div className="text-2xl font-bold text-blue-800">{newQuestionsCount}</div>
                  <div className="text-sm text-blue-600">New Questions Generated</div>
                  <div className="text-xs text-blue-500">Ready for practice</div>
                </CardContent>
              </Card>
              
              <Card className="border-0 shadow-lg bg-gradient-to-br from-green-50 to-green-100">
                <CardContent className="p-4 text-center">
                  <div className="text-2xl font-bold text-green-800">{pyqSolutionsCount}</div>
                  <div className="text-sm text-green-600">PYQ Solutions Generated</div>
                  <div className="text-xs text-green-500">Solutions completed</div>
                </CardContent>
              </Card>
            </div>
            {/* Generated Question */}
            {generatedQuestion && (
              <Card className="border-0 shadow-xl bg-white/90 backdrop-blur-sm">
                <CardHeader className="bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-t-lg">
                  <CardTitle className="text-lg">Generated Question</CardTitle>
                  <div className="flex gap-2">
                    <Badge variant="secondary" className="bg-white/20 text-white">
                      {generatedQuestion.question_type}
                    </Badge>
                    <Badge variant="secondary" className="bg-white/20 text-white">
                      {generatedQuestion.difficulty_level}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-6 space-y-4" data-testid="generated-question">
                  <div>
                    <h4 className="font-semibold text-slate-800 mb-2">Question:</h4>
                    <p className="text-slate-700 leading-relaxed">{generatedQuestion.question_statement}</p>
                  </div>

                  {generatedQuestion.options && renderOptions(generatedQuestion.options, generatedQuestion.answer, generatedQuestion.question_type)}

                  {!generatedQuestion.options && (
                    <div>
                      <h4 className="font-semibold text-slate-800 mb-2">Answer:</h4>
                      <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                        <p className="text-emerald-800">{generatedQuestion.answer}</p>
                      </div>
                    </div>
                  )}

                  <div>
                    <h4 className="font-semibold text-slate-800 mb-2">Solution:</h4>
                    <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                      <p className="text-slate-700 whitespace-pre-wrap">{generatedQuestion.solution}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Existing Questions Reference */}
            {existingQuestions.length > 0 && (
              <Card className="border-0 shadow-lg bg-white/70 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-lg text-slate-800">Reference Questions</CardTitle>
                  <CardDescription>
                    Previous questions from this topic for context
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="space-y-4">
                    {existingQuestions.slice(0, 2).map((question, index) => (
                      <div key={index} className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                        <p className="text-sm text-slate-700">{question.question_statement}</p>
                        {question.question_type && (
                          <Badge variant="outline" className="mt-2">{question.question_type}</Badge>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
      <Toaster />
    </div>
  );
}

export default App;