#!/usr/bin/env python3
"""
Daily memory maintenance script: Promote + Re-index

Combines auto-promotion of significant daily log entries with automatic
memory system re-indexing for seamless maintenance.

Designed to be run daily via cron or heartbeat checks.
"""

import os
import sys
import subprocess
from datetime import datetime

def run_promotion(days_back=2, min_confidence=0.8, dry_run=False):
    """Run the auto-promotion script with specified parameters."""
    script_dir = os.path.dirname(__file__)
    promote_script = os.path.join(script_dir, "auto_promote.py")
    
    cmd = [
        sys.executable, promote_script,
        "--days", str(days_back),
        "--confidence", str(min_confidence)
    ]
    
    if dry_run:
        cmd.append("--dry-run")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout, ""
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def run_indexer():
    """Re-index the memory system after promotions."""
    script_dir = os.path.dirname(__file__)
    indexer_script = os.path.join(script_dir, "indexer.py")
    venv_python = os.path.join(script_dir, "venv", "bin", "python")
    
    # Use venv python if available, fallback to system python
    python_cmd = venv_python if os.path.exists(venv_python) else sys.executable
    
    try:
        result = subprocess.run([python_cmd, indexer_script], 
                              capture_output=True, text=True, check=True)
        return True, result.stdout, ""
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def daily_maintenance(days_back=2, min_confidence=0.8, dry_run=False):
    """
    Run full daily memory maintenance: promotion + indexing.
    
    Args:
        days_back: Days to analyze for promotion
        min_confidence: Minimum confidence for promotion
        dry_run: If True, show what would be done without changes
        
    Returns:
        Dict with maintenance results
    """
    results = {
        'timestamp': datetime.now().isoformat(),
        'dry_run': dry_run,
        'promotion': {'success': False, 'output': '', 'error': ''},
        'indexing': {'success': False, 'output': '', 'error': ''},
        'summary': ''
    }
    
    print(f"🧠 Daily Memory Maintenance - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()
    
    # Step 1: Auto-promote significant entries
    print("📝 Step 1: Promoting significant daily log entries...")
    success, stdout, stderr = run_promotion(days_back, min_confidence, dry_run)
    
    results['promotion'] = {
        'success': success,
        'output': stdout,
        'error': stderr
    }
    
    if success:
        print("✅ Promotion completed")
        print(stdout)
    else:
        print("❌ Promotion failed")
        print(f"Error: {stderr}")
        return results
    
    # Step 2: Re-index memory system (only if not dry run)
    if not dry_run:
        print("\n🔍 Step 2: Re-indexing memory system...")
        success, stdout, stderr = run_indexer()
        
        results['indexing'] = {
            'success': success,
            'output': stdout,
            'error': stderr
        }
        
        if success:
            print("✅ Memory system re-indexed")
            # Parse indexing output for stats
            if "chunks" in stdout:
                chunk_match = stdout.split("chunks")[0].split()[-1] if "chunks" in stdout else "?"
                print(f"   {chunk_match} memory chunks indexed")
            if "nodes" in stdout:
                node_info = [line for line in stdout.split('\n') if 'nodes' in line and 'edges' in line]
                if node_info:
                    print(f"   {node_info[0].strip()}")
        else:
            print("❌ Re-indexing failed")
            print(f"Error: {stderr}")
    else:
        print("\n🔍 Step 2: Skipped (dry run mode)")
        results['indexing'] = {'success': True, 'output': 'Skipped in dry run', 'error': ''}
    
    # Summary
    if results['promotion']['success'] and results['indexing']['success']:
        results['summary'] = 'Daily memory maintenance completed successfully'
        print(f"\n✅ {results['summary']}")
    else:
        results['summary'] = 'Daily memory maintenance had errors'
        print(f"\n❌ {results['summary']}")
    
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Daily memory maintenance: promotion + re-indexing")
    parser.add_argument("--days", type=int, default=2, help="Days to analyze for promotion (default: 2)")
    parser.add_argument("--confidence", type=float, default=0.8, help="Minimum confidence threshold (default: 0.8)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    results = daily_maintenance(args.days, args.confidence, args.dry_run)
    
    # Exit with appropriate code
    if results['promotion']['success'] and results['indexing']['success']:
        sys.exit(0)
    else:
        sys.exit(1)