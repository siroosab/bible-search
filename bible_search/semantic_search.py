"""
Semantic search module for Bible Search Library
Handles semantic similarity search using sentence-transformers
"""

import os
import pickle
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bible_search.semantic")

class SemanticSearcher:
    def __init__(self, model_name: str = 'paraphrase-MiniLM-L6-v2'):
        """
        Initialize semantic searcher with a sentence transformer model
        
        Args:
            model_name: Sentence transformer model name
        """
        logger.info(f"Initializing semantic search with model: {model_name}")
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.verses = []
        self.embeddings = None
        self.embeddings_file = f"verse_embeddings_{model_name.replace('-', '_')}.pkl"
        
    def load_verses(self, verses: List[Dict[str, Any]], force_recompute: bool = False) -> None:
        """
        Load verse data and compute embeddings
        
        Args:
            verses: List of verse dictionaries with text and metadata
            force_recompute: Whether to force recomputing embeddings
        """
        logger.info(f"Loading {len(verses)} verses for semantic search")
        self.verses = verses
        
        # Check if embeddings are already computed
        if not force_recompute and os.path.exists(self.embeddings_file):
            logger.info(f"Loading pre-computed embeddings from {self.embeddings_file}")
            with open(self.embeddings_file, 'rb') as f:
                saved_data = pickle.load(f)
                
                # Validate that saved embeddings match current verses
                if (len(saved_data['verse_ids']) == len(verses) and
                    all(str(saved_data['verse_ids'][i]) == str(verse.get('id', i)) 
                        for i, verse in enumerate(verses))):
                    self.embeddings = saved_data['embeddings']
                    logger.info(f"Loaded {len(self.embeddings)} pre-computed embeddings")
                    return
                else:
                    logger.warning("Saved embeddings don't match current verses. Recomputing...")
        
        # Compute embeddings
        logger.info("Computing verse embeddings (this may take a while)...")
        texts = [verse['text'] for verse in verses]
        self.embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Save embeddings for future use
        with open(self.embeddings_file, 'wb') as f:
            pickle.dump({
                'verse_ids': [verse.get('id', i) for i, verse in enumerate(verses)],
                'embeddings': self.embeddings
            }, f)
        logger.info(f"Computed and saved {len(self.embeddings)} verse embeddings")
        
    def search(self, query: str, limit: int = 20, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Perform semantic search for verses similar to query
        
        Args:
            query: Search query text
            limit: Maximum number of results to return
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of matching verses with metadata and similarity scores
        """
        if self.embeddings is None or not self.verses:
            logger.warning("No verses or embeddings available for semantic search")
            return []
            
        logger.info(f"Performing semantic search for: {query}")
        
        # Encode the query
        query_embedding = self.model.encode(query)
        
        # Calculate cosine similarity between query and all verse embeddings
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Get top results
        top_indices = np.argsort(-similarities)[:limit]
        results = []
        
        for idx in top_indices:
            similarity = float(similarities[idx])
            if similarity >= threshold:
                verse = self.verses[idx].copy()
                verse['semantic_score'] = similarity
                results.append(verse)
                
        return results
    
    def search_by_theme(self, theme: str, limit: int = 20, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Search for verses related to a particular theme or concept
        
        Args:
            theme: Theme or concept to search for
            limit: Maximum number of results to return
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of matching verses with metadata and similarity scores
        """
        # Theme search is essentially the same as semantic search
        return self.search(theme, limit, threshold)
