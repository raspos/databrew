"""Static regression checks for per-NOW-entry commenting and sharing.

The anonymous Cloudflare Worker requires account-owned deployment and Turnstile,
so frontend invariants are checked without claiming live write verification.
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
NOW = (ROOT / "now" / "index.html").read_text(encoding="utf-8")


class NowEngagementTests(unittest.TestCase):
    def test_every_entry_path_attaches_actions(self):
        self.assertIn("addInteractions(node,post);\n  return node;", NOW)  # inbound Threads
        self.assertIn("node.appendChild(foot);\naddInteractions(node,post);", NOW)
        self.assertIn("function addInteractions(node,post)", NOW)
        self.assertIn("function postLink(post)", NOW)
        self.assertIn("url.searchParams.set('filter',post.type)", NOW)
        self.assertIn("url.searchParams.set('item',String(post.id))", NOW)
        self.assertIn("var item=query.get('item')", NOW)
        self.assertIn("limit=Math.max(limit,position+1)", NOW)

    def test_comment_provider_is_guest_only_and_lazy_loaded(self):
        self.assertIn("fetch('comments-config.json'", NOW)
        self.assertIn("var guestSettings=", NOW)
        self.assertIn("var key=post.type+':'+String(post.id)", NOW)
        self.assertIn("async function refreshGuests()", NOW)
        self.assertIn("function renderGuests(rows)", NOW)
        self.assertIn("function loadTurnstile()", NOW)
        self.assertIn("https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit", NOW)
        self.assertIn("form.addEventListener('submit'", NOW)
        self.assertIn("turnstile_token:token", NOW)
        self.assertIn("post_key:key", NOW)
        self.assertIn("closeComments();", NOW)
        self.assertIn("syncCommentTheme()", NOW)
        self.assertNotIn("utteranc.es", NOW)
        self.assertNotIn("GitHub 계정으로 댓글", NOW)
        self.assertNotIn("GitHub Issues", NOW)

    def test_shares_are_explicit_and_reader_initiated(self):
        for url in (
            "https://www.threads.com/intent/post",
            "https://twitter.com/intent/tweet",
            "https://www.facebook.com/sharer/sharer.php",
        ):
            with self.subTest(url=url):
                self.assertIn(url, NOW)
        self.assertIn("navigator.clipboard.writeText(direct)", NOW)
        self.assertIn("navigator.share({title:heading,text:heading,url:direct})", NOW)
        self.assertIn("status.setAttribute('aria-live','polite')", NOW)
        self.assertIn("shareButton.setAttribute('aria-expanded','false')", NOW)
        self.assertIn("commentButton.setAttribute('aria-expanded','false')", NOW)
        self.assertIn("menu.hidden=false", NOW)
        self.assertIn("commentPane.hidden=false", NOW)
        self.assertIn("post.type==='threads'", NOW)
        self.assertIn("댓글 · Threads ↗", NOW)

    def test_security_and_display_settings(self):
        self.assertIn("rel='noopener noreferrer'", NOW)
        self.assertIn("js.async=true", NOW)
        self.assertIn("로그인 없이 닉네임으로 댓글", NOW)
        self.assertIn("관리자 승인 후 공개됩니다.", NOW)
        self.assertIn("aria-live", NOW)
        self.assertIn(".share-menu[hidden],.comment-panel[hidden]{display:none}", NOW)
        self.assertIn("comment-slot", NOW)
        self.assertNotIn("THREADS_ACCESS_TOKEN", NOW)
        self.assertNotIn("GITHUB_TOKEN", NOW)

    def test_guest_moderator_interface_uses_memory_only_authorization(self):
        moderator = (ROOT / "now" / "moderate" / "index.html").read_text(encoding="utf-8")
        self.assertIn("name=\"viewport\"", moderator)
        self.assertIn('content="noindex,nofollow,noarchive"', moderator)
        self.assertIn("now/moderate/", "now/moderate/")
        self.assertIn("Authorization", moderator)
        self.assertIn("Bearer ", moderator)
        self.assertIn("DATABREW_COMMENTS_ADMIN_TOKEN", moderator)
        self.assertIn("async function update(id,action)", moderator)
        self.assertIn("action('승인','approve')", moderator)
        self.assertIn("action('반려','reject')", moderator)
        self.assertIn("action('영구 삭제','delete')", moderator)
        self.assertNotIn("localStorage", moderator)
        self.assertNotIn("sessionStorage", moderator)
        self.assertNotIn("innerHTML", moderator)


if __name__ == "__main__":
    unittest.main()
