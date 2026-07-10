import argparse
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CARDS_DIR = ROOT / "output" / "cards"
REPORTS_DIR = ROOT / "output" / "reports"


STEPS = [
    ("Build KBO", ["python", "cheek_splitters_engine.py"], False),
    ("Build MLB", ["python", "tools_build_mlb_card.py"], True),
    ("Build First 5 Lab", [sys.executable, "tools_build_first5_card.py"],True,),
    ("Build Bomb Lab", ["python", "tools_build_bomb_lab.py"], True),
    ("Track Recommendations", ["python", "tools_track_recommendations.py"], False),
    ("Build Discord Report", ["python", "tools_build_discord_report.py"], False),
]


def run_step(name, command, required=True):
    print("")
    print("=" * 60)
    print(name)
    print("=" * 60)

    start = time.time()

    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
        )
    except Exception as ex:
        print(f"❌ {name} failed to start: {ex}")
        if required:
            raise SystemExit(1)
        return False

    elapsed = round(time.time() - start, 1)

    if result.returncode == 0:
        print(f"✅ {name} completed in {elapsed}s")
        return True

    print(f"⚠️ {name} exited with code {result.returncode} after {elapsed}s")

    if required:
        raise SystemExit(result.returncode)

    return False


def validate_outputs():
    print("")
    print("=" * 60)
    print("Validating Outputs")
    print("=" * 60)

    expected = [
        CARDS_DIR / "mlb_card.json",
        CARDS_DIR / "bomb_lab_card.json",
    ]

    all_good = True

    for path in expected:
        if path.exists() and path.stat().st_size > 0:
            print(f"✅ {path.relative_to(ROOT)}")
        else:
            print(f"❌ Missing or empty: {path.relative_to(ROOT)}")
            all_good = False

    latest_report = REPORTS_DIR / "discord_report_latest.md"

    if latest_report.exists() and latest_report.stat().st_size > 0:
        print(f"✅ {latest_report.relative_to(ROOT)}")
    else:
        print(f"⚠️ Missing Discord report: {latest_report.relative_to(ROOT)}")

    return all_good


def print_summary():
    print("")
    print("=" * 60)
    print("SharpStack Build Complete")
    print("=" * 60)

    report = REPORTS_DIR / "discord_report_latest.md"

    if report.exists():
        print("")
        print("Discord report:")
        print(report)

    print("")
    print("Next:")
    print("  python -m streamlit run dashboard/app.py")


def main():
    parser = argparse.ArgumentParser(description="SharpStack unified build runner.")
    parser.add_argument("--skip-pull", action="store_true", help="Skip git pull.")
    parser.add_argument("--launch", action="store_true", help="Launch Streamlit after build.")
    parser.add_argument("--no-kbo", action="store_true", help="Skip KBO build.")
    args = parser.parse_args()

    print("")
    print("==========================================")
    print("        SharpStack Unified Build")
    print("==========================================")

    if not args.skip_pull:
        run_step("Pull Latest Code", ["git", "pull"], required=False)

    for name, command, required in STEPS:
        if args.no_kbo and name == "Build KBO":
            print("")
            print("Skipping KBO build.")
            continue

        run_step(name, command, required=required)

    validate_outputs()
    print_summary()

    if args.launch:
        run_step(
            "Launching Dashboard",
            ["python", "-m", "streamlit", "run", "dashboard/app.py"],
            required=True,
        )


if __name__ == "__main__":
    main()
