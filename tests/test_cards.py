import json
import unittest

from cards import create_post_form, draft_review
from content import Draft


def card_metadata(message):
    block = next(
        item for item in message.content if item.type == "metadata"
    )
    return block.metadata


class InteractiveCardTests(unittest.TestCase):
    def test_create_form_is_interactive(self):
        metadata = card_metadata(create_post_form())
        self.assertEqual(metadata["card_protocol_version"], "1")
        self.assertEqual(metadata["card_kind"], "form")
        payload = json.loads(metadata["card_payload"])
        field_names = {field["name"] for field in payload["fields"]}
        self.assertIn("topic", field_names)
        self.assertIn("tag_sana", field_names)

    def test_submit_cta_does_not_force_person_tag(self):
        payload = json.loads(card_metadata(create_post_form())["card_payload"])
        selection = payload["submit_cta"]["selection"]
        self.assertEqual(selection["action"], "create_draft")
        self.assertNotIn("tag_fetch", selection)
        self.assertNotIn("tag_lab", selection)
        self.assertNotIn("tag_sana", selection)
        sana = next(
            field for field in payload["fields"] if field["name"] == "tag_sana"
        )
        self.assertFalse(sana.get("value"))

    def test_review_requires_explicit_publish_action(self):
        draft = Draft(
            id="draft123",
            topic="Agentverse",
            post="A useful draft about Agentverse.",
            image_prompt="An abstract agent network",
            visual_headline="Agents that work together",
            tone="professional",
            audience="developers",
            objective="educate",
            mention_keys=["fetch"],
            source_url="",
            status="pending",
            created_at="2026-09-12T00:00:00+00:00",
        )
        metadata = card_metadata(draft_review(draft))
        payload = json.loads(metadata["card_payload"])
        serialized = json.dumps(payload)
        self.assertIn('"action": "publish"', serialized)
        self.assertIn('"action": "cancel"', serialized)
        self.assertIn('"action": "regenerate"', serialized)
        self.assertIn("Agents that work together", serialized)


if __name__ == "__main__":
    unittest.main()
