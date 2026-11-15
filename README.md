# DevASC IP Address App

A menu-driven Python command-line tool that shows a computer's current **public IPv4 and IPv6 addresses**, with details about them, and gives network technicians quick IP tools in one place.

Built by team **NEVER GROW OLD** for DevNet Associate (DEVASC) Project Activity 3: Social Coding.

## Features

| Menu # | Feature | Module | Owner |
|---|---------|--------|-------|
| 1 | My public IP: this computer's public IPv4 and IPv6 (with a clear message when the network has no IPv6), plus ISP/ASN/country/region/city/timezone | `ip_info.py` | Jerome |
| 2 | Look up an IP or domain: paste any IP address, domain name or URL and get the same provider details | `lookup.py` | John Patrick |
| 3 | Classify an IP address: Public / Private / Loopback / Link-local / Multicast / Reserved / Unspecified, offline | `subnet_tools.py` | Francis |
| 4 | Subnet calculator: network, netmask, wildcard, broadcast, usable host range from CIDR notation, offline | `subnet_tools.py` | Francis |
| 5 | Export the last result to JSON or CSV | `ui.py` | Elijah |

## APIs used

All free, no API key needed - and all have limits worth knowing about:

- [ipify](https://www.ipify.org/): `https://api.ipify.org` (IPv4), `https://api6.ipify.org` (IPv6). If the computer's network has no IPv6 connectivity, the app shows **"not available on this network"** instead of an error.
- [ipapi.co](https://ipapi.co/): `https://ipapi.co/json/` and `https://ipapi.co/<ip>/json/`. Tried first. Free tier is limited to **1,000 requests/day** per IP.
- [ip-api.com](https://ip-api.com/): `http://ip-api.com/json/<ip>`. Fallback used when ipapi.co fails or is rate-limited. Free tier is **HTTP only (no HTTPS) and non-commercial use only**.

Every lookup result includes a `Source` field so you can see which provider actually answered.

## Setup and run

Requires Python 3.10 or newer.

```bash
git clone https://github.com/zaiddan27/devasc-ip-address-app.git
cd devasc-ip-address-app

# optional: keep dependencies in a virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux

pip install -r requirements.txt
python main.py
```

## Using the menu

```
=== DevASC IP Address App ===
  1. My public IP
  2. Look up an IP or domain
  3. Classify an IP address
  4. Subnet calculator
  5. Export last result
  0. Exit
Choose an option:
```

### 1. My public IP

Shows this computer's own public address and provider details - no input needed.

```
Choose an option: 1

--- My public IP ---
IPv4             203.0.113.42
IPv6             not available on this network
IP               203.0.113.42
ISP              Example Broadband Co.
ASN              AS64500
Country          Philippines
Country code     PH
Region           Metro Manila
City             Manila
Timezone         Asia/Manila
Source           ipapi.co
```

### 2. Look up an IP or domain

Accepts a plain IP, a domain name, or a pasted URL (the scheme, path and port are stripped automatically). Example with Google's public DNS resolver:

```
Choose an option: 2
Enter an IP address or domain: 8.8.8.8

--- Lookup: 8.8.8.8 ---
Query            8.8.8.8
IP               8.8.8.8
ISP              Google LLC
ASN              AS15169
Country          United States
Country code     US
Region           California
City             Mountain View
Timezone         America/Los_Angeles
Source           ipapi.co
```

Private, loopback, link-local, reserved, multicast, unspecified and CGNAT (`100.64.0.0/10`) addresses are never sent to the lookup APIs - there's nothing public to report, so you get a note instead:

```
Enter an IP address or domain: 10.0.0.5

--- Lookup: 10.0.0.5 ---
Query            10.0.0.5
IP               10.0.0.5
Note             Private address - no public provider details
```

### 3. Classify an IP address

Offline - works without internet.

```
Choose an option: 3
Enter an IP address: 10.0.0.5

--- Address: 10.0.0.5 ---
Address          10.0.0.5
Version          IPv4
Type             Private
```

### 4. Subnet calculator

Offline. Accepts CIDR notation, including addresses with host bits set (e.g. `192.168.10.5/26` is treated as network `192.168.10.0/26`).

```
Choose an option: 4
Enter a network in CIDR notation (e.g. 192.168.10.0/26): 192.168.10.0/26

--- Subnet: 192.168.10.0/26 ---
Network          192.168.10.0
Version          IPv4
Prefix length    26
Netmask          255.255.255.192
Wildcard         0.0.0.63
Broadcast        192.168.10.63
First host       192.168.10.1
Last host        192.168.10.62
Usable hosts     62
Total addresses  64
```

### 5. Export last result

Exports whichever result (1-4) you looked at most recently.

```
Choose an option: 5
Format (json/csv): json
Saved to exports/result_20261115_143000.json
```

Exported files go to the `exports/` folder in the project root (created automatically on first export). Pass no path and the app names the file `result_<timestamp>.json` or `.csv` for you.

## Project structure

```
main.py           Menu that ties the features together
ip_info.py        Public IP detection and provider details (REST APIs)
lookup.py         Look up any IP address or domain name
subnet_tools.py   Offline IP classification and subnet calculator (ipaddress module)
ui.py             Tables, colours, JSON/CSV export
requirements.txt  Runtime packages (requests, rich)
requirements-dev.txt  Adds pytest, for running the test suite
docs/INTERFACES.md    The contract between modules - read this before changing one
tests/            pytest suite, one file per module, fully offline (mocked)
exports/          Created on first export; not committed to git
```

Each module's functions are documented in `docs/INTERFACES.md`, the binding contract the team agreed on so everyone could build their module in parallel without waiting on the others.

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

The whole suite runs offline: every module's tests mock its HTTP calls (or, for `lookup.py`, DNS resolution too) with `unittest.mock`, so `pytest` never needs internet access and never calls a real API.

### Continuous integration

A GitHub Actions workflow runs `pytest` automatically on every push and every pull request, so a broken test is caught before it reaches `main`.

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

1. Read [`docs/INTERFACES.md`](docs/INTERFACES.md) first - it's the contract the current modules depend on. Don't change an existing function's name, arguments, return shape or error type without the team agreeing, since `main.py` and other modules rely on them.
2. Create a new module, e.g. `my_feature.py`, with functions that return plain dictionaries (string keys, in the order you want them displayed).
3. Display results with `ui.show_table()` so output stays consistent, and add a corresponding entry to `docs/INTERFACES.md`.
4. Add a menu entry in `main.py`.
5. Add `tests/test_my_feature.py` that mocks any network calls.
6. Document it in this README and open a pull request.

## Backlog (Project Activity 4)

- Web or desktop version
- Show the IP's approximate location on a map
- Batch lookup from a file of IPs
- Reverse DNS, ping latency and traceroute

## Team

| Member | Role |
|--------|------|
| Jerome N. Ancheta | Facilitator / Scrum leader, IP detection and details |
| Elijah M. Dela Vega | Recorder, UI and output |
| Francis Iñigo B. Torres | Network tools |
| John Patrick SD. Naborte | Lookup feature, testing and documentation |
