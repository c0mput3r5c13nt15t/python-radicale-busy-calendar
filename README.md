# Radicale Python Free/Busy Calendar

`gunicorn -c gunicorn_config.py main:app`

## How it works

- A liile bit hacky: readys the radicale collections
- Combines into a single calendar with "Busy" as attribute
- Serves the calendar

## Limitations

- Quick and dirty POC
- Not performant

## Caddy

- More secure behind reverse proxy

```json
{
    "match": [
        {
            "host": ["busy.paulmaier.online"]
        }
    ],
    "handle": [
        {
            "handler": "subroute",
            "routes": [
                {
                    "handle": [
                    {
                        "handler": "reverse_proxy",
                        "transport": {
                            "protocol": "http",
                            "tls": {
                                "insecure_skip_verify": true
                            }
                        },
                        "upstreams": [
                            {
                                "dial": "127.0.0.1:8080"
                            }
                        ]
                    }
                    ]
                }
            ]
        }
    ],
    "terminal": true
},
```
