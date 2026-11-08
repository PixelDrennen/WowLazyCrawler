local _,LC=...
LC.modeNames={flip="Realm flip",posting="Posting",craft="Craft available",discover="Explore crafting"}
local function clamp(value,default,max) return math.max(1,math.min(max or 200,math.floor(tonumber(value) or default))) end
function LC:SessionElapsed()
    local s=self.db.activity;if not s then return 0 end
    return (s.seconds or 0)+(s.state=="running" and self.activityTick and math.max(0,GetTime()-self.activityTick) or 0)
end
function LC:CheckpointSession()
    local s=self.db.activity;if not s then return end
    s.seconds=self:SessionElapsed();self.activityTick=GetTime()
end
function LC:ToggleSessionPause()
    local s=self.db.activity;if not s or s.state=="stopped" or s.state=="complete" then return end
    self:CheckpointSession();s.state=s.state=="paused" and "running" or "paused";self:Changed()
end
function LC:StopActivity(complete)
    local s=self.db.activity;if not s then return end
    self:CheckpointSession();s.state=complete and "complete" or "stopped";s.ended_at=time();self:Changed()
end
function LC:SessionRoutes()
    local result={};local s=self.db.activity
    for _,key in ipairs(s and s.routes or {}) do if self.db.tasks[key] then result[#result+1]=self.db.tasks[key] end end
    return result
end
function LC:SessionMarkets(destination)
    local result,seen={},{}
    for _,t in ipairs(self:SessionRoutes()) do
        local realm=destination and t.to_realm or t.from_realm
        local key=self:Cluster(realm) or realm
        if not seen[key] then result[#result+1]=realm;seen[key]=true end
    end
    return result
end
function LC:SessionRealm()
    local s=self.db.activity;if not s then return end
    return self:SessionMarkets(s.phase~="buy" and s.phase~="deposit")[s.market or 1]
end
function LC:SessionItems()
    local result={};local s=self.db.activity;local realm=self:SessionRealm()
    for _,t in ipairs(self:SessionRoutes()) do
        local routeRealm=(s.phase=="buy" or s.phase=="deposit") and t.from_realm or t.to_realm
        if self:Cluster(routeRealm)==self:Cluster(realm) or routeRealm==realm then result[#result+1]=t end
    end
    return result
end
function LC:RecipeProfit(r)
    local sim=r.simulation
    if sim and sim.observed_at and time()-sim.observed_at<=43200 then return sim.profit_copper end
end
function LC:StartActivity(mode)
    local old=self.db.activity
    if old and (old.state=="running" or old.state=="paused") then self:Print("Stop the current session before starting another.");return false end
    if mode=="discover" then self.page="discover";self:RefreshUI();return true end
    local settings=self.db.settings
    local s={id="session:"..time()..":"..math.random(1000,9999),name=self.modeNames[mode],mode=mode,state="running",seconds=0,created_at=time(),market=1,
        stock=clamp(settings.minimumStock,1),bulk=clamp(settings.bulkQuantity,3),gold=math.max(0,math.min(1000000,tonumber(settings.postingGold) or 500)),routes={},recipes={}}
    if mode=="flip" or mode=="posting" then
        -- Completed crafting runs hand their observed outputs into a separate posting run.
        if mode=="posting" and old and old.mode=="craft" then
            for _,r in ipairs(self:SessionCrafts()) do
                if r.output_item_id and self.db.warbank and self:Count(self.db.warbank.items,r.output_item_id,true)>0 then
                    local destination=self:Current().realm
                    for _,estimate in ipairs(self.data.crafting_discovery or {}) do
                        if estimate.output_item_id==r.output_item_id and estimate.destination_realm and estimate.expires_at and estimate.expires_at>=time() and estimate.destination_realm~="Region-wide commodities" and (estimate.profit_copper or 0)>0 then destination=estimate.destination_realm;break end
                    end
                    local id="crafted:"..r.output_item_id..":"..destination
                    self.db.tasks[id]={id=id,name=r.name,item_id=r.output_item_id,from_realm=self:Current().realm,to_realm=destination,state="prepared",created_at=time(),origin="Observed crafting output"}
                end
            end
        end
        local tasks={};for _,t in pairs(self.db.tasks) do
            if t.state~="complete" and t.state~="skipped" and (not t.expires_at or t.expires_at>=time()) then tasks[#tasks+1]=t end
        end
        table.sort(tasks,function(a,b)return a.id<b.id end)
        if #tasks==0 and mode=="flip" then
            local selected={}
            for _,candidate in ipairs(self.data.opportunities or {}) do
                if #tasks>=10 then break end
                if not selected[candidate.item_key] and (not candidate.expires_at or candidate.expires_at>=time()) then
                    self:QueueCandidate(candidate);selected[candidate.item_key]=true
                end
            end
            for _,t in pairs(self.db.tasks) do if t.state~="complete" and t.state~="skipped" and (not t.expires_at or t.expires_at>=time()) then tasks[#tasks+1]=t end end
            table.sort(tasks,function(a,b)return a.id<b.id end)
        end
        for _,t in ipairs(tasks) do s.routes[#s.routes+1]=t.id end
        if #s.routes==0 then self:Print("No verified routes available. Refresh market feeds in the desktop app, /reload, and queue routes in Radar.");return false end
        s.phase=mode=="flip" and "buy" or "withdraw"
    elseif mode=="craft" then
        self:CaptureSimulation()
        local ranked={}
        for _,r in ipairs(self:Current().recipes or {}) do
            if r.learned~=false and not r.disabled and (self:RecipeProfit(r) or 0)>0 then ranked[#ranked+1]=r end
        end
        table.sort(ranked,function(a,b)return self:RecipeProfit(a)>self:RecipeProfit(b) end)
        for i=1,math.min(10,#ranked) do s.recipes[#s.recipes+1]=ranked[i].id end
        if #s.recipes==0 then self:Print("No fresh profitable CraftSim observations for this character. Open a learned recipe in CraftSim, then refresh its simulation.");return false end
        s.character=self.characterKey;s.phase="review"
    else return false end
    self.db.activity=s;self.activityTick=GetTime();self.page="queue";self:Changed();return true
end
function LC:SessionCrafts()
    local result={};local s=self.db.activity
    local char=s and self.db.characters[s.character]
    for _,id in ipairs(s and s.recipes or {}) do for _,r in ipairs(char and char.recipes or {}) do if r.id==id then result[#result+1]=r end end end
    return result
end
function LC:PlanSessionCrafts()
    local s=self.db.activity
    for _,r in ipairs(self:SessionCrafts()) do
        local owned=r.output_item_id and self:UsableCount(r.output_item_id) or 0
        r.crafts=math.max(0,math.ceil((s.stock-owned)/(r.output_quantity or 1)))
    end
    self:Changed()
end
function LC:SessionHint()
    local s=self.db.activity;if not s then return "Choose a mode to begin a guided session." end
    if s.state~="running" then return s.state=="paused" and "Session paused. Resume when you are ready; no actions or elapsed time accrue while paused." or "Session ended. Choose a mode for your next run." end
    local realm=self:SessionRealm()
    local hints={buy="Buy the listed quantities on "..tostring(realm)..". Search each item, check its exact variant and live price, then buy through the auction UI.",
        deposit="On "..tostring(realm)..", open your warbank. Move the route items and deposit your gold, then continue to the next source realm.",
        withdraw="Log into a posting alt on "..tostring(realm).." (or create one). Open your warbank; withdraw the target stock and top up the posting wallet.",
        post="Use TSM Auctioning on "..tostring(realm).." to run a post scan and post the prepared items. This step waits for observed owned auctions.",
        undercuts="Before logging out, run a TSM Auctioning cancel scan, review undercuts, cancel/repost as needed, then confirm the review below.",
        review="Review profitable recipes captured for this character. Adjust minimum stock, prepare materials with Auctionator/TSM, and simulate quality and specializations in CraftSim.",
        craft="Craft the queued quantities in your profession UI with CraftSim. Output stock is checked before the next phase.",
        craft_deposit="Open the warbank, deposit crafted outputs and gold. Posting is a separate session."}
    if s.character and s.character~=self.characterKey then return "Log into "..s.character.." to continue this crafting session." end
    return hints[s.phase] or "Choose a session."
end
function LC:SessionNext()
    local s=self.db.activity;if not s or s.state~="running" then return end
    if s.character and s.character~=self.characterKey then self:Print(self:SessionHint());return end
    local char=self:Current();local bags=char.storages.bags
    local count=function(id)return self:Count(bags and bags.items,id,true) end
    if s.phase=="buy" or s.phase=="withdraw" then
        if not self:Here(self:SessionRealm()) then self:Print(self:SessionHint());return end
        for _,t in ipairs(self:SessionItems()) do
            local goal=s.phase=="buy" and s.bulk or s.stock
            if count(t.item_id)<goal then self:Print("Still need "..goal.." × "..t.name.." in this character's bags. Reduce the target or explicitly remove the route in Radar.");return end
        end
        if s.phase=="withdraw" and GetMoney()<s.gold*10000 then self:Print("Top up the posting wallet before continuing.");return end
        s.phase=s.phase=="buy" and "deposit" or "post";s.phase_at=time()
        if s.phase=="post" then
            s.auctionBaseline={};for _,t in ipairs(self:SessionItems()) do s.auctionBaseline[t.id]=self:Count(char.storages.auctions and char.storages.auctions.items,t.item_id,true) end
        end
    elseif s.phase=="deposit" or s.phase=="craft_deposit" then
        if not self.bankOpen or not self.db.warbank or self.db.warbank.observed_at<(s.phase_at or s.created_at) then self:Print("Open the warbank and wait for a current capture.");return end
        local items=s.phase=="deposit" and self:SessionItems() or self:SessionCrafts()
        for _,t in ipairs(items) do if count(t.item_id or t.output_item_id)>0 then self:Print("Route/crafted items remain in bags. Deposit them before continuing.");return end end
        if GetMoney()>0 then self:Print("Deposit the remaining wallet gold before continuing.");return end
        if s.phase=="craft_deposit" then self:StopActivity(true);return end
        if (s.market or 1)<#self:SessionMarkets(false) then s.market=s.market+1;s.phase="buy" else s.market=1;s.phase="withdraw" end
    elseif s.phase=="post" then
        local auctions=char.storages.auctions
        if not self:Here(self:SessionRealm()) or not auctions or auctions.observed_at<(s.phase_at or s.created_at) then self:Print("Open the auction house and wait for owned auctions to update after posting.");return end
        for _,t in ipairs(self:SessionItems()) do if self:Count(auctions.items,t.item_id,true)<(s.auctionBaseline[t.id] or 0)+s.stock then self:Print("Posting target not yet observed for "..t.name..". Complete the TSM post scan.");return end end
        s.phase="undercuts"
    elseif s.phase=="undercuts" then
        -- No supported TSM scan-completion API: this is an explicit player acknowledgement.
        if not self.auctionOpen or not self:Here(self:SessionRealm()) then self:Print("Review undercuts at this realm's auction house first.");return end
        s.last_undercut_review=time()
        if s.market<#self:SessionMarkets(true) then s.market=s.market+1;s.phase="withdraw" else self:StopActivity(true);return end
    elseif s.phase=="review" then self:PlanSessionCrafts();s.phase="craft"
    elseif s.phase=="craft" then
        for _,r in ipairs(self:SessionCrafts()) do if not r.output_item_id or self:UsableCount(r.output_item_id)<s.stock then self:Print("Minimum output stock has not been observed for "..r.name);return end end
        s.phase="craft_deposit";s.phase_at=time()
    end
    self:Changed()
end
function LC:SessionBankAction(gold)
    local s=self.db.activity
    if not s or s.state~="running" or InCombatLockdown() or not self.bankOpen then self:Print("Open the warbank during an active session outside combat.");return end
    if s.character and s.character~=self.characterKey then self:Print(self:SessionHint());return end
    if s.mode~="craft" and not self:Here(self:SessionRealm()) then self:Print(self:SessionHint());return end
    local kind=Enum and Enum.BankType and Enum.BankType.Account
    if not kind or not C_Bank or not self:Call(C_Bank.CanUseBank,kind) then self:Print("The warbank is not currently usable.");return end
    if self.bankActionPending and GetTime()-self.bankActionPending<2 then self:Print("Wait for the previous bank action to update.");return end
    if CursorHasItem and CursorHasItem() then self:Print("Clear the item on your cursor first.");return end
    self.bankActionPending=GetTime()
    local withdraw=s.phase=="withdraw"
    if not withdraw and s.phase~="deposit" and s.phase~="craft_deposit" then return end
    if gold then
        if withdraw then
            local amount=math.max(0,s.gold*10000-GetMoney())
            local available=self:Call(C_Bank.FetchDepositedMoney,kind)
            if not available or available<amount then self:Print("Insufficient observed warbank gold for this posting target.");return end
            if amount>0 then self:Call(C_Bank.WithdrawMoney,kind,amount) end
        elseif GetMoney()>0 then self:Call(C_Bank.DepositMoney,kind,GetMoney()) end
        return
    end
    local items=s.mode=="craft" and self:SessionCrafts() or self:SessionItems()
    for _,t in ipairs(items) do
        local id=t.item_id or t.output_item_id
        local bag,slot,info
        if withdraw then
            local held=self:Count(self:Current().storages.bags and self:Current().storages.bags.items,id,true)
            local needed=math.max(0,s.stock-held)
            if needed>0 then
                for _,tab in ipairs(self:Call(C_Bank.FetchPurchasedBankTabIDs,kind) or {}) do
                    for index=1,(self:Call(C_Container.GetContainerNumSlots,tab) or 0) do
                        local item=self:Call(C_Container.GetContainerItemInfo,tab,index)
                        if item and item.itemID==id then
                            if item.isLocked then self:Print("Wait for the bank item to unlock.");return end
                            if item.stackCount>needed then
                                -- Split only into an available bag slot; never move more than the configured target.
                                if not C_Container.SplitContainerItem or not C_Container.PickupContainerItem then self:Print("Split "..needed.." items through the bank UI; stack-splitting API unavailable.");return end
                                for dest=0,(NUM_TOTAL_EQUIPPED_BAG_SLOTS or 4) do for empty=1,(C_Container.GetContainerNumSlots(dest) or 0) do
                                    if not C_Container.GetContainerItemInfo(dest,empty) then
                                        C_Container.SplitContainerItem(tab,index,needed);C_Container.PickupContainerItem(dest,empty);return
                                    end
                                end end
                                self:Print("Free a bag slot before withdrawing a partial stack.");return
                            end
                            C_Container.UseContainerItem(tab,index);return
                        end
                    end
                end
            end
        else
            bag,slot,info=self:FindBagItem(id)
            if bag then
                if info.isLocked then self:Print("Wait for the bag item to unlock.");return end
                local eligible=self:Call(C_Bank.IsItemAllowedInBankType,kind,ItemLocation:CreateFromBagAndSlot(bag,slot))
                if eligible~=true then self:Print("Transfer eligibility could not be verified for "..t.name);return end
                C_Container.UseContainerItem(bag,slot,kind);return
            end
        end
    end
    self:Print("No remaining planned items to move in accessible tabs. Wait for captures to update.")
end
LC:On("PLAYER_LOGIN",function() if LC.db then LC.activityTick=GetTime() end end)
LC:On("PLAYER_LOGOUT",function() if LC.db then LC:CheckpointSession();LC:Export() end end)

local function auctionKey(key)
    return table.concat({key.itemID or 0,key.itemLevel or 0,key.itemSuffix or 0,key.battlePetSpeciesID or 0},":")
end
function LC:CheckUndercut(task)
    local s=self.db.activity
    if not s or s.state~="running" or s.phase~="undercuts" or InCombatLockdown() or not self.auctionOpen or not self:Here(self:SessionRealm()) then self:Print("Open the posting realm's auction house during the undercut phase.");return end
    local api=C_AuctionHouse
    if not api or not api.GetOwnedAuctionInfo or not api.SendSearchQuery then self:Print("Live auction search API unavailable. Review a TSM cancel scan instead.");return end
    if self.undercutSearch and GetTime()-self.undercutSearch.started<15 then self:Print("A scan is still waiting for results. Retry after 15 seconds if it times out.");return end
    if api.IsThrottledMessageSystemReady and not api.IsThrottledMessageSystemReady() then self:Print("Auction search throttled. Try again shortly.");return end
    s.undercuts=s.undercuts or {}
    local variants={}
    for i=1,(api.GetNumOwnedAuctions() or 0) do
        local own=api.GetOwnedAuctionInfo(i)
        if own and own.itemKey and own.itemKey.itemID==task.item_id and own.buyoutAmount and own.buyoutAmount>0 then
            local key=auctionKey(own.itemKey);local value=own.buyoutAmount/math.max(1,own.quantity or 1)
            if not variants[key] or variants[key].price>value then variants[key]={key=own.itemKey,price=value} end
        end
    end
    local selected
    for key,variant in pairs(variants) do
        if not s.undercuts[key] or time()-s.undercuts[key].observed_at>60 then selected=variant;break end
    end
    if not selected then self:Print("No unscanned owned variants found. Results apply only to observed auction keys and remain a price check, not a sale guarantee.");return end
    self.undercutSearch={key=selected.key,price=selected.price,session=s.id,started=GetTime(),realm=self:SessionRealm()}
    self:Call(api.SendSearchQuery,selected.key,{},true)
    self:Print("Checking a posted variant. Wait for results before scanning the next variant.")
end
LC:On("ITEM_SEARCH_RESULTS_UPDATED",function(key)
    local request=LC.undercutSearch;local s=LC.db and LC.db.activity;local api=C_AuctionHouse
    if not request or not key or auctionKey(request.key)~=auctionKey(key) then return end
    if not s or s.id~=request.session or s.state~="running" or s.phase~="undercuts" or not LC.auctionOpen or not LC:Here(request.realm) or GetTime()-request.started>15 then LC.undercutSearch=nil;return end
    if not api.HasFullItemSearchResults or not api.HasFullItemSearchResults(key) then LC:Print("Partial search results. Continue the scan in TSM before confirming review.");return end
    local cheapest
    for i=1,(api.GetNumItemSearchResults(key) or 0) do
        local result=api.GetItemSearchResultInfo(key,i)
        if result and not result.containsOwnerItem and not result.containsAccountItem and result.buyoutAmount and result.buyoutAmount>0 then
            local value=result.buyoutAmount/math.max(1,result.quantity or 1)
            cheapest=math.min(cheapest or value,value)
        end
    end
    s.undercuts[auctionKey(key)]={item_id=key.itemID,observed_at=time(),own_price=request.price,competitor_price=cheapest,
        status=cheapest and cheapest<request.price and "Undercut detected" or "No cheaper result in this auction-key scan"}
    LC.undercutSearch=nil;LC:Changed()
end)
LC:On("AUCTION_HOUSE_CLOSED",function() LC.undercutSearch=nil end)
function LC:SkipSessionRoute(id)
    local s=self.db.activity;if not s or s.state~="running" then return end
    for index,key in ipairs(s.routes) do if key==id then table.remove(s.routes,index);break end end
    if self.db.tasks[id] then self.db.tasks[id].state="skipped" end
    if #s.routes==0 then self:StopActivity(false) else s.market=math.min(s.market,#self:SessionMarkets(s.phase~="buy" and s.phase~="deposit")) end
    self:Changed()
end
