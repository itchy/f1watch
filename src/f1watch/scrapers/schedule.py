import argparse
import json
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


def practice_events(year: int):
    return [
        {"event": "Sakhir", "session": "Winter", "start": f"{year}-02-11T09:30:00-00:00"},
        {"event": "Sakhir", "session": "Winter", "start": f"{year}-02-11T13:00:00-00:00"},
        {"event": "Sakhir", "session": "Winter", "start": f"{year}-02-12T09:30:00-00:00"},
        {"event": "Sakhir", "session": "Winter", "start": f"{year}-02-12T13:00:00-00:00"},
        {"event": "Sakhir", "session": "Winter", "start": f"{year}-02-13T09:30:00-00:00"},
        {"event": "Sakhir", "session": "Winter", "start": f"{year}-02-13T13:00:00-00:00"},
        {"event": "Sakhir", "session": "Winter", "start": f"{year}-02-18T09:30:00-00:00"},
        {"event": "Sakhir", "session": "Winter", "start": f"{year}-02-18T13:00:00-00:00"},
        {"event": "Sakhir", "session": "Winter", "start": f"{year}-02-19T09:30:00-00:00"},
        {"event": "Sakhir", "session": "Winter", "start": f"{year}-02-19T13:00:00-00:00"},
        {"event": "Sakhir", "session": "Winter", "start": f"{year}-02-20T09:30:00-00:00"},
        {"event": "Sakhir", "session": "Winter", "start": f"{year}-02-20T13:00:00-00:00"},
    ]


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
    return details


def get_f1_schedule(year: int):
    events = []
    events.extend(practice_events(year))

    response = requests.get(f"https://www.formula1.com/en/racing/{year}", timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    rows = soup.find_all("a", class_="group")
    for row in rows:
        href = row.get("href")
        if not href:
            continue
        events.extend(get_f1_event_details(year, href))

    return sorted(events, key=lambda e: e["start"])


def main():
    parser = argparse.ArgumentParser(description="Scrape F1 session schedule")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{args.year}_schedule.json"

    data = get_f1_schedule(args.year)
    output_file.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    print(f"Wrote {output_file}")


if __name__ == "__main__":
    main()
