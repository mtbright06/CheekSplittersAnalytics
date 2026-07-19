import argparse
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CARDS_DIR = ROOT / "output" / "cards"
REPORTS_DIR = ROOT / "output" / "reports"


STEPS = [
    ("Build KBO", [sys.executable, "cheek_splitters_engine.py"], False),
    ("Build MLB", [sys.executable, "tools_build_mlb_card.py"], True),
    ("Build First 5 Lab", [sys.executable, "tools_build_first5_card.py"], True),
    (
        "Build First 5 Market Edge",
        [sys.executable, "tools_build_first5_market_card.py"],
        False,
    ),
    ("Build Bomb Lab", [sys.executable, "tools_build_bomb_lab.py"], True),
    (
        "Track Recommendations",
        [sys.executable, "tools_track_recommendations.py"],
        False,
    ),
    (
        "Build Recommendation Explorer",
        [sys.executable, "tools_build_recommendation_explorer.py"],
        False,
    ),
    (
        "Build Discord Report",
        [sys.executable, "tools_build_discord_report.py"],
        False,
    ),
]


def run_step(
    name,
    command,
    required=True,
):
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
    except KeyboardInterrupt:
        print("")
        print(f"Stopped: {name}")
        return False
    except Exception as ex:
        print(
            f"❌ {name} failed to start: "
            f"{ex}"
        )

        if required:
            raise SystemExit(1)

        return False

    elapsed = round(
        time.time() - start,
        1,
    )

    if result.returncode == 0:
        print(
            f"✅ {name} completed "
            f"in {elapsed}s"
        )
        return True

    print(
        f"⚠️ {name} exited with code "
        f"{result.returncode} "
        f"after {elapsed}s"
    )

    if required:
        raise SystemExit(
            result.returncode
        )

    return False


def validate_file(
    path: Path,
    *,
    required: bool,
) -> bool:
    if (
        path.exists()
        and path.stat().st_size > 0
    ):
        print(
            f"✅ {path.relative_to(ROOT)}"
        )
        return True

    label = (
        "❌"
        if required
        else "⚠️"
    )

    print(
        f"{label} Missing or empty: "
        f"{path.relative_to(ROOT)}"
    )

    return not required


def validate_outputs():
    print("")
    print("=" * 60)
    print("Validating Outputs")
    print("=" * 60)

    required_outputs = [
        CARDS_DIR / "mlb_card.json",
        CARDS_DIR / "first5_card.json",
        CARDS_DIR / "bomb_lab_card.json",
        CARDS_DIR / "decision_card.json",
        CARDS_DIR / "play_of_day.json",
        (
            CARDS_DIR
            / "recommendation_registry.json"
        ),
    ]

    optional_outputs = [
        (
            CARDS_DIR
            / "first5_market_card.json"
        ),
        CARDS_DIR / "kbo_card.json",
    ]

    all_good = True

    for path in required_outputs:
        if not validate_file(
            path,
            required=True,
        ):
            all_good = False

    for path in optional_outputs:
        validate_file(
            path,
            required=False,
        )

    latest_report = (
        REPORTS_DIR
        / "discord_report_latest.md"
    )

    validate_file(
        latest_report,
        required=False,
    )

    return all_good


def print_summary(
    outputs_valid,
):
    print("")
    print("=" * 60)
    print("SharpStack Build Complete")
    print("=" * 60)

    if outputs_valid:
        print(
            "✅ Required outputs are present."
        )
    else:
        print(
            "⚠️ One or more required "
            "outputs are missing."
        )

    report = (
        REPORTS_DIR
        / "discord_report_latest.md"
    )

    if report.exists():
        print("")
        print("Discord report:")
        print(report)

    print("")
    print("Next:")
    print(
        f"  {sys.executable} "
        f"-m streamlit run "
        f"dashboard/app.py"
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "SharpStack unified build runner."
        )
    )

    parser.add_argument(
        "--skip-pull",
        action="store_true",
        help="Skip git pull.",
    )

    parser.add_argument(
        "--launch",
        action="store_true",
        help=(
            "Launch Streamlit after build."
        ),
    )

    parser.add_argument(
        "--no-kbo",
        action="store_true",
        help="Skip KBO build.",
    )

    parser.add_argument(
        "--no-market",
        action="store_true",
        help=(
            "Skip First 5 market "
            "edge build."
        ),
    )

    parser.add_argument(
        "--no-decision",
        action="store_true",
        help=(
            "Skip Decision Engine build."
        ),
    )

    parser.add_argument(
        "--no-registry",
        action="store_true",
        help=(
            "Skip Recommendation "
            "Registry build."
        ),
    )

    args = parser.parse_args()

    print("")
    print("==========================================")
    print("        SharpStack Unified Build")
    print("==========================================")
    print(f"Python: {sys.executable}")

    if not args.skip_pull:
        run_step(
            "Pull Latest Code",
            [
                "git",
                "pull",
            ],
            required=False,
        )

    for name, command, required in STEPS:
        if (
            args.no_kbo
            and name == "Build KBO"
        ):
            print("")
            print("Skipping KBO build.")
            continue

        if (
            args.no_market
            and name
            == "Build First 5 Market Edge"
        ):
            print("")
            print(
                "Skipping First 5 "
                "market edge build."
            )
            continue

        if (
            args.no_decision
            and name
            == "Build Decision Engine"
        ):
            print("")
            print(
                "Skipping Decision "
                "Engine build."
            )
            continue

        if (
            args.no_registry
            and name
            == "Build Recommendation Registry"
        ):
            print("")
            print(
                "Skipping Recommendation "
                "Registry build."
            )
            continue

        run_step(
            name,
            command,
            required=required,
        )

    outputs_valid = (
        validate_outputs()
    )

    print_summary(
        outputs_valid
    )

    if args.launch:
        print("")
        print(
            "Launching dashboard. "
            "Press Ctrl+C to stop."
        )

        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "dashboard/app.py",
                ],
                cwd=ROOT,
                check=False,
            )
        except KeyboardInterrupt:
            print("")
            print(
                "SharpStack dashboard "
                "stopped cleanly."
            )


if __name__ == "__main__":
    main()
