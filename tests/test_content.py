import unittest
from io import BytesIO

from PIL import Image

from content import ContentService, Draft
from visual import (
    POSTER_SIZE,
    compose_story_card,
    crop_model_marks,
    fallback_visual_copy,
    sanitize_generated_scene,
    validate_linkedin_image,
)


class VisualStoryTests(unittest.TestCase):
    def test_scene_prompt_uses_the_finished_post(self):
        prompt = ContentService.scene_prompt(
            "Autonomous agents can discover each other and complete a job.",
            "Agent discovery",
            "Two luminous agents meeting on a night skyline",
        )
        self.assertIn("discover each other", prompt)
        self.assertIn("Agent discovery", prompt)
        self.assertIn("cute rounded teal robot agent", prompt)
        self.assertIn("full-frame", prompt.lower())
        self.assertIn("high detail", prompt.lower())
        self.assertIn("zero text", prompt.lower())
        self.assertNotIn("gemini", prompt.lower())
        self.assertNotIn("google", prompt.lower())
        self.assertNotIn("imagen", prompt.lower())
        self.assertNotIn("lower fifth", prompt.lower())

    def test_scene_prompt_strips_other_ai_brands(self):
        prompt = ContentService.scene_prompt(
            "Students learn with agents.",
            "Student tools",
            "A Gemini sparkle logo beside a Google Imagen badge and Fetch.ai title",
        )
        self.assertNotIn("gemini", prompt.lower())
        self.assertNotIn("imagen", prompt.lower())
        # Brand names are stripped from the visual concept so the model
        # does not paint garbled "Fetclai.i" text into the artwork.
        self.assertNotIn("fetch.ai title", prompt.lower())
        self.assertIn("teal robot agent", prompt)

    def test_scene_prompt_stays_focused(self):
        long_post = " ".join(["Agents collaborate across networks."] * 40)
        prompt = ContentService.scene_prompt(
            long_post,
            "Collaboration",
            "An agent weaving glowing threads between towers",
        )
        self.assertLess(len(prompt), 1400)
        self.assertIn("Collaboration", prompt)

    def test_headline_comes_from_the_post(self):
        headline, subhead = fallback_visual_copy(
            "Autonomous agents can hire each other for real work.\n\n"
            "That is how Fetch.ai turns intent into action.\n\n"
            "#AI #Agents"
        )
        self.assertIn("Autonomous agents", headline)
        self.assertIn("Fetch.ai", subhead)
        self.assertNotIn("#AI", headline)

    def test_model_marks_are_cropped_from_corners(self):
        image = Image.new("RGB", (1000, 1000), (20, 40, 80))
        cropped = crop_model_marks(image)
        self.assertEqual(cropped.size, (940, 870))

    def test_generated_scene_keeps_most_of_the_art(self):
        image = Image.new("RGB", (1000, 1000), (20, 40, 80))
        scrubbed = sanitize_generated_scene(image)
        self.assertGreaterEqual(scrubbed.size[0], 850)
        self.assertGreaterEqual(scrubbed.size[1], 800)

    def test_story_card_keeps_the_headline_readable(self):
        raw = BytesIO()
        canvas = Image.new("RGB", (1024, 1024), (20, 40, 80))
        pixels = canvas.load()
        for y in range(0, 1024, 3):
            for x in range(0, 1024, 3):
                pixels[x, y] = ((x * 17) % 255, (y * 11) % 255, 140)
        canvas.save(raw, format="PNG")
        result = compose_story_card(
            raw.getvalue(),
            "Agents that find work for each other",
            "A visual take on today's draft",
            output_size=POSTER_SIZE,
        )
        image = Image.open(BytesIO(result))
        self.assertEqual(image.size, (POSTER_SIZE, POSTER_SIZE))
        self.assertGreater(len(result), 25000)
        validate_linkedin_image(result, min_edge=POSTER_SIZE)

    def test_tiny_images_are_rejected(self):
        raw = BytesIO()
        Image.new("RGB", (64, 64), (20, 40, 80)).save(raw, format="PNG")
        with self.assertRaises(ValueError):
            validate_linkedin_image(raw.getvalue(), min_edge=1024)

    def test_old_drafts_still_load(self):
        draft = Draft.from_dict(
            {
                "id": "abc",
                "topic": "Agents",
                "post": "A short post.",
                "image_prompt": "A network",
                "tone": "professional",
                "audience": "developers",
                "objective": "educate",
                "mention_keys": [],
                "source_url": "",
                "status": "pending",
                "created_at": "2026-09-12T00:00:00+00:00",
            }
        )
        self.assertEqual(draft.visual_headline, "")
        self.assertEqual(draft.visual_subhead, "")

    def test_draft_from_dict_ignores_unknown_and_missing_fields(self):
        draft = Draft.from_dict(
            {
                "id": "xyz",
                "topic": "Agents",
                "post": "Hello",
                "image_prompt": "Scene",
                "tone": "professional",
                "audience": "developers",
                "objective": "educate",
                "status": "pending",
                "created_at": "2026-09-12T00:00:00+00:00",
                "unexpected": "drop-me",
            }
        )
        self.assertEqual(draft.mention_keys, [])
        self.assertEqual(draft.source_url, "")
        self.assertFalse(hasattr(draft, "unexpected"))

    def test_polish_post_removes_hype_and_engagement_bait(self):
        cleaned = ContentService.polish_post(
            "This is REVOLUTIONARY!!!\n\n"
            "Comment YES if you agree\n\n"
            "Agents help teams ship faster."
        )
        self.assertIn("important", cleaned.lower())
        self.assertNotIn("REVOLUTIONARY", cleaned)
        self.assertNotIn("Comment YES", cleaned)
        self.assertIn("Agents help teams", cleaned)

if __name__ == "__main__":
    unittest.main()
