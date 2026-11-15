"""Tests for ui.py - offline, no network calls.

Run with:  python -m pytest
"""

import csv
import json
import sys

import ui

SAMPLE = {"IP": "8.8.8.8", "ISP": "Google LLC", "Country": "US"}


# ---------------------------------------------------------------------------
# export_json / export_csv - explicit path
# ---------------------------------------------------------------------------


def test_export_json_writes_expected_content(tmp_path):
    target = tmp_path / "out.json"
    path = ui.export_json(SAMPLE, path=str(target))

    assert path == str(target)
    with open(target, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == SAMPLE


def test_export_csv_writes_expected_content(tmp_path):
    target = tmp_path / "out.csv"
    path = ui.export_csv(SAMPLE, path=str(target))

    assert path == str(target)
    with open(target, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    assert rows[0] == ["Field", "Value"]
    assert rows[1:] == [[key, value] for key, value in SAMPLE.items()]


# ---------------------------------------------------------------------------
# export_json / export_csv - default path, under exports/
# ---------------------------------------------------------------------------


def test_export_json_default_path_goes_under_exports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    path = ui.export_json(SAMPLE)

    # cwd is tmp_path, so the returned path is "exports/result_....json"
    # relative to it - resolve it against tmp_path to check the real file.
    assert (tmp_path / "exports").is_dir()
    assert path.replace("\\", "/").startswith("exports/")
    assert path.endswith(".json")
    with open(tmp_path / path, encoding="utf-8") as f:
        assert json.load(f) == SAMPLE


def test_export_csv_default_path_goes_under_exports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    path = ui.export_csv(SAMPLE)

    assert (tmp_path / "exports").is_dir()
    assert path.replace("\\", "/").startswith("exports/")
    assert path.endswith(".csv")
    with open(tmp_path / path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["Field", "Value"]


# ---------------------------------------------------------------------------
# show_table - must never raise, with or without rich
# ---------------------------------------------------------------------------


def test_show_table_normal_dict_does_not_raise(capsys):
    ui.show_table("My public IP", SAMPLE)

    captured = capsys.readouterr()
    assert "IP" in captured.out
    assert "8.8.8.8" in captured.out


def test_show_table_empty_dict_does_not_raise(capsys):
    ui.show_table("Nothing here", {})

    captured = capsys.readouterr()
    # Something was printed (title and/or "no data"), and no exception.
    assert captured.out.strip() != ""


def test_show_table_highlights_informational_values_without_raising(capsys):
    data = {"IPv4": "8.8.8.8", "IPv6": "N/A", "Note": "Private address"}

    ui.show_table("Mixed values", data)

    captured = capsys.readouterr()
    assert "N/A" in captured.out
    assert "Private address" in captured.out


def test_show_table_plain_fallback_when_rich_missing(monkeypatch, capsys):
    # Simulate "rich is not installed": any `import rich...` raises
    # ImportError, because Python treats a None entry in sys.modules as
    # "this import is blocked".
    monkeypatch.setitem(sys.modules, "rich", None)
    monkeypatch.setitem(sys.modules, "rich.console", None)
    monkeypatch.setitem(sys.modules, "rich.table", None)
    monkeypatch.setitem(sys.modules, "rich.panel", None)

    ui.show_table("Plain fallback", SAMPLE)

    captured = capsys.readouterr()
    assert "Plain fallback" in captured.out
    assert "IP" in captured.out
    assert "8.8.8.8" in captured.out


def test_show_message_and_show_header_do_not_raise_without_rich(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "rich", None)
    monkeypatch.setitem(sys.modules, "rich.console", None)
    monkeypatch.setitem(sys.modules, "rich.panel", None)

    ui.show_header()
    ui.show_message("hello", "success")

    captured = capsys.readouterr()
    assert "DevASC" in captured.out
    assert "hello" in captured.out
