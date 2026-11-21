"""Offline tests of the NOW -> Meta Threads publishing safety rails."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "threads_outbound", ROOT / "scripts" / "publish_now_threads.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
TODAY = dt.date(2026, 11, 21)


def activity(version="1"):
    watch_text = " ".join(
        "2026-11-21 서울 주택시장 공개 자료에서 비교 가능한 표본의 움직임을 기록"
        + str(i) + " 확인." for i in range(1, 12)
    )
    if version == "2":
        watch_text += " 새 관측치가 추가된 점도 확인."
    return {
        "watch": [{
            "id": "watch:apt:2026-11-21", "day": "2026-11-21",
            "title": "APT워치 | 호가와 실거래 괴리 변화", "text": watch_text,
            "url": "https://raspos.github.io/apt-watch/",
        }],
        "stories": [{
            "id": "story-1", "day": "2026-11-20", "title": "검증된 기사",
            "summary_lines": ["한 줄 요약이지만 원문에서 검증한 문장입니다."] * 5,
        }],
        "projects": [{
            "id": "legacy", "name": "기존 프로젝트", "story": "소개",
            "first_seen": None,
        }, {
            "id": "brand-new", "name": "신규 프로젝트", "story": "공식 자료를 정리하는 새 서비스.",
            "first_seen": "2026-11-21T11:00:00+09:00",
        }],
    }


class FakeClient:
    def __init__(self, fail_at=None):
        self.sent = []
        self.fail_at = fail_at

    def identity(self):
        return "owned-test-user-id"

    def publish_text(self, text, reply_to_id=None):
        if self.fail_at is not None and len(self.sent) == self.fail_at:
            raise RuntimeError("simulated Meta response uncertainty")
        self.sent.append((text, reply_to_id))
        return "mock-post-" + str(len(self.sent))


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / "activity.json"
        self.state = Path(self.temp.name) / "state.json"
        self.data.write_text(json.dumps(activity(), ensure_ascii=False), encoding="utf-8")

    def test_only_watch_stories_new_projects_eligible(self):
        found = mod.candidates(activity(), TODAY)
        self.assertEqual({p["kind"] for p in found}, {"watch", "stories", "projects"})
        self.assertEqual(len(found), 3)
        self.assertNotIn("legacy", [p["id"] for p in found])
        self.assertTrue(all("threads" != p["kind"] for p in found))

    def test_text_fidelity_and_500_character_limit(self):
        post = next(x for x in mod.candidates(activity(), TODAY) if x["kind"] == "watch")
        parts = mod.chunks_for(post)
        self.assertGreaterEqual(len(parts), 2)
        self.assertLessEqual(len(parts), 4)
        self.assertTrue(all(len(p) <= 500 for p in parts))
        self.assertIn("filter=watch", parts[0])
        self.assertIn("watch%3Aapt", parts[0])
        body = " ".join(x.split("\n\n", 1)[1].split("\n\nNOW 원문:", 1)[0].strip()
                        for x in parts[:1])
        self.assertIn("2026-11-21", body)
        self.assertIn("새 관측치", mod.chunks_for({
            **post, "text": post["text"] + " 새 관측치 확인."
        })[-1])

    def test_preview_has_no_side_effect(self):
        with patch.dict("os.environ", {"THREADS_ACCESS_TOKEN": "not-a-real-token",
                                       "THREADS_PUBLISH_ENABLED": "true"}):
            self.assertEqual(mod.run(self.data, self.state, today=TODAY, dry_run=True), 0)
        self.assertFalse(self.state.exists())

    def test_no_token_no_publication_or_checkpoint(self):
        with patch.dict("os.environ", {"THREADS_ACCESS_TOKEN": "",
                                       "THREADS_PUBLISH_ENABLED": "true"}):
            self.assertEqual(mod.run(self.data, self.state, today=TODAY), 0)
        self.assertFalse(self.state.exists())

    def test_first_live_run_checkpoints_without_posting_old_news(self):
        client = FakeClient()
        self.assertEqual(mod.run(self.data, self.state, client, TODAY), 0)
        self.assertEqual(client.sent, [])
        state = json.loads(self.state.read_text())
        self.assertTrue(state["initialized_at"])
        self.assertEqual(len(state["seen"]), 3)

    def test_new_snapshot_publishes_once_and_preserves_full_text(self):
        client = FakeClient()
        mod.run(self.data, self.state, client, TODAY)
        new = activity("2")
        self.data.write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(mod.run(self.data, self.state, client, TODAY), 0)
        self.assertGreaterEqual(len(client.sent), 2)
        self.assertIsNone(client.sent[0][1])
        self.assertEqual(client.sent[1][1], "mock-post-1")
        size = len(client.sent)
        self.assertEqual(mod.run(self.data, self.state, client, TODAY), 0)
        self.assertEqual(len(client.sent), size)
        state = json.loads(self.state.read_text())
        self.assertEqual(len(state["published"]), 1)

    def test_reply_failure_is_blocked_instead_of_duplicating_first_post(self):
        initial = FakeClient()
        mod.run(self.data, self.state, initial, TODAY)
        self.data.write_text(json.dumps(activity("2"), ensure_ascii=False), encoding="utf-8")
        unreliable = FakeClient(fail_at=1)
        with self.assertRaisesRegex(RuntimeError, "simulated Meta"):
            mod.run(self.data, self.state, unreliable, TODAY)
        saved = json.loads(self.state.read_text())
        self.assertEqual(len(saved["pending"]), 1)
        self.assertEqual(len(next(iter(saved["pending"].values()))["ids"]), 1)
        with self.assertRaisesRegex(RuntimeError, "audit"):
            mod.run(self.data, self.state, FakeClient(), TODAY)

    def test_manual_first_backfill_is_limited(self):
        client = FakeClient()
        self.assertEqual(mod.run(self.data, self.state, client, TODAY,
                                 backfill_latest=True, max_items=1), 0)
        state = json.loads(self.state.read_text())
        self.assertEqual(len(state["published"]), 1)
        self.assertEqual(len(state["seen"]), 3)
        self.assertTrue(client.sent)

    def test_stale_dates_and_legacy_entries_not_cross_posted(self):
        rows = activity()
        rows["watch"][0]["day"] = "2026-10-20"
        rows["stories"][0]["day"] = "2026-10-20"
        rows["projects"][1]["first_seen"] = None
        self.assertEqual(mod.candidates(rows, TODAY), [])


if __name__ == "__main__":
    unittest.main()
