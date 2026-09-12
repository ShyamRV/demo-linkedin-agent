"""LinkedIn Buddy: an approval-first LinkedIn agent for Agentverse."""

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)

from cards import create_post_form, draft_review, settings_form, text_message
from config import DEFAULT_MENTION_KEYS, SETTINGS, Mention
from content import ContentService, Draft
from linkedin import LinkedInClient


TOPICS = [
    "How autonomous agents discover, collaborate, and transact with Fetch.ai",
    "Building a useful agent with the uAgents framework",
    "How Agentverse makes agents discoverable through ASI:One",
    "ASI:One Planner Mode and practical multi-agent workflows",
    "Combining reusable Agent Skills in the Fetch.ai ecosystem",
    "What developers learn by building and debugging real agents",
    "How agentic AI can remove repetitive digital work",
]

DEFAULT_PREFERENCES = {
    "tone": "professional",
    "audience": "technology leaders, founders, and AI practitioners",
    "objective": "share a clear professional insight that builds credibility",
}

HELP_TEXT = """I'm LinkedIn Buddy, an approval-first LinkedIn assistant.

I write highly professional Fetch.ai posts: clear insight, credible tone,
short paragraphs, and no hype.

Commands:
- create             Open the interactive post form
- preview about ...  Create a draft for review
- settings           Set tone, audience, and objective
- status             Show schedule and pending draft
- history            Show recent published posts
- mentions           Show available LinkedIn mentions
- claim              Become the owner for scheduled drafts
- schedule 18:00     Change the daily draft time
- pause / resume     Pause or resume scheduled drafts

Default mentions (only if the name appears in the draft):
- Fetch.ai
- Fetch.ai Innovation Lab

Person mentions such as Sana Wajid are opt-in from the create form.
I never publish a draft until you approve it."""


def public_error(error: Exception) -> str:
    """Keep chat replies free of secrets and stack noise."""
    name = type(error).__name__
    text = str(error).strip() or "unexpected error"
    text = re.sub(r"Bearer\s+\S+", "Bearer [redacted]", text, flags=re.I)
    text = re.sub(
        r"(api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*\S+",
        r"\1=[redacted]",
        text,
        flags=re.I,
    )
    if len(text) > 220:
        text = text[:217] + "..."
    return f"{name}: {text}"


def remember_owner(ctx: Context, sender: str) -> None:
    """Keep the first chatter as schedule owner unless they run `claim`."""
    if not ctx.storage.get("owner_sender"):
        ctx.storage.set("owner_sender", sender)


def claim_owner(ctx: Context, sender: str) -> None:
    ctx.storage.set("owner_sender", sender)


agent = Agent(
    name=SETTINGS.agent_name,
    handle=SETTINGS.agent_handle,
    seed=SETTINGS.agent_seed,
    port=SETTINGS.agent_port,
    mailbox=True,
    publish_agent_details=True,
    description=(
        "Approval-first LinkedIn assistant using ASI:One, interactive cards, "
        "scheduled drafts, and Fetch.ai ecosystem mentions."
    ),
)
protocol = Protocol(spec=chat_protocol_spec)


def content_service() -> ContentService:
    if not SETTINGS.asi_key:
        raise ValueError("ASI1_API_KEY is missing")
    return ContentService(
        SETTINGS.asi_key,
        SETTINGS.asi_url,
        image_size=SETTINGS.image_size,
        image_output_size=SETTINGS.image_output_size,
        image_retries=SETTINGS.image_retries,
    )


def linkedin_client() -> LinkedInClient:
    if not SETTINGS.linkedin_token or not SETTINGS.linkedin_author:
        raise ValueError(
            "LINKEDIN_ACCESS_TOKEN or LINKEDIN_AUTHOR_URN is missing"
        )
    return LinkedInClient(
        SETTINGS.linkedin_token,
        SETTINGS.linkedin_author,
        SETTINGS.linkedin_version,
    )


def storage_key(kind: str, sender: str) -> str:
    return f"{kind}:{sender}"


def get_preferences(ctx: Context, sender: str) -> Dict:
    saved = ctx.storage.get(storage_key("preferences", sender)) or {}
    return {**DEFAULT_PREFERENCES, **saved}


def get_draft(ctx: Context, sender: str) -> Optional[Draft]:
    value = ctx.storage.get(storage_key("draft", sender))
    return Draft.from_dict(value) if value else None


def save_draft(ctx: Context, sender: str, draft: Draft) -> None:
    ctx.storage.set(storage_key("draft", sender), draft.to_dict())


def clear_draft(ctx: Context, sender: str) -> None:
    ctx.storage.set(storage_key("draft", sender), None)


def get_schedule(ctx: Context) -> Dict:
    return ctx.storage.get("schedule") or {
        "hour": SETTINGS.post_hour,
        "minute": SETTINGS.post_minute,
        "paused": False,
        "timezone": SETTINGS.timezone_name,
    }


def truthy(value) -> bool:
    return value is True or str(value).lower() in {"true", "1", "yes", "on"}


def selected_mention_keys(data: Dict, default_all: bool = True) -> List[str]:
    present = any(key in data for key in ("tag_fetch", "tag_lab", "tag_sana"))
    if not present and default_all:
        return list(DEFAULT_MENTION_KEYS)

    keys = []
    if truthy(data.get("tag_fetch")):
        keys.append("fetch")
    if truthy(data.get("tag_lab")):
        keys.append("lab")
    if truthy(data.get("tag_sana")):
        keys.append("sana")
    return keys


def mention_by_key(key: str) -> Optional[Mention]:
    return next(
        (item for item in SETTINGS.mentions() if item.key == key),
        None,
    )


def mention_names(keys: List[str]) -> List[str]:
    return [
        mention.name
        for key in keys
        if (mention := mention_by_key(key)) is not None
    ]


def unresolved_mentions(keys: List[str]) -> str:
    notes = []
    for key in keys:
        mention = mention_by_key(key)
        if mention is None:
            continue
        if not mention.urn and mention.key == "sana":
            notes.append(
                f"@{mention.name} is opt-in visible text only; set "
                "SANA_WAJID_URN only if you have consent to mention them."
            )
    return " ".join(notes)


def message_text(msg: ChatMessage) -> str:
    if hasattr(msg, "text") and msg.text():
        return msg.text()
    return "".join(
        item.text for item in msg.content if isinstance(item, TextContent)
    )


def clean_message(text: str) -> str:
    text = re.sub(r"^@agent1[a-z0-9]+\s+", "", text, flags=re.IGNORECASE)
    return re.sub(
        r"^@linkedin-buddy\s+", "", text, flags=re.IGNORECASE
    ).strip()


def parse_selection(text: str) -> Dict:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        lowered = text.lower()
        for action, words in {
            "publish": ("approve", "publish", "confirm"),
            "regenerate": ("regenerate", "generate again"),
            "cancel": ("cancel", "reject"),
            "revise": ("revise", "apply edit", "edit"),
            "create_draft": ("generate draft",),
        }.items():
            if any(word in lowered for word in words):
                return {"action": action}
    return {}


async def build_draft(
    ctx: Context,
    sender: str,
    topic: str,
    tone: Optional[str] = None,
    audience: Optional[str] = None,
    objective: Optional[str] = None,
    keys: Optional[List[str]] = None,
    source_url: str = "",
    scheduled: bool = False,
) -> Draft:
    preferences = get_preferences(ctx, sender)
    selected = keys if keys is not None else list(DEFAULT_MENTION_KEYS)
    draft = await asyncio.to_thread(
        content_service().create_draft,
        topic,
        tone or preferences["tone"],
        audience or preferences["audience"],
        objective or preferences["objective"],
        mention_names(selected),
        source_url,
        scheduled,
    )
    draft.mention_keys = selected
    save_draft(ctx, sender, draft)
    return draft


async def send_draft(ctx: Context, sender: str, draft: Draft) -> None:
    await ctx.send(
        sender,
        draft_review(draft, unresolved_mentions(draft.mention_keys)),
    )


async def publish_draft(
    ctx: Context,
    sender: str,
    requested_id: str = "",
) -> None:
    draft = get_draft(ctx, sender)
    if not draft:
        await ctx.send(sender, text_message("There is no pending draft."))
        return
    if requested_id and requested_id != draft.id:
        await ctx.send(
            sender,
            text_message("That review card is old. Open the latest draft."),
        )
        return
    if draft.status == "publishing":
        await ctx.send(sender, text_message("This draft is already publishing."))
        return

    draft.status = "publishing"
    save_draft(ctx, sender, draft)
    await ctx.send(
        sender,
        text_message(
            "Approved. Generating a high-quality image and publishing now..."
        ),
    )

    try:
        generated = await asyncio.to_thread(
            content_service().generate_image_for_draft,
            draft,
        )
        image = generated.data
        if not image:
            raise RuntimeError("Image generation returned empty bytes")
    except Exception as error:
        draft.status = "pending"
        save_draft(ctx, sender, draft)
        ctx.logger.exception("High-quality image generation failed")
        if SETTINGS.require_image_on_publish:
            await ctx.send(
                sender,
                text_message(
                    "Publish blocked: a high-quality image is required for "
                    "every post. Draft is still pending — try Approve again. "
                    f"({public_error(error)})"
                ),
            )
            return
        await ctx.send(
            sender,
            text_message(
                "Image generation failed and text-only publish is allowed by "
                f"config. Continuing without an image. ({public_error(error)})"
            ),
        )
        image = None

    try:
        post_id = await asyncio.to_thread(
            linkedin_client().publish,
            draft.post,
            image,
            draft.mention_keys,
            SETTINGS.mentions(),
            draft.visual_headline or draft.image_prompt,
        )
    except Exception:
        draft.status = "pending"
        save_draft(ctx, sender, draft)
        raise

    draft.status = "published"
    history = ctx.storage.get("history") or []
    history.insert(
        0,
        {
            "id": draft.id,
            "post_id": post_id,
            "topic": draft.topic,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "had_image": bool(image),
        },
    )
    ctx.storage.set("history", history[:20])
    ctx.storage.set("last_post_date", SETTINGS.now().date().isoformat())
    clear_draft(ctx, sender)
    await ctx.send(
        sender,
        text_message(
            "Published successfully with a high-quality image.\n"
            f"Post ID: {post_id}"
            if image
            else f"Published successfully (text-only).\nPost ID: {post_id}"
        ),
    )


async def handle_action(
    ctx: Context,
    sender: str,
    data: Dict,
) -> bool:
    action = data.get("action")
    if not action:
        return False

    if action == "create_draft":
        topic = str(data.get("topic", "")).strip()
        if not topic:
            await ctx.send(sender, text_message("Please provide a topic."))
            return True
        keys = selected_mention_keys(data)
        draft = await build_draft(
            ctx,
            sender,
            topic,
            str(
                data.get("tone")
                or data.get("default_tone")
                or DEFAULT_PREFERENCES["tone"]
            ),
            str(
                data.get("audience")
                or data.get("default_audience")
                or DEFAULT_PREFERENCES["audience"]
            ),
            str(
                data.get("objective")
                or data.get("default_objective")
                or DEFAULT_PREFERENCES["objective"]
            ),
            keys,
            str(data.get("source_url", "")).strip(),
        )
        await send_draft(ctx, sender, draft)
        return True

    if action == "publish":
        await publish_draft(ctx, sender, str(data.get("draft_id", "")))
        return True

    if action == "cancel":
        clear_draft(ctx, sender)
        await ctx.send(sender, text_message("Draft cancelled. Nothing posted."))
        return True

    if action in {"revise", "regenerate"}:
        draft = get_draft(ctx, sender)
        if not draft:
            await ctx.send(sender, text_message("There is no pending draft."))
            return True
        instruction = str(data.get("edit_instruction", "")).strip()
        tone = str(data.get("tone", "")).strip() or draft.tone
        if action == "revise" and not instruction:
            await ctx.send(
                sender,
                text_message(
                    "Add an edit instruction in the review card first."
                ),
            )
            return True
        if action == "regenerate":
            instruction = "Rewrite it with a fresh hook and structure."
        draft = await asyncio.to_thread(
            content_service().revise_draft,
            draft,
            instruction,
            tone,
        )
        save_draft(ctx, sender, draft)
        await send_draft(ctx, sender, draft)
        return True

    if action == "save_settings":
        preferences = {
            "tone": str(
                data.get("tone")
                or data.get("current_tone")
                or DEFAULT_PREFERENCES["tone"]
            ),
            "audience": str(
                data.get("audience")
                or data.get("current_audience")
                or DEFAULT_PREFERENCES["audience"]
            ),
            "objective": str(
                data.get("objective")
                or data.get("current_objective")
                or DEFAULT_PREFERENCES["objective"]
            ),
        }
        ctx.storage.set(storage_key("preferences", sender), preferences)
        await ctx.send(sender, text_message("Preferences saved."))
        return True

    return False


def status_text(ctx: Context, sender: str) -> str:
    schedule = get_schedule(ctx)
    draft = get_draft(ctx, sender)
    state = "paused" if schedule["paused"] else "active"
    pending = (
        f"{draft.id} — {draft.topic}" if draft else "none"
    )
    owner = ctx.storage.get("owner_sender") or "unset (chat once or run claim)"
    you_own = "yes" if owner == sender else "no"
    return (
        f"Schedule: {schedule['hour']:02d}:{schedule['minute']:02d} "
        f"{schedule['timezone']} ({state})\n"
        f"Schedule owner: {owner}\n"
        f"You are owner: {you_own}\n"
        f"Pending draft: {pending}\n"
        f"Last published date: "
        f"{ctx.storage.get('last_post_date') or 'never'}"
    )


def history_text(ctx: Context) -> str:
    history = ctx.storage.get("history") or []
    if not history:
        return "No posts have been published by this agent yet."
    lines = ["Recent posts:"]
    for item in history[:5]:
        lines.append(
            f"- {item['published_at'][:10]} · {item['topic']} "
            f"({item['post_id']})"
        )
    return "\n".join(lines)


def mentions_text() -> str:
    lines = [
        "Available mentions:",
        "Names become @Name only when they already appear in the draft.",
        "Nothing is appended for selected mentions that are missing from the text.",
        "",
    ]
    for mention in SETTINGS.mentions():
        mode = "ready" if mention.urn else "visible @Name only"
        lines.append(f"- @{mention.name} ({mode})\n  {mention.url}")
    lines.append(
        "\nPerson mentions stay unchecked by default. Only enable them "
        "when you intend to mention that person."
    )
    return "\n".join(lines)


@agent.on_event("startup")
async def on_startup(ctx: Context):
    ctx.logger.info(f"LinkedIn Buddy started at {agent.address}")
    if SETTINGS.has_weak_seed():
        ctx.logger.error(
            "AGENT_SEED is a shared placeholder. Set a unique seed before "
            "deployment. Local demos can set ALLOW_INSECURE_SEED=1."
        )
    if not SETTINGS.asi_key:
        ctx.logger.warning("ASI1_API_KEY is missing")
    if not SETTINGS.linkedin_token or not SETTINGS.linkedin_author:
        ctx.logger.warning("LinkedIn credentials are missing")
    elif SETTINGS.linkedin_token_expires_at:
        seconds_left = (
            SETTINGS.linkedin_token_expires_at
            - int(datetime.now(timezone.utc).timestamp())
        )
        if seconds_left < 7 * 24 * 60 * 60:
            ctx.logger.warning(
                "LinkedIn token expires within 7 days; run "
                "linkedin_setup.py again"
            )


@agent.on_interval(period=60.0)
async def scheduled_draft(ctx: Context):
    schedule = get_schedule(ctx)
    if schedule.get("paused"):
        return
    now = SETTINGS.now()
    if now.hour != schedule["hour"] or now.minute != schedule["minute"]:
        return

    date_key = now.date().isoformat()
    if ctx.storage.get("last_scheduled_draft_date") == date_key:
        return
    owner = ctx.storage.get("owner_sender")
    if not owner:
        ctx.logger.warning(
            "Cannot send scheduled draft until a user chats with the agent"
        )
        return

    # Lock before the API call so overlapping interval invocations cannot
    # create duplicate drafts.
    ctx.storage.set("last_scheduled_draft_date", date_key)
    topic = TOPICS[now.timetuple().tm_yday % len(TOPICS)]
    try:
        draft = await build_draft(
            ctx,
            owner,
            topic,
            keys=list(DEFAULT_MENTION_KEYS),
            scheduled=True,
        )
        await ctx.send(
            owner,
            text_message(
                "Your scheduled draft is ready. It will not publish without "
                "your approval."
            ),
        )
        await send_draft(ctx, owner, draft)
    except Exception as error:
        ctx.storage.set("last_scheduled_draft_date", None)
        ctx.logger.exception("Scheduled draft failed")
        await ctx.send(
            owner,
            text_message(
                "Scheduled draft failed. Check the agent logs. "
                f"({public_error(error)})"
            ),
        )


@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc),
            acknowledged_msg_id=msg.msg_id,
        ),
    )
    remember_owner(ctx, sender)

    if any(isinstance(item, EndSessionContent) for item in msg.content):
        return
    if any(isinstance(item, StartSessionContent) for item in msg.content):
        await ctx.send(sender, text_message(HELP_TEXT))
        await ctx.send(sender, create_post_form(get_preferences(ctx, sender)))
        return

    text = clean_message(message_text(msg))
    if not text:
        return

    try:
        selection = parse_selection(text)
        if await handle_action(ctx, sender, selection):
            return

        lowered = text.lower()
        if lowered in {"hi", "hello", "help", "start", "create", "new post"}:
            await ctx.send(sender, text_message(HELP_TEXT))
            await ctx.send(
                sender,
                create_post_form(get_preferences(ctx, sender)),
            )
            return
        if lowered == "settings":
            await ctx.send(
                sender,
                settings_form(get_preferences(ctx, sender)),
            )
            return
        if lowered == "status":
            await ctx.send(sender, text_message(status_text(ctx, sender)))
            return
        if lowered == "history":
            await ctx.send(sender, text_message(history_text(ctx)))
            return
        if lowered == "mentions":
            await ctx.send(sender, text_message(mentions_text()))
            return
        if lowered == "claim":
            claim_owner(ctx, sender)
            await ctx.send(
                sender,
                text_message(
                    "You are now the schedule owner. Daily drafts will be "
                    "sent here."
                ),
            )
            return
        if lowered == "pause":
            schedule = get_schedule(ctx)
            schedule["paused"] = True
            ctx.storage.set("schedule", schedule)
            await ctx.send(sender, text_message("Scheduled drafts paused."))
            return
        if lowered == "resume":
            schedule = get_schedule(ctx)
            schedule["paused"] = False
            ctx.storage.set("schedule", schedule)
            await ctx.send(sender, text_message("Scheduled drafts resumed."))
            return

        schedule_match = re.fullmatch(
            r"schedule\s+([01]?\d|2[0-3]):([0-5]\d)",
            lowered,
        )
        if schedule_match:
            schedule = get_schedule(ctx)
            schedule["hour"] = int(schedule_match.group(1))
            schedule["minute"] = int(schedule_match.group(2))
            ctx.storage.set("schedule", schedule)
            await ctx.send(
                sender,
                text_message(
                    f"Daily draft time set to "
                    f"{schedule['hour']:02d}:{schedule['minute']:02d} "
                    f"{schedule['timezone']}."
                ),
            )
            return

        topic_match = re.match(
            r"^(?:preview|draft|post)(?:\s+now)?(?:\s+about)?\s+(.+)$",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if topic_match:
            topic = topic_match.group(1).strip()
            draft = await build_draft(
                ctx,
                sender,
                topic,
                keys=list(DEFAULT_MENTION_KEYS),
            )
            await send_draft(ctx, sender, draft)
            return

        if len(text) > 40:
            draft = await build_draft(
                ctx,
                sender,
                text,
                keys=list(DEFAULT_MENTION_KEYS),
            )
            await send_draft(ctx, sender, draft)
            return

        await ctx.send(sender, text_message(HELP_TEXT))
    except Exception as error:
        ctx.logger.exception("Chat request failed")
        await ctx.send(
            sender,
            text_message(
                "Request failed. Check the agent logs for details. "
                f"({public_error(error)})"
            ),
        )


@protocol.on_message(ChatAcknowledgement)
async def handle_ack(
    ctx: Context,
    sender: str,
    msg: ChatAcknowledgement,
):
    pass


agent.include(protocol, publish_manifest=True)

if __name__ == "__main__":
    if SETTINGS.has_weak_seed() and not SETTINGS.allow_insecure_seed:
        raise SystemExit(
            "Refusing to start with a placeholder AGENT_SEED.\n"
            "Set a unique AGENT_SEED in .env, or set ALLOW_INSECURE_SEED=1 "
            "for a local throwaway demo."
        )
    agent.run()
