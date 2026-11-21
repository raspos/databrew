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

    def test_bok_equal_weight_ois_and_msb91(self):
        meta = {"latest": "2026-11-20", "built": "2026-11-21T11:09+09:00",
                "upcoming": ["2026-11-26", "2027-01-14", "2027-02-25"]}
        snapshot = {
            "asof": "2026-11-20", "r0": 3.0,
            "inputs": [
                {"id": "msb91", "date": "2026-11-20", "rate": 3.198, "spread": -0.035},
                {"id": "cd91", "date": "2026-11-20", "rate": 3.39, "spread": 0.18},
                {"id": "ktb3y", "date": "2026-11-20", "rate": 3.642, "chg_bp": -7.4}
            ],
            "scenarios": {"0": {"meetings": [{
                "date": "2026-11-26", "p_hike": 0.6494,
                "p_hold": 0.3506, "expected": 3.1624,
                "source": "KOFR OIS(자체 산출)", "method": "kofr_ois",
                "ois_source": "1개월 OIS", "in_range": True,
                "cd91": {"p_hike": 0.8049}
            }]}}
        }
        reads = {
            mod.BASE["bok"] + "data/meta.json": meta,
            mod.BASE["bok"] + "data/snapshots/2026-11-20.json": snapshot
        }
        with patch.object(mod, "read_url", side_effect=lambda url: reads[url]):
            result = mod.bok_update()
        self.assertIn("81.3%", result["title"])
        self.assertIn("50:50", result["title"])
        self.assertIn("64.9%", result["text"])
        self.assertIn("97.6%", result["text"])
        self.assertNotIn("CD 91일 기준", result["text"])
        self.assertEqual(result["sentence_count"], 8)
        self.assertEqual(result["components"]["weights"], [0.5, 0.5])
        self.assertAlmostEqual(result["components"]["msb91"], 0.97576, places=4)

    def test_91day_cd_model_reproduces_official_calibration(self):
        prob, _ = mod._msb91_model("2026-11-20", 3.39, 0.18, 3.0,
                                   ["2026-11-26", "2027-01-14", "2027-02-25"])
        self.assertAlmostEqual(prob, 0.8049, places=4)

    def test_project_stories_are_concise_3_to_4_line_intros(self):
        projects = mod.parse_projects()
        self.assertEqual(len(projects), 26)
        for project in projects:
            with self.subTest(project=project["id"]):
                self.assertGreaterEqual(len(project["story"]), 90)
                self.assertLessEqual(len(project["story"]), 150)

    def test_fx_uses_reference_rate_not_1530_spot(self):
        item = {
            "base_date": "2026-11-20", "spot": 1355.2, "change": -2.3,
            "horizons": {"7": {"selected": "A", "models": {"A": {"pi80": [1330, 1370]}}},
                         "30": {"selected": "A", "models": {"A": {"pi80": [1300, 1400]}}}}
        }
        with patch.object(mod, "read_url", return_value=item):
            result = mod.fx_update()
        self.assertIn("1,355.20원", result["title"])
        self.assertIn("1,330.0~1,370.0원", result["text"])
        self.assertGreaterEqual(result["sentence_count"], 5)
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


    def test_story_summaries_and_watch_history_published(self):
        import json
        payload = json.loads((ROOT / "now" / "activity.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], 3)
        self.assertGreaterEqual(len(payload["stories"]), 4)
        story = next((s for s in payload["stories"] if s["id"] == "20261121-atls"), None)
        self.assertIsNotNone(story, "사회과부도 기사가 NOW에 반영되지 않음")
        self.assertEqual(len(story["summary_lines"]), 5)
        for item in payload["stories"]:
            self.assertTrue(4 <= len(item["summary_lines"]) <= 5)
        self.assertEqual({w["service"] for w in payload["watch"]},
                         {"bok", "fx", "apt", "records"})
        for post in payload["watch"]:
            self.assertGreaterEqual(post["sentence_count"], 5)
            self.assertGreaterEqual(len(post["text"].split(". ")), 5)
        self.assertIn("81.3%", next(p for p in payload["watch"] if p["service"] == "bok")["title"])

    def test_new_story_article_auto_extract(self):
        rows = mod._auto_story_lines({"url": "articles/20261119-t0xh/"})
        self.assertTrue(4 <= len(rows) <= 5)

if __name__ == "__main__":
    unittest.main()
