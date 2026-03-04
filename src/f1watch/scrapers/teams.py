import argparse
import json
import shutil
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def get_rows(year: int):
    if year < 2000:
        raise RuntimeError("Could not find team standings data")
    url = f"https://www.formula1.com/en/results/{year}/team"
    response = requests.get(url, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("tbody", class_="Table-module_tbody__KEiSx")
    if not table:
        raise RuntimeError("Could not locate teams table in Formula1.com response")

    rows = table.find_all("tr")
    if len(rows) == 1:
        return get_rows(year - 1)
    return rows


def get_teams(year: int):
    rows = get_rows(year)
    teams = []
    for row in rows:
        try:
            cells = row.find_all("td")
            teams.append(
                {
                    "team_name": cells[1].find("a").text,
                    "place": cells[0].text,
                    "points": cells[-1].text,
                }
            )
        except (IndexError, AttributeError) as e:
            print(f"Warning: skipping team row due to parse error: {e}")
    return teams


def main():
    parser = argparse.ArgumentParser(description="Scrape F1 team standings")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{args.year}_teams.json"
    backup_file = output_file.with_suffix(".json.bak")

    if output_file.exists():
        shutil.copy2(output_file, backup_file)
        print(f"Backed up {output_file} to {backup_file}")

    try:
        data = get_teams(args.year)
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
