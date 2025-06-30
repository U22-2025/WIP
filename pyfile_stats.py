import os
import time
from typing import Dict, List

def count_file_stats(filepath: str) -> Dict[str, int]:
    """Count lines and characters in a single file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.readlines()
    
    line_count = len(content)
    char_count = sum(len(line) for line in content)
    
    return {
        'filepath': filepath,
        'lines': line_count,
        'chars': char_count
    }

def find_py_files(root_dir: str) -> List[str]:
    """Find all .py files recursively"""
    py_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                py_files.append(os.path.join(dirpath, filename))
    return py_files

def print_stats(stats: List[Dict[str, int]]) -> None:
    """Print statistics in a formatted way"""
    total_lines = sum(s['lines'] for s in stats)
    total_chars = sum(s['chars'] for s in stats)
    
    print(f"{'File Path':<50} {'Lines':>8} {'Chars':>10}")
    print("-" * 70)
    for stat in stats:
        print(f"{stat['filepath']:<50} {stat['lines']:>8} {stat['chars']:>10}")
    
    print("-" * 70)
    print(f"{'TOTAL':<50} {total_lines:>8} {total_chars:>10}")

def main():
    start_time = time.time()
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    py_files = find_py_files(root_dir)
    if not py_files:
        print("No .py files found in the directory tree.")
        return
    
    stats = [count_file_stats(f) for f in py_files]
    print_stats(stats)
    
    elapsed = time.time() - start_time
    print(f"\nAnalysis completed in {elapsed:.2f} seconds")

if __name__ == "__main__":
    main()