#!/usr/bin/env python3
"""Fix remaining lint errors"""
import re
from pathlib import Path


def fix_ambiguous_l(file_path):
    """Replace ambiguous variable 'l' with 'line' or 'length'"""
    content = file_path.read_text()
    original = content

    # Pattern 1: for line in lines
    content = re.sub(r'\bfor l in ', 'for line in ', content)
    content = re.sub(r'\bfor l, ', 'for item, ', content)

    # Pattern 2: if line.strip()
    content = re.sub(r'\bif l\.', 'if line.', content)

    # Pattern 3: len(line)
    content = re.sub(r'len\(l\)', 'len(line)', content)

    # Pattern 4: (length - avg)
    content = re.sub(r'\(length - ', '(length - ', content)
    content = re.sub(r' for line in lengths', ' for length in lengths', content)

    if content != original:
        file_path.write_text(content)
        return True
    return False

def remove_unused_vars(file_path):
    """Comment out unused variable assignments"""
    content = file_path.read_text()
    original = content

    # List of unused vars from ruff output
    unused = [
        'total_words', 'q_lower', 'lang', 'title', 'source_spec',
        'sent_count', 'word_count', 'info_issues', 'score', 'calc',
        'v1', 'recs_text', 'has_format_detail', 'event_names'
    ]

    for var in unused:
        # Comment out assignment
        pattern = f'^(\\s*)({var} = .+)$'
        content = re.sub(pattern, r'\1# \2  # noqa: F841', content, flags=re.MULTILINE)

    if content != original:
        file_path.write_text(content)
        return True
    return False

# Process Python files
py_files = list(Path('.').rglob('*.py'))
fixed_count = 0

for py_file in py_files:
    if 'venv' in str(py_file) or '.git' in str(py_file):
        continue

    changed = False
    changed |= fix_ambiguous_l(py_file)
    changed |= remove_unused_vars(py_file)

    if changed:
        fixed_count += 1
        print(f"Fixed: {py_file}")

print(f"\nTotal files fixed: {fixed_count}")
