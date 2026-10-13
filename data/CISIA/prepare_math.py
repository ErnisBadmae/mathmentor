"""Render the 20 original math questions and package their official keys for import."""

import hashlib
import json
import re
from pathlib import Path

import pymupdf

root = Path(__file__).resolve().parent
source = root / "tolc-i-sinavi-ornek-sorulari.pdf"
doc = pymupdf.open(source)
key = json.loads((root / "extracted/answer-key.operator.json").read_text(encoding="utf-8"))["answers"]
out = root.parents[1] / "backend/data/cisia"
out.mkdir(parents=True, exist_ok=True)
questions = []
for page_index in range(2, 16):
    page = doc[page_index]
    starts = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"])
            match = re.match(r"^\s*(\d{1,2})\.\s*", text)
            if match and line["bbox"][0] < 100:
                starts.append((int(match.group(1)), line["bbox"][1]))
    starts.sort(key=lambda item: item[1])
    for index, (number, top) in enumerate(starts):
        bottom = starts[index + 1][1] - 12 if index + 1 < len(starts) else page.rect.height - 45
        clip = pymupdf.Rect(48, top - 8, page.rect.width - 48, bottom)
        filename = f"q{number:02d}.png"
        page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=clip).save(out / filename)
        questions.append({
            "number": number,
            "pdf_page": page_index + 1,
            "source_ref": f"cisia:english-tolc-i:sample-2021:q{number}",
            "expected_answer": key[str(number)],
            "asset": filename,
            "asset_sha256": hashlib.sha256((out / filename).read_bytes()).hexdigest(),
        })
if sorted(q["number"] for q in questions) != list(range(1, 21)):
    raise ValueError("Expected exactly 20 original mathematics questions")
(out / "math.json").write_text(json.dumps({
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "questions": sorted(questions, key=lambda item: item["number"]),
}, indent=2), encoding="utf-8")
print(f"Prepared {len(questions)} original question images with official keys in {out}")
