import os
import unittest
from unittest import mock

from agent import public_error
from config import DEFAULT_MENTION_KEYS, WEAK_AGENT_SEEDS, env_int


class ConfigHelperTests(unittest.TestCase):
    def test_default_mentions_exclude_people(self):
        self.assertEqual(DEFAULT_MENTION_KEYS, ["fetch", "lab"])
        self.assertNotIn("sana", DEFAULT_MENTION_KEYS)

    def test_weak_seeds_are_known(self):
        self.assertIn("replace-with-a-unique-private-seed", WEAK_AGENT_SEEDS)

    def test_env_int_tolerates_blank(self):
        with mock.patch.dict(os.environ, {"POST_HOUR": ""}, clear=False):
            self.assertEqual(env_int("POST_HOUR", 18), 18)

    def test_public_error_redacts_bearer_tokens(self):
        message = public_error(
            RuntimeError("LinkedIn failed Bearer abcdefghijklmnop")
        )
        self.assertIn("[redacted]", message)
        self.assertNotIn("abcdefghijklmnop", message)


if __name__ == "__main__":
    unittest.main()
