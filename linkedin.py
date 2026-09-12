import re
import time
from typing import Dict, Iterable, List, Optional

import requests

from config import Mention


class LinkedInError(RuntimeError):
    pass


class LinkedInClient:
    API = "https://api.linkedin.com"

    def __init__(
        self,
        token: str,
        author_urn: str,
        version: str = "202608",
    ):
        self.token = token
        self.author_urn = author_urn
        self.version = version

    def _headers(self, content_type: str = "application/json") -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Linkedin-Version": self.version,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": content_type,
        }

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        last_response: Optional[requests.Response] = None
        for attempt in range(3):
            response = requests.request(method, url, **kwargs)
            last_response = response
            if response.status_code not in {429, 500, 502, 503, 504}:
                break
            time.sleep(2 ** attempt)

        assert last_response is not None
        if not last_response.ok:
            message = last_response.text[:500]
            if last_response.status_code == 401:
                message = (
                    "LinkedIn token is invalid or expired. Run "
                    "linkedin_setup.py again."
                )
            raise LinkedInError(
                f"LinkedIn API {last_response.status_code}: {message}"
            )
        return last_response

    def validate_credentials(self) -> Dict:
        response = self._request(
            "GET",
            f"{self.API}/v2/userinfo",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=30,
        )
        return response.json()

    def upload_image(self, image: bytes) -> str:
        response = self._request(
            "POST",
            f"{self.API}/rest/images?action=initializeUpload",
            headers=self._headers(),
            json={"initializeUploadRequest": {"owner": self.author_urn}},
            timeout=30,
        )
        value = response.json().get("value") or {}
        upload_url = value.get("uploadUrl")
        image_urn = value.get("image")
        if not upload_url or not image_urn:
            raise LinkedInError("LinkedIn returned an invalid image upload")

        self._request(
            "PUT",
            upload_url,
            headers={"Content-Type": "application/octet-stream"},
            data=image,
            timeout=120,
        )
        return image_urn

    MENTION_MARKUP = re.compile(r"@\[([^\]\n]+)\]\(urn:li:[^)]+\)")
    RAW_URN = re.compile(r"urn:li:[A-Za-z0-9]+:[A-Za-z0-9._-]+")

    @classmethod
    def clean_post_text(cls, text: str) -> str:
        """Remove API markup so URNs never appear in the published post."""
        cleaned = cls.MENTION_MARKUP.sub(r"\1", text)
        cleaned = cls.RAW_URN.sub("", cleaned)
        cleaned = re.sub(r"\\([\\[\](){}@*_~<>|#])", r"\1", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        return cleaned.strip()

    @staticmethod
    def mention_token(mention: Mention) -> str:
        return f"@{mention.name}"

    @classmethod
    def add_mentions(
        cls,
        text: str,
        mention_keys: Iterable[str],
        mentions: List[Mention],
    ) -> str:
        """Turn selected names into @Name only where they already appear.

        Longer names are replaced first via placeholders so
        ``Fetch.ai`` cannot steal characters from
        ``Fetch.ai Innovation Lab``. Names that are not present in the
        draft are left out — nothing is appended at the bottom.
        """
        selected = [
            mention
            for mention in mentions
            if mention.key in set(mention_keys)
        ]
        selected.sort(key=lambda item: len(item.name), reverse=True)
        cleaned = cls.clean_post_text(text)
        if not selected:
            return cleaned

        placeholders: List[tuple[str, str]] = []
        for index, mention in enumerate(selected):
            cleaned = re.sub(
                rf"@+{re.escape(mention.name)}",
                mention.name,
                cleaned,
            )
            if mention.name not in cleaned:
                continue
            marker = f"<<<MENTION_{index}>>>"
            cleaned = cleaned.replace(mention.name, marker, 1)
            placeholders.append((marker, cls.mention_token(mention)))

        for marker, token in placeholders:
            cleaned = cleaned.replace(marker, token)
        return cleaned

    def publish(
        self,
        text: str,
        image: Optional[bytes],
        mention_keys: Iterable[str],
        mentions: List[Mention],
        alt_text: str = "AI-generated visual for this LinkedIn post",
    ) -> str:
        commentary = self.add_mentions(text, mention_keys, mentions)
        body = {
            "author": self.author_urn,
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        if image:
            body["content"] = {
                "media": {
                    "id": self.upload_image(image),
                    "altText": alt_text[:300],
                }
            }

        response = self._request(
            "POST",
            f"{self.API}/rest/posts",
            headers=self._headers(),
            json=body,
            timeout=45,
        )
        return response.headers.get("x-restli-id", "published")
