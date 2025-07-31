"""
Bible Search Library - Main Module
Provides a unified interface for various search methods
"""

import os
import json
import time
from typing import List, Dict, Any, Optional, Union, Tuple
from enum import Enum
import logging
from pathlib import Path

from .database import BibleDatabase
from .fuzzy_search import FuzzySearcher
from .semantic_search import SemanticSearcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bible_search")

class SearchType(Enum):
    """Enum for different search types"""
    EXACT = "exact"        # Exact text search using SQLite FTS5
    FUZZY = "fuzzy"        # Fuzzy search using RapidFuzz
    SEMANTIC = "semantic"  # Semantic/meaning search using sentence-transformers
    TOPIC = "topic"        # Topic/theme search (specialized semantic search)
    ALL = "all"            # Combine all search methods
    

class BibleSearcher:
    """Main class for Bible search functionality"""
    
    def __init__(self, 
                 data_dir: str = None,
                 db_path: str = "bible_search.db",
                 model_name: str = "paraphrase-MiniLM-L6-v2"):
        """
        Initialize the Bible searcher
        
        Args:
            data_dir: Directory containing Bible JSON files
            db_path: Path to SQLite database
            model_name: Sentence transformer model name
        """
        logger.info("Initializing Bible Search Library")
        
        self.data_dir = data_dir
        self.db = BibleDatabase(db_path)
        self.fuzzy_searcher = FuzzySearcher()
        self.semantic_searcher = SemanticSearcher(model_name)
        
        self.translations = set()
        self.is_initialized = False
        
    def initialize(self, force_reload: bool = False) -> None:
        """
        Initialize search engines and load data
        
        Args:
            force_reload: Whether to force reloading data from JSON files
        """
        if self.is_initialized and not force_reload:
            logger.info("Already initialized, skipping")
            return
            
        # Check if database is already populated
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM verses")
        verse_count = cursor.fetchone()[0]
        conn.close()
        
        # Import Bible data if needed
        if verse_count == 0 or force_reload:
            self._import_bible_data()
            
        # Load data for fuzzy and semantic search
        self._load_search_data()
        
        self.is_initialized = True
        logger.info("Bible Search Library initialization complete")
        
    def _import_bible_data(self) -> None:
        """Import Bible data from JSON files"""
        if not self.data_dir:
            raise ValueError("Data directory not specified")
            
        data_path = Path(self.data_dir)
        if not data_path.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")
            
        # Find and import all JSON files
        json_files = list(data_path.glob("*.json"))
        if not json_files:
            raise FileNotFoundError(f"No JSON files found in {self.data_dir}")
            
        for json_file in json_files:
            translation = json_file.stem  # Use filename as translation identifier
            self.translations.add(translation)
            self.db.import_bible_json(str(json_file), translation)
            
    def _load_search_data(self) -> None:
        """Load verse data for fuzzy and semantic search"""
        # Get all verses from database
        all_verses = self.db.get_all_verses()
        
        # Load data into search engines
        self.fuzzy_searcher.load_verses(all_verses)
        self.semantic_searcher.load_verses(all_verses)
        
    def _get_db_connection(self):
        """Get SQLite connection"""
        import sqlite3
        return sqlite3.connect(self.db.db_path)
        
    def search(self, 
               query: str, 
               search_type: Union[str, SearchType] = SearchType.ALL,
               limit: int = 20,
               categorize: bool = True,
               include_scores: bool = True) -> Dict[str, Any]:
        """
        Search Bible verses using specified search method
        
        Args:
            query: Search query text
            search_type: Type of search to perform
            limit: Maximum number of results to return
            categorize: Whether to categorize results by book/chapter
            include_scores: Whether to include relevance scores
            
        Returns:
            Search results with metadata
        """
        if not self.is_initialized:
            self.initialize()
            
        # Convert string to enum if needed
        if isinstance(search_type, str):
            search_type = SearchType(search_type.lower())
            
        start_time = time.time()
        results = []
        
        # Perform search based on search type
        if search_type == SearchType.EXACT or search_type == SearchType.ALL:
            exact_results = self.db.search_text(query, limit)
            for result in exact_results:
                result['search_method'] = 'exact'
            results.extend(exact_results)
                
        if search_type == SearchType.FUZZY or search_type == SearchType.ALL:
            fuzzy_results = self.fuzzy_searcher.search(query, limit)
            for result in fuzzy_results:
                result['search_method'] = 'fuzzy'
            results.extend(fuzzy_results)
                
        if search_type == SearchType.SEMANTIC or search_type == SearchType.ALL:
            semantic_results = self.semantic_searcher.search(query, limit)
            for result in semantic_results:
                result['search_method'] = 'semantic'
                # Rename score field for consistency
                if 'semantic_score' in result:
                    result['score'] = result.pop('semantic_score')
            results.extend(semantic_results)
                
        if search_type == SearchType.TOPIC:
            topic_results = self.semantic_searcher.search_by_theme(query, limit)
            for result in topic_results:
                result['search_method'] = 'topic'
                # Rename score field for consistency
                if 'semantic_score' in result:
                    result['score'] = result.pop('semantic_score')
            results = topic_results
            
        # Remove duplicates (prefer higher scores)
        unique_results = {}
        for result in results:
            verse_id = result.get('id')
            if verse_id not in unique_results or result.get('score', 0) > unique_results[verse_id].get('score', 0):
                unique_results[verse_id] = result
                
        results = list(unique_results.values())
        
        # Sort by score
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Limit results
        if limit > 0:
            results = results[:limit]
            
        # Clean up results if scores not wanted
        if not include_scores:
            for result in results:
                if 'score' in result:
                    del result['score']
                if 'rank' in result:
                    del result['rank']
                    
        # Categorize results if requested
        if categorize:
            categorized = self._categorize_results(results)
            response = {
                'query': query,
                'search_type': search_type.value,
                'total_results': len(results),
                'execution_time': time.time() - start_time,
                'categorized_results': categorized
            }
        else:
            response = {
                'query': query,
                'search_type': search_type.value,
                'total_results': len(results),
                'execution_time': time.time() - start_time,
                'results': results
            }
            
        return response
        
    def _categorize_results(self, results: List[Dict[str, Any]]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Categorize results by book and chapter
        
        Args:
            results: List of search results
            
        Returns:
            Nested dictionary of categorized results
        """
        categorized = {}
        
        for result in results:
            book_name = result.get('book_name')
            chapter_name = result.get('chapter_name')
            
            if book_name not in categorized:
                categorized[book_name] = {}
                
            if chapter_name not in categorized[book_name]:
                categorized[book_name][chapter_name] = []
                
            categorized[book_name][chapter_name].append(result)
            
        return categorized
        
    def get_available_translations(self) -> List[str]:
        """Get list of available Bible translations"""
        if not self.is_initialized:
            self.initialize()
            
        if not self.translations:
            # Query database for translations
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT translation FROM books")
            self.translations = set(row[0] for row in cursor.fetchall())
            conn.close()
            
        return sorted(list(self.translations))
