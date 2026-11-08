# Data-source verification and integration research

Verified 2026-11-08. These are primary-source observations and design decisions, not a claim that every future integration has been implemented.

## Market feeds

[TSM public pricing documentation](https://tradeskillmaster.com/public-data) provides unauthenticated CSV URLs for Retail realm items, regional items and commodities. Direct live CSV checks confirmed these headers:

```text
Realm/commodity: itemId,name,marketValue,minBuyout,recent,historical,updatedAt
Regional items: itemId,name,marketValue,historical,avgSalePrice,saleRate,soldPerDay,updatedAt
```

Prices are copper. `updatedAt` is upstream observation time. The publisher describes realm/commodity updates every few hours and daily regional updates. `recent` is retained by the upstream but not used by this first model; unknown schema fields are ignored, required fields are checked. The feed provides base IDs, not reliable full gear/pet identities or per-listing execution guarantees. The implementation separates all three scopes and never invents sale-rate values.

[Blizzard Game Data API](https://develop.battle.net/documentation/world-of-warcraft/game-data-apis) is dynamically rendered; the official [commodity endpoint announcement](https://us.forums.blizzard.com/en/blizzard/t/immediate-change-to-auction-apis-for-commodities-with-927/31522) confirms region-wide commodities and separate connected-realm auctions. It describes an hourly snapshot cadence and a higher commodity request cost. This historical statement is not treated as a current service-level guarantee. The [official client credentials example](https://github.com/Blizzard/node-signature-generator) supports the OAuth design. We use bearer headers, not token query parameters.

Endpoints implemented: OAuth client credentials; connected-realm index/detail; `/data/wow/connected-realm/{id}/auctions`; `/data/wow/auctions/commodities`. HTTP validators and actual response timestamps govern ingestion. Credentials, account quota behavior and live Blizzard responses still require an authenticated integration test. Missing Last-Modified currently uses a fetch-time proxy for stored Blizzard evidence, which does not enter the candidate engine.

Public accessibility does not imply permission to republish entire datasets or every competitor's assets. The app consumes feeds for the user's self-hosted analysis; no scraped commercial datasets or proprietary art/code are bundled. Review publisher terms before redistribution or a hosted multi-user service.

## Competitive comparison

Capabilities below reflect the publishers' descriptions, not hands-on certification of every UI or claim.

| Product and primary reference | Observed emphasis | Our direction |
| --- | --- | --- |
| [TSM](https://support.tradeskillmaster.com/en_US/api-documentation/what-is-the-tsm-addon-api-and-how-do-i-use-it) | In-game pricing API and established trading workflows | Reuse supported prices; add inspectable self-hosted planning |
| [FlipQueue](https://www.curseforge.com/wow/addons/flipqueue) | Cross-character tasks, inventory routing, Auctionator/TSM interoperability | Persistent setup state, resilient module navigation, evidence and recovery states |
| [GoldCap](https://goldcap.gg/addon) | Deal review, price evidence, posting and flip tracking | Transparent assumptions and combined craft/buy planning |
| [FlippingPal](https://flippingpal.com/) | Cross-realm opportunities and inventory analysis | Own data history, local budgets, explicit route/risk review |
| [Undermine Exchange](https://undermine.exchange/) | Market exploration, variants, price history and regional comparison | Keep identity distinctions explicit; provide local provenance |
| [CraftSim](https://github.com/derfloh205/CraftSim) | Character-specific profession simulation and queues | Import validated simulation results; avoid duplicating changing expansion formulas |
| [Auctionator](https://github.com/Auctionator/Auctionator) | Auction workflow and shopping-list interoperability | Isolate a version-tested adapter with quantity-aware internal plans |

FlipQueue's published workflow is useful inspiration, but this milestone does not claim a hands-on comparative UX audit. Its in-game walkthrough, scale/layout and conflict behavior must be evaluated during addon work. No proprietary code or visual assets were copied.

## CraftSim and addon foundations

The actual [CraftSim API README](https://github.com/derfloh205/CraftSim/blob/main/Util/API_README.md) was read. It documents recipe access, updates, profit/gear/reagent operations, concentration selection and last-crafting-cost lookup. It marks an older profit optimizer deprecated. This supports a capability-detected adapter; it does not establish that every queue, Knowledge allocation or order field is a stable API. Pin a tested addon version and inspect the exact installed source before implementation. Recipe gear-quality identities may require an item link; quality-specific reagent IDs alone are insufficient for all gear outputs.

[Ace3](https://github.com/WoWUIDev/Ace3) is a candidate for lifecycle, event, configuration and serialization foundations. AceGUI's stock visuals do not automatically satisfy the requested modern UI. Evaluate LibSharedMedia for user fonts/textures and CraftSim's GGUI dependency as alternatives during the addon milestone. No Lua library is bundled yet; exact licenses, client compatibility, maintenance and frame-time costs must pass a version-specific review before adoption. Leatrix is not assumed to be an embeddable GUI toolkit.

Auctionator shopping-list quantity semantics and current public API signatures are **not yet verified**, so this milestone exports our own explicit material quantities rather than producing an allegedly compatible import string. This is a deliberate integration gate.

## Highest-value differentiation to build next

| Idea | Usefulness | Complexity | Acceptance evidence |
| --- | --- | --- | --- |
| Evidence-linked craft-versus-buy routes | High | Medium | Same output compared at equal quality, fees and opportunity cost |
| Inventory-aware realm allocation | High | High | No duplicate stock routed onto already covered markets |
| Incremental concentration planner | High | Medium | Incremental rather than total profit drives constrained spending |
| Capital/turnover portfolio planner | High | High | Total budget and realm exposure hold across the whole plan |
| Knowledge investment comparison | Medium/high | High | Character-specific breakpoints with explicit uncertainty |
| Seasonal forecasts | Uncertain initially | High | Backtests beat a transparent baseline before recommendations |

The first milestone implements evidence breakdowns and single-plan concentration arithmetic; it does not claim validated predictive advantages over those products.

## Desktop sources

[Electron's Wayland migration](https://www.electronjs.org/blog/tech-talk-wayland) and [breaking changes](https://www.electronjs.org/docs/latest/breaking-changes) establish native Wayland selection in modern Electron. [electron-builder Linux targets](https://www.electron.build/v26/docs/linux/) document RPM/AppImage and desktop integration. Runtime and packaging versions are locked in package manifests. Native distro compatibility must still be checked on the actual Fedora installation.
