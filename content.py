import base64
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

import requests
from openai import OpenAI

from visual import compose_story_card, fallback_visual_copy, validate_linkedin_image


PROFESSIONAL_WRITING = (
    "Write a highly professional LinkedIn post suitable for founders, "
    "engineers, and technology leaders. "
    "Structure: (1) a sharp opening line that states the insight, "
    "(2) 2-4 short paragraphs that explain the idea with concrete detail, "
    "(3) one practical takeaway, (4) a calm closing line, "
    "(5) 4-6 relevant hashtags on the last line. "
    "Voice: confident, precise, credible, human. Prefer plain language over "
    "buzzwords. Use short paragraphs and strong verbs. "
    "Avoid: hype, clickbait, rhetorical spam, emoji floods, all-caps shouting, "
    "engagement bait ('comment YES', 'like if you agree'), fake metrics, "
    "invented announcements, markdown headings, bullet-list dumps, "
    "and generic AI filler. "
    "Length: 140-220 words. Fact-conscious only. "
)


@dataclass
class Draft:
    id: str
    topic: str
    post: str
    image_prompt: str
    tone: str
    audience: str
    objective: str
    mention_keys: List[str]
    source_url: str
    status: str
    created_at: str
    scheduled: bool = False
    visual_headline: str = ""
    visual_subhead: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Dict) -> "Draft":
        fields = set(cls.__dataclass_fields__)
        defaults = {
            "id": "",
            "topic": "",
            "post": "",
            "image_prompt": "",
            "tone": "professional",
            "audience": "",
            "objective": "",
            "mention_keys": [],
            "source_url": "",
            "status": "pending",
            "created_at": "",
            "scheduled": False,
            "visual_headline": "",
            "visual_subhead": "",
        }
        data = {key: defaults[key] for key in fields}
        for key, item in dict(value or {}).items():
            if key in fields:
                data[key] = item
        if not isinstance(data.get("mention_keys"), list):
            data["mention_keys"] = []
        return cls(**data)


@dataclass
class ImageResult:
    data: bytes
    url: Optional[str] = None


class ContentService:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        image_size: str = "1024x1024",
        image_output_size: int = 1200,
        image_retries: int = 3,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.image_size = image_size or "1024x1024"
        self.image_output_size = max(1024, int(image_output_size or 1200))
        self.image_retries = max(1, int(image_retries or 3))
        self.client = OpenAI(base_url=self.base_url, api_key=api_key)

    @staticmethod
    def _json_object(raw: str) -> Dict:
        raw = (raw or "").strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise ValueError("ASI:One did not return valid JSON")
        parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("ASI:One JSON was not an object")
        return parsed

    @staticmethod
    def _draft_fields(data: Dict) -> tuple[str, str, str, str]:
        post = str(
            data.get("post")
            or data.get("content")
            or data.get("caption")
            or data.get("text")
            or ""
        ).strip()
        image_prompt = str(
            data.get("image_prompt")
            or data.get("visual_prompt")
            or data.get("scene")
            or data.get("prompt")
            or ""
        ).strip()
        headline = str(
            data.get("visual_headline")
            or data.get("headline")
            or data.get("title")
            or ""
        ).strip()
        subhead = str(
            data.get("visual_subhead")
            or data.get("subhead")
            or data.get("subtitle")
            or ""
        ).strip()
        return post, image_prompt, headline, subhead

    @staticmethod
    def polish_post(text: str) -> str:
        """Light cleanup so drafts stay professional even if the model slips."""
        cleaned = text.replace("\r\n", "\n").strip()
        cleaned = re.sub(r"[^\S\n]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r"!{2,}", "!", cleaned)
        cleaned = re.sub(r"\?{2,}", "?", cleaned)
        cleaned = re.sub(
            r"(?im)^(comment|like|share|repost)\s+(yes|if you|this|below).*$",
            "",
            cleaned,
        )
        cleaned = re.sub(r"(?i)\bgame[- ]changer\b", "meaningful shift", cleaned)
        cleaned = re.sub(r"(?i)\brevolutionary\b", "important", cleaned)
        cleaned = re.sub(r"(?i)\bunleash\b", "enable", cleaned)
        cleaned = re.sub(r"(?i)\bdisrupt(ing|ive)?\b", "improving", cleaned)
        return cleaned.strip()

    def create_draft(
        self,
        topic: str,
        tone: str = "professional",
        audience: str = "technology leaders, founders, and AI practitioners",
        objective: str = "share a clear professional insight that builds credibility",
        mention_names: Optional[List[str]] = None,
        source_url: str = "",
        scheduled: bool = False,
    ) -> Draft:
        names = mention_names or []
        mention_rule = (
            "Naturally include these exact names as plain words, with no @, "
            "no markdown links, and no urn:li values: "
            + ", ".join(names)
            + "."
            if names
            else "Do not force any company or person names into the post."
        )
        source_rule = (
            f"Use this URL only as a user-provided reference: {source_url}. "
            "Do not invent details that are not in the supplied topic."
            if source_url
            else "Do not invent dates, metrics, partnerships, or announcements."
        )

        system_prompt = (
            "You are a senior LinkedIn ghostwriter and visual director for "
            "the Fetch.ai ecosystem. Return ONLY valid JSON with all four "
            "keys: "
            '{"post":"...","image_prompt":"...","visual_headline":'
            '"...","visual_subhead":"..."}. '
            "Never return markdown outside JSON. Never omit image_prompt. "
            f"{PROFESSIONAL_WRITING} "
            "Unless the user asks otherwise, keep the tone professional and "
            "executive-ready. "
            "image_prompt must describe one vivid, high-detail square scene "
            "with a clear hero action, dramatic light, and one cute teal "
            "rounded robot agent with a tiny antenna acting out the idea. "
            "Never write any words, letters, brand names, or 'Fetch.ai' "
            "inside image_prompt as on-image text — describe visuals only. "
            "Do not dump the whole post into the image prompt. "
            "Do not mention other AI products, logos, sparkle icons, or "
            "watermarks. "
            "visual_headline is a 4-7 word professional poster title. "
            "visual_subhead is one short supporting line. "
            f"{mention_rule} {source_rule}"
        )
        user_prompt = (
            f"Topic: {topic}\n"
            f"Tone: {tone}\n"
            f"Audience: {audience}\n"
            f"Objective: {objective}\n"
            "Write the most professional version of this post."
        )

        last_error: Optional[Exception] = None
        for attempt in range(self.image_retries):
            try:
                response = self.client.chat.completions.create(
                    model="asi1",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": (
                                user_prompt
                                if attempt == 0
                                else (
                                    user_prompt
                                    + "\n\nReturn complete JSON only. "
                                    "Include a highly professional non-empty "
                                    "post and image_prompt."
                                )
                            ),
                        },
                    ],
                    temperature=0.55 if attempt == 0 else 0.4,
                    max_tokens=1600,
                )
                raw = response.choices[0].message.content or ""
                data = self._json_object(raw)
                post, image_prompt, headline, subhead = self._draft_fields(data)
                post = self.polish_post(post)
                if post and not image_prompt:
                    image_prompt = (
                        "A cute teal Fetch.ai agent acting out this idea in a "
                        f"premium cinematic square scene: {topic}"
                    )
                if image_prompt and not post:
                    raise ValueError("ASI:One response is missing post")
                if not post or not image_prompt:
                    raise ValueError(
                        "ASI:One response is missing post or image_prompt"
                    )
                if len(post) > 3000:
                    raise ValueError("Generated post is unexpectedly long")

                if not headline or not subhead:
                    fallback_headline, fallback_subhead = fallback_visual_copy(post)
                    headline = headline or fallback_headline
                    subhead = subhead or fallback_subhead

                return Draft(
                    id=uuid4().hex[:10],
                    topic=topic,
                    post=post,
                    image_prompt=image_prompt,
                    tone=tone,
                    audience=audience,
                    objective=objective,
                    mention_keys=[],
                    source_url=source_url,
                    status="pending",
                    created_at=datetime.now(timezone.utc).isoformat(),
                    scheduled=scheduled,
                    visual_headline=headline,
                    visual_subhead=subhead,
                )
            except Exception as error:
                last_error = error

        raise ValueError(
            "Could not create a draft after retries: "
            f"{last_error}"
        )

    def revise_draft(
        self,
        draft: Draft,
        instruction: str,
        tone: Optional[str] = None,
    ) -> Draft:
        chosen_tone = tone or draft.tone
        response = self.client.chat.completions.create(
            model="asi1",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Revise a LinkedIn draft into a more professional "
                        "version. Return ONLY valid JSON as "
                        '{"post":"...","image_prompt":"...","visual_headline":'
                        '"...","visual_subhead":"..."}. '
                        f"{PROFESSIONAL_WRITING} "
                        "Preserve factual meaning and exact organization/"
                        "person names. Do not add unsupported facts. Rewrite "
                        "image_prompt as a fresh high-detail hero scene with "
                        "a cute Fetch.ai agent acting out the revised idea. "
                        "Refresh visual_headline to a 4-7 word professional "
                        "poster title. Fetch.ai original art only. Do not "
                        "name other AI products or brand marks."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Current post:\n{draft.post}\n\n"
                        f"Current image prompt:\n{draft.image_prompt}\n\n"
                        f"New tone: {chosen_tone}\n"
                        f"Revision instruction: {instruction}\n"
                        "Make the result highly professional."
                    ),
                },
            ],
            temperature=0.45,
            max_tokens=1600,
        )
        data = self._json_object(response.choices[0].message.content or "")
        post, image_prompt, headline, subhead = self._draft_fields(data)
        draft.post = self.polish_post(post or draft.post)
        draft.image_prompt = image_prompt or draft.image_prompt
        if not headline or not subhead:
            fallback_headline, fallback_subhead = fallback_visual_copy(draft.post)
            headline = headline or fallback_headline
            subhead = subhead or fallback_subhead
        draft.visual_headline = headline
        draft.visual_subhead = subhead
        draft.tone = chosen_tone
        draft.status = "pending"
        return draft

    @staticmethod
    def _visual_copy(data: Dict, post: str) -> tuple:
        headline = str(data.get("visual_headline", "")).strip()
        subhead = str(data.get("visual_subhead", "")).strip()
        fallback_headline, fallback_subhead = fallback_visual_copy(post)
        return headline or fallback_headline, subhead or fallback_subhead

    BRAND_LEAK = re.compile(
        r"\b(gemini|google|imagen|synthid|chatgpt|openai|dall-?e|"
        r"midjourney|stable diffusion|copilot|fetch\.ai|fetchai|"
        r"fetclai|fetche?\.?ai)\b",
        re.IGNORECASE,
    )

    @classmethod
    def scene_prompt(cls, post: str, topic: str, image_prompt: str) -> str:
        idea = " ".join(post.split())[:160]
        scene = cls.BRAND_LEAK.sub("teal robot agent", image_prompt).strip()
        if len(scene) > 380:
            scene = scene[:377].rstrip() + "..."
        return (
            "Create one complete full-frame square illustration. "
            "Ultra sharp, high detail, cinematic lighting, rich color, "
            "coherent composition, professional LinkedIn quality. "
            f"Core idea: {topic}. "
            f"Visual concept: {scene}. "
            f"Story cue: {idea}. "
            "Hero: one cute rounded teal robot agent with a tiny antenna, "
            "big friendly eyes, and a warm gold glow. Show the FULL agent "
            "in frame — head, body, and hands visible — actively doing the "
            "job. Large in frame, centered or rule-of-thirds, finished scene. "
            "Style: polished 2.5D campaign illustration, depth, soft "
            "volumetric light, teal and warm-gold accents. "
            "CRITICAL: render ZERO text. No letters, numbers, titles, "
            "captions, logos, watermarks, UI bars, dark empty panels, or "
            "cut-off rectangles. Do not write Fetch.ai or any misspelling "
            "of it. Keep the entire artwork continuous edge to edge."
        )

    def generate_image_for_draft(self, draft: Draft) -> ImageResult:
        headline = draft.visual_headline
        subhead = draft.visual_subhead
        if not headline:
            headline, subhead = fallback_visual_copy(draft.post)

        last_error: Optional[Exception] = None
        for attempt in range(self.image_retries):
            try:
                prompt = self.scene_prompt(
                    draft.post,
                    draft.topic,
                    draft.image_prompt,
                )
                if attempt:
                    prompt += (
                        " Increase sharpness, lighting contrast, material "
                        "detail, and hero-subject clarity even more."
                    )
                generated = self.generate_image(prompt)
                generated.data = compose_story_card(
                    generated.data,
                    headline,
                    subhead,
                    output_size=self.image_output_size,
                )
                validate_linkedin_image(
                    generated.data,
                    min_edge=min(1024, self.image_output_size),
                )
                return generated
            except Exception as error:
                last_error = error

        raise RuntimeError(
            "High-quality image generation failed after "
            f"{self.image_retries} attempts: {last_error}"
        )

    def generate_image(self, prompt: str) -> ImageResult:
        response = requests.post(
            f"{self.base_url}/image/generate",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "asi1",
                "prompt": prompt,
                "size": self.image_size,
            },
            timeout=180,
        )
        response.raise_for_status()
        payload = response.json()

        image = (
            payload.get("image")
            or payload.get("image_url")
            or payload.get("url")
        )
        for collection_name in ("data", "images"):
            items = payload.get(collection_name) or []
            if image or not items:
                continue
            first = items[0] if isinstance(items[0], dict) else {}
            image = (
                first.get("url")
                or first.get("b64_json")
                or first.get("image")
            )

        if not image:
            raise RuntimeError("ASI:One returned no image")
        if str(image).startswith("data:"):
            data = base64.b64decode(str(image).split(",", 1)[1])
            if len(data) < 20_000:
                raise ValueError("ASI:One returned an unexpectedly tiny image")
            return ImageResult(data=data)
        if str(image).startswith("http"):
            download = requests.get(str(image), timeout=90)
            download.raise_for_status()
            if len(download.content) < 20_000:
                raise ValueError("Downloaded image is unexpectedly tiny")
            return ImageResult(data=download.content, url=str(image))
        data = base64.b64decode(str(image))
        if len(data) < 20_000:
            raise ValueError("ASI:One returned an unexpectedly tiny image")
        return ImageResult(data=data)
