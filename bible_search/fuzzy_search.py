"""
Fuzzy search module for Bible Search Library
Handles fuzzy text matching using RapidFuzz
"""

from typing import List, Dict, Any, Tuple
from rapidfuzz import process, fuzz
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bible_search.fuzzy")

class FuzzySearcher:
    def __init__(self):
        """Initialize the fuzzy searcher"""
        self.verses = []
        self.text_corpus = []
        self.verse_index_map = {}
        
    def load_verses(self, verses: List[Dict[str, Any]]) -> None:
        """
        Load verse data for fuzzy searching
        
        Args:
            verses: List of verse dictionaries with text and metadata
        """
        logger.info(f"Loading {len(verses)} verses for fuzzy search")
        
        self.verses = verses
        self.text_corpus = [verse['text'] for verse in verses]
        self.verse_index_map = {i: verse for i, verse in enumerate(verses)}
        
    def search(self, query: str, limit: int = 20, score_cutoff: int = 70) -> List[Dict[str, Any]]:
        """
        Perform fuzzy search on loaded verses
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            score_cutoff: Minimum similarity score (0-100)
            
        Returns:
            List of matching verses with metadata and similarity scores
        """
        if not self.text_corpus:
            logger.warning("No verses loaded for fuzzy search")
            return []
            
        logger.info(f"Performing fuzzy search for: {query}")
        
        # Use RapidFuzz to find matches
        matches = process.extract(
            query, 
            self.text_corpus,
            scorer=fuzz.token_set_ratio,  # Good for finding words in different orders
            limit=limit,
            score_cutoff=score_cutoff
        )
        
        results = []
        for match in matches:
            text, score, idx = match
            verse = self.verse_index_map[idx].copy()
            verse['score'] = score
            results.append(verse)
            
        return results
        
    def search_by_fields(self, 
                         query: str, 
                         fields: List[str] = ['text'], 
                         limit: int = 20, 
                         score_cutoff: int = 70) -> List[Dict[str, Any]]:
        """
        Perform fuzzy search on specific fields of verse data
        
        Args:
            query: Search query text
            fields: List of fields to search in (e.g., ['text', 'book_name'])
            limit: Maximum number of results to return
            score_cutoff: Minimum similarity score (0-100)
            
        Returns:
            List of matching verses with metadata and similarity scores
        """
        if not self.verses:
            logger.warning("No verses loaded for fuzzy search")
            return []
            
        logger.info(f"Performing field-specific fuzzy search for: {query}")
        
        all_matches = []
        
        for field in fields:
            # Create corpus for this field
            field_corpus = []
            for i, verse in enumerate(self.verses):
                if field in verse:
                    field_corpus.append((verse[field], i))
                else:
                    field_corpus.append(("", i))
                    
            # Search in this field
            matches = process.extract(
                query, 
                [item[0] for item in field_corpus],
                scorer=fuzz.token_set_ratio,
                limit=limit,
                score_cutoff=score_cutoff
            )
            
            for match in matches:
                text, score, corpus_idx = match
                verse_idx = field_corpus[corpus_idx][1]
                verse = self.verse_index_map[verse_idx].copy()
                verse['score'] = score
                verse['matched_field'] = field
                all_matches.append((verse, score))
                
        # Sort by score and take top results
        all_matches.sort(key=lambda x: x[1], reverse=True)
        results = [match[0] for match in all_matches[:limit]]
        
        return results
