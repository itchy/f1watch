import argparse
import json
import shutil
from pathlib import Path

import requests
from bs4 import BeautifulSoup

CAR_NUMBER_OVERRIDES = {
    ("lando", "norris"): "4",
    ("max", "verstappen"): "3",
    ("lewis", "hamilton"): "44",
    ("charles", "leclerc"): "16",
    ("george", "russell"): "63",
    ("fernando", "alonso"): "14",
    ("sergio", "perez"): "11",
    ("carlos", "sainz"): "55",
    ("valtteri", "bottas"): "77",
    ("pierre", "gasly"): "10",
    ("lance", "stroll"): "18",
    ("kevin", "magnussen"): "20",
    ("yuki", "tsunoda"): "22",
    ("mick", "schumacher"): "47",
    ("nicholas", "latifi"): "6",
    ("sebastian", "vettel"): "5",
    ("zhou", "guanyu"): "24",
    ("alexander", "albon"): "23",
    ("logan", "sargent"): "2",
}


def get_car_number(first_name: str, last_name: str) -> str:
    key = (first_name.lower(), last_name.lower())
    if key in CAR_NUMBER_OVERRIDES:
        return CAR_NUMBER_OVERRIDES[key]

    url = f"https://www.formula1.com/en/drivers/{key[0]}-{key[1]}"
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        paragraphs = soup.find_all(
            "p",
            class_=(
                "typography-module_body-xs-semibold__Fyfwn "
                "typography-module_lg_body-s-compact-semibold__cpAmk"
            ),
        )
        if len(paragraphs) > 2:
            return paragraphs[2].text.strip()
    except requests.exceptions.RequestException as e:
        print(f"Warning: could not fetch car number for {first_name} {last_name}: {e}")
    return "00"


def get_rows(year: int):
    if year < 2000:
        raise RuntimeError("Could not find driver standings data")
    url = f"https://www.formula1.com/en/results/{year}/drivers"
    response = requests.get(url, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    rows = soup.find_all("tr", class_="Table-module_body-row__shKd-")
    if len(rows) == 1:
        return get_rows(year - 1)
    return rows


def get_drivers(year: int):
    rows = get_rows(year)
    drivers = []
    for row in rows:
        try:
            cells = row.find_all("td")
            first_name = cells[1].find_all("span", class_="max-lg:hidden")[0].text
            last_name = cells[1].find_all("span", class_="max-md:hidden")[0].text
            drivers.append(
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "place": cells[0].text,
                    "points": cells[-1].text,
                    "car_number": get_car_number(first_name, last_name),
                }
            )
        except (IndexError, AttributeError) as e:
            print(f"Warning: skipping driver row due to parse error: {e}")
    return drivers


def main():
    parser = argparse.ArgumentParser(description="Scrape F1 driver standings")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{args.year}_drivers.json"
    backup_file = output_file.with_suffix(".json.bak")

    if output_file.exists():
        shutil.copy2(output_file, backup_file)
        print(f"Backed up {output_file} to {backup_file}")

    try:
        data = get_drivers(args.year)
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
