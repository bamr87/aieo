#!/usr/bin/env python3
"""
Quick AIEO test - tests scoring engine directly without API
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.services.scoring_engine import ScoringEngine

def test_readme():
    """Test scoring the IT-Journey README"""
    print("=" * 60)
    print("  AIEO Test on IT-Journey README")
    print("=" * 60)
    print()
    
    readme_path = Path("/Users/bamr87/github/it-journey/README.md")
    if not readme_path.exists():
        print(f"✗ README not found: {readme_path}")
        return
    
    print(f"✓ Found README: {readme_path}")
    
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"Content length: {len(content)} characters")
    print("\nAnalyzing content with AIEO scoring engine...")
    
    try:
        engine = ScoringEngine()
        result = engine.score(content, format="markdown")
        
        print("\n" + "=" * 60)
        print("✓ ANALYSIS COMPLETE!")
        print("=" * 60)
        print(f"\nScore: {result.get('score', 0)}/100")
        print(f"Grade: {result.get('grade', 'F')}")
        print(f"Word count: {result.get('word_count', 0)}")
        
        gaps = result.get('gaps', [])
        if gaps:
            print(f"\nTop {min(10, len(gaps))} Gaps Found:")
            print("-" * 60)
            for i, gap in enumerate(gaps[:10], 1):
                print(f"\n{i}. Category: {gap.get('category', 'unknown')}")
                print(f"   Severity: {gap.get('severity', 'unknown')}")
                print(f"   Description: {gap.get('description', '')}")
                if gap.get('example_fix'):
                    print(f"   Fix: {gap.get('example_fix')}")
        else:
            print("\nNo gaps found!")
        
        # Show pattern scores
        pattern_scores = result.get('pattern_scores', {})
        if pattern_scores:
            print("\n" + "-" * 60)
            print("Pattern Scores:")
            print("-" * 60)
            for pattern, score_data in pattern_scores.items():
                score = score_data.get('score', 0)
                max_score = score_data.get('max', 0)
                detected = score_data.get('detected', False)
                status = "✓" if detected else "✗"
                print(f"{status} {pattern.replace('_', ' ').title():30s}: {score:5.1f}/{max_score}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_readme()
    print("\n" + "=" * 60)
    print("  Test Complete!")
    print("=" * 60)

