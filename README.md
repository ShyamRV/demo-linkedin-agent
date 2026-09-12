# LinkedIn Buddy

An interactive Fetch.ai agent that creates **highly professional** LinkedIn
content with ASI:One, shows a review card, waits for approval, generates an
image, and publishes to a personal LinkedIn profile.

Scheduled drafts are **never published without approval**.

Repository:
[github.com/ShyamRV/demo-linkedin-agent](https://github.com/ShyamRV/demo-linkedin-agent)

License: [MIT](LICENSE)

## Features

- ASI:One post and image generation
- Agentverse Agent Chat Protocol
- Interactive create, settings, and review cards
- Edit, regenerate, approve, or cancel a draft
- Persistent preferences, drafts, schedule, and post history
- Daily approval-first drafts with a claimed schedule owner
- Pause, resume, and change the schedule through chat
- Current LinkedIn Images and Posts APIs (`202608`)
- Retries for rate limits and temporary LinkedIn failures
- Safe `@Name` mentions without raw `urn:li:...` markup in the feed
- Poster framing that crops and covers common model corner badges

## LinkedIn mentions

By default, drafts may mention these **organizations** when the exact name
already appears in the post text:

- **Fetch.ai** → `@Fetch.ai`
- **Fetch.ai Innovation Lab** → `@Fetch.ai Innovation Lab`

Important limits for a personal **Share on LinkedIn** app:

- The agent writes visible `@Name` text.
- It does **not** insert Little Text `@[Name](urn:...)` into the post, because
  that markup has been showing up as raw code in the feed.
- These are not guaranteed blue notify-tags. Treat them as readable mentions.

**Person mentions are opt-in.** Sana Wajid is available in the create form but
unchecked by default. Do not enable person mentions unless you intend to
mention that person from your account. Leave `SANA_WAJID_URN` empty unless you
have a reason and consent to configure it.

Names that do not appear in the draft are **not** appended at the bottom.

Relevant profiles:

- [Fetch.ai](https://www.linkedin.com/company/fetch-ai/)
- [Fetch.ai Innovation Lab](https://www.linkedin.com/company/fetch-ai-innovation-lab/)
- [Sana Wajid](https://www.linkedin.com/in/sana-wajid-ab1b6169/) (opt-in only)

## Project structure

```text
agent.py             Agentverse handlers, workflow, schedule, storage
cards.py             Interactive Agentverse cards
config.py            Environment settings and mention definitions
content.py           ASI:One post and image generation
linkedin.py          LinkedIn Images and Posts API
linkedin_setup.py    One-time LinkedIn login helper
visual.py            Poster framing, mascot, and model-badge scrubbing
tests/               Unit tests that never publish to LinkedIn
.env.example         Configuration template
requirements.txt     Pinned Python dependencies
LICENSE              MIT license
CONTRIBUTING.md      Contribution and security notes
.github/workflows/   CI unit tests
```

## 1. Create the required accounts

### Agentverse

Create an account at [agentverse.ai](https://agentverse.ai).

### ASI:One

Create an API key at [asi1.ai/developer](https://asi1.ai/developer).

### LinkedIn

1. Create an app at
   [linkedin.com/developers/apps](https://www.linkedin.com/developers/apps).
2. Enable:
   - **Sign In with LinkedIn using OpenID Connect**
   - **Share on LinkedIn**
3. Open **Auth** and copy the Client ID and Client Secret.
4. Add this exact redirect URL:

```text
http://localhost:8000/callback
```

It must use `http`, `localhost`, port `8000`, and no trailing slash.

## 2. Download the project

Windows PowerShell:

```powershell
git clone https://github.com/ShyamRV/demo-linkedin-agent.git
cd demo-linkedin-agent
```

Mac Terminal:

```bash
git clone https://github.com/ShyamRV/demo-linkedin-agent.git
cd demo-linkedin-agent
```

## 3. Install Python and packages

Python 3.10 or newer is required.

Windows:

```powershell
python --version
python -m pip install -r requirements.txt
```

Mac:

```bash
python3 --version
python3 -m pip install -r requirements.txt
```

If the version is below 3.10, install Python from
[python.org/downloads](https://www.python.org/downloads/).

## 4. Create `.env`

Windows:

```powershell
copy .env.example .env
```

Mac:

```bash
cp .env.example .env
```

Fill the new `.env`:

```env
ASI1_API_KEY=your_asi_one_key
ASI1_BASE_URL=https://api.asi1.ai/v1
IMAGE_SIZE=1024x1024
IMAGE_OUTPUT_SIZE=1200
IMAGE_RETRIES=3
REQUIRE_IMAGE_ON_PUBLISH=1

LINKEDIN_ACCESS_TOKEN=
LINKEDIN_AUTHOR_URN=
LINKEDIN_TOKEN_EXPIRES_AT=0
LINKEDIN_VERSION=202608

POST_HOUR=18
POST_MINUTE=0
TIMEZONE=Asia/Kolkata

AGENT_NAME=LinkedIn Buddy
AGENT_HANDLE=linkedin-buddy
AGENT_SEED=replace-with-a-unique-private-seed
AGENT_PORT=8001
ALLOW_INSECURE_SEED=0

FETCH_AI_URN=urn:li:organization:27233415
FETCH_AI_LAB_URN=urn:li:organization:103686899
SANA_WAJID_URN=

LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/callback
```

Use a unique `AGENT_SEED`. Anyone using the same seed gets the same agent
identity. The agent **refuses to start** with a placeholder seed unless you set
`ALLOW_INSECURE_SEED=1` for a local throwaway demo.

`.env` is ignored by Git and must never be committed.

## 5. Get the LinkedIn token

Windows:

```powershell
python linkedin_setup.py
```

Mac:

```bash
python3 linkedin_setup.py
```

The script prints a LinkedIn login URL:

1. Open it and approve access.
2. LinkedIn redirects to
   `http://localhost:8000/callback?code=...`.
3. The page not loading is expected.
4. Copy only the value after `code=`.
5. Paste it into the terminal and press Enter.

The script saves `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_AUTHOR_URN`, and the token
expiration time in `.env`. It prints only a **masked** token preview, never the
full secret.

LinkedIn tokens usually expire after about 60 days. Run the setup script again
when the token expires.

## 6. Run tests

Tests do not call LinkedIn or publish anything.

Windows:

```powershell
python -m unittest discover -s tests -v
```

Mac:

```bash
python3 -m unittest discover -s tests -v
```

## 7. Run locally

Windows:

```powershell
python agent.py
```

Mac:

```bash
python3 agent.py
```

Open the Agent Inspector URL printed in the terminal. Select
**Connect → Mailbox** so Agentverse can deliver chat messages.

Then send `claim` once so scheduled drafts go to you, not the next stranger who
chats with a public agent.

## 8. Interactive workflow

Open **Chat with Agent** and send:

```text
create
```

The form asks for:

- Topic
- Tone
- Audience
- Objective
- Optional source URL
- Which entities to mention (person mentions stay unchecked by default)

After generation, the review card provides:

- **Approve & publish**
- **Apply edit**
- **Regenerate**
- **Cancel**

Publishing cannot happen until **Approve & publish** is selected.

## 9. Commands

```text
create
preview about Agentverse and ASI:One
settings
status
history
mentions
claim
schedule 18:00
pause
resume
```

`post about ...` also creates a draft for approval. It does not publish
immediately.

Examples:

```text
preview about the latest Agentverse developer tools
```

```text
post about Sana Wajid and the Fetch.ai Innovation Lab
```

The second example creates a draft. Enable the Sana checkbox in the create form
only if you intentionally want that person mention.

## 10. Scheduling

The default schedule is 6:00 PM in `Asia/Kolkata`.

```text
schedule 17:30
```

This changes the daily draft time to 5:30 PM. The timezone comes from `.env`.

At that time the agent:

1. Generates one draft.
2. Saves it in Agent Storage.
3. Sends the **schedule owner** an interactive review card.
4. Waits for approval.

Ownership rules:

- The first person who chats becomes the owner automatically.
- Later chatters do not steal ownership.
- Send `claim` to take ownership intentionally.

Use `pause` and `resume` to control scheduled drafts.

## 11. Deploy to Agentverse

Create a **Hosted Agent**, not External Integration.

1. Open [agentverse.ai](https://agentverse.ai).
2. Select **Launch an Agent**.
3. Choose a blank Hosted Agent.
4. In **Build**, create these files and copy their contents:
   - `agent.py`
   - `cards.py`
   - `config.py`
   - `content.py`
   - `linkedin.py`
   - `visual.py`
5. In **Secrets**, add the values from `.env`.
6. Click **Run**.

Agentverse injects ASI:One credentials for hosted agents, but explicitly adding
your own ASI:One key is also supported.

If Agentverse asks for an **Endpoint URL**, you selected External Integration.
Go back and choose a Hosted Agent. `localhost` is not a public endpoint.

## 12. Agentverse listing

Use:

```text
Name: LinkedIn Buddy
Handle: @linkedin-buddy
Keywords: linkedin, fetch.ai, asi:one, uagents, content, social media
```

Description:

```text
Approval-first LinkedIn assistant that creates posts and images with ASI:One,
supports interactive review cards, scheduled drafts, and Fetch.ai ecosystem
mentions.
```

## How mentions work

1. The draft writer includes organization or person names as plain text.
2. On publish, LinkedIn Buddy converts matching selected names to `@Name`.
3. Longer names are handled first so `Fetch.ai Innovation Lab` is not broken by
   a shorter `Fetch.ai` replacement.
4. Selected mentions that are missing from the draft are skipped, not appended.
5. Raw Little Text / URN markup is stripped if it ever appears in model output.

Check configuration through chat:

```text
mentions
```

## Images

Every approved publish generates and uploads a high-quality image by default.

ASI:One generates a full square scene. `visual.py` then builds a **full-bleed**
LinkedIn creative:

- keeps most of the artwork (light corner cleanup only)
- cover-fits to `IMAGE_OUTPUT_SIZE` (default 1200×1200) without stretching
- applies a subtle clarity pass
- adds a soft bottom gradient, headline, and one small mascot
- validates minimum size before upload
- retries up to `IMAGE_RETRIES` times if generation is weak or fails

`REQUIRE_IMAGE_ON_PUBLISH=1` (default) blocks the LinkedIn post if a strong
image cannot be produced. Set it to `0` only if you intentionally want
text-only fallback.

Prompts ask for premium, sharp, cinematic compositions instead of dumping the
entire post into the image request. Model corner badges are reduced best-effort;
always preview before approving a public post.

## Troubleshooting

- **`redirect_uri does not match`** — add
  `http://localhost:8000/callback` exactly in the LinkedIn app.
- **Callback page does not load** — expected; copy the `code` from the URL.
- **401 from LinkedIn** — token expired; run `linkedin_setup.py` again.
- **403 from LinkedIn** — the app lacks the required LinkedIn product/scope.
- **Refusing to start with placeholder AGENT_SEED** — set a unique seed, or use
  `ALLOW_INSECURE_SEED=1` for a local demo only.
- **Chat does not respond locally** — keep the agent running and connect its
  mailbox from the Inspector.
- **Scheduled draft does not arrive** — send `claim`, then check that scheduling
  is not paused.
- **Mentions look like code** — restart the agent; posts should show `@Name` only.
- **Agent identity changed** — `AGENT_SEED` changed.
- **Almanac contract funds warning** — safe to ignore for local testing.

## Security

- Never commit `.env`.
- Never paste API keys into source code, chat, or screenshots.
- Use a unique agent seed.
- Rotate any secret accidentally shown in chat, screenshots, or recordings.
- `linkedin_setup.py` masks tokens in terminal output; keep it that way.
- Chat errors are sanitized; full details stay in agent logs.
- Person mentions stay opt-in for open-source clones.
- Test with `preview` before approving a real post.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentation

- [Agentverse](https://agentverse.ai)
- [ASI:One developer portal](https://asi1.ai/developer)
- [Agent Chat Protocol](https://docs.agentverse.ai/documentation/getting-started/enable-chat-protocol)
- [Interactive cards](https://docs.agentverse.ai/documentation/advanced-usages/agent-driven-interactive-cards)
- [LinkedIn Posts API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2026-08)
- [LinkedIn Images API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/images-api?view=li-lms-2026-06)
