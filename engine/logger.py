from datetime import datetime
from pathlib import Path


class Logger:

    def __init__(self):

        Path("history").mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

        self.filename = f"history/{timestamp}.log"

        self.lines = []

    def write(self, text):

        print(text)

        self.lines.append(text)

    def save(self):

        with open(self.filename, "w", encoding="utf-8") as f:

            for line in self.lines:
                f.write(line + "\n")