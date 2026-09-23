# End-to-end research: a FiveM-style platform for No Man's Sky

Research date: **20 September 2026**, with a **21 September 2026 baseline-only source refresh in section 3**. User priority: persistent community servers with custom rules, economies, and roleplay. This is desk research from publisher, platform-vendor, and project-maintainer sources. Detailed lab evidence belongs to task records; [STEPS](STEPS.md) owns delivery status and links those records.

## 1. Findings and current engineering proposal

**The most consequential engineering unknown is how an external server gains reliable control over each desired gameplay operation.** The current proposal pairs a standalone service with a narrow game adapter, combines them into one playable interaction, then extends persistence and multiplayer behavior. This allows ordinary service development alongside investigation of the game boundary. It is an engineering proposal, not a verified integration route.

The public sources reviewed establish a functioning mod ecosystem and several approaches to client hooks. They do not establish a supported, current, independently operated NMS multiplayer runtime comparable to FXServer. No public Hello Games dedicated-server binary, headless simulation interface, or stable multiplayer mod SDK was identified. This is a search result, not proof that a solution is impossible.

The intended outcome and context behind the one-player milestone are in [PRODUCT](PRODUCT.md). [ROADMAP](ROADMAP.md) sets out the proposed work and its uncertainty; [EXPERIMENTS](EXPERIMENTS.md) supplies proposed tests. None of the source findings establishes that every desired capability can be delivered or how much integration work it will take.

Three outcomes must remain distinct:

| Path | What the operator actually controls | Assessment |
| --- | --- | --- |
| Independent multiplayer platform | Admission, declared simulation/rules, replicated entities, persistent state, resource lifecycle | Requested long-term direction; its integration boundaries remain unverified |
| Hybrid game extension | Platform state and selected client-integrated rules; native sessions still supply some multiplayer | Possible intermediate implementation; remaining native dependencies limit operator control |
| Companion RP service | Accounts, contracts, manual or reported activity, community records, overlay | Technically approachable and already has competition; a reduced-scope alternative requiring an explicit product decision |

## 2. What FiveM actually provides

FiveM is a capability reference, not a portable NMS backend. OneSync builds on GTA Online's codebase and adds synchronization, entity ownership and migration, culling, routing buckets, and server-created entities. Some operations still depend on client execution. Its advertised scale and architecture cannot be transferred to another engine. [OneSync documentation](https://docs.fivem.net/docs/scripting-reference/onesync/).

| Capability to learn from | Required NMS work | Primary reference |
| --- | --- | --- |
| Game integration and native functions | A maintained NMS adapter with explicit supported operations, thread/lifecycle rules, and build compatibility | [Native functions](https://docs.fivem.net/docs/scripting-manual/introduction/about-native-functions/) |
| Resources and scripting | Package metadata, dependency resolution, separate server/client roles, lifecycle, versioning, and one initial language | [Resource manifests](https://docs.fivem.net/docs/scripting-reference/resource-manifest/), [scripting reference](https://docs.fivem.net/docs/scripting-reference/) |
| Events and custom UI | Authenticated commands, validated payloads, event routing, and an in-game UI bridge | [Events](https://docs.fivem.net/docs/scripting-manual/working-with-events/triggering-events/), [NUI](https://docs.fivem.net/docs/scripting-manual/nui-development/full-screen-nui/) |
| Independently operated server artifact | Installation, configuration, admission, resource loading, compatibility, backups, and restart behavior | [Server setup](https://docs.fivem.net/docs/server-manual/setting-up-a-server/) |
| Operator administration | Roles, allowlists, bans, player records, audit logs, monitoring, and recovery | [txAdmin](https://docs.fivem.net/docs/resources/txAdmin/) |
| Trusted game transactions | Server validation and a clear distinction between authoritative data and client claims | [Securing events](https://docs.fivem.net/docs/developers/server-security/) |
| Identity and distribution | Our own identity/entitlement design, creator licenses, package review, support, and revocation | [Player identifiers](https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/GetPlayerIdentifiers/), [finding resources](https://docs.fivem.net/docs/server-manual/finding-resources/) |

An economy, job framework, or roleplay mode is then built on these capabilities. Do not confuse FiveM's platform with every third-party framework running on it. Replicating the whole ecosystem is much larger than shipping one working community mode.

## 3. Current NMS baseline and freshness

Dated release checks and native-baseline sources are kept in the [T-03.1 source review](tasks/T-03.1/sources.md). Installed-build evidence is separate from publisher release labels.

Cosmos already adds alliances, alliance rankings, space-station directorship, and orbital construction. It also extends modding support for trigger actions. These are baseline game capabilities, so an alliance directory or station ownership alone is weak differentiation. The proposed gap is custom enforceable rules, creator APIs, operator control, and durable community progression. That gap is a product hypothesis, not proven customer demand. [Cosmos update](https://www.nomanssky.com/cosmos-update/).

Worlds Part II deliberately improved mod compatibility/conflict handling and added settings for mod priority and disablement. It would be inaccurate to say the game has no mod support. These improvements do not themselves document arbitrary runtime scripts or custom servers. [Worlds Part II](https://www.nomanssky.com/worlds-part-ii-update/).

### Networking: services are not simulation authority

Hello Games replaced its networking backend for crossplay in June 2020. Microsoft identified NMS as a PlayFab Party customer in September 2022 and presented its matchmaking/lobby integration at GDC 2022. These are reliable historical implementation facts; they do not establish every detail of build 7.03.1. [Hello Games crossplay announcement](https://www.nomanssky.com/2020/06/introducing-crossplay-for-no-mans-sky/), [Microsoft Party announcement](https://developer.microsoft.com/en-us/games/articles/2022/09/playfab-party-expands-cross-platform-play-with-new-platforms/), [Microsoft NMS case study](https://developer.microsoft.com/en-us/games/events/gdc/2022/no-mans-sky-demo/).

Party exchanges messages between peers using a cloud relay, with optional direct connections. A relay forwards traffic; it does not establish who simulates entities, approves inventory changes, or owns world state. Purchasing generic networking middleware would not supply NMS's game protocol, simulation, or access to Hello Games' title configuration. The last point is an architectural inference, not a statement about an undisclosed partnership. [Party transport documentation](https://learn.microsoft.com/en-us/xbox/playfab/multiplayer/networking/concepts-direct-peer-connectivity).

### Player limits and persistence

Historical Beyond notes describe 32 PC players, 8 on contemporary consoles, and 16 in the Anomaly. Next Generation introduced 32-player sessions on newer consoles. The current homepage advertises up to 32 in the Anomaly. These sources differ by date and context; they are not a current certified compatibility table. Party size, scene population, community membership, and total concurrent platform users are different measurements. The frequently repeated four-person party limit was not established from a current primary source in this review. [Beyond](https://www.nomanssky.com/beyond-update/), [Next Generation](https://www.nomanssky.com/next-generation-update/), [current homepage](https://www.nomanssky.com/).

Uploaded discoveries and bases are shared across platforms. Cross-save transfers files to and from local storage and handles competing versions. Neither establishes a continuously simulated community world or a tamper-resistant inventory ledger. [Expeditions](https://www.nomanssky.com/expeditions-update/), [cross-save FAQ](https://cloud.nomanssky.com/cross-save).

### Platforms and join flow

Start investigation on Windows with one storefront. Switch 2 gained multiplayer and crossplay; that does not establish a supported route for arbitrary executable mods on consoles. GOG advertises offline play while its online features require Internet access and Galaxy. Offline single-player is not evidence of LAN multiplayer. [Beacon announcement](https://www.nomanssky.com/2025/06/no-mans-sky-beacon/), [GOG product listing](https://www.gog.com/en/game/no_mans_sky).

No public, supported launcher-to-private-NMS-server join API was identified. First measure native friend/group joining; do not promise a working one-click join button from a website design. Keep game-session identity, platform account identity, and the operator's community identity separate.

## 4. Tooling: what can be reused and what is missing

The following are maintainer-documented capabilities from the initial desk review. The later [T-04.2 source review](tasks/T-04.2/sources.md) and [lab evidence](tasks/T-04.2/evidence-2026-09-23.md) cover the selected pyMHF/NMS.py-derived probe. Dates indicate activity, not current-build compatibility. Licenses must be checked at the exact commit before incorporation; bundled dependencies and generated game-derived content need separate review.

| Tool | Documented role and limit | Activity and license evidence |
| --- | --- | --- |
| [MBINCompiler / libMBIN](https://github.com/monkeyman192/MBINCompiler) | MBIN/MXML conversion and game-data structures; useful asset pipeline, not a game server or scripting runtime | [7.03.2-pre2](https://github.com/monkeyman192/MBINCompiler/releases/tag/v7.03.2-pre2), 19 Sep 2026, explicitly prerelease; [LGPLv3](https://github.com/monkeyman192/MBINCompiler/blob/development/LICENSE.md) |
| [AMUMSS](https://github.com/HolterPhylo/AMUMSS) | Windows-oriented Lua build-time mod generation; its Lua scripts are not live gameplay scripts, and it is not a mod manager. Maintainer instructions use `GAMEDATA/MODS` subdirectories for NMS >=5.5; do not assume the old `PCBANKS/MODS` workflow | [5.6.2.0W](https://github.com/HolterPhylo/AMUMSS/releases/tag/v5.6.2.0W), 18 Nov 2025; auto-updated dependencies need pinning; [MIT](https://github.com/HolterPhylo/AMUMSS/blob/main/LICENSE) |
| [NMS.py](https://github.com/monkeyman192/NMS.py) and [pyMHF](https://github.com/monkeyman192/pyMHF) | Runtime hooks and callbacks; NMS.py explicitly excludes online-functionality functions and warns of update breakage. It cannot be assumed to supply a networking SDK or sandbox | [NMS.py commit, 15 Sep 2026](https://github.com/monkeyman192/NMS.py/commit/b41bf9e6fdff1c833b77d805bb0c8da555c4ced4); [NMS.py MIT](https://github.com/monkeyman192/NMS.py/blob/master/LICENSE), [pyMHF MIT](https://github.com/monkeyman192/pyMHF/blob/master/LICENSE) |
| [ReNMS](https://github.com/sonny-tel/renms) | Native C++ plugin framework explicitly targeting Fractal 4.13 Steam/GOG; historical reference | [Commit, 20 Jan 2024](https://github.com/sonny-tel/renms/commit/9696413ec82bd0bd6cea81565ef20122a1c168bb); [GPLv3](https://github.com/sonny-tel/renms/blob/main/LICENSE) |
| [NoMansSky.Api](https://github.com/gurrenm3/NoMansSky.Api) | Reloaded-II/C# API with frame hooks, player-stat events, and limited inventory access; current compatibility unverified | [1.0.3](https://github.com/gurrenm3/NoMansSky.Api/releases/tag/1.0.3), Jun 2022; [GPLv3](https://github.com/gurrenm3/NoMansSky.Api/blob/master/LICENSE) |
| [NMSDK](https://github.com/monkeyman192/NMSDK) | Blender scene/model import and export; asset creation does not provide network replication | [0.10.0-alpha13](https://github.com/monkeyman192/NMSDK/releases/tag/0.10.0-alpha13), Jun 2026; [manifest](https://github.com/monkeyman192/NMSDK/blob/master/src/addon/nmsdk/blender_manifest.toml) says GPL-3.0-or-later and Blender 5.0 minimum, conflicting with older README requirements |
| [NMSModBuilder](https://github.com/cmkushnir/NMSModBuilder) | C# build scripts, archive inspection, and conflict comparisons; not a live scripting server | [Commit, 19 Sep 2026](https://github.com/cmkushnir/NMSModBuilder/commit/f871fab62e4bae89675b86ebdd489f611c1fb32c); [README license provision](https://github.com/cmkushnir/NMSModBuilder#license) adds fork/competing-product restrictions to AGPL language; do not treat it as an ordinary AGPL dependency |
| [NomNom](https://github.com/zencq/NomNom) / [libNOM.io](https://github.com/zencq/libNOM.io) | Save editing, backup/conversion, and save I/O; demonstrates why client save values cannot certify community wealth | [NomNom 7.00.1](https://github.com/zencq/nomnom/releases/tag/7.00.1), 20 Sep 2026; [NomNom GPLv3](https://github.com/zencq/nomnom/blob/main/LICENSE), [libNOM.io GPLv3](https://github.com/zencq/libNOM.io/blob/master/LICENSE); validate library version separately |
| [NMSSaveEditor](https://github.com/goatfungus/NMSSaveEditor) | Java save-editing application; useful ecosystem reference, not multiplayer authority | No repository license was identified in this review; availability does not establish reuse rights |

**Recommended division of work:** reuse licensed data-conversion tools; evaluate client hooks with their actual scope and maintenance constraints; build an original game-facing protocol and resource contract only after the necessary game operations are demonstrated. No dependency is selected by this table.

## 5. Competition, demand, and differentiation

| Existing option | What the evidence establishes | Implication |
| --- | --- | --- |
| Native NMS communities | Cosmos capabilities are described in section 3 | Do not sell existing alliance functionality as a new platform capability |
| Galactic Hub and other civilizations | Community-run catalogs, events, organizations, and economy-related tools already exist | Pilot with operators who already coordinate play; do not assume players lack communities. [Galactic Hub links](https://nmsgalactichub.com/pages/links), [NMSCD directory](https://community.nmscd.com/) |
| Nexus Mods | Existing NMS mod distribution and discovery; Nexus also offers Collections and creator rewards | File hosting and modpack management alone have weak differentiation. [NMS catalog](https://www.nexusmods.com/games/nomanssky), [Nexus description](https://www.nexusmods.com/about) |
| NMS Alliance RP 2026 | Author advertises profiles, missions, economy, administration, and a Windows overlay; explicitly says it does not replace NMS multiplayer or modify saves | Direct competition for a companion service. Claims were not tested. [Author page](https://funscriptor.itch.io/rp-server-for-no-mans-sky), [Nexus listing, 16 Sep 2026](https://www.nexusmods.com/nomanssky/mods/4508) |
| Expedition proxy projects | A maintainer describes substituting expedition responses while forwarding other services | This does not prove private multiplayer hosting. The project's transport description is not a substitute for the official evidence in section 3. [nms-expeditions-online](https://github.com/BonzTM/nms-expeditions-online) |
| Generic LAN wrappers | UniverseLAN's compatibility list marks NMS unsupported | Replacing a store networking wrapper is not an established shortcut. [UniverseLAN](https://github.com/grasmanek94/UniverseLAN) |

The defensible differentiation hypothesis is **operators can publish and reliably enforce custom community gameplay**, with predictable content compatibility and recoverable progression. This is more valuable than another RP dashboard if it works; it is also the part with the least demonstrated technical support.

No market-size, conversion, revenue, or willingness-to-pay estimate is established by this research. Existing communities show activity, not demand for this product. Do not use total NMS sales or subreddit subscribers as an addressable paying market.

Proposed discovery sample: five active community operators, three mod authors, and ten players. Ask for a recent failed event, exploit, installation problem, or moderation incident; the current workaround; measurable time lost; the minimum in-game control required; willingness to install a native bridge; and willingness to maintain a pilot. These are future interviews, not work already done.

Possible discovery signals include repeated unmet needs across operators, willingness to host a pilot, and an outside creator successfully building a resource. These would inform the audience, feature priorities, and operating model. No demand threshold has been selected as a condition for local implementation; the sample sizes above are research planning assumptions.

## 6. Rules, economics, and trust

Persistence is straightforward only for data the platform actually owns. A durable database can store an RP profile and currency balance. It cannot prove a player mined an item, stayed in a restricted area, respected a PvP rule, or did not restore an old save.

| Community feature | Minimum control needed | What does not prove it |
| --- | --- | --- |
| Jobs and contract rewards | Verifiable action transition or explicitly moderated approval; one atomic reward | Client emits `contractComplete` |
| Economy and shops | Server-owned balances, prices, transaction IDs, inventory authority for anything sold | A save file reports an item count |
| Territory/building rules | Observe and reject the relevant placement/destruction at the correct boundary | A colored map on a community website |
| PvP rules and safe zones | Enforce damage decisions and handle participants without the extension | A mod changes the local HUD |
| Whitelist and bans | Exclude unauthorized users from the actual promised game environment | Their website account cannot sign in |
| Offline persistence | Define which timers/state advance without clients and demonstrate restoration | Keep a player account logged in as a host |

The first economy should use community credits stored by the platform with no promised cash value or redemption, no cashout, and no claimed conversion into official currencies. This reduces the initial integration surface; it does not cure fraudulent activity reports. For a competitive enforced economy, the critical gameplay event must have a trust basis beyond client testimony.

The proposed authority table, event format, and recovery model are in [ARCHITECTURE](ARCHITECTURE.md).

## 7. Permissions, licensing, and identity

The live NMS EULA states it was last updated 25 January 2019. Clauses 4.2.1-4.2.4 restrict redistribution, modification/reverse engineering subject to applicable-law exceptions, copy-protection circumvention, and commercial exploitation; 5.2 describes personal noncommercial use; 6.3 restricts real-money item/account sales. It contains no identified grant for this platform. Deliberate technical accommodation of data mods is distinct from permission for a commercial networking product. Interpretation and enforceability need review for the actual implementation and jurisdiction. [NMS EULA](https://www.nomanssky.com/end-user-licence-agreement/).

Cfx joined Rockstar in 2023. Its current Creator Platform License Agreement endpoint resolves to a document dated 10 September 2026 and grants conditional rights for covered Rockstar games. FiveM's source license generally points to that agreement, with specifically designated LGPL files and other third-party licenses. Neither its existence nor source availability provides blanket rights to port the entire framework to NMS; designated LGPL components may confer reuse rights subject to their terms. Use it as a design reference unless particular code reuse is cleared. [Cfx announcement](https://forum.cfx.re/t/cfx-re-officially-joins-rockstar-games/5158920), [current Creator PLA](https://fivem.net/terms), [repository license](https://raw.githubusercontent.com/citizenfx/fivem/master/LICENSE).

Steam OpenID can establish a Steam identity for a third-party website. That is distinct from proving NMS entitlement or binding the current game process to an account. Valve's `CheckAppOwnership` method requires the publisher key owning the target AppID; this project cannot assume it can call it for NMS. Design legitimate ownership requirements without asking users for passwords or Hello Games credentials, and resolve an approved entitlement route before claiming verification. [Steam authentication](https://partner.steamgames.com/doc/features/auth), [ownership API requirements](https://partner.steamgames.com/doc/webapi/ISteamUser#CheckAppOwnership).

### Concrete permission brief to prepare, not send automatically

Describe a Windows community platform with an original client adapter, operator-run services, resource scripting, separate community records, legitimate purchased installations, and no redistributed game executable or assets. Ask Hello Games which supported integration paths exist and what permission covers:

1. Private feasibility experiments and access to game functions.
2. Public adapter distribution and compatibility testing.
3. Independent sessions, transport, admission, and headless operation.
4. Identity/entitlement integration and separation from official services/saves.
5. Creator content, trademarks, naming, incident coordination, and discontinuation.
6. Commercial hosting, subscriptions, donations, creator compensation, and marketplaces, each separately.

Use the official [contact page](https://www.nomanssky.com/contact/) to identify a suitable route if the user authorizes outreach. No message has been sent. Silence, widespread mod use, a donation label, or building a separate website must not be treated as approval for a commercial product. Qualified review should identify what can proceed without special permission and what needs a written agreement; do not impose an invented blanket prohibition on ordinary research.

## 8. Proposed implementation and release sequence

| Phase | Bounded outcome | Next engineering step |
| --- | --- | --- |
| Service and game adapter | Runnable server, local game baseline, one supported interaction | Connect one real player; diagnose missing integration operations while service work continues |
| One-player server | In-game server-controlled response, then persistent reconnect/restart | Add the second player and synchronize the same state |
| Multiplayer and creator alpha | Shared state, operator rules, resources, community economy, admission and recovery | Extend the authority surface and make the artifact usable by another operator |
| Operator pilot | At least two communities can run the artifact and recover from a failed update | Improve reliability using support, creator, and player observations |
| Public release | Signed distribution, compatibility reporting, moderation, restoration, onboarding, and support | Release supported scope with its required external conditions resolved |
| Optional commercial service | A permitted offer with paying operator demand and measured costs | Price from support and operating data |

Anticipated core work is mapped in [ROADMAP](ROADMAP.md), with uncertainty described by workstream. The next few tasks receive immediate execution detail in [STEPS](STEPS.md). Optional expansion belongs to BACKLOG. This sequence is provisional and has no promised phase dates.

## 9. Team, effort, and cost scenarios

These are planning assumptions, **not vendor quotes, market salary data, feasibility guarantees, or approved expenditure**. Funding cannot ensure that an inaccessible game capability becomes available.

| Work | Planning envelope | Staffing need |
| --- | --- | --- |
| Initial server/adapter increment | 2-4 weeks as an initial budgeting cycle, followed by re-estimation from actual work | One senior engine/runtime engineer, part-time backend/security help, one game client initially |
| Narrow integrated alpha | 8-16 additional weeks as a provisional budgeting envelope; revise for measured integration work | Runtime/network engineer, backend engineer, part-time client UI and QA; additional game clients for multiplayer tests |
| Broader independent platform | No credible delivery estimate until authority and isolation pass | Continuing engine compatibility, networking, backend, client UX, creator support, QA, and operations |

An illustrative labor rate assumption of $15,000-$25,000 per engineer-month yields $90,000-$150,000 for two engineers over three months. A six-engineer, twelve-month scenario yields $1.08m-$1.8m before contingency. Adding 30% produces $1.404m-$2.34m. These illustrate exposure; they do not forecast how long an NMS runtime will take. Legal work, art, management, recruiting, equipment, and some operational roles are excluded.

### Hosting is not the dominant initial uncertainty

For a small platform-service pilot, use an initial **budget assumption of $50-$250/month** for compute/database, backups, modest bandwidth, and basic monitoring, then replace it with actual deployment measurements. It excludes game-simulation hosting, paid support, signing, moderation, and major artifact traffic. No VM size or player capacity is certified here.

Artifact distribution can exceed the cost of metadata services. The Backblaze public page reviewed quotes $6.95/TB-month, free direct egress up to three times average storage, and $0.01/GB thereafter. An illustrative 100 GB average store and 5,000 GB monthly direct downloads costs about $47.70 before free-tier credits/tax: `100 * 0.00695 + (5000 - 3 * 100) * 0.01`. CDN arrangements and actual billing change this result. This is a pricing example, not a selected provider. [Backblaze pricing](https://www.backblaze.com/cloud-storage/pricing).

A separate hypothetical simulation calculation shows why player density matters: `100 players * 20 visible peers * 10 updates/sec * 300 bytes = 6 MB/sec`, or about 48 Mbps before protocol overhead. Continuous operation for 30 days is roughly 15.6 TB. This is arithmetic using invented workload inputs, not measured NMS traffic and not evidence that 100 NMS clients can share a scene. Measure message size, interest sets, duty cycle, retransmissions, CPU, frame time, and rendering limits before buying capacity.

### Business model hypothesis

If permitted, test optional operator subscriptions for managed hosting, backups, analytics, and administration. Keep player access and creator participation uncomplicated during validation. Paid game advantages, cashout, and selling official currencies are outside the initial product.

At a hypothetical $25/community/month and $10 variable cost, a $5,000 monthly fixed operating burden needs about 334 paying communities before fees and tax. Covering $40,000 of monthly staff cost at the same $15 contribution needs about 2,667. No evidence currently establishes either customer count. This sensitivity check argues for validating operator demand and support time before treating the project as a business.

## 10. Engineering challenges and responses

| Risk | Early evidence needed | Response if evidence fails |
| --- | --- | --- |
| No stable game control | Runtime access and enforcement demonstration | Isolate the failing operation; test another hook/adapter or supported interface; preserve completed service work |
| Native network fights custom state | Isolation, late join, host departure, ownership tests | Revise ownership, isolate project-owned entities, and test reconciliation before extending the rule surface |
| False economy inputs | Forged event/save tests with no unauthorized rewards | Implement server-verifiable transitions or stronger game control; label interim cooperative behavior accurately |
| Permission or entitlement route unavailable | Scoped review and required publisher/platform agreement | Hold affected distribution/commercial features; reassess the viable scope |
| Game updates break integration | Build detection, safe disablement, measured repair on a second build | Improve adapter boundaries and repair workflow; discuss support scope if measured maintenance exceeds capacity |
| Malicious resources or operators | Package isolation, permissions, signed releases, revocation tests | Keep distribution curated and disclose operator trust boundaries |
| No demand beyond existing tools | Concrete operator pain and pilot commitment | Revise or end the product hypothesis |
| Creator ecosystem maintenance cost | Independent resource creation and patch update | Simplify the API before adding a marketplace |

## 11. Evidence limits and refresh policy

The original sources were reviewed on 2026-09-20; the linked T-03.1 source review records the limited baseline refresh on 2026-09-21. Publisher releases establish documented game behavior; vendor docs establish middleware capabilities; maintainer pages establish advertised tooling and license text. None substitutes for the installed-build tests. Search snippets were used to discover sources, with key claims checked against publisher/maintainer pages or read-only GitHub metadata. Galactic Hub's links page was available in search output but a direct fetch failed; treat it as community-discovery evidence only.

High-change sources: the NMS release log, compiler/hook releases, dependency licenses, current Creator PLA endpoint, and prices. Recheck them when starting a spike or release. The source dates above deliberately retain historical context instead of calling old documentation current behavior. Do not infer current compatibility from a recent repository commit.

Public-source search coverage included Hello Games releases/terms/support, Microsoft NMS/PlayFab material, Cfx documentation and licensing, NMS tooling repositories, community sites, and mod catalogs. No direct access to Hello Games' implementation or internal SDKs was available. The precise current network topology, authoritative state ownership, supported private-server route, arbitrary-mod replication, session caps, and enforceable rule surface remain unresolved.

The current implementation proposal and its prerequisites are in STEPS. Commercial discovery, permissions, and release preparation address additional questions whose relevance depends on the selected design and activity. Apart from the baseline sources explicitly refreshed in section 3, external findings retain their 2026-09-20 review date; no other source, tool license, service price, or game capability was reverified during T-03.1 preparation.
