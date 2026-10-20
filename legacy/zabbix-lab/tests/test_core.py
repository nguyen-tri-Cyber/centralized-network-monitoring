import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from a1lab.api import ZabbixAPI, ZabbixError
from a1lab.metrics import calculate_timings, detection_rate
from a1lab.provision import dashboard_definition, disk_item_definition, lab_map_definition, latency_trigger_definition, mail_action_definition
from a1lab.verify import evaluate_item
from a1lab.scenarios import newest_event_after, parse_mail_time, run_cases
from a1 import admin_password, is_local_zabbix
from a1lab.report import find_item, summarize_samples, summarize_case_runs


class ApiTests(unittest.TestCase):
    def test_api_error_never_includes_request_password(self):
        api = ZabbixAPI("http://127.0.0.1:8080")
        with self.assertRaises(ZabbixError) as caught:
            api.check_response({"error": {"message": "Login failed", "data": "Invalid credentials"}}, "user.login")
        self.assertIn("Login failed", str(caught.exception))
        self.assertNotIn("password", str(caught.exception).lower())

    def test_noninteractive_login_without_password_fails_fast(self):
        with tempfile.TemporaryDirectory() as directory, patch("a1.PROJECT_DIR", Path(directory)), \
                patch.dict(os.environ, {"A1_ADMIN_PASSWORD": ""}), patch("a1.sys.stdin.isatty", return_value=False):
            with self.assertRaisesRegex(ZabbixError, "A1_ADMIN_PASSWORD"):
                admin_password()


class MetricsTests(unittest.TestCase):
    def test_timings_use_actual_timestamps(self):
        result = calculate_timings(fault_at=100, event_at=150, mail_at=153)
        self.assertEqual(result, {"T_det_seconds": 50, "T_notify_seconds": 3})

    def test_missing_observation_is_not_zero(self):
        self.assertEqual(calculate_timings(fault_at=100, event_at=None, mail_at=None),
                         {"T_det_seconds": None, "T_notify_seconds": None})

    def test_detection_rate_requires_valid_cases(self):
        self.assertEqual(detection_rate(detected=2, valid=3), 66.67)
        self.assertIsNone(detection_rate(detected=0, valid=0))


class VerifyTests(unittest.TestCase):
    def test_recent_supported_item_passes(self):
        item = {"lastclock": "190", "lastvalue": "2.5", "state": "0", "status": "0"}
        self.assertEqual(evaluate_item(item, now=200, max_age=60)["status"], "PASS")

    def test_missing_or_stale_item_is_not_pass(self):
        self.assertEqual(evaluate_item(None, now=200, max_age=60)["status"], "FAIL")
        self.assertEqual(evaluate_item({"lastclock": "100", "lastvalue": "1", "state": "0", "status": "0"},
                                       now=200, max_age=60)["status"], "FAIL")


class ScenarioTests(unittest.TestCase):
    def test_lab_error_is_saved_as_failed_case(self):
        with patch("a1lab.scenarios.quick_cases", side_effect=RuntimeError("lab unavailable")):
            report = run_cases(None, Path("."), "http://127.0.0.1:8080", "TC01")
        self.assertFalse(report["pass"])
        self.assertEqual([row["id"] for row in report["cases"]], ["TC01"])
        self.assertEqual(report["cases"][0]["status"], "FAIL")

    def test_missing_case_result_cannot_make_run_pass(self):
        with patch("a1lab.scenarios.quick_cases", return_value=[]):
            report = run_cases(None, Path("."), "http://127.0.0.1:8080", "TC01")
        self.assertFalse(report["pass"])
        self.assertEqual(report["cases"][0]["status"], "FAIL")

    def test_new_event_ignores_prior_event_even_at_same_second(self):
        events = [{"eventid": "8", "clock": "101"}, {"eventid": "7", "clock": "100"}]
        self.assertEqual(newest_event_after(events, {"7"}, 100)["eventid"], "8")

    def test_mail_time_uses_mailpit_timestamp(self):
        self.assertEqual(parse_mail_time("2026-10-10T09:00:00Z"), 1791622800)

    def test_cli_rejects_non_lab_api_target(self):
        self.assertTrue(is_local_zabbix("http://127.0.0.1:8080"))
        self.assertFalse(is_local_zabbix("http://192.168.1.10:8080"))
        self.assertFalse(is_local_zabbix("https://example.com"))


class ProvisionTests(unittest.TestCase):
    def test_disk_item_measures_container_root_filesystem(self):
        item = disk_item_definition("123", "456")
        self.assertEqual(item["key_"], "vfs.fs.size[/,pused]")
        self.assertEqual(item["hostid"], "123")
        self.assertEqual(item["interfaceid"], "456")
        self.assertEqual(item["units"], "%")

    def test_latency_trigger_requires_two_high_samples(self):
        trigger = latency_trigger_definition()
        self.assertIn("min(/A1-LAB-ENDPOINT/icmppingsec,#2)>0.2", trigger["expression"])

    def test_lab_map_has_three_explicit_host_elements(self):
        hosts = {"A1-LAB-ENDPOINT": "1", "lab-linux-agent": "2", "A1-LAB-SNMP": "3"}
        definition = lab_map_definition(hosts, {"Cloud_(48)": "10", "Server_(48)": "11", "Network_(48)": "12"}, ["7"])
        self.assertEqual(len(definition["selements"]), 3)
        self.assertEqual({row["elements"][0]["hostid"] for row in definition["selements"]}, {"1", "2", "3"})

    def test_dashboard_limits_problem_and_availability_to_lab(self):
        definition = dashboard_definition("42", {"ping": "100"}, ["7", "8"])
        self.assertEqual(definition["name"], "A1 Lab - Tong quan")
        self.assertEqual(definition["private"], 0)
        self.assertTrue(any(w["type"] == "problems" for w in definition["pages"][0]["widgets"]))
        self.assertTrue(any(f == {"type": 2, "name": "groupids.0", "value": "42"}
                            for w in definition["pages"][0]["widgets"] for f in w.get("fields", [])))

    def test_mail_action_is_scoped_and_has_recovery(self):
        action = mail_action_definition("42", "7", "9")
        self.assertEqual(action["filter"]["conditions"][0]["value"], "42")
        self.assertEqual(action["operations"][0]["opmessage"]["mediatypeid"], "9")
        self.assertTrue(action["recovery_operations"])


class ReportTests(unittest.TestCase):
    def test_find_item_matches_exact_or_interface_prefix(self):
        items = [{"key_": "net.if.in[eth0]"}, {"key_": "net.if.out[eth0]"}]
        self.assertEqual(find_item(items, "net.if.in[", True)["key_"], "net.if.in[eth0]")
        self.assertIsNone(find_item(items, "net.if.in["))

    def test_sample_statistics_use_observed_values_only(self):
        result = summarize_samples(
            [{"value": "1"}, {"value": "0"}, {"value": "1"}],
            [{"value": "0.1"}, {"value": "0.3"}],
            [{"value": "100"}, {"value": "300"}],
        )
        self.assertEqual(result["icmp_samples"], 3)
        self.assertEqual(result["observed_reachable_percent"], 66.67)
        self.assertEqual(result["mean_rtt_ms"], 200.0)
        self.assertEqual(result["mean_snmp_in"], 200.0)

    def test_no_samples_do_not_become_perfect_uptime(self):
        result = summarize_samples([], [], [])
        self.assertIsNone(result["observed_reachable_percent"])
        self.assertIsNone(result["mean_rtt_ms"])

    def test_case_summary_selects_latest_result_and_marks_missing(self):
        runs = [
            ("old.json", {"cases": [{"id": "TC03", "status": "FAIL", "executed_at_utc": "2026-01-01T00:00:00Z"}]}),
            ("new.json", {"cases": [{"id": "TC03", "status": "PASS", "executed_at_utc": "2026-01-02T00:00:00Z",
                                       "evidence": {"T_det_seconds": 120}}]}),
        ]
        result = summarize_case_runs(runs)
        self.assertEqual(result["cases"]["TC03"]["status"], "PASS")
        self.assertEqual(result["cases"]["TC03"]["source_file"], "new.json")
        self.assertIn("TC04", result["missing"])
        self.assertFalse(result["pass"])


if __name__ == "__main__":
    unittest.main()
