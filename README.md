# Advanced Bible Search Library

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Issues](https://img.shields.io/github/issues/yourusername/bible-search)](https://github.com/yourusername/bible-search/issues)

A comprehensive Bible text search library that combines multiple advanced search techniques to provide powerful, flexible searching of biblical texts.

## Features

- **Fast Text Search**: Using SQLite with FTS5 for high-performance exact text matching
- **Fuzzy Search**: Powered by RapidFuzz for approximate string matching
- **Semantic Search**: Using sentence-transformers for meaning-based searches
- **Topic Search**: Find verses related to specific themes or concepts
- **Multiple Translations**: Support for different Bible translations (KJV, ASV included)
- **Categorized Results**: Results organized by book and chapter
- **Scored Results**: Relevance scoring for search results

## Requirements

- Python 3.7+
- Libraries: SQLite, RapidFuzz, sentence-transformers, etc. (see requirements.txt)

## Installation

### From GitHub

```bash
# Install directly from GitHub
pip install adv-bible-search

# Or install directly from GitHub
pip install git+https://github.com/siroosab/bible-search.git

# Or clone and install locally
git clone https://github.com/siroosab/bible-search.git
cd bible-search
pip install -e .
```

### From Source

1. Clone/download the repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Data Structure

The library expects Bible data in JSON format with the following structure:

```json
{
    "books": [
        {
            "name": "Genesis",
            "chapters": [
                {
                    "chapter": 1,
                    "name": "Genesis 1",
                    "verses": [
                        {
                            "verse": 1,
                            "chapter": 1,
                            "name": "Genesis 1:1",
                            "text": "In the beginning God created the heaven and the earth."
                        },
                        // More verses...
                    ]
                },
                // More chapters...
            ]
        },
        // More books...
    ]
}
```

## Usage

### Command Line Interface

The library includes a command-line interface for searching:

```bash
# Basic search (uses all search methods)
python search_cli.py "creation"

# Specify search type
python search_cli.py --type fuzzy "creation"
python search_cli.py --type semantic "love your neighbor"
python search_cli.py --type topic "forgiveness"

# Limit number of results
python search_cli.py --limit 10 "light"

# Show relevance scores
python search_cli.py --scores "faith"

# Output in JSON format
python search_cli.py --json "hope"
```

### Python API

```python
from bible_search import BibleSearcher, SearchType

# Initialize the searcher
searcher = BibleSearcher(data_dir="bible_data", db_path="bible_search.db")
searcher.initialize()

# Basic search (uses all search methods)
results = searcher.search("creation")

# Specify search type
results = searcher.search("creation", search_type=SearchType.FUZZY)
results = searcher.search("love your neighbor", search_type=SearchType.SEMANTIC)
results = searcher.search("forgiveness", search_type=SearchType.TOPIC)

# Control other parameters
results = searcher.search(
    query="light", 
    search_type=SearchType.ALL,
    limit=10,
    categorize=True,
    include_scores=True
)

# Available search types:
# - SearchType.EXACT: Exact text matching using SQLite FTS5
# - SearchType.FUZZY: Approximate string matching using RapidFuzz
# - SearchType.SEMANTIC: Meaning-based search using sentence-transformers
# - SearchType.TOPIC: Theme/concept search (specialized semantic search)
# - SearchType.ALL: Combine all search methods (default)
```

## Module Structure

- `bible_search.py`: Main interface for the search library
- `database.py`: SQLite database operations with FTS5
- `fuzzy_search.py`: Fuzzy text matching with RapidFuzz
- `semantic_search.py`: Semantic similarity search with sentence-transformers
- `search_cli.py`: Command-line interface

## Initial Setup

When first running the library, it will:

1. Create an SQLite database
2. Import Bible data from JSON files
3. Create necessary database tables and indexes
4. Generate semantic embeddings (this may take some time on first run)

The semantic embeddings are saved to disk for faster subsequent runs.

## Search Types Explained

1. **Exact Search**: Finds exact text matches using SQLite's FTS5 extension
2. **Fuzzy Search**: Finds approximate matches, helpful for typos or spelling variations
3. **Semantic Search**: Finds verses with similar meaning regardless of specific wording
4. **Topic Search**: Specialized semantic search focused on themes and concepts

## Performance Considerations

- Semantic search requires creating embeddings which can be time-consuming on first run
- The SQLite database provides efficient storage and fast exact searches
- For very large datasets, consider using a more robust search engine like Elasticsearch
