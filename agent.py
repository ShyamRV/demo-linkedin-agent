"""
Fetch.ai LinkedIn Poster — Agentverse Hosted Agent

Copy agent.py and .env into your Agentverse agent.
On Agentverse, paste .env values in the editor .env / Secrets tab.
"""

import os
import json
import base64
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4

import requests
from dotenv import load_dotenv
from openai import OpenAI
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Settings  (from .env)
# ---------------------------------------------------------------------------
POST_HOUR = int(os.getenv("POST_HOUR", "18"))          # 18 = 6pm
TIMEZONE_OFFSET = float(os.getenv("TIMEZONE_OFFSET", "5.5"))  # IST

ASI_KEY = os.getenv("ASI1_API_KEY", "")
ASI_URL = os.getenv("ASI1_BASE_URL", "https://api.asi1.ai/v1")

LINKEDIN_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_AUTHOR = os.getenv("LINKEDIN_AUTHOR_URN", "")  # urn:li:person:xxx

# One topic per day so posts do not repeat
TOPICS = [
    "What Fetch.ai is and how autonomous economic agents work",
    "Building agents with the uAgents Python framework",
    "Agentverse — hosting, discovering and chatting with agents",
    "ASI:One — the Fetch.ai LLM that talks to real agents",
    "The Agent Chat Protocol and multi-agent collaboration",
    "Real-world Fetch.ai use cases: DeFi, mobility, supply chain",
    "Why decentralized agent networks matter for the future of AI",
]


# ---------------------------------------------------------------------------
# Agent + ASI:One
# Local: uses name/seed/port/mailbox. Agentverse hosted: extra args are ignored.
# ---------------------------------------------------------------------------
agent = Agent(
    name=os.getenv("AGENT_NAME", "LinkedIn Buddy"),
    handle=os.getenv("AGENT_HANDLE", "linkedin-buddy"),
    seed=os.getenv("AGENT_SEED", "linkedin-fetchai-poster-seed"),
    port=int(os.getenv("AGENT_PORT", "8001")),
    mailbox=True,
    publish_agent_details=True,
    description="LinkedIn Buddy posts about Fetch.ai and people in the ecosystem every day at 6pm.",
)

asi = OpenAI(base_url=ASI_URL, api_key=ASI_KEY)

# Agent Chat Protocol — required so Agentverse / ASI:One can talk to this agent
protocol = Protocol(spec=chat_protocol_spec)


def now_local() -> datetime:
    return datetime.now(timezone(timedelta(hours=TIMEZONE_OFFSET)))


def today() -> str:
    return now_local().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# ASI:One — write the LinkedIn post
# ---------------------------------------------------------------------------
def write_post(topic: str) -> tuple[str, str]:
    """Returns (linkedin_text, image_prompt)."""
    date = now_local().strftime("%A, %d %B %Y")

    reply = asi.chat.completions.create(
        model="asi1",
        messages=[
            {
                "role": "system",
                "content": (
                    "You write LinkedIn posts. "
                    "Reply with ONLY valid JSON, no markdown:\n"
                    '{"post": "...", "image_prompt": "..."}\n'
                    "post: 120-180 words, professional, human, no markdown. "
                    "If the topic is a person or profile, write about them and "
                    "naturally mention Fetch.ai / agentic AI where it fits. "
                    "Otherwise write about Fetch.ai. "
                    "End with 4-6 hashtags including #FetchAI #uAgents #Agentverse #ASI.\n"
                    "image_prompt: one sentence, clean professional visual, "
                    "teal and purple, abstract agent network, NO text, NO logos."
                ),
            },
            {
                "role": "user",
                "content": f"Today is {date}. Write a LinkedIn post about:\n{topic}",
            },
        ],
        max_tokens=800,
        temperature=0.8,
    )

    raw = (reply.choices[0].message.content or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json", "", 1).strip()

    data = json.loads(raw)
    return data["post"].strip(), data["image_prompt"].strip()


# ---------------------------------------------------------------------------
# ASI:One — generate the image (returns raw bytes)
# ---------------------------------------------------------------------------
def make_image(prompt: str) -> bytes:
    response = requests.post(
        f"{ASI_URL.rstrip('/')}/image/generate",
        headers={
            "Authorization": f"Bearer {ASI_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": "asi1", "prompt": prompt, "size": "1024x1024"},
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()

    image = data.get("image") or data.get("image_url") or data.get("url")
    items = data.get("data") or []
    if not image and items:
        image = items[0].get("url") or items[0].get("b64_json")
        if items[0].get("b64_json") and not str(image).startswith("http"):
            return base64.b64decode(items[0]["b64_json"])

    if not image:
        raise RuntimeError(f"ASI:One returned no image: {data}")

    if str(image).startswith("data:"):
        return base64.b64decode(image.split(",", 1)[1])
    if str(image).startswith("http"):
        return requests.get(image, timeout=60).content
    return base64.b64decode(image)


# ---------------------------------------------------------------------------
# LinkedIn — upload image + publish
# ---------------------------------------------------------------------------
def _li_headers() -> dict:
    return {
        "Authorization": f"Bearer {LINKEDIN_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def upload_image(image: bytes) -> str:
    register = requests.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers=_li_headers(),
        json={
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": LINKEDIN_AUTHOR,
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent",
                    }
                ],
            }
        },
        timeout=30,
    )
    register.raise_for_status()
    value = register.json()["value"]
    upload_url = value["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset = value["asset"]

    kind = "image/jpeg" if image[:3] == b"\xff\xd8\xff" else "image/png"
    put = requests.put(
        upload_url,
        headers={"Authorization": f"Bearer {LINKEDIN_TOKEN}", "Content-Type": kind},
        data=image,
        timeout=60,
    )
    put.raise_for_status()
    return asset


def publish_linkedin(text: str, image: Optional[bytes]) -> str:
    share = {
        "shareCommentary": {"text": text},
        "shareMediaCategory": "NONE",
    }
    if image:
        asset = upload_image(image)
        share = {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "IMAGE",
            "media": [
                {"status": "READY", "media": asset, "title": {"text": "Fetch.ai"}}
            ],
        }

    response = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=_li_headers(),
        json={
            "author": LINKEDIN_AUTHOR,
            "lifecycleState": "PUBLISHED",
            "specificContent": {"com.linkedin.ugc.ShareContent": share},
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.headers.get("x-restli-id", "published")


# ---------------------------------------------------------------------------
# Create + publish one post
# ---------------------------------------------------------------------------
def run_daily_post(ctx: Context, topic: Optional[str] = None) -> str:
    if not ASI_KEY:
        return "Missing ASI1_API_KEY. Agentverse normally injects this for you."
    if not LINKEDIN_TOKEN or not LINKEDIN_AUTHOR:
        return (
            "Missing LinkedIn secrets. Add LINKEDIN_ACCESS_TOKEN and "
            "LINKEDIN_AUTHOR_URN in the Agentverse Secrets tab."
        )

    if not topic:
        topic = TOPICS[now_local().timetuple().tm_yday % len(TOPICS)]
    ctx.logger.info(f"Writing post about: {topic}")

    text, image_prompt = write_post(topic)
    ctx.logger.info(f"Post ready ({len(text)} chars)")

    image = None
    try:
        image = make_image(image_prompt)
        ctx.logger.info(f"Image ready ({len(image)} bytes)")
    except Exception as err:
        ctx.logger.warning(f"Image failed, posting text only: {err}")

    post_id = publish_linkedin(text, image)
    ctx.storage.set("last_post_date", today())
    ctx.storage.set("last_post_text", text)
    ctx.storage.set("last_post_id", post_id)
    ctx.logger.info(f"Published: {post_id}")
    return f"Published to LinkedIn.\n\n{text}"


@agent.on_event("startup")
async def on_startup(ctx: Context):
    ctx.logger.info(f"LinkedIn Buddy started at {agent.address}")
    if not ASI_KEY:
        ctx.logger.warning("ASI1_API_KEY is empty - add it to .env")
    if not LINKEDIN_TOKEN or not LINKEDIN_AUTHOR:
        ctx.logger.warning(
            "LinkedIn secrets are empty - add LINKEDIN_ACCESS_TOKEN and "
            "LINKEDIN_AUTHOR_URN to .env"
        )


# ---------------------------------------------------------------------------
# 6pm daily check  (runs every 60 seconds, posts once per day)
# ---------------------------------------------------------------------------
@agent.on_interval(period=60.0)
async def daily_6pm(ctx: Context):
    now = now_local()
    if now.hour != POST_HOUR:
        return
    if ctx.storage.get("last_post_date") == today():
        return

    ctx.logger.info("It is 6pm — posting to LinkedIn")
    try:
        run_daily_post(ctx)
    except Exception as err:
        ctx.logger.error(f"Daily post failed: {err}")


# ---------------------------------------------------------------------------
# Chat Protocol  (Agentverse + ASI:One)
# ---------------------------------------------------------------------------
HELP_TEXT = (
    "I'm LinkedIn Buddy (@linkedin-buddy). "
    "I post about Fetch.ai on LinkedIn every day at 6:00 PM.\n\n"
    "You can say:\n"
    "• post now — publish today's Fetch.ai post\n"
    "• post about <topic or profile> — write and publish that\n"
    "• preview — write a post without publishing\n"
    "• preview about <topic> — draft only\n"
    "• status — last post and next schedule"
)


def create_text_chat(text: str, end_session: bool = False) -> ChatMessage:
    content = [TextContent(type="text", text=text)]
    if end_session:
        content.append(EndSessionContent(type="end-session"))
    return ChatMessage(
        timestamp=datetime.utcnow(),
        msg_id=uuid4(),
        content=content,
    )


def message_text(msg: ChatMessage) -> str:
    if hasattr(msg, "text"):
        text = msg.text()
        if text:
            return text
    text = ""
    for part in msg.content:
        if isinstance(part, TextContent):
            text += part.text
    return text


@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.now(), acknowledged_msg_id=msg.msg_id
        ),
    )

    for part in msg.content:
        if isinstance(part, StartSessionContent):
            ctx.logger.info(f"New chat session from {sender}")
            await ctx.send(sender, create_text_chat(HELP_TEXT))
            return
        if isinstance(part, EndSessionContent):
            ctx.logger.info(f"Chat session ended by {sender}")
            return

    text = message_text(msg).strip()
    text = re.sub(r"^@agent1[a-z0-9]+\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^@linkedin-buddy\s+", "", text, flags=re.IGNORECASE)
    if not text:
        return

    lowered = text.lower()
    ctx.logger.info(f"Chat from {sender}: {text}")

    try:
        if lowered in ("status", "help"):
            if lowered == "help":
                await ctx.send(sender, create_text_chat(HELP_TEXT))
                return
            last = ctx.storage.get("last_post_date") or "never"
            await ctx.send(
                sender,
                create_text_chat(
                    f"Last post: {last}\n"
                    f"Next auto-post: today {POST_HOUR}:00 "
                    f"(offset {TIMEZONE_OFFSET}h)\n"
                    f"Today's topic: {TOPICS[now_local().timetuple().tm_yday % len(TOPICS)]}"
                ),
            )
            return

        if lowered.startswith("preview"):
            topic = re.sub(r"^preview(\s+about)?\s*", "", text, flags=re.IGNORECASE).strip()
            if not topic:
                topic = TOPICS[now_local().timetuple().tm_yday % len(TOPICS)]
            post, _ = write_post(topic)
            await ctx.send(sender, create_text_chat(f"Preview (not posted):\n\n{post}"))
            return

        if lowered in ("post now", "publish") or lowered.startswith("post"):
            topic = re.sub(r"^post(\s+now)?(\s+about)?\s*", "", text, flags=re.IGNORECASE).strip()
            result = run_daily_post(ctx, topic or None)
            await ctx.send(sender, create_text_chat(result))
            return

        # Any other longer message is treated as a custom post topic
        if len(text) > 40:
            result = run_daily_post(ctx, text)
            await ctx.send(sender, create_text_chat(result))
        else:
            await ctx.send(sender, create_text_chat(HELP_TEXT))
    except Exception as err:
        ctx.logger.exception("Error handling chat")
        await ctx.send(
            sender,
            create_text_chat(f"Something went wrong: {err}"),
        )


@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


# publish_manifest=True registers AgentChatProtocol on Agentverse
agent.include(protocol, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
