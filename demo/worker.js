// IP_PAPI live demo worker.
// Loads Python (Pyodide) and the team's real modules from the GitHub repo,
// then runs one feature per message. Running here, off the page's thread,
// keeps the page responsive while the APIs answer.

importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js");

const OWNER_REPO = "zaiddan27/devasc-ip-address-app";
const MODULES = ["ip_info.py", "lookup.py", "subnet_tools.py"];

const HARNESS = `
import sys, json, types
import socket as _socket
sys.path.insert(0, "/home/pyodide")

import pyodide_http
pyodide_http.patch_all()          # lets the requests library work inside a browser
import requests

# In a browser a failed request (for example api6.ipify.org on a network
# without IPv6) surfaces as a JavaScript error. Turn it into the same
# requests.ConnectionError a PC would raise, so ip_info.py handles it the
# way it was written to.
_browser_get = requests.get
def _get(*args, **kwargs):
    try:
        return _browser_get(*args, **kwargs)
    except requests.RequestException:
        raise
    except Exception as exc:
        raise requests.ConnectionError(str(exc)) from exc
requests.get = _get

import ip_info, lookup, subnet_tools


def _doh_getaddrinfo(host, port=None, *args, **kwargs):
    """Browsers cannot use the computer's DNS resolver, so domain names are
    resolved through Google's DNS-over-HTTPS instead. Returns the same shape
    as socket.getaddrinfo(), which is all lookup.py reads."""
    found = []
    for rtype, code, family in (("A", 1, _socket.AF_INET), ("AAAA", 28, _socket.AF_INET6)):
        try:
            reply = requests.get("https://dns.google/resolve",
                                 params={"name": host, "type": rtype}, timeout=5).json()
        except Exception:
            continue
        for answer in reply.get("Answer", []):
            if answer.get("type") == code:
                found.append((family, 1, 6, "", (answer["data"], port or 0)))
    if not found:
        raise _socket.gaierror(f"getaddrinfo failed for {host!r}")
    return found


lookup.socket = types.SimpleNamespace(
    getaddrinfo=_doh_getaddrinfo,
    gaierror=_socket.gaierror,
    AF_INET=_socket.AF_INET,
    AF_INET6=_socket.AF_INET6,
)


def run_action(action, value=""):
    """Same bridge as gui.run_action() in the desktop app."""
    value = (value or "").strip()
    if action == "my_ip":
        ipv4 = ip_info.get_public_ipv4()
        ipv6 = ip_info.get_public_ipv6()
        try:
            details = ip_info.get_ip_details()
        except ConnectionError as exc:
            details = {"Note": f"Provider details unavailable - {exc}"}
        return "My public IP", {
            "IPv4": ipv4 or "not available",
            "IPv6": ipv6 or "not available on this network",
            **details,
        }
    if action == "lookup":
        return f"Lookup: {value}", lookup.lookup(value)
    if action == "classify":
        return f"Address: {value}", subnet_tools.classify_address(value)
    if action == "subnet":
        return f"Subnet: {value}", subnet_tools.subnet_info(value)
    raise ValueError(f"Unknown feature: {action}")


def run(action, value):
    try:
        title, data = run_action(action, value)
        return json.dumps({"ok": True, "title": title, "data": data}, default=str)
    except ValueError as exc:
        message = f"Invalid input: {exc}"
    except ConnectionError as exc:
        message = f"Network error: {exc}"
    except Exception as exc:
        message = f"Error: {exc}"
    return json.dumps({"ok": False, "message": message})
`;

let runner = null;

async function boot() {
  try {
    postMessage({ type: "progress", text: "Starting Python in your browser" });
    const py = await loadPyodide();

    postMessage({ type: "progress", text: "Loading the requests library" });
    await py.loadPackage(["requests", "pyodide-http"]);

    postMessage({ type: "progress", text: "Downloading the team's modules from GitHub" });
    let ref = "main";
    try {
      const head = await fetch(`https://api.github.com/repos/${OWNER_REPO}/commits/main`);
      if (head.ok) ref = (await head.json()).sha;
    } catch (_) { /* fall back to the branch name */ }

    for (const name of MODULES) {
      const res = await fetch(`https://raw.githubusercontent.com/${OWNER_REPO}/${ref}/${name}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`Could not download ${name} (HTTP ${res.status})`);
      py.FS.writeFile(`/home/pyodide/${name}`, await res.text());
    }

    py.runPython(HARNESS);
    runner = py.globals.get("run");
    postMessage({ type: "ready", ref, modules: MODULES });
  } catch (err) {
    postMessage({ type: "failed", text: String(err && err.message ? err.message : err) });
  }
}

onmessage = (event) => {
  const { id, action, value } = event.data;
  if (!runner) {
    postMessage({ type: "result", id, payload: { ok: false, message: "Python is still loading." } });
    return;
  }
  let payload;
  try {
    payload = JSON.parse(runner(action, value || ""));
  } catch (err) {
    payload = { ok: false, message: `Error: ${err}` };
  }
  postMessage({ type: "result", id, payload });
};

boot();
