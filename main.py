from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

app = Flask(__name__)

OBITS_URL = "https://www.shannonfuneralhome.com/obits"

@app.route("/api/obits")
def get_obits():
    try:
        response = requests.get(OBITS_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        items = soup.select(".obit-item")  # Update this selector
        services = []

        for item in items:
            name_el = item.select_one(".obit-name")
            date_el = item.select_one(".service-date")

            if not name_el or not date_el:
                continue

            name = name_el.get_text(strip=True)
            date_text = date_el.get_text(strip=True)
            parsed_date = parse_date(date_text)

            if parsed_date and is_within_next_7_days(parsed_date):
                services.append({
                    "name": name,
                    "date": parsed_date.isoformat()
                })

        return jsonify(services)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def parse_date(date_str):
    # Try multiple formats
    for fmt in ["%B %d, %Y %I:%M %p", "%B %d, %Y"]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    return None

def is_within_next_7_days(dt):
    now = datetime.now()
    week_later = now + timedelta(days=7)
    return now <= dt <= week_later

if __name__ == "__main__":
    app.run(debug=True)
