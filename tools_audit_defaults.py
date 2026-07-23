from pathlib import Path
import re

ROOT = Path("engine")

patterns = [
    r"return\s+50\b",
    r"return\s+0\b",
    r"return\s+None\b",
    r"or\s+50\b",
    r"or\s+0\b",
    r"or\s+None\b",
    r"Unknown Starter",
    r"except\s+.*?:\s*$",
    r"pass\s*$",
]

print("=" * 72)
print("SharpStack Default Value Audit")
print("=" * 72)

hits = 0

for path in ROOT.rglob("*.py"):
    text = path.read_text(encoding="utf-8")

    lines = text.splitlines()

    for lineno, line in enumerate(lines, start=1):
        for pattern in patterns:
            if re.search(pattern, line):
                hits += 1
                print(f"\n{path}:{lineno}")
                print(f"    {line.strip()}")

print("\n" + "=" * 72)
print(f"Potential defaults found: {hits}")
print("=" * 72)