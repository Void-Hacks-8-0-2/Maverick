import os
from pathlib import Path

qa_dir = Path("docs/qa")
for sub in ["raw", "logs", "benchmarks", "screenshots"]:
    (qa_dir / sub).mkdir(parents=True, exist_ok=True)
print("QA directories created.")
