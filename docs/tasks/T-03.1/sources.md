# T-03.1 — Baseline source review

Type: dated source review. Reviewed: 2026-09-21. These notes were relocated without a new external-source review.

[Task plan and procedure](README.md) · [Observed evidence](evidence-2026-09-21.md) · [Cross-cutting research](../../RESEARCH.md)

## Release context

**Baseline refresh, reviewed 2026-09-21:** The official release log now lists Cosmos 7.04 for PC. The linked notice is titled 7.04 and dated 21 September 2026, but its introductory paragraph still calls the patch 7.03; preserve that source inconsistency instead of deriving an installed version from it. The earlier 2026-09-20 review found 7.03.1. A test must record the installed storefront build and executable hash, independently of the public patch label. [Release log](https://www.nomanssky.com/release-log/), [7.04 notice](https://www.nomanssky.com/2026/09/cosmos-7-04/). Initial installed metadata and its limits belong to the [task plan](README.md#initial-setup-and-evidence-limits).

## Native procedure sources

These findings are limited to T-03.1 preparation. Publisher/vendor descriptions support what the baseline should check; they do not establish the current installation's settings or successful restoration.

| Source | Verified source statement | Implication for the proposed baseline |
| --- | --- | --- |
| [Waypoint 4.0 saving notes](https://www.nomanssky.com/waypoint-update/) | Describe ongoing autosaving alongside full saves at earlier save triggers, including leaving a ship; also describe naming saves | Enter/exit a landed ship is a candidate native action. Observe actual save feedback and reload behavior on the recorded build; do not treat a transient message as proof of durable state |
| [Steam Cloud documentation](https://partner.steamgames.com/doc/features/cloud) | Describes synchronization around game sessions and a per-game cloud option | Record the NMS-specific Steam setting and relevant sync state before backup/restoration; global Steam settings are not a baseline shortcut |
| [NMS Cross-Save FAQ](https://cloud.nomanssky.com/cross-save) | Describes automatic upload of the most recent save when starting on a connected platform, save selection for upload/download, and version-conflict choices | Inspect this separately from Steam Cloud. A disposable local slot does not prove that no cloud copy exists |
| [Worlds Part II modding notes](https://www.nomanssky.com/worlds-part-ii-update/) | Describe a Mod Settings file controlling mod priority and disablement | Record relevant existing content/settings without installing a mod or assuming an old folder/disablement procedure applies |

**Engineering proposal:** For the selected raw Steam installation, use a disposable native save, repeat a simple ship interaction and full game restart, and test restoration of an explicitly declared local checkpoint. The source review does not select or require a mod, hook framework, save editor, SDK, or game update. The [task plan](README.md#e-01a-procedure-and-acceptance) owns E-01a's procedure and setup; [STEPS](../../STEPS.md) owns delivery status.
