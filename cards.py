import json
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    MetadataContent,
    TextContent,
)

from content import Draft


def text_message(text: str) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=text)],
    )


def card_message(
    text: str,
    kind: str,
    payload: Dict,
) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[
            TextContent(type="text", text=text),
            MetadataContent(
                type="metadata",
                metadata={
                    "card_protocol_version": "1",
                    "requires_card_interaction": "true",
                    "card_kind": kind,
                    "card_payload": json.dumps(payload),
                    "preferred_drawer_width_px": "620",
                },
            ),
        ],
    )


def create_post_form(defaults: Optional[Dict] = None) -> ChatMessage:
    defaults = defaults or {}
    payload = {
        "title": "Create a LinkedIn draft",
        "fields": [
            {
                "name": "topic",
                "kind": "text",
                "label": "Topic or profile details",
                "required": True,
            },
            {
                "name": "tone",
                "kind": "select",
                "label": "Tone",
                "options": [
                    {"value": "professional", "label": "Professional"},
                    {"value": "educational", "label": "Educational"},
                    {"value": "conversational", "label": "Conversational"},
                    {"value": "bold", "label": "Bold"},
                    {"value": "storytelling", "label": "Storytelling"},
                ],
            },
            {
                "name": "audience",
                "kind": "text",
                "label": "Audience",
                "required": True,
            },
            {
                "name": "objective",
                "kind": "text",
                "label": "Objective",
                "required": True,
            },
            {
                "name": "source_url",
                "kind": "text",
                "label": "Optional source URL",
            },
            {
                "name": "tag_fetch",
                "kind": "checkbox",
                "label": "Mention Fetch.ai when the name appears in the draft",
                "value": True,
            },
            {
                "name": "tag_lab",
                "kind": "checkbox",
                "label": "Mention Fetch.ai Innovation Lab when the name appears",
                "value": True,
            },
            {
                "name": "tag_sana",
                "kind": "checkbox",
                "label": "Mention Sana Wajid only if you choose to (opt-in)",
                "value": False,
            },
        ],
        "submit_cta": {
            "label": "Generate draft",
            "selection": {
                "action": "create_draft",
                "default_tone": defaults.get("tone", "professional"),
                "default_audience": defaults.get(
                    "audience",
                    "technology leaders, founders, and AI practitioners",
                ),
                "default_objective": defaults.get(
                    "objective",
                    "share a clear professional insight that builds credibility",
                ),
            },
        },
    }
    return card_message(
        "Tell me what you want to post. I'll draft a highly professional LinkedIn post. Nothing is published yet.",
        "form",
        payload,
    )


def settings_form(defaults: Optional[Dict] = None) -> ChatMessage:
    defaults = defaults or {}
    payload = {
        "title": "LinkedIn Buddy preferences",
        "fields": [
            {
                "name": "tone",
                "kind": "select",
                "label": "Default tone",
                "options": [
                    {"value": "professional", "label": "Professional"},
                    {"value": "educational", "label": "Educational"},
                    {"value": "conversational", "label": "Conversational"},
                    {"value": "bold", "label": "Bold"},
                    {"value": "storytelling", "label": "Storytelling"},
                ],
            },
            {
                "name": "audience",
                "kind": "text",
                "label": "Default audience",
                "required": True,
            },
            {
                "name": "objective",
                "kind": "text",
                "label": "Default objective",
                "required": True,
            },
        ],
        "submit_cta": {
            "label": "Save preferences",
            "selection": {
                "action": "save_settings",
                "current_tone": defaults.get("tone", "professional"),
                "current_audience": defaults.get(
                    "audience",
                    "technology leaders, founders, and AI practitioners",
                ),
                "current_objective": defaults.get(
                    "objective",
                    "share a clear professional insight that builds credibility",
                ),
            },
        },
    }
    return card_message(
        "Set your reusable professional writing defaults.",
        "form",
        payload,
    )


def draft_review(draft: Draft, unresolved_mentions: str = "") -> ChatMessage:
    preview = draft.post
    if len(preview) > 1800:
        preview = preview[:1797] + "..."

    mention_text = ", ".join(draft.mention_keys) or "none"
    warning = (
        f"\n\nMention note: {unresolved_mentions}" if unresolved_mentions else ""
    )
    payload = {
        "root": {
            "type": "section",
            "title": "Review LinkedIn draft",
            "subtitle": f"Draft {draft.id} · approval required",
            "children": [
                {"type": "text", "value": preview, "style": "body"},
                {"type": "divider"},
                {
                    "type": "text",
                    "value": f"Tone: {draft.tone} · Tags: {mention_text}",
                    "style": "muted",
                },
                {
                    "type": "text",
                    "value": (
                        f"Image: {draft.visual_headline or 'visual from this post'}"
                        + (f" — {draft.visual_subhead}" if draft.visual_subhead else "")
                    ),
                    "style": "muted",
                },
                {
                    "type": "input",
                    "name": "edit_instruction",
                    "kind": "text",
                    "label": "Optional edit instruction",
                    "placeholder": "Example: make the opening more personal",
                },
                {
                    "type": "input",
                    "name": "tone",
                    "kind": "select",
                    "label": "Tone for edit/regeneration",
                    "options": [
                        {"value": draft.tone, "label": draft.tone.title()},
                        {"value": "professional", "label": "Professional"},
                        {"value": "educational", "label": "Educational"},
                        {"value": "conversational", "label": "Conversational"},
                        {"value": "bold", "label": "Bold"},
                        {"value": "storytelling", "label": "Storytelling"},
                    ],
                },
                {
                    "type": "group",
                    "direction": "row",
                    "gap": 8,
                    "children": [
                        {
                            "type": "button",
                            "label": "Approve & publish",
                            "primary": True,
                            "action": {
                                "selection": {
                                    "action": "publish",
                                    "draft_id": draft.id,
                                }
                            },
                        },
                        {
                            "type": "button",
                            "label": "Apply edit",
                            "action": {
                                "selection": {
                                    "action": "revise",
                                    "draft_id": draft.id,
                                }
                            },
                        },
                        {
                            "type": "button",
                            "label": "Regenerate",
                            "action": {
                                "selection": {
                                    "action": "regenerate",
                                    "draft_id": draft.id,
                                }
                            },
                        },
                        {
                            "type": "button",
                            "label": "Cancel",
                            "action": {
                                "selection": {
                                    "action": "cancel",
                                    "draft_id": draft.id,
                                }
                            },
                        },
                    ],
                },
            ],
        }
    }
    return card_message(
        f"Draft ready. Review it before publishing.{warning}",
        "custom",
        payload,
    )
