# main.py — Updated Scraper for paginated /obituaries/obituary-listings
from flask import Flask, jsonify, Response
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

app = Flask(__name__)

BASE_URL = "https://www.shannonfuneralhome.com"
LISTING_URL = f"{BASE_URL}/obituaries/obituary-listings?page=1"

@app.route("/api/obits")
def get_obits():
    try:
        response = requests.get(LISTING_URL, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all obituary links on the listing page
        obit_links = []
        for a in soup.select("a[href^='/obituary/']"):
            href = a.get("href")
            if href and href.startswith("/obituary/") and href not in obit_links:
                obit_links.append(href)

        services = []

        for link in obit_links:
            full_url = BASE_URL + link
            try:
                svc = parse_obituary_page(full_url)
                if svc and is_within_next_7_days(svc["date"]):
                    services.append({
                        "name": svc["name"],
                        "date": svc["date"].isoformat(),
                        "link": full_url
                    })
            except Exception as e:
                print(f"Error parsing {full_url}: {e}")
                continue

        return jsonify(services)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def parse_obituary_page(url):
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract name (usually in <h1>)
    name_el = soup.find("h1")
    name = name_el.get_text(strip=True) if name_el else ""

    # Search full text for possible service datetime
    text = soup.get_text(" ", strip=True)
    dt = extract_date_time(text)

    if dt:
        return {"name": name, "date": dt}
    return None


def extract_date_time(text):
    # Regex: "January 20, 2026 11:00 AM" or similar
    date_pattern = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\\s+\\d{1,2},\\s+\\d{4}\\s+\\d{1,2}:\\d{2}\\s*(AM|PM|am|pm)")
    match = date_pattern.search(text)
    if match:
        try:
            return datetime.strptime(match.group(0), "%B %d, %Y %I:%M %p")
        except ValueError:
            return None
    return None


def is_within_next_7_days(dt):
    now = datetime.now()
    return now <= dt <= now + timedelta(days=7)


@app.route("/calendar.ics")
def generate_calendar():
    try:
        response = requests.get("https://schedule-app-q8rw.onrender.com/api/obits")
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
            except:
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
        return Response("\r\n".join(lines), mimetype="text/calendar")

    except Exception as e:
        return Response(f"Error generating calendar: {e}", mimetype="text/plain")


@app.route("/")
def home():
    return """
    <h2>Obit Feed is Running</h2>
    <ul>
        <li><a href='/api/obits'>JSON Feed</a></li>
        <li><a href='/calendar.ics'>Calendar Feed (.ics)</a></li>
    </ul>
    """

if __name__ == '__main__':
    app.run(debug=True)
