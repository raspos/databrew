"""Offline Cloudflare bootstrap tests; no account or network access required."""
import importlib.util
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "now_comments_bootstrap", ROOT / "comments-api" / "scripts" / "provision.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
DB_ID = "496bf648-18a2-46f2-890d-6ce6b603d921"


class ProvisionTests(unittest.TestCase):
    def test_reuse_existing_d1(self):
        with patch.object(module, "api", return_value={
            "result": [{"name": module.D1, "uuid": DB_ID}]
        }) as request:
            self.assertEqual(module.d1_database("a" * 32, "redacted"), DB_ID)
        self.assertEqual(request.call_count, 1)

    def test_create_d1_once_when_missing(self):
        responses = [
            {"result": []},
            {"result": {"name": module.D1, "uuid": DB_ID}},
        ]
        with patch.object(module, "api", side_effect=responses) as request:
            self.assertEqual(module.d1_database("b" * 32, "redacted"), DB_ID)
        self.assertEqual([c.args[0] for c in request.call_args_list], ["GET", "POST"])

    def test_create_turnstile_for_exact_static_host(self):
        responses = [
            {"result": [], "result_info": {"total_pages": 1}},
            {"result": {"sitekey": "public-sitekey", "secret": "private-secret"}},
        ]
        with patch.object(module, "api", side_effect=responses) as request:
            self.assertEqual(
                module.turnstile("a" * 32, "redacted"),
                ("public-sitekey", "private-secret"),
            )
        self.assertEqual(request.call_args_list[1].args[3]["domains"], ["raspos.github.io"])

    def test_reuse_turnstile_and_reject_unsafe_domain(self):
        safe = {"name": module.WIDGET_NAME, "sitekey": "public-sitekey",
                "domains": ["raspos.github.io"]}
        with patch.object(module, "api", side_effect=[
            {"result": [safe], "result_info": {"total_pages": 1}},
            {"result": {"sitekey": "public-sitekey", "secret": "private-secret"}},
        ]):
            self.assertEqual(module.turnstile("a" * 32, "redacted")[0], "public-sitekey")
        unsafe = {**safe, "domains": ["evil.example"]}
        with patch.object(module, "api", return_value={
            "result": [unsafe], "result_info": {"total_pages": 1}
        }):
            with self.assertRaisesRegex(RuntimeError, "unexpected"):
                module.turnstile("a" * 32, "redacted")

    def test_ephemeral_wrangler_config_never_contains_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "wrangler.deploy.toml"
            with patch.object(module, "TOML", path):
                module.config_file(DB_ID)
                contents = path.read_text()
        self.assertIn(DB_ID, contents)
        self.assertIn("ALLOWED_ORIGIN", contents)
        self.assertNotIn("ADMIN_TOKEN", contents)
        self.assertNotIn("TURNSTILE_SECRET", contents)
        self.assertNotIn("COMMENT_HASH_SALT", contents)

    def test_fail_closed_if_cloudflare_secrets_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "CLOUDFLARE_API_TOKEN"):
                module.main()


if __name__ == "__main__":
    unittest.main()
