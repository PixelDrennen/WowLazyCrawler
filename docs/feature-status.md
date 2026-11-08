# Feature and verification status

The target is a feature-complete addon. This update realigns the product and begins actual addon implementation; it must not be labeled production-complete based solely on passing simulated tests.

| Requirement | Implemented in 0.4.0 | Remaining gate |
| --- | --- | --- |
| Admin-only dashboard | Region service settings, health, coverage, character/storage review, read-only radar/crafting, graphs | Native visual QA at desktop sizes |
| Automatic realm coverage | All supported-region realm metadata, one feed per AH cluster, own markets inferred from characters | Catalog-layout monitoring; live full-region scale profiling |
| Gurubashi exclusion | Connected cluster grouping, no comparisons within that group | Match client/server identity in game |
| Automatic bags/wallet | Login, bag and money events | Native API/secret-value regression |
| Bank/warbank | Open-bank captures, shared identity, non-wiping unavailable tabs | Native tab and transfer tests |
| Mailboxes | Item attachments, COD, receivable money, loaded/total completeness | Native inbox pagination, sale/return/COD cases |
| Auctions/guild/equipped | Owned auctions, viewed guild bank and equipped capture | Native event timing and inventory semantics |
| Safe companion | Stable export parsing; no Lua execution or SavedVariables writes; atomic data-addon publication, immediate explicit clipboard import/export, automatic addon-file updates for /reload | Native Wine/Proton process verification and migration tests |
| Guided arbitrage | Persistent timed multi-realm sessions, configurable stock/gold targets, exact-stack player-click moves, TSM handoff, auction-key undercut checks, sale collection | Complete custom purchase UI; exact variants; native protected-action/taint tests |
| Crafting | Learned/unlearned recipe capture, available CraftSim profit observation, timed minimum-stock runs, price/demand-backed exploration with requirement detail | Full quality/gear/Knowledge/concentration optimization, order/recraft support, multi-character allocation |
| Housing focus | Decor classification and focused crafting view | Complete production/restocking/dependency planning |
| Lumber estimates | Personal measured sessions, provider registration, time-weighted server rates, read-only calculator | Verified adapters for user's actual lumber addon; full localized item catalog |
| Theme/flexible UI | Three palettes, rounded panels, gradients, resizing, page pooling and help | Native resolution/scale/scroll/focus regression |
| Missing data | Live-only dashboard; legacy demo settings ignored; unknown balances and capture/feed issues visible | Native capture completeness verification |
| Monetization room | Server-side provider/access interface; self-hosted features unlocked | Separate policy/licensing and product review; no billing/paywall exists |

No fake data is portrayed as observed. Unknown storage, missing simulations and unavailable integrations remain explicitly unknown. See the roadmap for work needed before a production-complete claim.
