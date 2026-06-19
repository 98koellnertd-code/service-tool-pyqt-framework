"""
Extracts spare parts from alphaJET PDF spare parts lists and generates JSON data files.
Output: res/aj5.json, res/ajx.json, res/ajd.json
"""

import re
import json
import os
import pdfplumber

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RES_DIR = os.path.join(BASE_DIR, "res", "et")

PDF_DIR = r"C:\Users\marvi\Desktop\123"

PDF_GROUPS = {
    "aj5": [
        ("ET-alphaJET_5 HS__Vers. 4.2.pdf",      "AJ5 HS"),
        ("ET-alphaJET_5 HS-M__Vers. 4.2.pdf",    "AJ5 HS-M"),
        ("ET-alphaJET_5 SP__Vers. 4.2.pdf",       "AJ5 SP"),
    ],
    "ajx": [
        ("ET-alphaJET_5 X, X-FP__Vers. 4.2.pdf", "AJ5 X/X-FP"),
    ],
    "ajd": [
        ("ET-alphaJET_evo_045_2024_01_15.pdf",        "AJD evo"),
        ("ET-alphaJET_into_045_2024_01_15.pdf",       "AJD into"),
        ("ET-alphaJET_mondo_ 04_2024_01_16.pdf",      "AJD mondo"),
        ("ET-alphaJET_tempo + pico_045_2024_01_15.pdf","AJD tempo/pico"),
    ],
}

ORDER_NO_RE = re.compile(r"^\d{4}\.\d{4}$")
POS_RE      = re.compile(r"^\d{1,3}[a-zA-Z]?$")
FOOTER_RE   = re.compile(r"(Ersatzteilliste|Spare Part List|Manual spare part|alphaJET.*Vers\.|Coding\s+Technical\s+Manual)", re.IGNORECASE)
SKIP_HEADER_WORDS = {
    "Pos.", "Bezeichnung", "Designation", "description",
    "Bestell-Nr.", "Order", "no.", "number", "order",
    "Ersatzteil", "Spare", "part", "/spare", "E",
    "Baugruppe", "Assembly", "assembly", "group", "/"
}


def is_footer(y, page_height):
    return y > page_height - 55


def extract_page_parts(page, source_label):
    """Extract spare part entries from one page."""
    h = page.height
    words = page.extract_words(keep_blank_chars=False, x_tolerance=3, y_tolerance=3)

    # Determine column split by looking at x-coordinate of "Baugruppe" header
    # Default: group column starts around x=460
    group_x_start = 440

    # Filter out footer and header words
    data_words = [
        w for w in words
        if not is_footer(w["top"], h)
        and w["top"] > h * 0.12         # skip very top (section header area)
        and w["text"] not in SKIP_HEADER_WORDS
        and not FOOTER_RE.search(w["text"])
    ]

    # Separate into desc-column words and group-column words
    desc_words  = [w for w in data_words if w["x0"] < group_x_start]
    group_words = [w for w in data_words if w["x0"] >= group_x_start]

    # Find position entries in desc_words
    pos_entries = sorted(
        [(w["top"], w["text"]) for w in desc_words if POS_RE.match(w["text"])],
        key=lambda x: x[0]
    )
    if not pos_entries:
        return []

    # Build y-range boundaries for each pos entry
    boundaries = [(pos_entries[i][0], pos_entries[i + 1][0] if i + 1 < len(pos_entries) else h * 0.9)
                  for i in range(len(pos_entries))]

    def words_in_range(wlist, y1, y2, margin=5):
        return sorted([w for w in wlist if y1 - margin < w["top"] < y2 + margin],
                      key=lambda w: (w["top"], w["x0"]))

    parts = []
    for i, (pos_y, pos_no) in enumerate(pos_entries):
        y_start, y_end = boundaries[i]

        d_words = words_in_range(desc_words, y_start, y_end)
        g_words = words_in_range(group_words, y_start, y_end)

        # Remove the pos number itself
        d_words = [w for w in d_words if not (POS_RE.match(w["text"]) and abs(w["top"] - pos_y) < 10)]

        # Extract order number
        order_no = ""
        name_words = []
        for w in d_words:
            if ORDER_NO_RE.match(w["text"]):
                if not order_no:
                    order_no = w["text"]
            else:
                name_words.append(w)

        if not order_no:
            continue  # Skip entries without order number

        # Build name: words above order-no y give us the names
        # Group by y to form text lines, then join
        name_lines = _group_into_lines(name_words)
        name = " ".join(name_lines).strip()

        # Assembly group: first line German, second English
        g_lines = _group_into_lines(g_words)
        g_lines = [l for l in g_lines if l not in SKIP_HEADER_WORDS]
        group_de = g_lines[0] if g_lines else ""
        group_en = g_lines[1] if len(g_lines) > 1 else ""

        parts.append({
            "pos":      pos_no,
            "order_no": order_no,
            "name":     name,
            "group_de": group_de,
            "group_en": group_en,
            "sources":  [source_label],
        })

    return parts


def _group_into_lines(words, y_tol=4):
    """Group words with similar y into lines, return list of line strings."""
    if not words:
        return []
    lines = []
    current_y = None
    current_line = []
    for w in sorted(words, key=lambda x: (round(x["top"] / y_tol), x["x0"])):
        if current_y is None or abs(w["top"] - current_y) > y_tol:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [w["text"]]
            current_y = w["top"]
        else:
            current_line.append(w["text"])
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def parse_pdf(pdf_path, source_label):
    """Extract spare parts from all pages of a PDF."""
    all_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[1:]:  # skip title page
            parts = extract_page_parts(page, source_label)
            all_parts.extend(parts)
    return all_parts


def merge_parts(parts_lists):
    """Merge parts from multiple PDFs, deduplicating by order_no."""
    merged = {}
    for parts in parts_lists:
        for part in parts:
            ono = part["order_no"]
            if ono not in merged:
                merged[ono] = dict(part)
            else:
                for src in part["sources"]:
                    if src not in merged[ono]["sources"]:
                        merged[ono]["sources"].append(src)
                # Prefer longer name (more complete)
                if len(part["name"]) > len(merged[ono]["name"]):
                    merged[ono]["name"] = part["name"]
                if part["group_de"] and not merged[ono]["group_de"]:
                    merged[ono]["group_de"] = part["group_de"]
                if part["group_en"] and not merged[ono]["group_en"]:
                    merged[ono]["group_en"] = part["group_en"]

    result = sorted(merged.values(), key=lambda p: p["order_no"])
    return result


def main():
    os.makedirs(RES_DIR, exist_ok=True)

    for group_key, file_list in PDF_GROUPS.items():
        print(f"\n=== Processing {group_key.upper()} ===")
        all_parts_lists = []

        for fname, label in file_list:
            pdf_path = os.path.join(PDF_DIR, fname)
            if not os.path.exists(pdf_path):
                print(f"  MISSING: {fname}")
                continue
            print(f"  Parsing [{label}]: {fname}")
            parts = parse_pdf(pdf_path, label)
            print(f"    Found {len(parts)} parts")
            all_parts_lists.append(parts)

        merged = merge_parts(all_parts_lists)
        print(f"  Total unique parts: {len(merged)}")

        out_path = os.path.join(RES_DIR, f"{group_key}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"parts": merged}, f, ensure_ascii=False, indent=2)
        print(f"  Saved: {out_path}")


if __name__ == "__main__":
    main()
