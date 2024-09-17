# Radicale Python Free/Busy Calendar

`gunicorn -c gunicorn_config.py main:app`

## How it works

- A liile bit hacky: readys the radicale collections
- Combines into a single calendar with "Busy" as attribute
- Serves the calendar

## Limitations

- Quick and dirty POC
- Not performant
