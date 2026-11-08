# Addon and companion

## Files and modules

`addon/LazyCrawler`: Core (lifecycle/export), Capture (accessible storage and money), Crafting (recipe/simulation/material/lumber adapters), Workflow (guided route states and player actions), UI (reusable rounded panels, palettes, lists and diagnostics). `LazyCrawler_Data` is a separate server-generated data addon.

Both addons load through ordinary Retail TOCs. `/lc` opens the UI; `/lc capture` captures currently accessible data; `/lc gather` starts/stops a measured session; `/lc help` enables contextual guidance. Retail APIs are capability-checked. The build has not yet been certified against the user's client build; an out-of-date TOC must be updated only after that version is tested.

## Capture triggers

| Source | Trigger | Important limit |
| --- | --- | --- |
| Wallet/bags | Login, bag updates, money updates | Combat capture defers until safe |
| Equipped items | Login/equipment changes | Not tradable reagent stock |
| Character/warbank | Bank opened and container updates | Only viewable, loaded purchased tabs; zero-slot unavailable tabs do not erase old data |
| Mail | Mailbox opened/inbox updated | Partial inbox retained as partial; COD marked; gold stays receivable |
| Auctions | AH opened / owned-auctions update | Listed items are not liquid gold or usable reagents |
| Guild bank | Guild bank opened/viewed tab changes | Partial viewed-tab data; excluded from personal funds |
| Recipes | Profession opened/list updated | Learned recipes from the currently accessible profession |
| Crafting results | Client crafting result event | Decrements the observed queued recipe when result identity is available |

Capture handlers contain errors so one missing API does not stop the whole addon. Errors appear in Settings & diagnostics. This is not a substitute for native regression tests against TSM, Auctionator and banking UIs.

## Guided routes

Review → acquire → retrieve → transfer → post → collect → complete. Source/destination cluster checks, stale-evidence checks, baselines and observed item changes determine progress. A user click authorizes supported single-item bank movement, posting or matching-sale collection. Other mail is not collected by a task. Posting price is shown on the action button; a required confirmation remains a separate click.

The current acquisition action issues an item search and uses the existing auction UI to verify/buy the exact listing. It does not implement a complete custom auction purchase surface. Full item-variant matching, portfolio exposure/duplicate limits, deposits, auction failures and native protected-action behavior remain validation/implementation gates. No unattended buying or posting is scheduled.

## CraftSim and Auctionator

CraftSim's documented open-recipe data and average-profit methods are called only when present. Their failure leaves simulation unavailable. Specialization/quality/stats are not reconstructed from guesses. Known recipes and `C_Item.IsDecorItem` produce a dedicated housing view. The server reviews observations rather than requiring JSON recipe forms.

Resolved, single-choice material requirements are consolidated once across the current character's queue. Shared stock is counted once; stale captures, COD mail, equipped items, guild storage, auctions and unverified transferable stock on other characters are excluded. Multiple quality alternatives stay unresolved until a supported simulation/quality-selection adapter exists.

Auctionator API v1 is capability-detected. The initial operation uses `MultiSearch` when present, with quantities retained in LazyCrawler's material plan. The current official repository/API documentation could not be retrieved, so that call still requires installed-version validation. No unrelated Auctionator lists are overwritten; no unsupported queue or list internals are modified.

## Lumber providers

Personal sessions count the player's own recognized lumber loot and measure elapsed time, including travel. The initial recognition path uses observed recipe reagent names containing “lumber” (English client) plus registered provider item IDs. It does not claim a complete localized lumber catalog.

Providers can register without changing their internal storage:

```lua
LazyCrawler:RegisterLumberProvider("ProviderName", function()
    return {
        {id="stable-session-id", item_id=ITEM_ID, quantity=100, seconds=1800, zone="Zone name"}
    }
end)
```

Only positive quantities, sessions of at least ten seconds and stable unique IDs are accepted. Time-weighted server rates use total quantity / total observed time, grouped by item, zone and provider. Unknown rates suppress an ETA; no fabricated average is substituted.

Housing Lumber Helper and Thendar's Lumber & Gathering Tracker are detected when loaded, but no stable documented session API was verified. They are shown as **detected without a verified adapter**, not falsely advertised as integrated. Their All Rights Reserved implementations are not copied or bundled. Version-specific adapters or a provider callback must be verified with the actual installed addon.

## Layout

A shared Grove/Spectral/Ember palette, first-party rounded texture, gradient highlights, clamped resize bounds, paginated scrolling, pooled rows, contextual help, scale control and combat hiding form the first UI layer. Repeated refreshes reuse rows. The test harness exercises page rendering and reuse, but cannot prove on-screen text bounds, native focus/scroll behavior, protected calls or taint safety. In-game tests at the user's resolutions/UI scales remain required.
