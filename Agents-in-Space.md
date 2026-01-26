# Agents in Space!!!

*Or: Why Your AI Assistant Doesn't Know What's Next Door*

---

## The Problem No One Talks About

Your AI agent is brilliant. It can write code, analyze documents, plan your calendar, and debate philosophy. Ask it about the café around the corner and it'll happily tell you about coffee culture, brewing methods, and the history of espresso.

What it *can't* tell you: whether that café is open right now. If there's construction blocking the entrance. Whether drones are allowed to deliver to that address. What the building's policy is on photography.

This isn't a failure of intelligence. It's a failure of *infrastructure*.

The internet was built to link *information*. Documents point to documents. Names resolve to addresses. But physical space? The real world you actually live in? It's almost entirely illegible to AI systems.

Your agent knows everything about everywhere. It knows nothing about *here*.

---

## The Missing Layer

Think about what happened when DNS came along in the 1980s. Before DNS, if you wanted to connect to a computer, you needed to know its numeric address. DNS created a simple mapping: human-readable names → machine addresses. Suddenly the internet became navigable. You could find things.

Now imagine the equivalent for physical space.

You're standing at coordinates -33.8591, 151.2050 (that's near the Sydney Opera House, if you're wondering). What services exist here? What permissions apply? What metadata does this location want to tell you about itself?

Today, there's no standard way to ask. Every application reinvents the wheel. Google Maps knows about businesses. Airbnb knows about rentals. Niantic knows where Pokémon spawn. But none of them talk to each other, and none of them are open to your AI agent.

**Mixed Reality Service (MRS)** is the missing layer. It's DNS for space: an open, federated protocol that maps coordinates to services.

```
f(coordinates) → services
```

That's it. That's the whole idea. Simple enough to explain in one line, powerful enough to change how agents interact with the physical world.

---

## What Agents Actually Need

Let's get concrete. Here are things an AI agent might need to know about a location:

**For reasoning about the physical world:**
- What is this place? (A hospital, a school, a private residence?)
- What are the operating hours?
- Who controls this space?
- What hazards exist here?

**For coordinating with physical systems:**
- Can a drone fly here?
- Can a delivery robot enter?
- What are the access requirements?
- Is photography permitted?

**For respecting human preferences:**
- Does the owner want to be contacted?
- Is this a "do not disturb" zone?
- What communication channels are preferred?

None of this information exists in a way AI agents can access. It's locked in proprietary databases, or it simply doesn't exist digitally at all.

MRS provides a universal query interface. Your agent asks: "What services are registered at these coordinates?" MRS answers with a list of URIs. The agent follows those URIs to get whatever metadata the space owner has chosen to publish.

The space *speaks for itself*.

---

## How It Works (The Non-Technical Version)

Imagine every piece of land, every building, every room could have a tiny flag planted in it that says: "If you want to know about this place, ask *here*."

That's MRS.

**Property owners register their spaces.** They define a boundary (maybe a building footprint, maybe a whole campus) and point it to a service endpoint—a URL that provides information about that space.

**Agents query MRS when they need spatial context.** "I'm planning a route through downtown Sydney. What should I know about the spaces along the way?"

**MRS returns pointers, not data.** It doesn't try to be a universal database of everything. It just tells you where to ask. The actual services—hours of operation, access policies, hazard warnings—live at the service endpoints, controlled by the space owners.

**Federation means no central authority.** Anyone can run an MRS server. Servers refer to each other. Your query might touch a municipal server, a corporate server, and a private server, and you'd never know the difference. Just like email, just like the web itself.

---

## The FOAD Flag (Yes, Really)

Sometimes the most important thing a space can communicate is: *leave me alone*.

MRS includes a privacy marker called FOAD. When a space is registered with FOAD=true, it means:

- Yes, this space is claimed
- No, we're not providing any services
- Don't ask follow-up questions
- Go away

This is important. Not every space wants to participate in the digital economy. Some people just want to live their lives without being indexed, queried, and optimized. MRS respects that by making "no" a first-class answer.

(If you're wondering what FOAD stands for, you probably already know. If you don't, it's "Forbidden/Off-limits And Declared." Sure it is.)

---

## Integrating with AI Agents

Here's where it gets practical.

Modern AI agents—like those built on Claude, GPT, or open-source models—support "tools" or "skills" that extend their capabilities. An agent might have a tool for searching the web, another for reading files, another for running code.

**MRS becomes a spatial awareness skill.**

When an agent needs to reason about physical space, it invokes the MRS skill:

```
Agent: I need to plan a drone delivery to 425 George Street, Sydney.

[MRS Skill]: Querying coordinates -33.8688, 151.2070...
  → Found 3 registrations:
    1. Sydney CBD Airspace Authority (municipal)
    2. 425 George Street Building Management
    3. Retail tenant "Café Luna" (ground floor)

Agent: Let me check the airspace authority for drone permissions...

[Fetches service point → drone overflight: permitted below 50m,
 landing zones: designated rooftop only, delivery protocol: v2.1]

Agent: And the building management for access...

[Fetches service point → deliveries: rooftop drone port active,
 notify concierge on arrival, no weekend deliveries before 9am]

Agent: I can plan this delivery. The route is clear,
       landing zone is the rooftop port, and I'll need to
       schedule after 9am since today is Saturday.
```

The agent didn't need a special integration with Sydney's airspace system, or the building's management software, or the café's booking system. It just asked MRS "what's here?" and followed the pointers.

**This is the power of open infrastructure.** Build once, query anywhere.

---

## Why Now?

This idea has been kicking around since 1994. (Seriously—the first version was called "Cyberspace Protocol" and was presented at the first World Wide Web conference.) So why does it matter now?

**AI agents are becoming autonomous actors in the physical world.**

When AI was just a chatbot, spatial awareness didn't matter much. You asked questions, it gave answers, humans did the actual moving around.

But agents are starting to *do things*. They book reservations. They schedule deliveries. They coordinate with robots and drones and autonomous vehicles. They make plans that involve physical space and then execute those plans.

An agent that can't perceive space is like a self-driving car with no sensors. It might be very smart, but it's going to crash into things.

**MRS gives agents spatial perception as a standard capability.**

Not a proprietary capability locked to one vendor. Not a bespoke integration for each use case. A standard, open, federated layer that any agent can query, any space owner can publish to, and any developer can build on.

---

## The Bigger Picture

DNS didn't just make the internet easier to use. It made the *web* possible. Once you could find things by name, you could link to them. Once you could link, you could build a web of documents. Once you had a web, you could build search engines, social networks, e-commerce—everything that came after.

MRS could do the same for physical space.

Once agents can query "what's here?", they can reason about routes, permissions, and context. Once they can reason spatially, they can coordinate with physical systems. Once coordination is possible, you get autonomous delivery, robotic services, smart cities that actually work—not as proprietary silos, but as an open ecosystem.

The real world becomes *addressable*.

Not addressable in the sense of street addresses—we've had those for centuries. Addressable in the sense of URLs: every space can publish its own services, link to other spaces, participate in a web of spatial information.

That's the vision. DNS for space. A metadata layer for the real world.

**And it all starts with a simple query:**

*What's here?*

---

## Get Involved

MRS is an open specification and open implementation.

- **Read the spec:** Technical details for implementers
- **Run a server:** Host registrations for your spaces
- **Build a skill:** Integrate MRS into your agent framework
- **Register your space:** Make your corner of the world legible to agents

The infrastructure is being built. The question is whether you want to help shape it.

---

*MRS is the continuation of work begun in 1994 by Mark Pesce, co-inventor of VRML. Thirty years later, the need for spatial infrastructure has never been greater. The agents are here. It's time to give them eyes.*
