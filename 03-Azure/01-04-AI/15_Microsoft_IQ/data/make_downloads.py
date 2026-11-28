"""Build the two download zips participants use in challenge 1. Run after changing data/documents or data/lakehouse:

    python data/make_downloads.py
"""
import zipfile
from pathlib import Path

DATA = Path(__file__).resolve().parent
OUT = DATA / "downloads"
SETS = {"strandvik-documents.zip": ("documents", "*.md"), "strandvik-lakehouse-csv.zip": ("lakehouse", "*.csv")}


def build() -> None:
    OUT.mkdir(exist_ok=True)
    for name, (folder, pattern) in SETS.items():
        files = sorted((DATA / folder).glob(pattern))
        with zipfile.ZipFile(OUT / name, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                # Fixed timestamp keeps the zip byte-identical between runs.
                info = zipfile.ZipInfo(f.name, date_time=(2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, f.read_bytes())
        print(f"{name}: {len(files)} files")


if __name__ == "__main__":
    build()
