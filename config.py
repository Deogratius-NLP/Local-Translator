"""
Configuration settings for the English to Local Languages Translator
"""

import os
from typing import List, Dict



class Config:
    """Application configuration"""
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    LANGUAGE = "en-US"

    
    # CSV file settings
    CSV_FILES: List[str] = [
        "english_to_haya_sukuma_nyakyusa 2.csv",
        "english_to_haya_sukuma_nyakyusa.csv"
         # Add your new CSV file here
    ]
    
    # Encoding options for CSV files
    CSV_ENCODINGS: List[str] = ['utf-8', 'windows-1252', 'latin-1', 'iso-8859-1']
    
    # Google Translate settings
    GOOGLE_TRANSLATE_TIMEOUT: int = 10
    GOOGLE_TRANSLATE_MAX_RETRIES: int = 3
    GOOGLE_TRANSLATE_RETRY_DELAY: tuple = (1, 3)  # Random delay between retries
    GOOGLE_TRANSLATE_RATE_LIMIT_DELAY: int = 5
    
    # Supported languages
    SUPPORTED_LANGUAGES: Dict[str, str] = {
        "swahili": "Swahili",
        "haya": "Haya", 
        "sukuma": "Sukuma"
    }
    
    # Language codes for Google Translate
    GOOGLE_TRANSLATE_CODES: Dict[str, str] = {
        "english": "en",
        "swahili": "sw"
    }
    
    # Common fallback words (offline dictionary)
    FALLBACK_TRANSLATIONS: Dict[str, Dict[str, str]] = {
        "swahili": {
            "hello": "hujambo",
            "goodbye": "kwaheri", 
            "thank you": "asante",
            "please": "tafadhali",
            "yes": "ndiyo",
            "no": "hapana",
            "water": "maji",
            "food": "chakula",
            "house": "nyumba",
            "family": "familia",
            "friend": "rafiki",
            "love": "upendo",
            "peace": "amani",
            "school": "shule",
            "book": "kitabu",
            "teacher": "mwalimu",
            "student": "mwanafunzi",
            "mother": "mama",
            "father": "baba",
            "child": "mtoto",
            "good": "nzuri",
            "bad": "mbaya",
            "big": "kubwa",
            "small": "ndogo"
        },
        "haya": {
            "hello": "oriire ota",
            "water": "amizi",
            "food": "ebyakula", 
            "house": "enju",
            "thank you": "waakera",
            "good": "kirungi",
            "man": "mushaija",
            "woman": "mukazi",
            "child": "mwana",
            "book": "ekitabu",
            "school": "umosomelo",
            "sleep": "okunyama",
            "eat": "okulya",
            "walk": "iruka",
            "morning": "bwakya",
            "one": "emo",
            "two": "ibili",
            "three": "ishatu",
            "four": "ina",
            "five": "itanu"
        },
        "sukuma": {
            "hello": "mwangaluka",
            "world": "welelo",
            "food": "shilewa",
            "water": "minze",
            "house": "numba",
            "school": "shule",
            "friend": "nsumba",
            "man": "ngosha",
            "woman": "nkima",
            "child": "mwana",
            "tomorrow": "ntondo",
            "home": "mukaya",
            "yes": "geko",
            "salt": "munhu",
            "shop": "iduka",
            "milk": "mabwhela",
            "talk": "goyomba",
            "one": "emo",
            "buy": "gula",
            "sell": "guzu"
        }
    }
    
    # API response messages
    MESSAGES: Dict[str, str] = {
        "empty_word": "Please enter a valid English word",
        "invalid_language": "Target language must be 'swahili', 'haya', or 'sukuma'",
        "csv_not_found": "Translation dictionary not found",
        "network_error": "Network timeout - please check your internet connection",
        "rate_limit": "Rate limit exceeded - please try again later",
        "translation_failed": "Translation failed after multiple attempts",
        "no_translation": "No translation found for this word",
        "server_error": "Internal server error occurred"
    }
    
    # Frontend settings
    FRONTEND_SETTINGS: Dict[str, any] = {
        "auto_focus": True,
        "copy_timeout": 2000,  # milliseconds
        "loading_timeout": 30000,  # 30 seconds max for translation
        "debounce_delay": 300,  # milliseconds for input debouncing
        "animation_duration": 500  # milliseconds
    }
    
    @classmethod
    def get_csv_file_path(cls) -> str:
        """Get the first available CSV file path"""
        for file in cls.CSV_FILES:
            if os.path.exists(file):
                return file
        return None
    
    @classmethod
    def get_all_csv_files(cls) -> List[str]:
        """Get all available CSV file paths"""
        available_files = []
        for file in cls.CSV_FILES:
            if os.path.exists(file):
                available_files.append(file)
        return available_files
    
    @classmethod
    def is_supported_language(cls, language: str) -> bool:
        """Check if language is supported"""
        return language.lower() in cls.SUPPORTED_LANGUAGES
    
    @classmethod
    def get_fallback_translation(cls, word: str, target_language: str) -> str:
        """Get fallback translation for common words"""
        word_lower = word.lower().strip()
        if target_language in cls.FALLBACK_TRANSLATIONS:
            return cls.FALLBACK_TRANSLATIONS[target_language].get(word_lower, None)
        return None