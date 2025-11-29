"""
Enhanced FastAPI backend for English to Local Languages Translator
Production-ready version with improved error handling, caching, and logging
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi import UploadFile, File
from Audio_1 import transcribe_audio_file
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
import pandas as pd
import os
import time
import logging
from datetime import datetime
from utils import log_translation


# Import our custom modules
from config import Config
from utils import CSVLoader, TranslationService, WordMatcher, TextProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
translation_service = TranslationService()
translation_df = pd.DataFrame()

# Load dataset at startup
try:
    translation_df = CSVLoader.load_translation_data()
    logger.info(f"Successfully loaded translation data with {len(translation_df)} entries")
except Exception as e:
    logger.error(f"Error loading CSV: {e}")
    translation_df = pd.DataFrame()

# Initialize FastAPI app
app = FastAPI(
    title="English to Local Languages Translator",
    description="Translate English words to Swahili, Haya, and Sukuma languages",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Serve static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Request/Response models
class TranslationRequest(BaseModel):
    english_word: str = Field(..., min_length=1, max_length=100, description="English word to translate")
    target_language: str = Field(..., pattern="^(swahili|haya|sukuma)$", description="Target language")

class TranslationResponse(BaseModel):
    english: str
    translation: str
    target_language: str
    language_name: str
    method: str
    success: bool
    timestamp: str
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    message: str
    csv_loaded: bool
    csv_entries: int
    supported_languages: List[str]
    uptime: str

class LanguageInfo(BaseModel):
    code: str
    name: str
    available: bool
    entries_count: int

# Global variables for tracking
start_time = time.time()
request_count = 0
translation_stats = {
    "total_requests": 0,
    "successful_translations": 0,
    "failed_translations": 0,
    "methods_used": {
        "csv_lookup": 0,
        "google_translate": 0,
        "fallback_dictionary": 0,
        "not_found": 0
    }
}

@app.middleware("http")
async def add_process_time_header(request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    try:
        if os.path.exists("index.html"):
            with open("index.html", "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        else:
            # Return a basic interface if index.html doesn't exist
            return HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>English to Local Languages Translator</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .container { max-width: 600px; margin: 0 auto; }
                    h1 { color: #333; }
                    .form-group { margin: 20px 0; }
                    input, select, button { padding: 10px; margin: 5px; }
                    button { background: #007bff; color: white; border: none; cursor: pointer; }
                    .result { margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>English to Local Languages Translator</h1>
                    <p>API is running! Please create index.html for the full interface.</p>
                    <p><strong>API Endpoints:</strong></p>
                    <ul>
                        <li>POST /translate - Translate words</li>
                        <li>GET /health - Health check</li>
                        <li>GET /available-languages - Supported languages</li>
                        <li>GET /api/docs - API documentation</li>
                    </ul>
                </div>
            </body>
            </html>
            """)
    except Exception as e:
        logger.error(f"Error serving index.html: {e}")
        return HTMLResponse(content=f"<h1>Error loading page</h1><p>{str(e)}</p>")

@app.post("/transcribe/")
async def transcribe_audio(file: UploadFile = File(...)):
    if not file.content_type.startswith("audio/"):
        raise HTTPException(400, "Invalid audio file")
    wav_bytes = await file.read()
    try:
        text = transcribe_audio_file(wav_bytes, language=Config.LANGUAGE)
        return {"text": text}
    except Exception as e:
        raise HTTPException(422, str(e))

@app.post("/translate", response_model=TranslationResponse)
async def translate_word(request: TranslationRequest, background_tasks: BackgroundTasks):
    """Translate English word to specified target language"""
    global request_count, translation_stats
    
    request_count += 1
    translation_stats["total_requests"] += 1
    
    try:
        # Validate input
        is_valid, error_message = TextProcessor.validate_input(request.english_word)
        if not is_valid:
            translation_stats["failed_translations"] += 1
            raise HTTPException(status_code=400, detail=error_message)
        
        english_word = request.english_word.strip()
        target_language = request.target_language.lower()
        
        logger.info(f"Translation request: '{english_word}' -> {target_language}")
        
        # Method 1: Try CSV lookup first
        csv_translation = WordMatcher.search_in_csv(english_word, target_language, translation_df)
        if csv_translation:
            translation_stats["successful_translations"] += 1
            translation_stats["methods_used"]["csv_lookup"] += 1
            
            response = TranslationResponse(
                english=english_word,
                translation=csv_translation,
                target_language=target_language,
                language_name=Config.SUPPORTED_LANGUAGES[target_language],
                method="csv_lookup",
                success=True,
                timestamp=datetime.now().isoformat()
            )
            
            # Log successful translation in background
            background_tasks.add_task(log_translation, english_word, csv_translation, target_language, "csv_lookup")
            return response
        
        # Method 2: Try fallback dictionary
        fallback_translation = Config.get_fallback_translation(english_word, target_language)
        if fallback_translation:
            translation_stats["successful_translations"] += 1
            translation_stats["methods_used"]["fallback_dictionary"] += 1
            
            response = TranslationResponse(
                english=english_word,
                translation=fallback_translation,
                target_language=target_language,
                language_name=Config.SUPPORTED_LANGUAGES[target_language],
                method="fallback_dictionary",
                success=True,
                timestamp=datetime.now().isoformat()
            )
            
            background_tasks.add_task(log_translation, english_word, fallback_translation, target_language, "fallback_dictionary")
            return response
        
        # Method 3: For Swahili, use Google Translate
        if target_language == "swahili":
            try:
                swahili_translation = translation_service.translate_to_swahili(english_word)
                translation_stats["successful_translations"] += 1
                translation_stats["methods_used"]["google_translate"] += 1
                
                response = TranslationResponse(
                    english=english_word,
                    translation=swahili_translation,
                    target_language=target_language,
                    language_name=Config.SUPPORTED_LANGUAGES[target_language],
                    method="google_translate",
                    success=True,
                    timestamp=datetime.now().isoformat()
                )
                
                background_tasks.add_task(log_translation, english_word, swahili_translation, target_language, "google_translate")
                return response
                
            except Exception as e:
                logger.error(f"Google Translate failed for '{english_word}': {str(e)}")
                translation_stats["failed_translations"] += 1
                translation_stats["methods_used"]["not_found"] += 1
                
                return TranslationResponse(
                    english=english_word,
                    translation="",
                    target_language=target_language,
                    language_name=Config.SUPPORTED_LANGUAGES[target_language],
                    method="failed",
                    success=False,
                    timestamp=datetime.now().isoformat(),
                    error=str(e)
                )
        
        # Method 4: No translation found
        translation_stats["failed_translations"] += 1
        translation_stats["methods_used"]["not_found"] += 1
        
        return TranslationResponse(
            english=english_word,
            translation="",
            target_language=target_language,
            language_name=Config.SUPPORTED_LANGUAGES[target_language],
            method="not_found",
            success=False,
            timestamp=datetime.now().isoformat(),
            error=f"No {target_language} translation found for '{english_word}'"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        translation_stats["failed_translations"] += 1
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

@app.get("/available-languages", response_model=List[LanguageInfo])
async def get_available_languages():
    """Get list of available target languages with statistics"""
    languages = []
    
    for code, name in Config.SUPPORTED_LANGUAGES.items():
        # Count entries for this language in CSV
        entries_count = 0
        if not translation_df.empty and code in translation_df.columns:
            entries_count = len(translation_df[translation_df[code].notna() & (translation_df[code] != '')])
        
        languages.append(LanguageInfo(
            code=code,
            name=name,
            available=True,
            entries_count=entries_count
        ))
    
    return languages

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "English to Local Languages Translator API is running",
        "csv_loaded": not translation_df.empty,
        "csv_entries": len(translation_df) if not translation_df.empty else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)