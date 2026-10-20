"""Export operational statistics and consolidate observed lab test evidence."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .provision import single
from .scenarios import TESTS
from .verify import EXPECTED_HOSTS


def mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def summarize_samples(ping: list[dict], rtt: list[dict], snmp_in: list[dict]) -> dict:
    reachable = sum(float(row["value"]) >= 1 for row in ping)
    rtt_ms = [float(row["value"]) * 1000 for row in rtt if float(row["value"]) > 0]
    traffic = [float(row["value"]) for row in snmp_in]
    return {
        "icmp_samples": len(ping),
        "reachable_samples": reachable,
        "observed_reachable_percent": round(100 * reachable / len(ping), 2) if ping else None,
        "rtt_samples": len(rtt_ms),
        "mean_rtt_ms": mean(rtt_ms),
        "max_rtt_ms": round(max(rtt_ms), 2) if rtt_ms else None,
        "snmp_in_samples": len(traffic),
        "mean_snmp_in": mean(traffic),
        "max_snmp_in": round(max(traffic), 2) if traffic else None,
    }


def find_item(items: list[dict], key: str, prefix: bool = False) -> dict | None:
    for row in items:
        matches = row["key_"].startswith(key) if prefix else row["key_"] == key
        if matches:
            return row
    return None


def get_history(api, item: dict | None, since: int, until: int) -> list[dict]:
    if not item:
        return []
    rows = api.call("history.get", {"itemids": [item["itemid"]], "history": int(item["value_type"]),
                                    "time_from": since, "time_till": until,
                                    "output": ["clock", "value"], "sortfield": "clock",
                                    "sortorder": "DESC", "limit": 20000})
    return sorted(rows, key=lambda row: int(row["clock"]))


def operational_report(api, hours: int) -> tuple[dict, list[dict]]:
    if not 1 <= hours <= 168:
        raise ValueError("--hours must be between 1 and 168")
    until = int(datetime.now(timezone.utc).timestamp())
    since = until - hours * 3600
    host_ids = {}
    all_items = {}
    for name in EXPECTED_HOSTS:
        host = single(api, "host.get", "host", name, ["hostid", "host"])
        if not host:
            raise ValueError(f"Missing lab host: {name}; run provision first")
        host_ids[name] = host["hostid"]
        all_items[name] = api.call("item.get", {"hostids": host["hostid"],
                                                "output": ["itemid", "key_", "name", "value_type", "units"]})

    desired = {
        "A1-LAB-ENDPOINT": [("icmpping", False), ("icmppingloss", False), ("icmppingsec", False)],
        "lab-linux-agent": [("system.cpu.util", False), ("vm.memory.size[pavailable]", False),
                            ("vfs.fs.size[/,pused]", False)],
        "A1-LAB-SNMP": [("net.if.in[", True), ("net.if.out[", True)],
    }
    histories = {}
    csv_rows = []
    missing_items = []
    empty_series = []
    for name, keys in desired.items():
        histories[name] = {}
        for key, prefix in keys:
            item = find_item(all_items[name], key, prefix)
            series = get_history(api, item, since, until)
            if item is None:
                missing_items.append(f"{name}: {key}")
            elif not series:
                empty_series.append(f"{name}: {item['key_']}")
            histories[name][key] = {"item": item, "series": series}
            for sample in series:
                csv_rows.append({"host": name, "item_key": item["key_"],
                                 "timestamp_utc": datetime.fromtimestamp(int(sample["clock"]), timezone.utc).isoformat(),
                                 "value": sample["value"], "units": item.get("units", "")})

    def series(host: str, key: str) -> list[dict]:
        return histories[host][key]["series"]

    stats = summarize_samples(series("A1-LAB-ENDPOINT", "icmpping"),
                              series("A1-LAB-ENDPOINT", "icmppingsec"),
                              series("A1-LAB-SNMP", "net.if.in["))
    for label, key in (("cpu_percent", "system.cpu.util"),
                       ("ram_available_percent", "vm.memory.size[pavailable]"),
                       ("disk_used_percent", "vfs.fs.size[/,pused]")):
        values = [float(row["value"]) for row in series("lab-linux-agent", key)]
        stats[label] = {"samples": len(values), "mean": mean(values),
                        "max": round(max(values), 2) if values else None}
    snmp_item = histories["A1-LAB-SNMP"]["net.if.in["]["item"]
    stats["snmp_in_units"] = snmp_item.get("units", "") if snmp_item else ""

    problem_events = {}
    for name, host_id in host_ids.items():
        problem_events[name] = api.call("event.get", {
            "hostids": [host_id], "source": 0, "object": 0, "value": 1,
            "time_from": since, "time_till": until,
            "output": ["eventid", "clock", "name", "r_eventid"],
            "sortfield": ["clock", "eventid"], "sortorder": "DESC", "limit": 5000})

    report = {"generated_at_utc": datetime.fromtimestamp(until, timezone.utc).isoformat(),
              "window_start_utc": datetime.fromtimestamp(since, timezone.utc).isoformat(),
              "window_hours": hours, "scope": "Docker lab only",
              "complete": not missing_items and not empty_series,
              "missing_items": missing_items, "items_without_samples": empty_series,
              "statistics": stats,
              "problem_counts": {name: len(rows) for name, rows in problem_events.items()},
              "problem_events": problem_events, "exported_samples": len(csv_rows),
              "limitations": "Reachability is the ratio of available ICMP samples, not a continuous SLA uptime guarantee."}
    return report, csv_rows


def save_operational_report(report: dict, csv_rows: list[dict], project_dir: Path) -> tuple[Path, Path, Path]:
    output = project_dir / "output"
    output.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = output / f"operations-{stamp}"
    json_path, md_path, csv_path = stem.with_suffix(".json"), stem.with_suffix(".md"), stem.with_suffix(".csv")
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fields = ["host", "item_key", "timestamp_utc", "value", "units"]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(csv_rows)
    stats = report["statistics"]
    lines = ["# A1 Lab — báo cáo vận hành", "", f"Khoảng đo: {report['window_start_utc']} → {report['generated_at_utc']}",
             f"Dữ liệu: {'đủ các chỉ số bắt buộc' if report['complete'] else 'thiếu chỉ số hoặc mẫu đo'}",
             f"Mẫu xuất CSV: {report['exported_samples']}", "",
             "| Chỉ số | Giá trị |", "|---|---:|",
             f"| ICMP mẫu quan sát | {stats['icmp_samples']} |",
             f"| Tỷ lệ mẫu ICMP phản hồi | {stats['observed_reachable_percent']}% |",
             f"| RTT trung bình | {stats['mean_rtt_ms']} ms |",
             f"| SNMP interface in trung bình | {stats['mean_snmp_in']} {stats['snmp_in_units']} |"]
    lines += [f"| Sự cố {name} | {count} |" for name, count in report["problem_counts"].items()]
    lines += ["", report["limitations"], "Dữ liệu chỉ phản ánh Docker lab và cửa sổ đo này."]
    if not report["complete"]:
        lines += ["", f"Item thiếu: {', '.join(report['missing_items']) or 'không có'}",
                  f"Item chưa có mẫu: {', '.join(report['items_without_samples']) or 'không có'}"]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, csv_path


def summarize_case_runs(runs: list[tuple[str, dict]]) -> dict:
    latest = {}
    for filename, report in runs:
        for row in report.get("cases", []):
            code = row.get("id")
            if code not in TESTS:
                continue
            candidate = {**row, "source_file": filename}
            if code not in latest or row.get("executed_at_utc", "") >= latest[code].get("executed_at_utc", ""):
                latest[code] = candidate
    missing = [code for code in TESTS if code not in latest]
    fault_cases = [latest[code] for code in ("TC03", "TC06") if code in latest]
    notification = latest.get("TC09")
    return {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "Docker lab only", "pass": not missing and all(row["status"] == "PASS" for row in latest.values()),
            "cases": latest, "missing": missing,
            "detected_fault_trials": sum(row["status"] == "PASS" for row in fault_cases),
            "executed_fault_trials": len(fault_cases),
            "detection_rate_percent": round(100 * sum(row["status"] == "PASS" for row in fault_cases) / len(fault_cases), 2) if fault_cases else None,
            "notification_rate_percent": 100.0 if notification and notification["status"] == "PASS" else (0.0 if notification else None)}


def collect_case_runs(project_dir: Path) -> dict:
    runs = []
    for path in sorted((project_dir / "output").glob("test-run-*.json")):
        runs.append((path.name, json.loads(path.read_text(encoding="utf-8"))))
    return summarize_case_runs(runs)


def save_case_summary(report: dict, project_dir: Path) -> tuple[Path, Path]:
    output = project_dir / "output"
    output.mkdir(exist_ok=True)
    json_path, md_path = output / "test-summary.json", output / "test-summary.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# A1 Lab — tổng hợp TC01–TC12", "", f"Tạo lúc: {report['generated_at_utc']}",
             f"Kết luận: {'PASS' if report['pass'] else 'INCOMPLETE/FAIL'}", "",
             "| Mã | Trạng thái | Thời điểm UTC | Tệp bằng chứng |", "|---|---|---|---|"]
    for code in TESTS:
        row = report["cases"].get(code)
        lines.append(f"| {code} | {row['status'] if row else 'MISSING'} | {row.get('executed_at_utc', '') if row else ''} | {row['source_file'] if row else ''} |")
    lines += ["", f"Tỷ lệ phát hiện trên {report['executed_fault_trials']} lần gây lỗi đã chạy: {report['detection_rate_percent']}%.",
              f"Tỷ lệ thông báo trên lần thử TC09: {report['notification_rate_percent']}%.",
              "Các tỷ lệ chỉ áp dụng cho ca lab đã chạy, không phải chỉ số hạ tầng LIC."]
    outage = report["cases"].get("TC03")
    if outage:
        evidence = outage.get("evidence", {})
        lines += [f"T_det sự cố ICMP: {evidence.get('T_det_seconds')} giây.",
                  f"T_notify email: {evidence.get('T_notify_seconds')} giây."]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
