# DevASC IP Address App

A menu-driven Python command-line tool that shows a computer's current **public IPv4 and IPv6 addresses**, with details about them, and gives network technicians quick IP tools in one place.

Built by team **NEVER GROW OLD** for DevNet Associate (DEVASC) Project Activity 3: Social Coding.

## Features

| # | Feature | Module | Owner |
|---|---------|--------|-------|
| 1 | Public IPv4 and IPv6 detection, with a clear message when the network has no IPv6 | `ip_info.py` | Jerome |
| 2 | Provider details: ISP, ASN, country, region, city, timezone (ipapi.co, falling back to ip-api.com) | `ip_info.py` | Jerome |
| 3 | Look up any IP address or domain name | `lookup.py` | John Patrick |
| 4 | Offline tools: classify an address and calculate a subnet | `subnet_tools.py` | Francis |
| 5 | Colour-formatted tables and export to JSON or CSV | `ui.py` | Elijah |

## APIs used

All free, no API key needed:

- [ipify](https://www.ipify.org/): `https://api.ipify.org` (IPv4), `https://api6.ipify.org` (IPv6)
- [ipapi.co](https://ipapi.co/): `https://ipapi.co/json/` and `https://ipapi.co/<ip>/json/`
- [ip-api.com](https://ip-api.com/): `http://ip-api.com/json/<ip>` (fallback; free tier is HTTP only and non-commercial)

## Setup and run

Requires Python 3.10 or newer.

```bash
git clone https://github.com/zaiddan27/devasc-ip-address-app.git
cd devasc-ip-address-app
pip install -r requirements.txt
python main.py
```

## Project structure

```
main.py           Menu that ties the features together
ip_info.py        Public IP detection and provider details (REST APIs)
lookup.py         Look up any IP address or domain name
subnet_tools.py   Offline IP classification and subnet calculator (ipaddress module)
ui.py             Tables, colours, JSON/CSV export
requirements.txt  Python packages
```

Each module starts as a stub: its functions are defined with docstrings and raise `NotImplementedError` until the owner implements them. The menu already runs and shows "not implemented yet" for unfinished features.

## How we work (GitHub workflow)

1. **Never commit straight to `main`.** `main` always holds working code.
2. Create your branch from the latest `main`:
   ```bash
   git checkout main
   git pull
   git checkout -b feature/<your-feature>
   ```
   Branches: `feature/ip-info` (Jerome), `feature/ui-output` (Elijah), `feature/subnet-tools` (Francis), `feature/lookup` (John Patrick), `docs/readme`.
3. Commit small changes with clear messages, then push: `git push -u origin feature/<your-feature>`.
4. Open a **pull request** into `main` describing what changed and how to test it.
5. At least **one other member reviews** and approves it. The Scrum leader merges it.
6. Merge conflict? Pull the latest `main` into your branch, fix the conflict, push again.

## Adding a new feature (for future teams)

1. Create a new module, e.g. `my_feature.py`, with functions that return plain dictionaries.
2. Display results with `ui.show_table()` so output stays consistent.
3. Add a menu entry in `main.py`.
4. Document it in this README and open a pull request.

## Backlog (Project Activity 4)

- Web or desktop version
- Show the IP's approximate location on a map
- Batch lookup from a file of IPs
- Reverse DNS, ping latency and traceroute
- Automated tests on GitHub Actions for every pull request

## Team

| Member | Role |
|--------|------|
| Jerome N. Ancheta | Facilitator / Scrum leader, IP detection and details |
| Elijah M. Dela Vega | Recorder, UI and output |
| Francis Iñigo B. Torres | Network tools |
| John Patrick SD. Naborte | Lookup feature, testing and documentation |
