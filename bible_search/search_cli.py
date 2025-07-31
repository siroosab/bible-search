"""
Command Line Interface for Bible Search Library
Allows users to search Bible data using various search methods
"""

import os
import sys
import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from . import BibleSearcher, SearchType

def setup_logging():
    """Set up logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

def format_verse_result(verse: Dict[str, Any], show_score: bool = False) -> str:
    """Format a single verse result for display"""
    result = f"\033[1m{verse['name']}\033[0m: {verse['text']}"
    
    if show_score and 'score' in verse:
        # Format score as percentage with 2 decimal places
        score_pct = verse['score'] * 100 if verse['search_method'] == 'semantic' else verse['score']
        result += f" \033[90m[Score: {score_pct:.2f}%]\033[0m"
        
    return result

def display_results(search_results: Dict[str, Any], show_scores: bool = False, 
                    colored_output: bool = True, show_time: bool = True):
    """Display search results in a user-friendly format"""
    query = search_results['query']
    search_type = search_results['search_type']
    total_results = search_results['total_results']
    
    # Detect if terminal supports colors
    if not colored_output or not sys.stdout.isatty():
        # Remove color codes for terminals that don't support them
        global_reset = ""
        cyan = ""
        green = ""
        yellow = ""
        magenta = ""
        bold = ""
        reset = ""
    else:
        # ANSI color codes
        global_reset = "\033[0m"
        cyan = "\033[36m"
        green = "\033[32m"
        yellow = "\033[33m"
        magenta = "\033[35m"
        bold = "\033[1m"
        reset = "\033[0m"
    
    # Print header
    print(f"\n{cyan}{bold}===== Bible Search Results ====={reset}")
    print(f"{cyan}Query:{reset} {bold}{query}{reset}")
    print(f"{cyan}Search Type:{reset} {bold}{search_type}{reset}")
    print(f"{cyan}Total Results:{reset} {bold}{total_results}{reset}")
    
    if show_time and 'execution_time' in search_results:
        print(f"{cyan}Execution Time:{reset} {bold}{search_results['execution_time']:.3f} seconds{reset}")
    
    print("\n")
    
    # Display categorized results
    if 'categorized_results' in search_results:
        for book_name, chapters in search_results['categorized_results'].items():
            print(f"{green}{bold}{book_name}{reset}")
            
            for chapter_name, verses in chapters.items():
                print(f"  {yellow}{chapter_name}{reset}")
                
                for verse in verses:
                    result_text = format_verse_result(verse, show_scores)
                    print(f"    - {result_text}")
                    
                print()  # Empty line between chapters
                
    # Display uncategorized results
    elif 'results' in search_results:
        for verse in search_results['results']:
            book_name = verse.get('book_name', '')
            chapter_name = verse.get('chapter_name', '')
            
            print(f"{green}{bold}{book_name}{reset} - {yellow}{chapter_name}{reset}")
            result_text = format_verse_result(verse, show_scores)
            print(f"  - {result_text}\n")

def main():
    """Main function for CLI interface"""
    setup_logging()
    
    parser = argparse.ArgumentParser(description='Bible Search CLI')
    parser.add_argument('query', nargs='?', help='Search query text')
    parser.add_argument('--type', '-t', choices=['exact', 'fuzzy', 'semantic', 'topic', 'all'], 
                       default='all', help='Search type')
    parser.add_argument('--limit', '-l', type=int, default=20,
                       help='Maximum number of results to return')
    parser.add_argument('--data-dir', '-d', default='bible_data',
                       help='Directory containing Bible JSON files')
    parser.add_argument('--db-file', '-db', default='bible_search.db',
                       help='SQLite database file path')
    parser.add_argument('--json', '-j', action='store_true',
                       help='Output results in JSON format')
    parser.add_argument('--scores', '-s', action='store_true',
                       help='Show relevance scores')
    parser.add_argument('--no-categorize', action='store_true',
                       help='Do not categorize results by book/chapter')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    parser.add_argument('--initialize-only', action='store_true',
                       help='Only initialize database without performing search')
    
    args = parser.parse_args()
    
    # Create Bible searcher
    data_dir = os.path.abspath(args.data_dir)
    searcher = BibleSearcher(data_dir=data_dir, db_path=args.db_file)
    
    try:
        # Initialize searcher
        searcher.initialize()
        
        # If initialize-only flag is set, exit after initialization
        if args.initialize_only:
            print(f"Database initialized successfully at {args.db_file}")
            print(f"Available translations: {', '.join(searcher.get_available_translations())}")
            return
        
        # Check if query is provided
        if not args.query:
            print("Error: Search query is required")
            parser.print_help()
            return 1
        
        # Perform search
        results = searcher.search(
            query=args.query,
            search_type=args.type,
            limit=args.limit,
            categorize=not args.no_categorize,
            include_scores=args.scores or args.json
        )
        
        # Display results
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            display_results(results, show_scores=args.scores, 
                          colored_output=not args.no_color)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
        
    return 0

if __name__ == '__main__':
    sys.exit(main())
