import os
import requests
from icalendar import Calendar, FreeBusy
from flask import Flask, Response
from dotenv import load_dotenv
from datetime import datetime, date, time, timedelta
import pytz


load_dotenv()


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
        return ics_content
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


# Function to combine .ics files into one and include only busy events
def combine_ics_files(ics_files):
    combined_cal = Calendar()
    combined_cal.add(
        "prodid", "-//free-busy_" + os.getenv("NAME").replace(" ", "_") + "//EN"
    )
    combined_cal.add("version", "2.0")

    for ics_file in ics_files:
        free_busy = FreeBusy()  # Create a FreeBusy object for each ics file
        now = datetime.now()
        free_busy.add("uid", "freebusy-" + os.path.basename(ics_file) + "-" + str(int(datetime.timestamp(now))))
        free_busy.add("dtstamp", now)
        free_busy.add('ATTENDEE', 'mailto:' + str(os.getenv("EMAIL")).lower())

        try:
            if isinstance(ics_file, str) and ics_file.startswith("http"):
                ics_content = fetch_ics_from_url(ics_file)
                gcal = Calendar.from_ical(ics_content)
            else:
                with open(ics_file, "r", encoding="utf-8", errors="ignore") as f:
                    gcal = Calendar.from_ical(f.read())

            has_entry = False

            for component in gcal.walk():
                if component.name == "VEVENT":
                    # Check TRANSP field to determine if the event should be included
                    transp = component.get("transp", "OPAQUE")
                    if transp == "OPAQUE":
                        # Generate a unique key for the busy time based on start and end times
                        start = ensure_datetime(component.get("dtstart").dt)
                        end = ensure_datetime(component.get("dtend").dt)

                        free_busy.add("FREEBUSY", (start, end))

                        has_entry = True

            if has_entry:
                # Add the grouped VFREEBUSY for this ics file to the combined calendar
                combined_cal.add_component(free_busy)

        except Exception as e:
            print(f"Error processing {ics_file}: {e}")

    return combined_cal

def ensure_datetime(dt):
    if isinstance(dt, date) and not isinstance(dt, datetime):
        # Convert datetime.date to datetime.datetime at midnight with no timezone info
        return datetime.combine(dt, time()).replace(tzinfo=pytz.UTC)
    elif isinstance(dt, datetime):
        if dt.tzinfo is None:
            # Add default timezone info if missing
            return dt.replace(tzinfo=pytz.UTC)
        return dt
    return None

def convert_to_datetime(dt):
    if isinstance(dt, datetime.date) and not isinstance(dt, datetime.datetime):
        # Convert datetime.date to datetime.datetime at midnight with no timezone info
        return datetime.combine(dt, datetime.min.time())
    return dt


# Function to generate and serve an online .ics feed
@app.route("/")
def serve_calendar():
    ics_directory = os.getenv("COLLECTIONS_DIR")
    ics_files = find_ics_files(ics_directory)
    combined_cal = combine_ics_files(ics_files)

    response = Response(combined_cal.to_ical(), mimetype="text/calendar")
    response.headers["Content-Disposition"] = (
        "attachment; filename=free-busy_" + os.getenv("NAME").replace(" ", "_") + ".ics"
    )
    return response


# Run the Flask web server
if __name__ == "__main__":
    app.run(debug=True)
