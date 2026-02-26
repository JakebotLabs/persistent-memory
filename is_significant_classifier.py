#!/usr/bin/env python3
"""
is_significant() LLM classifier for automatic memory promotion pipeline.

Purpose: Classify daily interactions/events to determine if they should be promoted 
from daily logs to MEMORY.md for long-term retention.

Based on memory system research (memory/research_agent_memory_2026-02-16.md):
- Use low threshold (capture more, not less)
- Inspired by Mem0's automatic ADD/UPDATE/DELETE pattern
- CrewAI's contextual memory classification approach
"""

import os
import re
import sys
import json
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def is_significant(interaction: str, context: str = "") -> Tuple[bool, str, float]:
    """
    Classify if an interaction/event is significant enough for long-term memory.
    
    Args:
        interaction: The text to classify (conversation, event, decision, etc.)
        context: Optional additional context (previous messages, session info)
        
    Returns:
        Tuple of (is_significant: bool, reason: str, confidence: float)
    """
    
    # Significance criteria based on our memory research
    significant_indicators = [
        # Decisions & Architecture
        "decided", "chose", "selected", "architecture", "design", "approach",
        "strategy", "plan", "direction", "solution", 
        
        # State Changes & Progress  
        "completed", "finished", "deployed", "implemented", "fixed", "resolved",
        "updated", "changed", "modified", "installed", "configured",
        
        # Lessons & Insights
        "learned", "discovered", "found", "realized", "insight", "mistake", 
        "error", "problem", "issue", "bug", "failure", "works", "doesn't work",
        
        # Blockers & Dependencies
        "blocked", "waiting", "dependency", "requires", "needs", "missing",
        "broken", "unavailable", "credential", "access", 
        
        # Project Milestones
        "milestone", "release", "version", "complete", "ready", "shipped",
        "tested", "validated", "approved", "deployed",
        
        # Research & Analysis
        "research", "analysis", "findings", "conclusion", "recommendation",
        "comparison", "evaluation", "assessment", "study"
    ]
    
    # Non-significant patterns (routine chatter)
    routine_indicators = [
        "hello", "hi", "thanks", "okay", "sure", "sounds good",
        "got it", "understood", "yes", "no", "maybe", "hmm",
        "checking", "looking", "reviewing", "reading", "browsing"
    ]
    
    # Convert to lowercase for matching
    text_lower = interaction.lower()
    context_lower = context.lower()
    combined_text = f"{text_lower} {context_lower}"
    
    # Score calculation
    significant_count = sum(1 for indicator in significant_indicators 
                          if indicator in combined_text)
    routine_count = sum(1 for indicator in routine_indicators 
                       if indicator in combined_text)
    
    # Length-based significance (longer interactions more likely significant)
    length_score = min(len(interaction) / 200.0, 1.0)  # Cap at 1.0
    
    # Special high-significance patterns
    high_significance_patterns = [
        "error", "failure", "crash", "bug", "fix", "solve",
        "breakthrough", "discovery", "major", "critical", "important",
        "decision", "architecture", "design", "strategy", "direction"
    ]
    
    high_sig_count = sum(1 for pattern in high_significance_patterns 
                        if pattern in combined_text)
    
    # Calculate final score
    base_score = significant_count * 0.3 + length_score * 0.2 + high_sig_count * 0.5
    penalty = routine_count * 0.1
    final_score = max(0, base_score - penalty)
    
    # Decision threshold (intentionally low per research recommendations)
    threshold = 0.3
    is_sig = final_score >= threshold
    
    # Generate reason
    if is_sig:
        reasons = []
        if significant_count > 0:
            reasons.append(f"{significant_count} significance indicators")
        if high_sig_count > 0:
            reasons.append(f"{high_sig_count} high-priority patterns")
        if length_score > 0.5:
            reasons.append("substantial content")
        reason = f"SIGNIFICANT: {', '.join(reasons)} (score: {final_score:.2f})"
    else:
        reason = f"ROUTINE: Low significance score ({final_score:.2f}), likely routine interaction"
    
    return is_sig, reason, final_score


def classify_daily_log(file_path: str) -> List[Dict]:
    """
    Classify all entries in a daily log file.
    
    Args:
        file_path: Path to daily log markdown file
        
    Returns:
        List of classification results with metadata
    """
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Split on markdown headers (# or ##)
    sections = re.split(r'(^##?\s+.*$)', content, flags=re.MULTILINE)
    results = []
    
    # Pair headers with their body content
    parsed_sections = []
    intro = sections[0].strip()
    if intro:
        parsed_sections.append(intro)
    for i in range(1, len(sections), 2):
        body = sections[i + 1].strip() if i + 1 < len(sections) else ""
        if body:
            parsed_sections.append(body)
    
    for i, section in enumerate(parsed_sections):
        if len(section.strip()) < 50:  # Skip very short sections
            continue
            
        is_sig, reason, score = is_significant(section)
        
        results.append({
            'section_index': i,
            'content': section[:200] + "..." if len(section) > 200 else section,
            'is_significant': is_sig,
            'reason': reason,
            'confidence': score,
            'timestamp': datetime.now().isoformat()
        })
    
    return results


def analyze_recent_logs(days_back: int = 7) -> Dict:
    """
    Analyze recent daily logs for promotion candidates.
    
    Args:
        days_back: Number of days to analyze
        
    Returns:
        Analysis summary with promotion recommendations
    """
    memory_dir = os.path.join(os.path.dirname(__file__), "..", "memory")
    results = {
        'analyzed_files': [],
        'significant_items': [],
        'promotion_candidates': [],
        'summary': {}
    }
    
    if not os.path.exists(memory_dir):
        return results
    
    # Find daily log files
    from datetime import timedelta
    today = date.today()
    
    for i in range(days_back):
        target_date = today - timedelta(days=i)
        log_file = f"{target_date.strftime('%Y-%m-%d')}.md"
        log_path = os.path.join(memory_dir, log_file)
        
        if os.path.exists(log_path):
            file_results = classify_daily_log(log_path)
            results['analyzed_files'].append(log_file)
            
            # Collect significant items
            for item in file_results:
                if item['is_significant']:
                    item['source_file'] = log_file
                    results['significant_items'].append(item)
                    
                    # High-confidence items are promotion candidates
                    if item['confidence'] > 0.6:
                        results['promotion_candidates'].append(item)
    
    # Generate summary
    results['summary'] = {
        'files_analyzed': len(results['analyzed_files']),
        'total_significant': len(results['significant_items']),
        'high_confidence': len(results['promotion_candidates']),
        'promotion_rate': len(results['promotion_candidates']) / max(1, len(results['significant_items']))
    }
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Classify interactions for memory significance")
    parser.add_argument("--text", type=str, help="Text to classify")
    parser.add_argument("--file", type=str, help="Daily log file to classify")
    parser.add_argument("--analyze", action="store_true", help="Analyze recent logs")
    parser.add_argument("--days", type=int, default=7, help="Days to analyze (default: 7)")
    
    args = parser.parse_args()
    
    if args.text:
        is_sig, reason, score = is_significant(args.text)
        print(f"Text: {args.text[:100]}...")
        print(f"Result: {is_sig}")
        print(f"Reason: {reason}")
        print(f"Score: {score:.3f}")
        
    elif args.file:
        results = classify_daily_log(args.file)
        print(f"Analyzed {args.file}:")
        for result in results:
            print(f"  Section {result['section_index']}: {result['is_significant']} ({result['confidence']:.2f})")
            print(f"    {result['reason']}")
            print(f"    Content: {result['content'][:100]}...")
            print()
            
    elif args.analyze:
        results = analyze_recent_logs(args.days)
        print(f"Memory Promotion Analysis (last {args.days} days):")
        print(f"Files analyzed: {results['summary']['files_analyzed']}")
        print(f"Significant items: {results['summary']['total_significant']}")
        print(f"Promotion candidates: {results['summary']['high_confidence']}")
        print(f"Promotion rate: {results['summary']['promotion_rate']:.1%}")
        print()
        
        if results['promotion_candidates']:
            print("Top promotion candidates:")
            for candidate in results['promotion_candidates'][:5]:
                print(f"  {candidate['source_file']}: {candidate['reason']}")
                print(f"    {candidate['content'][:100]}...")
                print()
    
    else:
        print("Usage: python is_significant_classifier.py [--text TEXT] [--file FILE] [--analyze]")