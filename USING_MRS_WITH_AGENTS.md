# Using MRS with AI Agents

*Give your agent spatial awareness in five minutes*

---

## The Problem

Your AI agent is smart. It can reason, plan, and execute complex tasks. But ask it to do anything involving a physical location and it hits a wall.

"Can a drone deliver to this address?" — It doesn't know.
"What are the building's access hours?" — It can't find out.
"Is photography allowed here?" — It has no way to ask.

The agent knows *about* places (from its training data). It doesn't know what's *at* places right now — what services exist, what rules apply, who controls the space.

MRS fixes this. It gives your agent a single skill that lets it query any coordinates on Earth and get back live, authoritative answers from the people who control those spaces.

---

## What the MRS Skill Does

The MRS agent skill is a capability document — a structured file that teaches your agent how to talk to MRS servers. Once loaded, your agent can:

- **Search** any location for registered services, permissions, and metadata
- **Register** spaces on behalf of users (bind a location to a service endpoint)
- **Update** and **release** registrations
- **Follow referrals** across federated servers for comprehensive coverage

The most common operation — searching — requires no authentication. Your agent can start querying locations immediately.

### Before MRS

```
User: Can I fly a drone to deliver a package to 425 George Street, Sydney?

Agent: I can tell you about drone regulations in Australia generally.
       The CASA rules say... [generic information from training data]
       I'd recommend checking with local authorities.
```

### After MRS

```
User: Can I fly a drone to deliver a package to 425 George Street, Sydney?

Agent: Let me check what's registered at those coordinates.

[Searches MRS → finds 3 registrations]
  → Sydney CBD Airspace Authority: overflight permitted below 50m
  → 425 George Street Building Management: rooftop drone port active,
    notify concierge, no deliveries before 9am on weekends
  → Ground floor tenant (Café Luna): no drone-relevant info

Agent: Yes, drone delivery is allowed. The building has a rooftop
       drone port. You'll need to stay below 50m altitude and notify
       the concierge on arrival. If this is a weekend, deliveries
       can't start before 9am. Want me to schedule it?
```

The difference: real, current, authoritative information from the people who control the space — not a guess from training data.

---

## How to Add the Skill

### Step 1: Get the Skill File

The skill definition lives in this repository at [`docs/AGENT_SKILL.md`](docs/AGENT_SKILL.md). It contains everything your agent needs: endpoint descriptions, request/response schemas, error handling, common workflows, and practical reference data.

You can grab it from the canonical MRS server:

```bash
curl -O https://owen.iz.net/skill/
```

Or directly from the repo:

```bash
curl -O https://raw.githubusercontent.com/mpesce/mrs-server/main/docs/AGENT_SKILL.md
```

Or just copy the file from your local clone.

### Step 2: Load It Into Your Agent

How you load the skill depends on your agent framework. Here are the most common approaches:

#### Claude (via Claude Code or API)

Place `AGENT_SKILL.md` in your project root or a `skills/` directory. Claude Code will pick it up automatically. For the API, include it in your system prompt or as a document attachment.

```python
# Claude API — include as part of the system prompt
from anthropic import Anthropic

client = Anthropic()
skill = open("AGENT_SKILL.md").read()

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    system=f"You have the following skill available:\n\n{skill}",
    messages=[{"role": "user", "content": "What services are near the Sydney Opera House?"}]
)
```

#### OpenAI (GPT-4, etc.)

Include the skill file content in your system message:

```python
from openai import OpenAI

client = OpenAI()
skill = open("AGENT_SKILL.md").read()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": f"You have the following skill:\n\n{skill}"},
        {"role": "user", "content": "What services are near the Sydney Opera House?"}
    ]
)
```

#### LangChain / LangGraph

Use the skill as a tool description, or wrap MRS calls as a custom tool:

```python
from langchain_core.tools import tool
import httpx

@tool
def mrs_search(lat: float, lon: float, range_m: float = 1000) -> dict:
    """Search for services registered near a geographic location using MRS."""
    response = httpx.post(
        "https://owen.iz.net/search",
        json={"location": {"lat": lat, "lon": lon}, "range": range_m}
    )
    return response.json()
```

#### Any Framework with HTTP Access

If your agent can make HTTP requests, it can use MRS. The skill file teaches it the endpoints. The simplest integration is just giving your agent the skill document and letting it make `curl`-style calls:

```
POST https://owen.iz.net/search
Content-Type: application/json

{"location": {"lat": -33.8568, "lon": 151.2153}, "range": 1000}
```

No API keys. No SDK. No setup. Just HTTPS and JSON.

### Step 3: Point at a Server

The canonical public MRS server is:

```
https://owen.iz.net
```

This is the default in the skill file. Your agent can start querying it immediately — search requires no authentication.

For write operations (registering spaces), your agent will need an account:

```bash
curl -X POST https://owen.iz.net/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "myagent", "password": "secure-password", "email": "you@example.com"}'
```

This returns a bearer token that lasts one week. The skill file teaches your agent how to handle token refresh automatically.

---

## What Your Agent Can Do With MRS

### Read Operations (no auth needed)

**Search nearby.** The bread and butter. Your agent queries coordinates and gets back everything registered there — services, permissions, metadata, whatever space owners have published.

```
POST /search
{"location": {"lat": 48.8584, "lon": 2.2945}, "range": 500}
```

**Discover the federation.** Your agent can explore the MRS network — find peer servers, learn what regions they cover, build a map of the spatial web.

```
GET /.well-known/mrs
```

**Follow referrals.** Search results include referrals to other MRS servers. A spatially-aware agent follows them automatically for comprehensive coverage, deduplicating by registration ID.

### Write Operations (auth needed)

**Register a space.** Your agent can bind a geographic area to a service endpoint on behalf of a user. Useful for publishing spatial metadata — operating hours, access policies, hazard warnings, contact information.

**Update a registration.** Change the service endpoint, adjust the radius, toggle the FOAD privacy flag.

**Release a registration.** Remove it when it's no longer needed. This propagates across the federation via tombstones.

---

## Architecture in Brief

MRS is federated — like email, like DNS. There's no central authority. Anyone can run a server.

```
┌──────────┐     ┌──────────────────┐     ┌──────────┐
│  Agent   │────▶│  MRS Server      │────▶│ Service  │
│          │◀────│  (owen.iz.net)   │     │ Endpoint │
└──────────┘     └──────────────────┘     └──────────┘
                   │            ▲
            referral│            │ sync
                   ▼            │
                 ┌──────────────────┐
                 │  Peer Server     │
                 │  (other.mrs.net) │
                 └──────────────────┘
```

1. Your agent searches an MRS server for a location.
2. The server returns matching registrations and referrals to peers.
3. Your agent follows the referrals (if it wants comprehensive results).
4. Each registration contains a `service_point` URL — your agent fetches that to get the actual metadata about the space.

MRS doesn't store the metadata itself. It stores *pointers*. The actual content — hours, permissions, policies, hazard data — lives at the service point, controlled by the space owner. MRS just helps your agent find it.

---

## Running Your Own Server

If you want to register spaces authoritatively (rather than on someone else's server), you can run your own MRS server. It takes about 90 seconds:

```bash
git clone https://github.com/mpesce/mrs-server.git
cd mrs-server
./scripts/bootstrap.sh
./scripts/verify.sh
```

See [QUICKSTART.md](QUICKSTART.md) for a walkthrough and [INSTALL.md](INSTALL.md) for production deployment.

Your server can peer with the public federation:

```bash
export MRS_BOOTSTRAP_PEERS='["https://owen.iz.net"]'
```

Now searches on your server include referrals to the public network, and vice versa. Your registrations become discoverable globally.

---

## Key Concepts for Agent Developers

**Registrations are spatial, not textual.** You search by coordinates and radius, not by name or keyword. If your user says "the Sydney Opera House," you need to geocode that to coordinates first (your agent probably already knows how).

**Results are sorted most-specific first.** A 50-meter registration (a building) comes before a 50-kilometer one (a city district). This means the first result is usually the most relevant.

**FOAD means "go away."** Some registrations have `foad: true` — the owner has claimed the space but explicitly doesn't want to be found. These never appear in search results. Your agent will never see them, and that's by design.

**Referrals are hints, not guarantees.** When a server refers your agent to a peer, the peer might have additional results or it might not. Your agent should follow referrals when comprehensive coverage matters, skip them when speed matters.

**Federation means eventual consistency.** If a registration was just created on one server, it might take a few minutes to propagate to peers. For most use cases this doesn't matter. If it does, query the authoritative server directly (check the `origin_server` field).

**Tokens expire, plan for it.** Bearer tokens last one week by default. If your agent gets a `401`, it should re-authenticate with `/auth/login` and retry. The skill file includes this in its error handling guidance.

---

## Further Reading

- [**Agents in Space**](Agents-in-Space.md) — The vision: why AI agents need spatial awareness
- [**Agent Skill Reference**](docs/AGENT_SKILL.md) — The complete skill file your agent consumes
- [**MRS Protocol Spec**](MRS-SPEC-DRAFT.md) — The full protocol specification
- [**About MRS**](ABOUT.md) — The thirty-year history from VRML to spatial agents
- [**Quick Start**](QUICKSTART.md) — Run your own MRS server in 90 seconds
