from engine.reports.discord_report import build_discord_report


def main():
    output, latest, text = build_discord_report()

    print(f"Discord report written to: {output}")
    print(f"Latest report written to:  {latest}")
    print("")
    print(text)


if __name__ == "__main__":
    main()