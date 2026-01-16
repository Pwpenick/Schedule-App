# main.py
from flask import Flask, jsonify, Response
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

app = Flask(__name__)

OBITS_URL = "https://www.shannonfuneralhome.com/obituaries/obituary-listings?page=1"

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route("/")
def home():
    return "<h1>Obituary API is Running</h1><p>Try <a href='/api/obits'>/api/obits</a> or <a href='/calendar.ics'>/calendar.ics</a></p>"


@app.route("/api/obits")
def get_obits():
    try:
        response = requests.get(OBITS_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        items = soup.select(".obit-item")  # UPDATE this selector to match the site's HTML
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

@app.route("/calendar.ics")
def generate_calendar():
    try:
        api_url = "https://schedule-app-q8rw.onrender.com/api/obits"  # use your actual Render API URL here
        response = requests.get(api_url)
        response.raise_for_status()
        obits = response.json()

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Obit Calendar Feed//EN"
        ]

        for obit in obits:
            name = obit.get("name", "")
            try:
                date = datetime.fromisoformat(obit.get("date"))
            except Exception:
                continue
            dt_start = date.strftime("%Y%m%dT%H%M%S")
            dt_end = (date + timedelta(hours=1)).strftime("%Y%m%dT%H%M%S")

            lines.extend([
                "BEGIN:VEVENT",
                f"SUMMARY:{name}",
                f"DTSTART;TZID=America/New_York:{dt_start}",
                f"DTEND;TZID=America/New_York:{dt_end}",
                f"DESCRIPTION:Service for {name}",
                "END:VEVENT"
            ])

        lines.append("END:VCALENDAR")

        ics_content = "\r\n".join(lines)
        return Response(ics_content, mimetype="text/calendar")

    except Exception as e:
        return Response(f"Error generating calendar: {e}", mimetype="text/plain")

def parse_date(date_str):
    for fmt in ["%B %d, %Y %I:%M %p", "%B %d, %Y"]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

def is_within_next_7_days(dt):
    now = datetime.now()
    week_later = now + timedelta(days=7)
    return now <= dt <= week_later

if __name__ == '__main__':
    app.run(debug=True)
