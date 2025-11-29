"""
Utility functions for the English to Local Languages Translator
"""

import pandas as pd
import os
import re
import time
import random
from typing import Optional, Dict, List, Tuple
from googletrans import Translator
from config import Config
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CSVLoader:
    """Handle CSV file loading and processing"""

    @staticmethod
    def load_translation_data() -> pd.DataFrame:
        """Load and clean the translation dataset with robust error handling"""
        csv_file = Config.get_csv_file_path()
        
        if not csv_file:
            raise FileNotFoundError(f"CSV file not found. Looked for: {Config.CSV_FILES}")
        
        logger.info(f"Loading CSV file: {csv_file}")
        
        df = None
        for encoding in Config.CSV_ENCODINGS:
            try:
                df = pd.read_csv(csv_file, encoding=encoding)
                logger.info(f"Successfully loaded CSV with {encoding} encoding")
                break
            except UnicodeDecodeError:
                logger.warning(f"Failed to load CSV with {encoding} encoding")
                continue
            except Exception as e:
                logger.error(f"Error loading CSV with {encoding}: {str(e)}")
                continue
        
        if df is None:
            raise Exception(f"Could not read CSV file with any encoding: {Config.CSV_ENCODINGS}")
        
        df = CSVLoader._clean_dataframe(df)
        logger.info(f"Loaded {len(df)} translation entries")
        
        return df

    @classmethod
    def load_specific_csv(cls, csv_file: str) -> pd.DataFrame:
        """Load a specific CSV file with encoding detection"""
        if not os.path.exists(csv_file):
            logger.warning(f"CSV file not found: {csv_file}")
            return pd.DataFrame()
        
        logger.info(f"Loading CSV file: {csv_file}")
        
        for encoding in Config.CSV_ENCODINGS:
            try:
                df = pd.read_csv(csv_file, encoding=encoding)
                logger.info(f"Successfully loaded CSV with {encoding} encoding")
                
                # Clean column names
                df.columns = df.columns.str.strip().str.lower()
                
                # Check for required columns
                required_columns = ['english'] + list(Config.SUPPORTED_LANGUAGES.keys())
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    logger.warning(f"Missing columns in CSV: {missing_columns}")
                
                # Clean and prepare data
                df = df.dropna(subset=['english'])
                df['english'] = df['english'].str.strip().str.lower()
                df = df[df['english'] != '']
                
                logger.info(f"Loaded {len(df)} translation entries")
                return df
                
            except UnicodeDecodeError:
                logger.warning(f"Failed to load CSV with {encoding} encoding")
                continue
            except Exception as e:
                logger.error(f"Error loading CSV file {csv_file}: {e}")
                continue
        
        logger.error(f"Failed to load CSV file {csv_file} with any encoding")
        return pd.DataFrame()

    @staticmethod
    def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate the dataframe"""
        df.columns = df.columns.str.lower().str.strip()
        
        required_columns = ['english'] + list(Config.SUPPORTED_LANGUAGES.keys())
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.warning(f"Missing columns in CSV: {missing_columns}")
        
        for col in df.columns:
            if col in required_columns:
                df[col] = df[col].fillna('').astype(str).str.strip()
                df[col] = df[col].apply(lambda x: ' '.join(x.split()) if x else '')
        
        df = df[df['english'].str.len() > 0]
        
        return df



class TranslationService:
    """Handle all translation operations"""
    
    def __init__(self):
        self.translator = Translator()
        self.translation_cache = {}  # Simple in-memory cache
    
    def translate_to_swahili(self, english_word: str) -> str:
        """Translate English to Swahili using Google Translate with caching"""
        # Check cache first
        cache_key = f"en_to_sw_{english_word.lower()}"
        if cache_key in self.translation_cache:
            logger.info(f"Using cached translation for: {english_word}")
            return self.translation_cache[cache_key]
        
        # Translate using Google Translate
        for attempt in range(Config.GOOGLE_TRANSLATE_MAX_RETRIES):
            try:
                if attempt > 0:
                    delay = random.uniform(*Config.GOOGLE_TRANSLATE_RETRY_DELAY)
                    time.sleep(delay)
                
                result = self.translator.translate(
                    english_word, 
                    src=Config.GOOGLE_TRANSLATE_CODES['english'], 
                    dest=Config.GOOGLE_TRANSLATE_CODES['swahili']
                )
                
                if result and hasattr(result, 'text') and result.text:
                    translation = result.text.strip()
                    # Cache the result
                    self.translation_cache[cache_key] = translation
                    logger.info(f"Successfully translated '{english_word}' to '{translation}'")
                    return translation
                else:
                    raise Exception("Empty translation result")
                    
            except Exception as e:
                error_msg = str(e).lower()
                
                if any(keyword in error_msg for keyword in ['timeout', 'handshake', 'ssl', 'connection']):
                    if attempt == Config.GOOGLE_TRANSLATE_MAX_RETRIES - 1:
                        raise Exception(Config.MESSAGES["network_error"])
                    logger.warning(f"Network error on attempt {attempt + 1}: {str(e)}")
                    continue
                    
                elif 'rate limit' in error_msg or '429' in error_msg:
                    if attempt == Config.GOOGLE_TRANSLATE_MAX_RETRIES - 1:
                        raise Exception(Config.MESSAGES["rate_limit"])
                    logger.warning(f"Rate limit hit on attempt {attempt + 1}")
                    time.sleep(Config.GOOGLE_TRANSLATE_RATE_LIMIT_DELAY)
                    continue
                    
                else:
                    logger.error(f"Translation service error: {str(e)}")
                    raise Exception(f"Translation service error: {str(e)}")
        
        raise Exception(Config.MESSAGES["translation_failed"])


class WordMatcher:
    """Handle word matching and searching in the CSV data"""
    
    @staticmethod
    def search_in_csv(english_word: str, target_language: str, df: pd.DataFrame) -> Optional[str]:
        """Search for English word in CSV and return translation with fuzzy matching"""
        if df.empty or target_language not in df.columns:
            return None
        
        english_clean = WordMatcher._clean_word(english_word)
        
        # Method 1: Exact match
        exact_match = WordMatcher._exact_match(english_clean, target_language, df)
        if exact_match:
            logger.info(f"Found exact match for '{english_word}' -> '{exact_match}'")
            return exact_match
        
        # Method 2: Case-insensitive match
        case_match = WordMatcher._case_insensitive_match(english_clean, target_language, df)
        if case_match:
            logger.info(f"Found case-insensitive match for '{english_word}' -> '{case_match}'")
            return case_match
        
        # Method 3: Partial match (contains)
        partial_match = WordMatcher._partial_match(english_clean, target_language, df)
        if partial_match:
            logger.info(f"Found partial match for '{english_word}' -> '{partial_match}'")
            return partial_match
        
        # Method 4: Fuzzy match (similar words)
        fuzzy_match = WordMatcher._fuzzy_match(english_clean, target_language, df)
        if fuzzy_match:
            logger.info(f"Found fuzzy match for '{english_word}' -> '{fuzzy_match}'")
            return fuzzy_match
        
        return None
    
    @staticmethod
    def _clean_word(word: str) -> str:
        """Clean and normalize a word"""
        # Remove extra whitespace and convert to lowercase
        cleaned = ' '.join(word.strip().lower().split())
        # Remove punctuation except hyphens and apostrophes
        cleaned = re.sub(r'[^\w\s\'-]', '', cleaned)
        return cleaned
    
    @staticmethod
    def _exact_match(word: str, target_language: str, df: pd.DataFrame) -> Optional[str]:
        """Find exact match in CSV"""
        matches = df[df['english'].str.lower().str.strip() == word]
        return WordMatcher._get_best_translation(matches, target_language)
    
    @staticmethod
    def _case_insensitive_match(word: str, target_language: str, df: pd.DataFrame) -> Optional[str]:
        """Find case-insensitive match"""
        matches = df[df['english'].str.lower().str.strip().str.replace(r'\s+', ' ', regex=True) == word]
        return WordMatcher._get_best_translation(matches, target_language)
    
    @staticmethod
    def _partial_match(word: str, target_language: str, df: pd.DataFrame) -> Optional[str]:
        """Find partial match (word contains or is contained in CSV entry)"""
        # Try both directions: CSV contains word, and word contains CSV entry
        contains_matches = df[df['english'].str.lower().str.contains(word, na=False, regex=False)]
        contained_matches = df[df['english'].str.lower().apply(lambda x: word in x if x else False)]
        
        # Combine and prioritize shorter matches (more specific)
        all_matches = pd.concat([contains_matches, contained_matches]).drop_duplicates()
        if not all_matches.empty:
            # Sort by length of English word (shorter = more specific)
            all_matches = all_matches.sort_values('english', key=lambda x: x.str.len())
            return WordMatcher._get_best_translation(all_matches, target_language)
        
        return None
    
    @staticmethod
    def _fuzzy_match(word: str, target_language: str, df: pd.DataFrame) -> Optional[str]:
        """Find fuzzy match using simple similarity"""
        # Simple similarity based on common words/substrings
        word_parts = set(word.split())
        
        best_match = None
        best_score = 0
        
        for idx, row in df.iterrows():
            english_entry = row['english'].lower().strip()
            if not english_entry:
                continue
                
            entry_parts = set(english_entry.split())
            
            # Calculate Jaccard similarity
            intersection = word_parts.intersection(entry_parts)
            union = word_parts.union(entry_parts)
            
            if union:
                similarity = len(intersection) / len(union)
                if similarity > best_score and similarity >= 0.5:  # 50% similarity threshold
                    translation = WordMatcher._get_best_translation(pd.DataFrame([row]), target_language)
                    if translation:
                        best_match = translation
                        best_score = similarity
        
        return best_match
    
    @staticmethod
    def _get_best_translation(matches: pd.DataFrame, target_language: str) -> Optional[str]:
        """Get the best translation from matches"""
        if matches.empty:
            return None
        
        # Filter out empty translations
        valid_matches = matches[
            (matches[target_language].notna()) & 
            (matches[target_language].str.strip() != '')
        ]
        
        if not valid_matches.empty:
            # Return the first valid translation
            translation = valid_matches.iloc[0][target_language].strip()
            return translation if translation else None
        
        return None


class TextProcessor:
    """Handle text processing and validation"""
    
    @staticmethod
    def validate_input(text: str) -> Tuple[bool, str]:
        """Validate user input"""
        if not text or not text.strip():
            return False, Config.MESSAGES["empty_word"]
        
        # Check for reasonable length
        if len(text.strip()) > 100:
            return False, "Word is too long (max 100 characters)"
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r'^[a-zA-Z\s\'-]+$', text.strip()):
            return False, "Word contains invalid characters"
        
        return True, ""
    
    @staticmethod
    def detect_language(text: str) -> str:
        """Simple language detection based on patterns"""
        # This is a simple heuristic - in a real app you might use a proper language detection library
        text_lower = text.lower().strip()
        
        # Common English patterns
        english_indicators = ['the', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'have', 'has', 'will', 'would']
        
        if any(indicator in text_lower.split() for indicator in english_indicators):
            return 'english'
        
        # For now, assume English if we can't detect
        return 'english'
    
    @staticmethod
    def format_translation_response(english: str, translation: str, target_language: str, method: str) -> Dict:
        """Format the translation response"""
        return {
            "english": english.strip(),
            "translation": translation.strip() if translation else "",
            "target_language": target_language,
            "method": method,
            "success": bool(translation and translation.strip()),
            "language_name": Config.SUPPORTED_LANGUAGES.get(target_language, target_language.title())
        }

def log_translation(english_word: str, translation: str, target_language: str, method: str):
    logger.info(f"Logged Translation - '{english_word}' -> '{translation}' | Language: {target_language} | Method: {method}")
