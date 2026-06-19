"""
Extracts error diagnosis entries from alphaJET Google-Sites HTML files
and generates local JSON data files.

Output: res/fd/aj5.json, res/fd/ajd.json, res/fd/ajd_epti.json
"""

import json
import os
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR  = os.path.join(BASE_DIR, "res", "fd")

HTML_SOURCES = [
    {
        "key":    "aj5",
        "label":  "AJ5",
        "path":   r"C:\Users\marvi\Desktop\123\Technische Hilfe - Fehler AJ5.html",
    },
    {
        "key":    "ajd",
        "label":  "AJD",
        "path":   r"C:\Users\marvi\Desktop\123\Technische Hilfe - Fehle Mondor.html",
    },
    {
        "key":    "ajd_epti",
        "label":  "AJ epti",
        "path":   r"C:\Users\marvi\Desktop\123\Technische Hilfe - Fehler AJ epti.html",
    },
]


def extract_entries(html_path):
    """Parse one HTML file and return list of error entries."""
    with open(html_path, encoding="utf-8", errors="replace") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    entries = []
    current_cat = ""

    for elem in soup.body.descendants:
        if not hasattr(elem, "name"):
            continue

        if elem.name == "h2":
            cat = elem.get_text(strip=True)
            if cat:
                current_cat = cat

        elif elem.name == "div" and "vhaaFf" in (elem.get("class") or []):
            h3 = elem.find("h3")
            if not h3:
                continue
            title = h3.get_text(strip=True)
            if not title:
                continue

            # Extract content without the h3 title by cloning the div
            import copy
            elem_clone = copy.copy(elem)
            for h in elem_clone.find_all("h3"):
                h.decompose()
            content_raw = elem_clone.get_text(" ", strip=True)

            # Clean up whitespace
            content = " ".join(content_raw.split())

            entries.append({
                "id":      len(entries) + 1,
                "cat":     current_cat,
                "title":   title,
                "content": content,
            })

    return entries


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    for src in HTML_SOURCES:
        path = src["path"]
        key  = src["key"]
        label = src["label"]

        if not os.path.exists(path):
            print(f"MISSING: {path}")
            continue

        print(f"Parsing [{label}] ...")
        entries = extract_entries(path)

        # Stats
        cats = {}
        for e in entries:
            cats[e["cat"]] = cats.get(e["cat"], 0) + 1
        print(f"  {len(entries)} entries, categories: {dict(sorted(cats.items()))}")

        out_path = os.path.join(OUT_DIR, f"{key}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"system": label, "entries": entries}, f, ensure_ascii=False, indent=2)
        print(f"  Saved: {out_path}")


if __name__ == "__main__":
    main()
