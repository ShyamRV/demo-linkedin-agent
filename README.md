# LinkedIn Buddy

Workshop guide: build a Fetch.ai agent that writes a LinkedIn post with **ASI:One**, generates an image with **ASI:One**, and publishes it every day at **6:00 PM IST**.

You can chat with it on Agentverse / ASI:One using the **Chat Protocol**.

Works on **Windows** and **Mac**. Use the command for your computer.

Repo: [github.com/ShyamRV/demo-linkedin-agent](https://github.com/ShyamRV/demo-linkedin-agent)

---

## Before you start

| You use | Open this app |
| --- | --- |
| **Windows** | PowerShell |
| **Mac** | Terminal |

On Windows, `python` is the usual command.  
On Mac, `python3` is the usual command.

If a command fails, try the other one (`python` vs `python3`).

---

## What you will build

```text
You (chat)  -->  LinkedIn Buddy (uAgent)
                      |
                      +--> ASI:One writes the post
                      +--> ASI:One generates an image
                      +--> LinkedIn API publishes it
                      +--> every day at 6:00 PM it posts by itself
```

| Piece | What it does |
| --- | --- |
| **uAgents** | Agent framework (Fetch.ai) |
| **Agentverse** | Host / discover / chat with the agent |
| **Chat Protocol** | Lets ASI:One and Agentverse talk to the agent |
| **ASI:One** (`asi1.ai`) | Writes the post + generates the image |
| **LinkedIn UGC API** | Publishes the post on your profile |

---

## Accounts you need (create these first)

Do these **before** writing any code.

### 1. Fetch.ai / Agentverse

1. Open [agentverse.ai](https://agentverse.ai)
2. Sign up / log in
3. Keep this tab open

### 2. ASI:One API key

1. Open [asi1.ai](https://asi1.ai) and sign in
2. Go to [asi1.ai/developer](https://asi1.ai/developer)
3. Create an API key
4. Copy it. It looks like `sk_...`
5. You will paste it into `.env` as `ASI1_API_KEY`

Hosted agents on Agentverse already get this key. You still need it for **local** runs.

### 3. LinkedIn Developer App

1. Open [linkedin.com/developers/apps](https://www.linkedin.com/developers/apps)
2. Click **Create app**
3. Add a name, LinkedIn page, and logo
4. Open **Products** and enable:
   - **Sign In with LinkedIn using OpenID Connect**
   - **Share on LinkedIn**
5. Open **Auth**
6. Copy **Client ID** and **Client Secret**
7. Under **Authorized redirect URLs**, add exactly:

```text
http://localhost:8000/callback
```

Must match exactly:

- `http` not `https`
- `localhost` not `127.0.0.1`
- no slash at the end
- port `8000`

Wrong URL = `The redirect_uri does not match the registered value`.

---

## Files in this project

| File | Purpose |
| --- | --- |
| `agent.py` | The whole agent. Paste this into Agentverse **Build**. |
| `.env` | Your secrets. **Do not share this file.** |
| `.env.example` | Empty template of the same keys |
| `linkedin_setup.py` | One-time script that gets the LinkedIn token |
| `requirements.txt` | Python packages |
| `README.md` | This workshop guide |

---

## Step 1 — Get the code

**Windows**

```powershell
git clone https://github.com/ShyamRV/demo-linkedin-agent.git
cd demo-linkedin-agent
```

**Mac**

```bash
git clone https://github.com/ShyamRV/demo-linkedin-agent.git
cd demo-linkedin-agent
```

No Git? Download the ZIP from GitHub, unzip it, then open that folder in your terminal.

---

## Step 2 — Check Python (3.10 or newer)

This agent needs **Python 3.10+**.

**Windows**

```powershell
python --version
```

**Mac**

```bash
python3 --version
```

You should see `Python 3.10`, `3.11`, or `3.12`.

If you see `3.8`, `3.9`, or `not found`, install Python from [python.org/downloads](https://www.python.org/downloads/). On the Windows installer, tick **Add python.exe to PATH**.

---

## Step 3 — Install packages

**Windows**

```powershell
python -m pip install -r requirements.txt
```

**Mac**

```bash
python3 -m pip install -r requirements.txt
```

This installs: `uagents`, `openai`, `requests`, `python-dotenv`.

---

## Step 4 — Create `.env`

**Windows**

```powershell
copy .env.example .env
```

**Mac**

```bash
cp .env.example .env
```

Open `.env` in any editor and fill these values:

```env
# ASI:One  — from https://asi1.ai/developer
ASI1_API_KEY=sk_your_key_here
ASI1_BASE_URL=https://api.asi1.ai/v1

# LinkedIn  — leave these empty until Step 5
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_AUTHOR_URN=

# 18 = 6pm, 5.5 = India (IST)
POST_HOUR=18
TIMEZONE_OFFSET=5.5

# Agent identity
AGENT_NAME=LinkedIn Buddy
AGENT_HANDLE=linkedin-buddy
AGENT_SEED=linkedin-fetchai-poster-seed
AGENT_PORT=8001

# LinkedIn app  — from LinkedIn Developers → Auth
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/callback
```

Handle must be `linkedin-buddy` (with a hyphen).  
Do **not** use `linkedin buddy` (space). Agentverse will not accept that.

Do not put real secrets on GitHub.

---

## Step 5 — Get the LinkedIn token

This login is one time. The script writes two values into `.env`:

- `LINKEDIN_ACCESS_TOKEN` — lets the agent post as you
- `LINKEDIN_AUTHOR_URN` — `urn:li:person:xxxxxxxx`

### 5.1 Run the script

**Windows**

```powershell
python linkedin_setup.py
```

**Mac**

```bash
python3 linkedin_setup.py
```

### 5.2 Log in

The script prints a URL. Open it, log in to LinkedIn, click **Allow**.

### 5.3 Copy the code

LinkedIn opens a page like:

```text
http://localhost:8000/callback?code=AQS...
```

The page **will not load**. That is normal.

Copy only the part after `code=` (stop before `&` if you see one).

Paste it into the terminal at `Paste the code here:` and press Enter.

The code expires in a few minutes. If it fails, run the script and log in again.

### 5.4 Check `.env`

You should now see:

```env
LINKEDIN_ACCESS_TOKEN=AQV...
LINKEDIN_AUTHOR_URN=urn:li:person:xxxxxxxx
```

The token lasts about **60 days**. If posting starts failing, run `linkedin_setup.py` again.

To post as a company page, use `urn:li:organization:YOUR_ID`.

---

## Step 6 — Run the agent on your computer

**Windows**

```powershell
python agent.py
```

**Mac**

```bash
python3 agent.py
```

Good logs look like this:

```text
INFO: [LinkedIn Buddy]: Starting agent with address: agent1q...
INFO: [LinkedIn Buddy]: Agent inspector available at https://agentverse.ai/inspect/?uri=...
INFO: [LinkedIn Buddy]: Starting server on http://0.0.0.0:8001
INFO: [LinkedIn Buddy]: Manifest published successfully: AgentChatProtocol
```

Leave this terminal open. Do not close it.

| Warning | What it means |
| --- | --- |
| `I do not have enough funds to register on Almanac contract` | Safe to ignore |
| `LinkedIn secrets are empty` | Finish Step 5, then restart |
| `ASI1_API_KEY is empty` | Add the ASI:One key to `.env`, then restart |

---

## Step 7 — Connect the mailbox (needed for chat)

A local agent cannot receive Agentverse / ASI:One chat until the mailbox is connected.

1. Copy the **Agent inspector** URL from the terminal
2. Open it in a browser (agent must still be running)
3. Click **Connect**
4. Choose **Mailbox**

Then use **Chat with Agent** on Agentverse.

---

## Step 8 — Talk to the agent

Use **Chat with Agent** on Agentverse, or ASI:One with **`@linkedin-buddy`**.

| You type | What happens |
| --- | --- |
| `help` | Shows commands |
| `status` | Last post + next 6pm slot |
| `preview` | Draft today's post (does **not** publish) |
| `preview about uAgents` | Draft about that topic |
| `post now` | Write, make image, publish today's post |
| `post about <topic>` | Write, make image, publish that topic |

**Try `preview` first.** `post now` and `post about` publish for real.

```text
preview about Fetch.ai Agentverse and ASI:One
```

```text
post about Fetch.ai Agentverse and ASI:One
```

You can also paste a LinkedIn profile after `post about`.

---

## Step 9 — Host on Agentverse

Use a **Hosted Agent**. Do not use External Integration unless you have a public HTTPS URL.

1. Go to [agentverse.ai](https://agentverse.ai)
2. Click **Launch an Agent**
3. Choose **Generate Agent** or a **blank Hosted Agent**
4. Do **not** choose External Integration (that asks for an Endpoint URL)
5. Open **Build** and paste all of `agent.py`
6. Open **`.env` / Secrets** and paste at least:
   - `LINKEDIN_ACCESS_TOKEN`
   - `LINKEDIN_AUTHOR_URN`
   - `POST_HOUR=18`
   - `TIMEZONE_OFFSET=5.5`
7. Click **Run**

Hosted agents already get `ASI1_API_KEY`. Extra local settings like `port` and `mailbox` are ignored there. That is normal.

### What is Agent Endpoint URL?

If you see that field, you chose the **external** path by mistake.

It wants a public server address, for example:

```text
https://your-server.com:8000/submit
```

`localhost` will not work. Go back and create a **Hosted Agent**.

---

## Step 10 — Agentverse profile

| Field | Value |
| --- | --- |
| **Name** | LinkedIn Buddy |
| **Handle** | `@linkedin-buddy` (no space) |
| **Keywords** | fetch.ai, linkedin, uagents, agentverse, asi:one, daily post, linkedin-buddy |
| **Description** | Posts about Fetch.ai on LinkedIn every day at 6pm. Uses ASI:One for text and images. |
| **README** | LinkedIn Buddy writes and publishes a daily Fetch.ai LinkedIn post. Say `preview`, `post now`, or `post about <topic>`. |

ASI:One can then find it as **`@linkedin-buddy`**.

---

## How the agent works

1. **`agent.py` is the whole agent.** One file, easy to paste into Agentverse.
2. **`.env` holds secrets.** Local runs load it automatically. On Agentverse, use Secrets.
3. **Chat Protocol** is enabled with `publish_manifest=True`. That is why it shows as `AgentChatProtocol`.
4. **ASI:One** writes the text and creates the image.
5. **LinkedIn** uploads the image and publishes the post.
6. Every minute the agent checks the clock. At **6:00 PM** it posts once per day.
7. Chat can also trigger `preview`, `post now`, or `post about ...` any time.

---

## Restart after you change `.env`

Stop the agent with `Ctrl + C`, then run `agent.py` again.

**Windows**

```powershell
python agent.py
```

**Mac**

```bash
python3 agent.py
```

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `python` not found on Mac | Use `python3` |
| `python3` not found on Windows | Use `python` |
| `python` is 3.8 | Install Python 3.12 from python.org. On Windows, tick **Add to PATH** |
| `linkedin_setup.py is not recognized` (Windows) | Run `python linkedin_setup.py` from the project folder |
| `Permission denied` (Mac) | Run `python3 linkedin_setup.py` |
| `redirect_uri does not match` | Add `http://localhost:8000/callback` exactly in the LinkedIn app |
| Localhost page will not load after LinkedIn login | Normal. Copy `code=` from the address bar |
| Code expired | Run the setup script and log in again |
| Chat does not respond | Agent must be running. Local agents also need **Connect → Mailbox** |
| Agent only replies with help | Say `post about ...` or `post now`. Use `@linkedin-buddy` (hyphen) |
| `LinkedIn secrets are empty` | Finish Step 5, then restart |
| Endpoint URL required | You created an External agent. Create a Hosted Agent |
| 401 from LinkedIn | Token expired. Run `linkedin_setup.py` again |
| Almanac contract funds warning | Safe to ignore |

---

## Workshop checklist

- [ ] Agentverse account
- [ ] ASI:One API key in `.env`
- [ ] LinkedIn app with OpenID + Share on LinkedIn
- [ ] Redirect URL `http://localhost:8000/callback`
- [ ] Client ID + Secret in `.env`
- [ ] `linkedin_setup.py` wrote token + URN
- [ ] Python 3.10+ and packages installed
- [ ] `agent.py` is running
- [ ] Inspector → Connect → Mailbox
- [ ] `preview` works
- [ ] Hosted Agent on Agentverse with the same secrets
- [ ] Name **LinkedIn Buddy**, handle **`@linkedin-buddy`**

---

## Useful links

- Agentverse: [agentverse.ai](https://agentverse.ai)
- ASI:One keys: [asi1.ai/developer](https://asi1.ai/developer)
- Chat Protocol: [docs.agentverse.ai](https://docs.agentverse.ai/documentation/getting-started/enable-chat-protocol)
- LinkedIn apps: [linkedin.com/developers/apps](https://www.linkedin.com/developers/apps)
- This repo: [github.com/ShyamRV/demo-linkedin-agent](https://github.com/ShyamRV/demo-linkedin-agent)
