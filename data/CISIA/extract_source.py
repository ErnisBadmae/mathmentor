"""Preserve the supplied sample as PDF pages; text is a search aid, not math truth.

Run: uv run --no-project --with pymupdf python data/CISIA/extract_source.py
"""

import hashlib
import json
import re
from pathlib import Path

import pymupdf


root = Path(__file__).resolve().parent
source = root / "tolc-i-sinavi-ornek-sorulari.pdf"
out = root / "extracted"
out.mkdir(exist_ok=True)
doc = pymupdf.open(source)
pages = [page.get_text(sort=True) for page in doc]
(out / "source-text.txt").write_text(
    "\n\n".join(f"=== PDF PAGE {i + 1} ===\n{text}" for i, text in enumerate(pages)),
    encoding="utf-8",
)

# The supplied document has its official answer table on PDF pages 49 and 50.
answers = {}
for text in pages[48:50]:
    for number, letter in re.findall(r"(?m)^\s*(\d{1,2})\s+([A-E])\s*$", text):
        number = int(number)
        if number in answers:
            raise ValueError(f"Duplicate key: {number}")
        answers[number] = letter
if set(answers) != set(range(1, 51)):
    raise ValueError("Incomplete official key; stop before producing a task manifest")

questions = []
for index in range(2, 48):
    page = doc[index]
    numbers = [int(n) for n in re.findall(r"(?m)^\s*(\d{1,2})\.\s", pages[index])]
    # Keep vector pages intact: fractions, radicals, superscripts and diagrams
    # retain the original layout without relying on OCR or an LLM transcription.
    if numbers:
        filename = f"page-{index + 1:02d}.pdf"
        single = pymupdf.open()
        single.insert_pdf(doc, from_page=index, to_page=index)
        single.save(out / filename)
        single.close()
        for number in numbers:
            section = (
                "mathematics" if number <= 20 else "logic" if number <= 30
                else "science" if number <= 40 else "reading_comprehension"
            )
            questions.append({
                "source_ref": f"cisia:english-tolc-i:sample-2021:q{number}",
                "number": number,
                "section": section,
                "pdf_page": index + 1,
                "source_page_asset": filename,
                "context_pdf_pages": [35, 36, 37, 38] if 41 <= number <= 45
                else [43, 44, 45] if number >= 46 else [],
                "status": "source_extracted_not_approved",
            })
if sorted(q["number"] for q in questions) != list(range(1, 51)):
    raise ValueError("Question numbering is incomplete or duplicated")

manifest = {
    "source_file": source.name,
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "source_language": "en",
    "source_copyright_year": 2021,
    "page_count": len(doc),
    "text_warning": "Extracted text can corrupt math glyphs/layout; use original PDF pages.",
    "exam_warning": "Historical English TOLC-I sample; check current university requirements (CEnT-S).",
    "questions": sorted(questions, key=lambda q: q["number"]),
}
(out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
(out / "answer-key.operator.json").write_text(
    json.dumps({"source_pdf_pages": [49, 50], "answers": answers}, indent=2),
    encoding="utf-8",
)
math = pymupdf.open()
math.insert_pdf(doc, from_page=2, to_page=15)
math.save(out / "mathematics.student.pdf")
math.close()
print(f"Extracted {len(questions)} question references and {len(answers)} official keys.")
print(f"Student mathematics: {out / 'mathematics.student.pdf'} (20 questions, no key)")
