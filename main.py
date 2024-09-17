import os
import requests
from icalendar import Calendar, Event
from flask import Flask, Response

app = Flask(__name__)


# Function to recursively search for .ics files in a directory, excluding .Radicale.cache
def find_ics_files(directory):
    ics_files = []
    for root, _, files in os.walk(directory):
        if ".Radicale.cache" in root:
            continue  # Skip .Radicale.cache directories
        for file in files:
            if file.endswith(".ics"):
                ics_files.append(os.path.join(root, file))
            elif file.endswith(".Radicale.props"):
                ics_files.extend(fetch_calendar_from_props(os.path.join(root, file)))
    return ics_files


# Function to fetch calendar URL from .Radicale.props and return list of .ics URLs
def fetch_calendar_from_props(props_file):
    urls = []
    try:
        with open(props_file, "r", encoding="utf-8") as f:
            props = f.read()
            if "CS:source" in props:
                import json

                data = json.loads(props)
                calendar_url = data.get("CS:source")
                if calendar_url:
                    urls.append(calendar_url)
    except Exception as e:
        print(f"Error reading {props_file}: {e}")
    return urls


# Function to fetch and parse .ics content from a URL
def fetch_ics_from_url(url):
    ics_content = []
    try:
        response = requests.get(url)
        response.raise_for_status()
        ics_content = response.content
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
    return ics_content


# Function to determine availability based on TRANSP field
def is_busy(transp):
    return transp == "OPAQUE"


# Function to combine .ics files into one and include only busy events
def combine_ics_files(ics_files):
    combined_cal = Calendar()
    combined_cal.add("prodid", "-//Free Busy Paul Maier//EN")
    combined_cal.add("version", "2.0")

    # Add default color to the calendar (using X- prefix for custom property)
    combined_cal.add("X-CALENDAR-COLOR", "#d20f44")

    seen_events = set()  # To track seen events and avoid duplicates

    for ics_file in ics_files:
        try:
            if isinstance(ics_file, str) and ics_file.startswith("http"):
                ics_content = fetch_ics_from_url(ics_file)
                gcal = Calendar.from_ical(ics_content)
            else:
                with open(ics_file, "r", encoding="utf-8", errors="ignore") as f:
                    gcal = Calendar.from_ical(f.read())

            for component in gcal.walk():
                if component.name == "VEVENT":
                    # Check TRANSP field to determine if the event should be included
                    transp = component.get("transp", "OPAQUE")
                    if is_busy(transp):
                        # Generate a unique key for the event based on start and end times
                        start = component.get("dtstart").to_ical()
                        end = component.get("dtend").to_ical()
                        event_key = (start, end)

                        if event_key not in seen_events:
                            seen_events.add(event_key)
                            # Create a new event with anonymized details
                            event = Event()

                            # Set availability as summary based on TRANSP
                            availability = "Busy"

                            event.add("summary", availability)
                            event.add("dtstart", component.get("dtstart"))
                            event.add("dtend", component.get("dtend"))

                            # Copy RRULE directly (for recurring events)
                            if component.get("rrule"):
                                event.add("rrule", component.get("rrule"))

                            # Copy EXDATE directly if present (handling exceptions for recurring events)
                            if component.get("exdate"):
                                event.add("exdate", component.get("exdate"))

                            combined_cal.add_component(event)
        except Exception as e:
            print(f"Error processing {ics_file}: {e}")

    return combined_cal


# Function to generate and serve an online .ics feed
@app.route("/")
def generate_ics():
    ics_directory = "./collections"  # Replace with your directory
    ics_files = find_ics_files(ics_directory)
    combined_cal = combine_ics_files(ics_files)

    response = Response(combined_cal.to_ical(), mimetype="text/calendar")
    response.headers["Content-Disposition"] = (
        "attachment; filename=combined_calendar.ics"
    )
    return response


# Run the Flask web server
if __name__ == "__main__":
    app.run(debug=True)
