# Module interfaces

This is the contract between modules. Each owner can change *how* their module works, but not these names, arguments, return shapes or error types without agreeing with the team, because `main.py` and the other modules depend on them.

All results are plain `dict`s with **string keys in display order** (`ui.show_table` prints them top to bottom). Values are strings or numbers.

## ip_info.py (Jerome)

| Function | Returns | Errors |
|---|---|---|
| `get_public_ipv4()` | IPv4 string, or `None` if it can't be reached | never raises |
| `get_public_ipv6()` | IPv6 string, or `None` if the network has no IPv6 | never raises |
| `get_ip_details(ip=None)` | dict with keys, in order: `IP`, `ISP`, `ASN`, `Country`, `Country code`, `Region`, `City`, `Timezone`, `Source` | `ConnectionError` with a friendly message if every API fails |

- `ip=None` means "this computer's public IP".
- Tries ipapi.co first, then ip-api.com. `Source` names the API that answered (`"ipapi.co"` or `"ip-api.com"`).
- Missing fields are `"N/A"`, never absent.
- Every HTTP request uses `TIMEOUT = 5` seconds.

## lookup.py (John Patrick)

| Function | Returns | Errors |
|---|---|---|
| `resolve_target(target)` | IP address string | `ValueError` with a friendly message for empty, invalid or unresolvable input |
| `lookup(target)` | dict: `Query`, `IP`, then the `get_ip_details` keys (without repeating `IP`) | `ValueError` for bad input; `ConnectionError` if the APIs fail |

- Private, loopback and other non-public addresses are not sent to the APIs. `lookup` returns `Query`, `IP`, `Note` (e.g. `"Private address - no public provider details"`) instead.

## subnet_tools.py (Francis)

Offline only (Python's `ipaddress` module, no network).

| Function | Returns | Errors |
|---|---|---|
| `classify_address(address)` | dict: `Address`, `Version` (`"IPv4"`/`"IPv6"`), `Type`, plus for IPv6 `Expanded` | `ValueError` with a friendly message |
| `subnet_info(cidr)` | dict: `Network`, `Version`, `Prefix length`, `Netmask`, `Wildcard`, `Broadcast`, `First host`, `Last host`, `Usable hosts`, `Total addresses` | `ValueError` with a friendly message |

- `Type` is one of: `Loopback`, `Unspecified`, `Link-local`, `Multicast`, `Shared (CGNAT)`, `Private`, `Reserved`, `Public`.
  - `Private` means only RFC 1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) and IPv6 Unique Local fc00::/7.
  - `Shared (CGNAT)` is 100.64.0.0/10 (RFC 6598, carrier-grade NAT).
  - `Reserved` covers other special-purpose blocks: documentation (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24, 2001:db8::/32), benchmarking 198.18.0.0/15, 192.0.0.0/24, 240.0.0.0/4 and 255.255.255.255.
- Accepts host bits set (`192.168.10.5/26` -> network `192.168.10.0/26`).
- IPv6 has no broadcast: `Broadcast` is `"N/A (IPv6)"`. `/31` and `/32` (and IPv6 `/127`, `/128`) follow RFC 3021 (no network/broadcast subtraction).
- Example: `192.168.10.0/26` -> Netmask `255.255.255.192`, Wildcard `0.0.0.63`, Broadcast `192.168.10.63`, First host `192.168.10.1`, Last host `192.168.10.62`, Usable hosts `62`, Total addresses `64`.

## ui.py and main.py (Elijah)

| Function | Returns | Errors |
|---|---|---|
| `show_table(title, data)` | prints a coloured two-column table (Field / Value) with `rich`; falls back to plain text if `rich` is not installed | never raises |
| `export_json(data, path=None)` | path of the written file | `OSError` if it can't write |
| `export_csv(data, path=None)` | path of the written file (`Field,Value` header, one row per key) | `OSError` if it can't write |

- With `path=None`, files go to `exports/result_YYYYMMDD_HHMMSS.json` / `.csv` (folder created if missing).
- `main.py` keeps the menu numbers used in the presentation: 1 My public IP, 2 Look up an IP or domain, 3 Classify an IP address, 4 Subnet calculator, 5 Export last result, 0 Exit.
- `main.py` catches `ValueError` and `ConnectionError` and shows them as friendly messages; the menu never crashes.

## Tests

Each owner adds `tests/test_<module>.py` (pytest). Tests must not need the internet: mock HTTP calls with `unittest.mock`. Run all tests with:

```bash
pip install -r requirements-dev.txt
pytest
```
