# About MRS

*Three decades from virtual worlds to spatial intelligence*

---

## A Note to the Reader

You're looking at the source code for a server that maps geographic coordinates to URIs. It's a simple idea — deceptively so. Behind this codebase lies a thirty-year journey from the first 3D web browser to the age of autonomous agents. This is the story of how we got here, and why it matters now more than ever.

---

## 1994: A Paper in Geneva

In the winter of 1993, Mark Pesce had a problem. He'd just come off the collapse of Ono-Sendai Corporation — a VR startup named after the fictional company in William Gibson's *Neuromancer* — which had bet on turning Sega's games console into a cheap VR platform. That bet died when Sega cancelled its VR headset. But the underlying idea — that virtual reality needed to be *networked* — refused to go away.

Pesce had been electrified two years earlier by a Jaron Lanier interview in *Mondo 2000*: "VR is not the television of the future. It's the telephone of the future." Not a broadcast medium. A communication medium. That distinction split his life into before and after.

In San Francisco, Pesce found a kindred spirit in Tony Parisi — a compilers engineer who shared his obsession with networked 3D. Over beers, Pesce laid out his vision: a protocol that could bind the World Wide Web to three-dimensional space. Two hours later, Parisi was in. Their skills were perfectly complementary: Pesce knew networking and rendering, Parisi knew parsers and compilers.

By February 1994, they'd knit together three technologies: Tim Berners-Lee's `libwww` (the original web library), a 3D rendering toolkit from the English company Rendermorphics, and Parisi's custom parser. On February 2nd, they rendered their first model — a 3D banana. The first object ever displayed in a web browser from a URL. Five weeks later, they had an alpha of their browser, which they called **Labyrinth**.

But Labyrinth was only the visible part. The paper Pesce was writing — the one he'd been working toward all along — was about seventy percent something called **Cyberspace Protocol** and about thirty percent a description of the visualisation layer built on top of it. Cyberspace Protocol was a system for *permissioning space* — for binding metadata, rules, and services to geographic and virtual coordinates. The 3D browser was proof that the protocol worked.

Pesce sent a note to "this guy in Switzerland" — Tim Berners-Lee — who had been asking about VR on the web. Berners-Lee wrote back with an invitation: come present at the **First International Conference on the World Wide Web**, WWW1, in Geneva.

In May 1994, Pesce, Parisi, and Peter Kennard [presented Labyrinth](http://hyperreal.org/~mpesce/www.html) and Cyberspace Protocol to the assembled web pioneers. The demo caught the eye of Silicon Graphics, then the most powerful 3D graphics company in the world. Dave Raggett, a web standards pioneer, coined the term **VRML** — Virtual Reality Modeling Language — at a Birds of a Feather session Tim Berners-Lee had convened.

What happened next is well documented: VRML exploded. Silicon Graphics' Rikk Carey and Gavin Bell joined Pesce and Parisi. Microsoft, Netscape, Sun, and Sony piled in. VRML became an ISO standard. The 3D web was born.

What *didn't* happen is the point of this story: **everyone took the visualisation layer and ignored the permissioning protocol underneath it.**

The world wasn't ready. In 1994, GPS was still military technology. There were no smartphones. The idea of binding real-world coordinates to digital services was science fiction. So Cyberspace Protocol — the part Pesce cared about most — sat dormant for twenty-two years.

---

## 2016: Pokémon Go Changes Everything

Fast forward to the summer of 2016. Millions of people are wandering into traffic, trespassing on private property, and stumbling through cemeteries and memorials — all chasing virtual creatures overlaid on the real world through their phone cameras.

Pokémon Go didn't just prove that augmented reality worked. It proved that augmented reality *without spatial permissions* was dangerous. Niantic had no protocol for asking "is it okay to put a PokéStop here?" Property owners had no way to say "no." There was no infrastructure for space to speak for itself.

Mark Pesce recognised the moment. The use case he'd imagined in 1994 had finally arrived — not through VR headsets, but through the billion smartphones already in everyone's pockets. In September 2016, he published a new specification: the **Mixed Reality Service**.

MRS took the core of Cyberspace Protocol — bind coordinates to URIs — and reimagined it for the age of mixed reality. Three commands: `add`, `delete`, `search`. A federated architecture modeled on DNS and email. No central authority. Anyone could run a server authoritative for their own spaces.

At the first meeting of the WebVR W3C Community Group in San Jose, Tony Parisi — still Pesce's collaborator after twenty-two years — [presented the MRS proposal](https://www.w3.org/2016/06/vr-workshop/papers/W3C_WebVR_Position_Statement_Mark_Pesce.html) on Pesce's behalf. In 2017, Pesce [keynoted the Web3D conference](https://medium.com/ghvr/one-hundred-years-of-aptitude-99c90ae48431) in Brisbane, requesting the web research community join the effort. A W3C Community Group was formed. The specification was published at mixedrealityservice.org.

The vision was broad: AR permissions, drone airspace management, hazmat warnings, building access rules, hours of operation — any metadata a physical space might want to communicate. MRS would be the universal query layer. Your application asks "what's here?" and MRS returns pointers to whatever the space owner has chosen to publish.

But the timing was still slightly off. The AR headsets everyone expected to make MRS essential — Apple's, Meta's, Google's — were years away from mass adoption. WebVR standards moved slowly. The W3C group did important foundational work, but MRS remained a solution slightly ahead of its problem.

---

## 2025: The Agents Arrive

Then the world changed again. Not through headsets this time, but through intelligence.

Starting in 2023, AI agents began doing things in the physical world. Not just answering questions about coffee culture — actually booking reservations, scheduling deliveries, coordinating with robots and drones. Agents that could reason, plan, and execute multi-step operations involving real places.

These agents had a problem: **they couldn't perceive space.**

An AI agent can tell you everything about everywhere. It can summarise the history of the Sydney Opera House, explain the architecture, recommend nearby restaurants. What it cannot tell you: whether drones are allowed to deliver there, what the building's access policy is, whether there's construction blocking the entrance, or who to contact about filming permits.

This isn't a failure of intelligence. It's a failure of infrastructure. The internet was built to link *information* — documents to documents, names to addresses. Physical space remained illegible to digital systems.

MRS suddenly had its killer application. Not AR headsets. Not Pokémon. **Agents.**

An agent with MRS becomes spatially aware. It queries coordinates and gets back URIs — pointers to whatever services, permissions, and metadata the space owner has published. The agent follows those pointers. The space speaks for itself.

```
Agent: I need to plan a drone delivery to 425 George Street, Sydney.

[MRS query → coordinates -33.8688, 151.2070]
  → Sydney CBD Airspace Authority (municipal)
  → 425 George Street Building Management
  → Café Luna (ground floor tenant)

Agent: Let me check airspace permissions...
  → Drone overflight permitted below 50m, rooftop landing only

Agent: And building access...
  → Deliveries via rooftop drone port, notify concierge, no weekends before 9am

Agent: Delivery scheduled for Monday 10am, rooftop port, concierge notified.
```

No special integration with Sydney's airspace system. No bespoke API for the building. No partnership with the café. The agent just asked "what's here?" and followed the pointers. Open infrastructure. Build once, query anywhere.

---

## 2026: DNS for Space

The server in this repository is the current incarnation of MRS. It implements the core protocol:

- **Register** a space — bind a geographic volume to a service endpoint
- **Search** nearby — query coordinates, get back matching registrations
- **Release** a space — remove a registration when it's no longer needed
- **Federate** — servers peer with each other, refer queries, sync registrations

It's built on the same architectural principles as DNS and email: federated, open, nobody in charge. A city government runs an MRS server for municipal boundaries. A property developer runs one for their buildings. A drone operator runs one for airspace clearances. They all peer with each other. A single query touches all of them.

The protocol is deliberately simple. Three core operations. JSON over HTTPS. No complex state machines. No distributed consensus algorithms. Eventual consistency through a straightforward sync protocol. The real world is messy and approximate — the infrastructure that describes it should be too.

The **FOAD flag** — a privacy marker that says "this space is registered, but go away" — embodies a design principle that runs through the whole system: *not every space wants to participate in the digital economy, and that's a first-class answer.* MRS doesn't just enable spatial awareness. It enables spatial *refusal*.

---

## The Thread

There is a direct line from Pesce and Parisi's Labyrinth browser in 1994 to this Python server in 2026. The insight has never changed:

**Physical space needs a resolution service.**

Just as DNS made the web possible — you can't link to what you can't name — MRS aims to make the spatial web possible. You can't reason about what you can't query. You can't coordinate in space you can't perceive.

DNS didn't just help people find websites. It enabled everything that came after: search engines, e-commerce, social networks, the entire digital economy. It did this by solving one small problem — name resolution — and solving it in a way that was open, federated, and infinitely extensible.

MRS solves one small problem: spatial resolution. `f(coordinates) → services`. The rest — the autonomous deliveries, the smart cities, the agents that can actually navigate the world they reason about — those are what come after.

In 1994, the idea was thirty years too early. In 2016, it was a few years too early. In 2026, the agents are here, the drones are flying, and physical space still can't speak for itself.

It's time to fix that.

---

## People

MRS exists because of the work of many people across three decades:

- **Mark Pesce** — Co-inventor of VRML. Author of the original Cyberspace Protocol (1994), the Mixed Reality Service specification (2016), and the current MRS server implementation.
- **Tony Parisi** — Co-inventor of VRML. Built the first VRML parser. Presented the MRS proposal to the W3C WebVR Community Group in 2016.
- **Peter Kennard** — Co-presenter of Labyrinth at WWW1 in Geneva, 1994.
- **Owen Rowley** — Early VRML community contributor and collaborator.
- **Sir Tim Berners-Lee** — Invited Pesce to present at WWW1. Convened the VRML Birds of a Feather session.
- **Dave Raggett** — Coined the term "VRML" at WWW1.
- **Rikk Carey & Gavin Bell** (Silicon Graphics) — Contributed Open Inventor as the basis for VRML 1.0.

And the global community of VRML enthusiasts, WebVR pioneers, and spatial computing researchers who kept the idea alive across the decades when the world wasn't ready for it.

---

## Links

- [The original WWW1 paper](http://hyperreal.org/~mpesce/www.html) — Pesce's 1994 Cyberspace Protocol presentation
- [W3C Position Statement](https://www.w3.org/2016/06/vr-workshop/papers/W3C_WebVR_Position_Statement_Mark_Pesce.html) — MRS proposal for the 2016 W3C VR Workshop
- [One Hundred Years of Aptitude](https://medium.com/ghvr/one-hundred-years-of-aptitude-99c90ae48431) — Pesce's Web3D 2017 keynote
- [Voices of VR #528](http://voicesofvr.com/528-geospatial-ar-permissions-with-the-mixed-reality-service-spec/) — Interview on the history and vision of MRS
- [Agents in Space](Agents-in-Space.md) — Why AI agents need spatial awareness
- [MRS Protocol Specification](MRS-SPEC-DRAFT.md) — The current protocol draft

---

*MRS is open source under the MIT License. The protocol is open. The infrastructure is being built. The question is whether you want to help shape it.*
