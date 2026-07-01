#!/usr/bin/env python3
"""
Pipeline: Zhou Lulu 188-page OCR → extract Q&A → dedup → ingest
Strategy: Use Solution markers as anchors, extract pre-Solution text as question stem.
"""
import json
import re
import sqlite3

OCR_PATH = "output/ZhouLulu/ocr_meta.json"
DB_PATH = "backend/quantquiz.db"

CHAPTER_MAP = [
    (range(3, 29),    "Chapter 2: Brain Teasers"),
    (range(29, 33),   "Chapter 4: Probability Theory"),
    (range(33, 103),  "Chapter 3: Calculus and Linear Algebra"),
    (range(103, 135), "Chapter 5: Stochastic Processes"),
    (range(135, 168), "Chapter 6: Finance"),
    (range(168, 189), "Chapter 7: Algorithms and Numerical Methods"),
]

PAGE_HEADER_RE = re.compile(
    r'^(A Practical Guide|Brain Teasers|Calculus and Linear|Probability Theory|'
    r'Stochastic|Finance|Algorithm|Algonthm|Pracucal|Quantitative Finance|'
    r'Quanutative|Quantifative|Quanntative|Chapter \d|Stochaste|Stech)',
    re.IGNORECASE
)

CONTINUATION_RE = re.compile(
    r'^(If |The |Let |For |So |We |In |This |That |Using |Note |From |Since |When '
    r'|As |It |By |At |On |An |To |With |After |Before |Now |Thus |Hence |Therefore '
    r'|Since |Given |Consider |Suppose |Applying |Plugging |Solving |Clearly |However '
    r'|Moreover |Furthermore |Also |Besides |But |And |Or |While |Because |Although)',
    re.IGNORECASE
)


def get_chapter(pnum):
    for r, ch in CHAPTER_MAP:
        if pnum in r:
            return ch
    return None


def is_noise_line(line):
    s = line.strip()
    if not s:
        return True
    if PAGE_HEADER_RE.match(s):
        return True
    if re.match(r'^\d{1,3}$', s):
        return True
    # Mostly math/symbols
    if len(s) <= 3:
        return True
    # Lines with way too many special chars
    special = sum(1 for c in s if not c.isalnum() and c not in ' .,!?;:()-\'\"')
    if special > len(s) * 0.6:
        return True
    return False


def clean_block(text):
    lines = [l for l in text.split('\n') if not is_noise_line(l)]
    return '\n'.join(lines).strip()


def find_title_in_block(block):
    """Find the question title - typically a short capitalized phrase."""
    lines = [l.strip() for l in block.split('\n') if l.strip() and not is_noise_line(l)]

    # Try to find the last short non-continuation line (question title is usually near end of block)
    for line in reversed(lines):
        if (5 < len(line) <= 70 and
            re.match(r'^[A-Z]', line) and
            not CONTINUATION_RE.match(line) and
            not line.endswith('.') and
            not line.endswith(',') and
            not re.search(r'[=\\|∑∫≤≥→]', line) and
            '  ' not in line[:20]):  # Not indented code
            return line

    # Fallback: first short capitalized line
    for line in lines[:5]:
        if 5 < len(line) <= 70 and re.match(r'^[A-Z]', line):
            return line

    return lines[-1] if lines else None


def extract_stem_from_block(block, title):
    """Extract the question stem starting from the title."""
    if not title:
        lines = [l.strip() for l in block.split('\n') if l.strip() and not is_noise_line(l)]
        return '\n'.join(lines[-10:]).strip()

    # Find title in block and take everything from there
    title_pos = block.find(title)
    if title_pos >= 0:
        stem = block[title_pos:].strip()
    else:
        # Just use last part of block
        lines = [l.strip() for l in block.split('\n') if l.strip() and not is_noise_line(l)]
        # Find line closest to title
        best_i = 0
        for i, line in enumerate(lines):
            if title[:20] in line:
                best_i = i
                break
        stem = '\n'.join(lines[best_i:]).strip()

    # Clean up stem
    stem = re.sub(r'\n{3,}', '\n\n', stem)
    return stem[:2000]  # Cap at 2000 chars


def build_chapter_combined(pages, ch_range):
    """Build combined text and page break index for a chapter range."""
    combined = ''
    page_breaks = []
    for p in pages:
        pnum = p['page']
        if pnum in ch_range:
            page_breaks.append((len(combined), pnum))
            combined += p['text'] + '\n'
    return combined, page_breaks


def get_page_at(pos, page_breaks):
    pg = page_breaks[0][1] if page_breaks else 1
    for p, pnum in page_breaks:
        if pos >= p:
            pg = pnum
        else:
            break
    return pg


SOL_RE = re.compile(
    r'(?:^|\n)(Solution|Solu[ti]on|Solulion|Sohulion|Sohition)[\s\.\:]*',
    re.IGNORECASE
)


def extract_questions_from_chapter(combined, page_breaks, chapter_name):
    """Extract Q&A pairs from a chapter's combined text."""
    questions = []
    sol_matches = list(SOL_RE.finditer(combined))

    if not sol_matches:
        return []

    for idx, m in enumerate(sol_matches):
        sol_pos = m.start()

        # Solution text: from here to next solution (max 2500 chars)
        if idx + 1 < len(sol_matches):
            sol_end = min(sol_matches[idx+1].start(), sol_pos + 2500)
        else:
            sol_end = min(len(combined), sol_pos + 2500)

        solution_text = combined[sol_pos:sol_end].strip()

        # Question block: from end of previous solution to this solution
        if idx > 0:
            # Previous solution text goes about 1500 chars from previous marker
            prev_sol_pos = sol_matches[idx-1].start()
            block_start = min(prev_sol_pos + 1500, sol_pos - 5)
            block_start = max(0, block_start)
        else:
            block_start = max(0, sol_pos - 1500)

        question_block = combined[block_start:sol_pos]

        # Find the title
        title = find_title_in_block(question_block)

        # Build stem
        stem = extract_stem_from_block(question_block, title)
        stem = clean_block(stem)

        if not stem or len(stem) < 25:
            continue

        # Quality check: should contain question-like text
        has_q = '?' in stem or '?' in solution_text[:400]
        has_task = any(kw in stem.lower() for kw in [
            'find', 'calculate', 'compute', 'show', 'prove', 'design', 'write',
            'determine', 'explain', 'derive', 'what', 'how', 'when', 'which',
            'algorithm', 'program', 'code'
        ])

        if not has_q and not has_task:
            continue

        page_num = get_page_at(sol_pos, page_breaks)

        questions.append({
            'title': title or stem[:50],
            'stem': stem,
            'solution': solution_text,
            'chapter': chapter_name,
            'page': page_num,
        })

    return questions


def tokenize(text):
    return set(re.findall(r'\b[a-z]{3,}\b', text.lower()))


def overlap_ratio(s1, s2):
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / min(len(s1), len(s2))


def main():
    print("Loading OCR...")
    with open(OCR_PATH) as f:
        d = json.load(f)
    pages = d['pages']

    print("\nExtracting Q&A by chapter...")
    all_questions = []
    for ch_range, ch_name in CHAPTER_MAP:
        combined, page_breaks = build_chapter_combined(pages, ch_range)
        if not combined.strip():
            continue
        qs = extract_questions_from_chapter(combined, page_breaks, ch_name)
        print(f"  {ch_name}: {len(qs)} candidates")
        all_questions.extend(qs)

    print(f"\nTotal candidates: {len(all_questions)}")

    con = sqlite3.connect(DB_PATH)

    # Get or create source
    existing = con.execute(
        "SELECT id FROM sources WHERE book_title LIKE '%188p%'"
    ).fetchone()

    if existing:
        source_id = existing[0]
        print(f"Using existing source_id={source_id}")
        q_ids = [r[0] for r in con.execute(
            "SELECT id FROM questions WHERE source_id=?", (source_id,)
        ).fetchall()]
        if q_ids:
            con.execute(f"DELETE FROM solutions WHERE question_id IN ({','.join(str(i) for i in q_ids)})")
            con.execute("DELETE FROM questions WHERE source_id=?", (source_id,))
            print(f"  Cleared {len(q_ids)} existing for re-run")
    else:
        cur = con.execute("""
            INSERT INTO sources (book_title, author, edition, notes)
            VALUES ('A Practical Guide to Quant Finance Interviews (Zhou, 188p)',
                    'Xinfeng Zhou', '2nd/Extended',
                    '188-page lulu.com version, OCR from ZhouLulu scan')
        """)
        source_id = cur.lastrowid
        print(f"Created source_id={source_id}")

    # Load existing for dedup (source_id=5)
    print("\nLoading existing questions for dedup...")
    existing_tokens = []
    for _, stem in con.execute("SELECT id, stem_markdown FROM questions WHERE source_id=5"):
        existing_tokens.append(tokenize(stem or ""))
    print(f"  {len(existing_tokens)} existing questions")

    # Ingest
    ingested = 0
    skipped_dup = 0
    skipped_quality = 0
    chapter_counts = {}
    sample_qs = []
    batch_tokens = []

    for qa in all_questions:
        stem_toks = tokenize(qa['stem'])

        # Quality gate
        if len(qa['stem'].split()) < 8:
            skipped_quality += 1
            continue

        # Dedup vs source_id=5
        is_dup = any(overlap_ratio(stem_toks, et) > 0.62 for et in existing_tokens)
        if not is_dup:
            # Intra-batch dedup
            is_dup = any(overlap_ratio(stem_toks, bt) > 0.65 for bt in batch_tokens)

        if is_dup:
            skipped_dup += 1
            continue

        cur = con.execute("""
            INSERT INTO questions (stem_markdown, question_type, source_id, difficulty,
                                   book_chapter, book_page, status, ingested_at, updated_at)
            VALUES (?, 'short', ?, 3, ?, ?, 'published', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (qa['stem'], source_id, qa['chapter'], qa['page']))

        q_id = cur.lastrowid

        con.execute("""
            INSERT INTO solutions (question_id, content_markdown, source_id, version)
            VALUES (?, ?, ?, 1)
        """, (q_id, qa['solution'], source_id))

        batch_tokens.append(stem_toks)
        existing_tokens.append(stem_toks)  # Avoid re-ingesting same content
        ingested += 1
        ch = qa['chapter']
        chapter_counts[ch] = chapter_counts.get(ch, 0) + 1

        if len(sample_qs) < 10:
            sample_qs.append(qa)

    con.commit()
    con.close()

    print(f"\n{'='*55}")
    print("RESULTS")
    print('='*55)
    print(f"Source ID:          {source_id}")
    print(f"Candidates:         {len(all_questions)}")
    print(f"Ingested:           {ingested}")
    print(f"Skipped (dedup):    {skipped_dup}")
    print(f"Skipped (quality):  {skipped_quality}")
    print(f"\nBy chapter:")
    for ch, cnt in sorted(chapter_counts.items()):
        print(f"  {ch}: {cnt}")
    print(f"\nSample questions:")
    for qa in sample_qs:
        title_str = (qa['title'] or '')[:60]
        stem_str = qa['stem'][:120].replace('\n', ' ')
        print(f"  [p{qa['page']}] {title_str}")
        print(f"    {stem_str}...")
        print()


if __name__ == "__main__":
    main()
