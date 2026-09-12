import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

load_dotenv()

IST = timezone(timedelta(hours=5, minutes=30))

WEAK_AGENT_SEEDS = frozenset(
    {
        "",
        "change-this-seed-before-running",
        "linkedin-fetchai-poster-seed",
        "replace-with-a-unique-private-seed",
    }
)


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return int(str(raw).strip())


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def local_now(timezone_name: str) -> datetime:
    try:
        return datetime.now(ZoneInfo(timezone_name))
    except ZoneInfoNotFoundError:
        if timezone_name in {"Asia/Kolkata", "Asia/Calcutta"}:
            return datetime.now(IST)
        return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Mention:
    key: str
    name: str
    urn: str
    url: str


@dataclass(frozen=True)
class Settings:
    asi_key: str = os.getenv("ASI1_API_KEY", "")
    asi_url: str = os.getenv("ASI1_BASE_URL", "https://api.asi1.ai/v1")
    linkedin_token: str = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    linkedin_author: str = os.getenv("LINKEDIN_AUTHOR_URN", "")
    linkedin_token_expires_at: int = env_int("LINKEDIN_TOKEN_EXPIRES_AT", 0)
    linkedin_version: str = os.getenv("LINKEDIN_VERSION", "202608")
    timezone_name: str = os.getenv("TIMEZONE", "Asia/Kolkata")
    post_hour: int = env_int("POST_HOUR", 18)
    post_minute: int = env_int("POST_MINUTE", 0)
    agent_name: str = os.getenv("AGENT_NAME", "LinkedIn Buddy")
    agent_handle: str = os.getenv("AGENT_HANDLE", "linkedin-buddy")
    agent_seed: str = os.getenv("AGENT_SEED", "change-this-seed-before-running")
    agent_port: int = env_int("AGENT_PORT", 8001)
    allow_insecure_seed: bool = env_bool("ALLOW_INSECURE_SEED", False)
    image_size: str = os.getenv("IMAGE_SIZE", "1024x1024").strip() or "1024x1024"
    image_output_size: int = env_int("IMAGE_OUTPUT_SIZE", 1200)
    image_retries: int = env_int("IMAGE_RETRIES", 3)
    require_image_on_publish: bool = env_bool("REQUIRE_IMAGE_ON_PUBLISH", True)

    def now(self) -> datetime:
        return local_now(self.timezone_name)

    def has_weak_seed(self) -> bool:
        return self.agent_seed.strip() in WEAK_AGENT_SEEDS

    def mentions(self) -> List[Mention]:
        return [
            Mention(
                key="fetch",
                name="Fetch.ai",
                urn=os.getenv(
                    "FETCH_AI_URN", "urn:li:organization:27233415"
                ),
                url="https://www.linkedin.com/company/fetch-ai/",
            ),
            Mention(
                key="lab",
                name="Fetch.ai Innovation Lab",
                urn=os.getenv(
                    "FETCH_AI_LAB_URN", "urn:li:organization:103686899"
                ),
                url=(
                    "https://www.linkedin.com/company/"
                    "fetch-ai-innovation-lab/"
                ),
            ),
            Mention(
                key="sana",
                name="Sana Wajid",
                # Person tags are opt-in. Leave empty unless you have consent
                # to mention this person from your account.
                urn=os.getenv("SANA_WAJID_URN", "").strip(),
                url=(
                    "https://www.linkedin.com/in/"
                    "sana-wajid-ab1b6169/"
                ),
            ),
        ]


# Organizations only by default. Person tags stay opt-in via the create form.
DEFAULT_MENTION_KEYS = ["fetch", "lab"]

SETTINGS = Settings()
