import unittest

from config import Mention
from linkedin import LinkedInClient


class LinkedInFormattingTests(unittest.TestCase):
    def setUp(self):
        self.mentions = [
            Mention(
                "fetch",
                "Fetch.ai",
                "urn:li:organization:27233415",
                "https://www.linkedin.com/company/fetch-ai/",
            ),
            Mention(
                "lab",
                "Fetch.ai Innovation Lab",
                "urn:li:organization:103686899",
                "https://www.linkedin.com/company/fetch-ai-innovation-lab/",
            ),
            Mention(
                "sana",
                "Sana Wajid",
                "",
                "https://www.linkedin.com/in/sana-wajid-ab1b6169/",
            ),
        ]

    def test_missing_names_are_not_appended(self):
        result = LinkedInClient.add_mentions(
            "A post about agents. #AI",
            ["fetch", "lab", "sana"],
            self.mentions,
        )
        self.assertEqual(result, "A post about agents. #AI")
        self.assertNotIn("@Fetch.ai", result)
        self.assertNotIn("@Sana", result)

    def test_both_fetch_names_can_be_tagged(self):
        result = LinkedInClient.add_mentions(
            "Built with Fetch.ai Innovation Lab and Fetch.ai.",
            ["fetch", "lab", "sana"],
            self.mentions,
        )
        self.assertIn("@Fetch.ai Innovation Lab", result)
        self.assertIn("and @Fetch.ai.", result)
        self.assertNotIn("@Sana", result)
        self.assertNotIn("urn:li:", result)

    def test_inline_name_becomes_linkedin_mention(self):
        result = LinkedInClient.add_mentions(
            "People like Sana Wajid are helping students.",
            ["sana"],
            self.mentions,
        )
        self.assertIn("People like @Sana Wajid are helping students.", result)
        self.assertNotIn("https://", result)

    def test_selected_but_absent_person_is_not_forced(self):
        result = LinkedInClient.add_mentions(
            "Thanks for the workshop.",
            ["sana"],
            self.mentions,
        )
        self.assertEqual(result, "Thanks for the workshop.")

    def test_little_text_markup_never_reaches_linkedin(self):
        result = LinkedInClient.add_mentions(
            "Built with Fetch.ai and @[Fetch.ai](urn:li:organization:27233415).",
            ["fetch"],
            self.mentions,
        )
        self.assertEqual(result.count("@Fetch.ai"), 1)
        self.assertNotIn("urn:li:", result)
        self.assertNotIn("@[", result)

    def test_existing_at_sign_is_not_doubled(self):
        result = LinkedInClient.add_mentions(
            "Thanks @Sana Wajid for the session.",
            ["sana"],
            self.mentions,
        )
        self.assertIn("Thanks @Sana Wajid for the session.", result)
        self.assertNotIn("@@Sana", result)


if __name__ == "__main__":
    unittest.main()
