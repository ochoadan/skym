# Product

## Purpose

Enable communities to create distinct, persistent multiplayer experiences inside No Man's Sky, with the practical freedom that attracts creators and operators to FiveM.

The user's request is broader than distributing mods: recreate the platform model for this game. The user explicitly selected persistent community servers with custom rules, economies, and roleplay as the priority on 2026-09-20. Creator-authored activities serve that experience. A universal MMO is a separate expansion hypothesis. No public name, commercial model, vendor, or release date is selected.

External capability findings belong to [RESEARCH](RESEARCH.md). The proposed engineering path belongs to [ROADMAP](ROADMAP.md), and delivery state belongs to [STEPS](STEPS.md).

## Context behind the direction

The user found the initial five-part plan too focused on deciding whether to proceed. It obscured the construction work between research and a usable platform. They expected a substantial engineering effort and considered operating a server with one player a useful early outcome. The expanded roadmap made that work visible; the user has not specified a required task count, fixed implementation order, or commitment to pursue every approach regardless of what is learned.

The later note, *Expressing Intent Without Prescribing Behavior*, raised a concern about explanations becoming standing instructions detached from the situation that prompted them. It describes an unresolved problem with communicating intent; it does not propose a prompting method that guarantees good judgment.

## Users and jobs

| User | Outcome |
| --- | --- |
| Player | Discover a community, understand its rules and required content, join reliably, and retain community progression |
| Community operator | Run a distinct environment, configure rules and resources, moderate access, recover data, and export the community's records |
| Creator | Implement a bounded game mode or activity through a documented API and distribute a versioned resource |
| Platform maintainer | Maintain game compatibility, revoke unsafe packages, diagnose failures, and keep releases reproducible |

## Intended experience

An operator creates a small salvage-and-trade community and installs a custom contract resource. A player selects it in the launcher, sees the operator and required package permissions, and joins using a legitimate installation of the game. In-game actions drive a server-validated contract. Two players see consistent results, progress survives disconnects and server restarts, and an administrator can explain a disputed reward using an audit record.

For platform currency, a client cannot mint rewards by editing its local save or replaying a request. If the product cannot establish a trustworthy connection between a gameplay action and the reward, that reward must be described as manually moderated or based on an untrusted report. A database entry alone does not establish gameplay authority.

## What would fulfill the FiveM-style goal

1. Operators control admission and the declared rules of a community game environment, not just membership in a website.
2. Creators can change meaningful gameplay through a supported, versioned resource interface.
3. The system has an explicit, tested authority model for each gameplay feature it promises to enforce.
4. Relevant game state synchronizes between clients and survives the lifecycle promised to players.
5. Players can install, update, join, leave, and restore their original setup reliably.
6. Another operator and another creator can use the documented system without its authors intervening.

Operators should own a deployable server, its community rules, and persistent records. The design may delegate rendering, physics, or other declared work to game clients; replacing the entire game engine is not a requirement. Dependence on native sessions or official services must be explicit, particularly where it affects admission or rule enforcement. A companion service is a different product scope from the selected game-integrated platform.

## Proposed first playable milestone: one player and their server

The user can start their own server, connect one running NMS client, perform a small in-game action, and see a response determined by server configuration/state. Changing that configuration changes the result inside the game. This defines the intended outcome; the interaction and adapter route remain unselected.

A one-player server is a legitimate engineering and personal-use outcome. A standalone server process with a test client is also useful earlier progress. Each is evaluated against its actual behavior. Neither needs to deliver every multiplayer, security, hosting, or simulation feature of the eventual platform to count as completed work.

Support for a server process alongside the player's game and, potentially, a listen-server mode can be evaluated as hosting options. Dedicated operation means the server process can operate separately from the player client; it does not require continuous simulation of all planets while nobody is connected. Persisted state can remain idle, pause specified timers, or compute elapsed-time effects on reconnect according to the resource's declared rules.

## Product boundaries

- Start with original or explicitly licensed test content. Preserve existing mod creators' distribution choices and attribution.
- Keep community identities, contract state, and platform currency separate from official Units, Nanites, Quicksilver, discoveries, and cloud saves.
- Make resource permissions visible. Ordinary downloadable resources should not receive unrestricted native execution on a player's PC.
- A supported-build mismatch should stop integration with an explanation and recovery route.
- Platform moderation governs platform services. Game-session exclusion must be demonstrated separately.
- Public distribution and commercial operation require a resolved rights and service-access position for the selected design.

## Explicitly outside the first implementation

A seamless MMO; hundreds of players in one scene; console injection; replacing the entire procedural universe; arbitrary native-code marketplace uploads; trading official items for real money; player-to-player cashout; cryptocurrency; custom voice infrastructure; and promises that cheating is eliminated.

These boundaries constrain the first implementation, not the long-term exploration. Later ideas and the evidence needed to select them belong to [BACKLOG](BACKLOG.md).

## Current implementation proposal

The current route starts with a standalone service and a narrow game adapter, then combines them into the one-player interaction. Persistence and a second client extend that loop. The service can be developed without game access, while adapter work investigates the project's largest technical uncertainty. This is the present engineering proposal; its order and design depend on what the integration supports.

Windows on one exact Steam build is the initial lab target. Other storefronts and platforms add their own compatibility work. [ROADMAP](ROADMAP.md) defines milestones, [EXPERIMENTS](EXPERIMENTS.md) indexes verification, and [STEPS](STEPS.md) links current task records.
