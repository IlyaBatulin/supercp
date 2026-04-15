# Minimal Access Control Model

A Flask web application simulating a multi-layered authentication process for accessing cluster nodes (servers).

## Overview

The app demonstrates a secure login flow:
1. **Initial Authentication** — login, password, and access key
2. **Node Selection** — choose from compute/storage nodes (alpha, beta, gamma)
3. **Secondary Authentication** — node-specific password
4. **Statistics** — tracks access attempts; generates charts via matplotlib

## Tech Stack

- **Language:** Python 3.12
- **Web Framework:** Flask 3.x
- **Visualization:** Matplotlib
- **Environment:** python-dotenv
- **Production Server:** Gunicorn

## Project Structure

```
.
├── main.py          # Core logic: authentication, stats tracking, chart generation
├── web_app.py       # Flask web interface and routes
├── requirements.txt # Python dependencies
├── .env             # Environment variables (copied from .env.example)
├── templates/       # HTML templates (base, login, nodes)
└── charts/          # Generated charts directory
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

- `LAB_LOGIN` — login credential (default: `student`)
- `LAB_PASSWORD` — password (default: `lab123`)
- `SUPERCOMPUTER_ACCESS_KEY` — access key (default: `super-key-demo`)
- `NODE_PASSWORD_ALPHA/BETA/GAMMA` — per-node passwords
- `FLASK_SECRET_KEY` — session secret key

## Running

- **Development:** `python web_app.py` (port 5000)
- **Production:** `gunicorn --bind=0.0.0.0:5000 --reuse-port web_app:app`

## Deployment

Configured for Replit autoscale deployment using gunicorn.
