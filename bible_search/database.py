"""
Database module for Bible Search Library
Handles SQLite operations with FTS5 for full-text search
"""

import os
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bible_search.database")

class BibleDatabase:
    def __init__(self, db_path: str = "bible_search.db"):
        """
        Initialize the Bible database
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._create_tables_if_needed()
        
    def _create_tables_if_needed(self) -> None:
        """Create necessary tables if they don't exist"""
        logger.info(f"Setting up database at {self.db_path}")
        
        with sqlite3.connect(self.db_path) as conn:
            # Create books table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    translation TEXT NOT NULL
                )
            ''')
            
            # Create chapters table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chapters (
                    id INTEGER PRIMARY KEY,
                    book_id INTEGER NOT NULL,
                    chapter_num INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    FOREIGN KEY (book_id) REFERENCES books(id)
                )
            ''')
            
            # Create verses table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS verses (
                    id INTEGER PRIMARY KEY,
                    chapter_id INTEGER NOT NULL,
                    book_id INTEGER NOT NULL,
                    verse_num INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    name TEXT NOT NULL,
                    FOREIGN KEY (chapter_id) REFERENCES chapters(id),
                    FOREIGN KEY (book_id) REFERENCES books(id)
                )
            ''')
            
            # Create FTS5 virtual table for full-text search
            conn.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS verse_search 
                USING fts5(
                    name, 
                    text, 
                    book_name,
                    chapter_name,
                    verse_id UNINDEXED,
                    content='verses',
                    content_rowid='id',
                    tokenize='porter unicode61'
                )
            ''')
            
            # Create trigger to keep FTS table in sync with main table
            conn.executescript('''
                CREATE TRIGGER IF NOT EXISTS verses_ai AFTER INSERT ON verses BEGIN
                    INSERT INTO verse_search(verse_id, name, text, book_name, chapter_name)
                    SELECT new.id, new.name, new.text, b.name, c.name
                    FROM books b, chapters c
                    WHERE b.id = new.book_id AND c.id = new.chapter_id;
                END;
                
                CREATE TRIGGER IF NOT EXISTS verses_ad AFTER DELETE ON verses BEGIN
                    DELETE FROM verse_search WHERE verse_id = old.id;
                END;
                
                CREATE TRIGGER IF NOT EXISTS verses_au AFTER UPDATE ON verses BEGIN
                    DELETE FROM verse_search WHERE verse_id = old.id;
                    INSERT INTO verse_search(verse_id, name, text, book_name, chapter_name)
                    SELECT new.id, new.name, new.text, b.name, c.name
                    FROM books b, chapters c
                    WHERE b.id = new.book_id AND c.id = new.chapter_id;
                END;
            ''')
            
            conn.commit()
            logger.info("Database tables created successfully")

    def import_bible_json(self, json_path: str, translation: str) -> None:
        """
        Import Bible data from JSON file
        
        Args:
            json_path: Path to JSON file
            translation: Bible translation identifier (e.g., 'KJV', 'ASV')
        """
        logger.info(f"Importing {translation} from {json_path}")
        
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Bible file not found: {json_path}")
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                bible_data = json.load(f)
                
            # Start transaction for better performance
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("BEGIN TRANSACTION")
                
                try:
                    # Process each book
                    for book_idx, book in enumerate(bible_data.get('books', [])):
                        book_name = book.get('name')
                        
                        # Insert book
                        cursor = conn.execute(
                            "INSERT INTO books (name, translation) VALUES (?, ?)",
                            (book_name, translation)
                        )
                        book_id = cursor.lastrowid
                        
                        # Process each chapter
                        for chapter in book.get('chapters', []):
                            chapter_num = chapter.get('chapter')
                            chapter_name = chapter.get('name')
                            
                            # Insert chapter
                            cursor = conn.execute(
                                "INSERT INTO chapters (book_id, chapter_num, name) VALUES (?, ?, ?)",
                                (book_id, chapter_num, chapter_name)
                            )
                            chapter_id = cursor.lastrowid
                            
                            # Process each verse
                            for verse in chapter.get('verses', []):
                                verse_num = verse.get('verse')
                                verse_text = verse.get('text')
                                verse_name = verse.get('name')
                                
                                # Insert verse
                                conn.execute(
                                    """INSERT INTO verses 
                                       (chapter_id, book_id, verse_num, text, name) 
                                       VALUES (?, ?, ?, ?, ?)""",
                                    (chapter_id, book_id, verse_num, verse_text, verse_name)
                                )
                    
                    # Commit transaction
                    conn.commit()
                    logger.info(f"Successfully imported {translation} Bible data")
                    
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Error importing Bible data: {str(e)}")
                    raise
        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON file: {json_path}")
            raise
            
    def search_text(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Perform full-text search using SQLite FTS5
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            
        Returns:
            List of matching verses with metadata
        """
        logger.info(f"Starting search_text with query: {query}, limit: {limit}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Completely different approach: Use a direct query on the verses table with LIKE
                # This is less efficient but avoids FTS5 issues
                logger.info("Using direct LIKE query instead of FTS5")
                search_pattern = f"%{query}%"
                
                cursor = conn.execute(
                    """SELECT v.id, v.name, v.text, b.name as book_name, c.name as chapter_name, b.translation
                       FROM verses v
                       JOIN books b ON v.book_id = b.id
                       JOIN chapters c ON v.chapter_id = c.id
                       WHERE v.text LIKE ? OR v.name LIKE ?
                       LIMIT ?""",
                    (search_pattern, search_pattern, limit)
                )
                
                results = []
                for row in cursor:
                    # Calculate a simple relevance score based on the number of query term occurrences
                    query_terms = query.lower().split()
                    text = row['text'].lower()
                    name = row['name'].lower()
                    
                    # Count occurrences of query terms in text and name
                    count = 0
                    for term in query_terms:
                        count += text.count(term) + name.count(term)
                    
                    # Higher count means more relevant
                    score = min(100, count * 10)  # Cap at 100
                    
                    verse_data = {
                        'id': row['id'],
                        'name': row['name'],
                        'text': row['text'],
                        'book_name': row['book_name'],
                        'chapter_name': row['chapter_name'],
                        'translation': row['translation'],
                        'rank': score  # Simple relevance score
                    }
                    results.append(verse_data)
                
                # Sort by score (descending)
                results.sort(key=lambda x: x['rank'], reverse=True)
                
                logger.info(f"Found {len(results)} results using direct query")
                return results
                
        except Exception as e:
            logger.error(f"Error in search_text: {str(e)}")
            logger.error(traceback.format_exc())
            raise
            
    def get_all_verses(self, translation: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all verses from the database
        
        Args:
            translation: Optional filter for specific translation
            
        Returns:
            List of all verses with metadata
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = """
                SELECT v.id, v.name, v.text, b.name as book_name, c.name as chapter_name, b.translation
                FROM verses v
                JOIN books b ON v.book_id = b.id
                JOIN chapters c ON v.chapter_id = c.id
            """
            
            params = []
            if translation:
                query += " WHERE b.translation = ?"
                params.append(translation)
                
            cursor = conn.execute(query, params)
            
            results = []
            for row in cursor:
                results.append({
                    'id': row['id'],
                    'name': row['name'],
                    'text': row['text'],
                    'book_name': row['book_name'],
                    'chapter_name': row['chapter_name'],
                    'translation': row['translation']
                })
                
            return results
