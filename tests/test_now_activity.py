"""Tests for source-dated databrew NOW without network access."""
import datetime as dt
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("now_build", ROOT / "scripts" / "build_now_activity.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class NowBuildTests(unittest.TestCase):
    def test_existing_project_inventory_is_not_a_launch_event(self):
        projects = mod.parse_projects()
        self.assertGreaterEqual(len(projects), 26)
        self.assertTrue(any(p["name"] == "서울 아파트 신고가 트래커" for p in projects))
        self.assertTrue(any(p["name"] == "이재명 X 트래커" and p["paused"] for p in projects))

    def test_bok_preserves_source_day_and_wording(self):
        item = {"generated": "2026-11-20T16:50+09:00",
                "text": "BOK워치: 11월 인상확률 68.0%→68.0%\n- 시장 확률(11월 20일 종가): 68.0%."}
        with patch.object(mod, "read_url", return_value=item):
            result = mod.bok_update()
        self.assertEqual(result["day"], "2026-11-20")
        self.assertIn("68.0%", result["title"])
        self.assertNotIn("2026-11-21", result["title"])

    def test_fx_uses_reference_rate_not_1530_spot(self):
        item = {
            "base_date": "2026-11-20", "spot": 1355.2, "change": -2.3,
            "horizons": {"7": {"selected": "A", "models": {"A": {"pi80": [1330, 1370]}}}}
        }
        with patch.object(mod, "read_url", return_value=item):
            result = mod.fx_update()
        self.assertIn("1,355.20원", result["title"])
        self.assertIn("1,330.0~1,370.0원", result["text"])
        self.assertIn("매매기준율", result["source"])

    def test_apt_verification_disables_metric(self):
        item = {"negoIndex": {"asOf": "2026-11-20", "status": "HELD_VERIFICATION",
                              "currentNegoLevel": 4.45}}
        with patch.object(mod, "read_url", return_value=item):
            result = mod.apt_update()
        self.assertIn("검증 중", result["title"])
        self.assertNotIn("4.45", result["title"])

    def test_apt_numeric_index_when_published(self):
        item = {"negoIndex": {"asOf": "2026-11-20", "currentNegoLevel": 4.45,
                              "changes": {"1d": {"deltaPctPoint": -0.2}}}}
        with patch.object(mod, "read_url", return_value=item):
            result = mod.apt_update()
        self.assertIn("+4.45%", result["title"])
        self.assertIn("-0.20%p", result["text"])

    def test_records_are_contract_date_trailing_thirty(self):
        meta = {"snapshotDate": "2026-11-21", "asOf": "2026-11-21T10:31+09:00"}
        days = {"2026-11-21": {"records": 2}, "2026-11-20": {"records": 3},
                "2026-10-21": {"records": 500}}
        with patch.object(mod, "read_url", side_effect=[meta, days]):
            result = mod.records_update()
        self.assertIn("5건", result["title"])
        self.assertEqual(result["day"], "2026-11-21")
        self.assertIn("계약일", result["text"])


if __name__ == "__main__":
    unittest.main()
