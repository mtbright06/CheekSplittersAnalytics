# kbo_schedule_test.py
import requests
from datetime import date

def main():
    today = date.today().isoformat()
    print("=" * 50)
    print(f"KBO DATA COLLECTOR TEST — {today}")
    print("=" * 50)

    print("\nStep 1: Get today's games")
    print("TODO: connect schedule source")

    print("\nStep 2: Get odds")
    print("TODO: connect odds source")

    print("\nStep 3: Get probable starters")
    print("TODO: connect starter source")

    print("\nStep 4: Print game card")
    print("""
Example output:

KIA vs Kiwoom
Odds: KIA -180 / Kiwoom +145
Starter: TBD vs TBD
Status: READY FOR MODEL
""")

if __name__ == "__main__":
    main()