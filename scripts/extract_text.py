#!/usr/bin/env python3
"""Extract text from specific PDF pages."""
import sys
import pymupdf


def main():
    pdf_path = sys.argv[1]
    pages = [int(p) for p in sys.argv[2:]]
    doc = pymupdf.open(pdf_path)
    for p in pages:
        page = doc[p - 1]
        print(f"========== PAGE {p} ==========")
        print(page.get_text())
        print()


if __name__ == "__main__":
    main()
