from datetime import datetime


def print_banner(version, sport=None):

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 60)
    print("                 SHARPSTACK")
    print("        Cheek Splitters Decision Support System")
    print("              We split cheeks, not bankrolls")
    print("=" * 60)
    print(f"Version: {version}")
    print(f"Run Time: {now}")

    if sport:
        print(f"Sport: {sport}")

    print("=" * 60)
    print()