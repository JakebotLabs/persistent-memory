#!/usr/bin/env python3
"""
Automatic memory promotion script for daily logs → MEMORY.md

Purpose: Take high-confidence significant events from daily logs and automatically
promote them to MEMORY.md for long-term retention.

Integrates with is_significant_classifier.py for content evaluation.
"""

import os
import sys
import re
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple

# Import our classifier
sys.path.append(os.path.dirname(__file__))
from is_significant_classifier import analyze_recent_logs, is_significant

def load_memory_md() -> Tuple[str, List[str]]:
    """
    Load current MEMORY.md content and return (content, sections).
    
    Returns:
        Tuple of (full_content, section_headers)
    """
    memory_path = os.path.join(os.path.dirname(__file__), "..", "MEMORY.md")
    
    if not os.path.exists(memory_path):
        return "", []
    
    with open(memory_path, 'r') as f:
        content = f.read()
    
    # Extract section headers for placement logic
    headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
    
    return content, headers


def format_promotion_entry(item: Dict, source_date: str) -> str:
    """
    Format a significant item for insertion into MEMORY.md.
    
    Args:
        item: Classification result from is_significant_classifier
        source_date: Date of the source log file
        
    Returns:
        Formatted markdown entry
    """
    # Clean up content (remove markdown formatting artifacts)
    content = item['content'].strip()
    content = re.sub(r'^#+\s*', '', content)  # Remove header markers
    content = re.sub(r'\n+', ' ', content)    # Collapse newlines
    
    # Truncate if very long
    if len(content) > 300:
        content = content[:297] + "..."
    
    # Format entry
    confidence_marker = "⭐" if item['confidence'] > 0.8 else "•"
    
    entry = f"- **{source_date}:** {confidence_marker} {content}"
    
    return entry


def find_insertion_point(memory_content: str, category: str = "Recent Updates") -> int:
    """
    Find the best insertion point in MEMORY.md for new content.
    
    Args:
        memory_content: Current MEMORY.md content
        category: Target section name
        
    Returns:
        Character position for insertion
    """
    # Look for existing "Recent Updates" or similar section
    recent_patterns = [
        r'## Recent Updates.*?(?=\n##|\n---|\Z)',
        r'## Latest.*?(?=\n##|\n---|\Z)', 
        r'## Current.*?(?=\n##|\n---|\Z)'
    ]
    
    for pattern in recent_patterns:
        match = re.search(pattern, memory_content, re.DOTALL)
        if match:
            # Insert at end of this section
            return match.end()
    
    # If no Recent Updates section, create one before Key Lessons
    lessons_match = re.search(r'\n## Key Lessons', memory_content)
    if lessons_match:
        insert_pos = lessons_match.start()
        return insert_pos
    
    # Fallback: insert before the last major section
    last_section = re.search(r'\n##[^#].*?(?=\n##|\Z)', memory_content[::-1])
    if last_section:
        return len(memory_content) - last_section.start()
    
    # Ultimate fallback: end of file
    return len(memory_content)


def promote_to_memory(days_back: int = 3, min_confidence: float = 0.7, dry_run: bool = False) -> Dict:
    """
    Promote high-confidence significant items to MEMORY.md.
    
    Args:
        days_back: How many days to analyze
        min_confidence: Minimum confidence threshold for promotion
        dry_run: If True, don't actually modify MEMORY.md
        
    Returns:
        Dictionary with promotion results
    """
    # Analyze recent logs
    analysis = analyze_recent_logs(days_back)
    
    # Filter for high-confidence items
    promotion_candidates = [
        item for item in analysis['significant_items']
        if item['confidence'] >= min_confidence
    ]
    
    results = {
        'analyzed_days': days_back,
        'candidates_found': len(promotion_candidates),
        'promotions_made': 0,
        'promoted_items': [],
        'dry_run': dry_run
    }
    
    if not promotion_candidates:
        return results
    
    # Load current MEMORY.md
    memory_content, sections = load_memory_md()
    
    # Group candidates by date for organized insertion
    candidates_by_date = {}
    for item in promotion_candidates:
        date_key = item['source_file'].replace('.md', '')
        if date_key not in candidates_by_date:
            candidates_by_date[date_key] = []
        candidates_by_date[date_key].append(item)
    
    # Build promotion content
    new_entries = []
    new_entries.append("\n## Recent Updates (Auto-Promoted)\n")
    
    for date_key in sorted(candidates_by_date.keys(), reverse=True):
        items = candidates_by_date[date_key]
        for item in items:
            entry = format_promotion_entry(item, date_key)
            new_entries.append(entry)
            results['promoted_items'].append({
                'date': date_key,
                'content': item['content'][:100] + "...",
                'confidence': item['confidence']
            })
    
    new_entries.append(f"\n*Last auto-promotion: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    
    # Count actual promotion entries
    promotion_count = len([e for e in new_entries if e.startswith('- **')])
    
    # Insert into MEMORY.md
    if not dry_run and new_entries:
        insertion_point = find_insertion_point(memory_content)
        
        # Insert new content
        updated_content = (
            memory_content[:insertion_point] + 
            ''.join(new_entries) + 
            memory_content[insertion_point:]
        )
        
        # Write back to MEMORY.md
        memory_path = os.path.join(os.path.dirname(__file__), "..", "MEMORY.md")
        with open(memory_path, 'w') as f:
            f.write(updated_content)
        
        results['promotions_made'] = promotion_count
    else:
        # For dry run, still count what would be promoted
        results['promotions_made'] = promotion_count
    
    return results


def cleanup_old_promotions(memory_content: str, days_to_keep: int = 30) -> str:
    """
    Clean up old auto-promoted entries to prevent MEMORY.md bloat.
    
    Args:
        memory_content: Current MEMORY.md content  
        days_to_keep: Keep promotions newer than this many days
        
    Returns:
        Cleaned content
    """
    # Find auto-promoted section
    auto_section_match = re.search(
        r'## Recent Updates \(Auto-Promoted\)\n(.*?)(?=\n##|\Z)', 
        memory_content, 
        re.DOTALL
    )
    
    if not auto_section_match:
        return memory_content
    
    section_content = auto_section_match.group(1)
    cutoff_date = (date.today() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
    
    # Keep only recent entries
    lines = section_content.split('\n')
    kept_lines = []
    
    for line in lines:
        date_match = re.search(r'\*\*(\d{4}-\d{2}-\d{2})\*\*', line)
        if date_match:
            entry_date = date_match.group(1)
            if entry_date >= cutoff_date:
                kept_lines.append(line)
        else:
            kept_lines.append(line)  # Keep non-entry lines
    
    # Rebuild section
    new_section = '\n'.join(kept_lines)
    updated_content = memory_content[:auto_section_match.start(1)] + new_section + memory_content[auto_section_match.end(1):]
    
    return updated_content


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Automatically promote significant daily log entries to MEMORY.md")
    parser.add_argument("--days", type=int, default=3, help="Days to analyze (default: 3)")
    parser.add_argument("--confidence", type=float, default=0.7, help="Minimum confidence threshold (default: 0.7)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be promoted without making changes")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old auto-promoted entries")
    
    args = parser.parse_args()
    
    if args.cleanup:
        memory_content, _ = load_memory_md()
        cleaned_content = cleanup_old_promotions(memory_content)
        
        memory_path = os.path.join(os.path.dirname(__file__), "..", "MEMORY.md")
        with open(memory_path, 'w') as f:
            f.write(cleaned_content)
        
        print("✅ Cleaned up old auto-promoted entries")
        
    else:
        results = promote_to_memory(args.days, args.confidence, args.dry_run)
        
        print(f"Memory Promotion Results:")
        print(f"Analyzed last {results['analyzed_days']} days")
        print(f"Candidates found: {results['candidates_found']}")
        print(f"Promotions {'planned' if results['dry_run'] else 'made'}: {results['promotions_made']}")
        
        if results['promoted_items']:
            print(f"\n{'Planned promotions' if results['dry_run'] else 'Promoted items'}:")
            for item in results['promoted_items']:
                print(f"  {item['date']}: {item['content']} (conf: {item['confidence']:.2f})")
        
        if not results['dry_run'] and results['promotions_made'] > 0:
            print(f"\n✅ MEMORY.md updated with {results['promotions_made']} new entries")
            print("💡 Run vector_memory/venv/bin/python vector_memory/indexer.py to re-index")