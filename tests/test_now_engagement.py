"""Static regression checks for per-NOW-entry commenting and sharing.

The hosted utterances app and OAuth-based posting require a real browser and
GitHub account, so only structure and security invariants are verified here.
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

    def test_comment_provider_lazy_loaded_per_stable_post_identity(self):
        self.assertIn("script.src='https://utteranc.es/client.js'", NOW)
        self.assertIn("script.setAttribute('repo','raspos/databrew')", NOW)
        self.assertIn("script.setAttribute('issue-term','databrew-now:'", NOW)
        self.assertIn("if(!slot.dataset.loaded)", NOW)
        self.assertIn("closeComments();", NOW)
        self.assertIn("window.matchMedia", NOW)
        self.assertIn("syncCommentTheme()", NOW)
        self.assertIn("https://github.com/raspos/databrew/issues", NOW)
        self.assertNotIn('<script src="https://utteranc.es/client.js"', NOW)

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
        self.assertIn("script.async=true", NOW)
        self.assertIn("GitHub 계정으로 댓글을 남길 수 있습니다.", NOW)
        self.assertIn("댓글은 GitHub Issues에 공개됩니다.", NOW)
        self.assertIn(".share-menu[hidden],.comment-panel[hidden]{display:none}", NOW)
        self.assertIn("comment-slot", NOW)
        self.assertNotIn("THREADS_ACCESS_TOKEN", NOW)
        self.assertNotIn("GITHUB_TOKEN", NOW)


if __name__ == "__main__":
    unittest.main()
