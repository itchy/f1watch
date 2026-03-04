import argparse
import json
import shutil
from pathlib import Path

import requests
from bs4 import BeautifulSoup


SESSION_ABR = {
    "Practice 1": "FP1",
    "Practice 2": "FP2",
    "Practice 3": "FP3",
    "Qualifying": "Q",
    "Sprint Qualifying": "SQ",
    "Sprint": "Sprint",
    "Race": "Grand Prix",
}

EVENT_NAME_MAP = {
    "Pre Season Testing 1": "Sakhir",
    "Pre Season Testing 2": "Sakhir",
    "Australia": "Melbourne",
    "China": "Shanghai",
    "Japan": "Suzuka",
    "Bahrain": "Bahrain",
    "Saudi Arabia": "Jeddah",
    "Emilia Romagna": "Imola",
    "Spain": "Barcelona",
    "Canada": "Montreal",
    "Austrian": "Red Bull",
    "British": "Silverstone",
    "Belgian": "Spa",
    "Hungarian": "Hungary",
    "Italy": "Monza",
    "United States": "Austin",
    "Sao Paulo": "Brazil",
    "S\u00e3o Paulo": "Brazil",
    "United Arab Emirates": "Abu Dhabi",
    "Barcelona Catalunya": "Barcelona Catalunya",
}

MONTH_TO_NUM = {
    "Jan": "01",
    "Feb": "02",
    "Mar": "03",
    "Apr": "04",
    "May": "05",
    "Jun": "06",
    "Jul": "07",
    "Aug": "08",
    "Sep": "09",
    "Oct": "10",
    "Nov": "11",
    "Dec": "12",
}


def session_abr(session_name: str) -> str:
    return SESSION_ABR.get(session_name, session_name)


def event_name(name: str) -> str:
    stripped = name.replace(" Grand Prix", "")
    return EVENT_NAME_MAP.get(stripped, stripped)


def get_f1_event_details(year: int, url: str):
    event = event_name(url.split("/")[-1].replace("-", " ").title())
    response = requests.get(f"https://www.formula1.com{url}", timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    ul = soup.find("ul")
    if not ul:
        return []

    details = []
    for row in ul.find_all("li"):
        try:
            spans = row.find_all("span")
            if len(spans) < 8:
                continue
            day = spans[1].text
            month = MONTH_TO_NUM.get(spans[2].text)
            if not month:
                continue
            start = spans[7].text.split(" - ")[0]
            details.append(
                {
                    "event": event,
                    "session": session_abr(spans[4].text),
                    "start": f"{year}-{month}-{day}T{start}:00-00:00",
                }
            )
        except (IndexError, AttributeError) as e:
            print(f"Warning: skipping session row due to parse error: {e}")
    return details


def get_f1_schedule(year: int):
    events = []

    response = requests.get(f"https://www.formula1.com/en/racing/{year}", timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    rows = soup.find_all("a", class_="group")
    for row in rows:
        href = row.get("href")
        if not href:
            continue
        try:
            events.extend(get_f1_event_details(year, href))
        except requests.exceptions.RequestException as e:
            print(f"Warning: skipping event {href} due to request error: {e}")

    return sorted(events, key=lambda e: e["start"])


def main():
    parser = argparse.ArgumentParser(description="Scrape F1 session schedule")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{args.year}_schedule.json"
    backup_file = output_file.with_suffix(".json.bak")

    if output_file.exists():
        shutil.copy2(output_file, backup_file)
        print(f"Backed up {output_file} to {backup_file}")

    try:
        data = get_f1_schedule(args.year)
        output_file.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
        print(f"Wrote {output_file}")
    except Exception as e:
        print(f"Error: {e}")
        if backup_file.exists():
            shutil.copy2(backup_file, output_file)
            print(f"Restored {output_file} from backup")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
