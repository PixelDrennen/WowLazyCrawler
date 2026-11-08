local _,LC=...
local function normalized(value) return tostring(value or ""):lower():gsub("[%s%-']","") end
function LC:Cluster(realm)
    for _,market in ipairs(self.data.catalog or {}) do
        for _,member in ipairs(market.realms or {}) do
            if normalized(member.slug)==normalized(realm) or normalized(member.name)==normalized(realm) then return market.connected_id end
        end
    end
    return nil
end
function LC:Here(realm)
    local char=self:Current();if not char then return false end
    local a,b=self:Cluster(char.realm),self:Cluster(realm)
    return a and b and a==b or normalized(char.realm)==normalized(realm)
end
function LC:Count(items,id,usable)
    local result=0
    for _,item in ipairs(items or {}) do if item.item_id==id and (not usable or not item.cod) then result=result+item.count end end
    return result
end
function LC:UsableCount(id)
    local result=0
    -- Personal bags/bank/reagents across characters, shared warbank exactly once.
    -- Mail, equipped, guild storage and active auctions are not spendable reagent stock.
    for key,char in pairs(self.db.characters or {}) do
        for _,scope in ipairs({"bags","bank","reagents"}) do
            local capture=char.storages[scope]
            if capture and capture.complete~=false and time()-capture.observed_at<=86400 then
                for _,item in ipairs(capture.items or {}) do
                    if item.item_id==id and not item.cod and (key==self.characterKey or item.transferable==true) then result=result+item.count end
                end
            end
        end
    end
    if self.db.warbank and self.db.warbank.complete~=false and time()-self.db.warbank.observed_at<=86400 then result=result+self:Count(self.db.warbank.items,id,true) end
    return result
end
function LC:FindBagItem(id)
    for bag=0,(NUM_TOTAL_EQUIPPED_BAG_SLOTS or 4) do
        local slots=self:Call(C_Container.GetContainerNumSlots,bag) or 0
        for slot=1,slots do
            local info=self:Call(C_Container.GetContainerItemInfo,bag,slot)
            if info and info.itemID==id then return bag,slot,info end
        end
    end
end
function LC:QueueCandidate(candidate)
    if candidate.expires_at and time()>candidate.expires_at then self:Print("This market evidence expired. Refresh the server and load a fresh bundle.");return end
    local id=tonumber(candidate.item_key)
    if not id then self:Print("This item identity is unsupported.");return end
    local source,dest=self:Cluster(candidate.source_realm),self:Cluster(candidate.destination_realm)
    if not source or not dest or source==dest then self:Print("Separate auction clusters must be verified before this route can be queued.");return end
    local key=id..":"..source..":"..dest
    if self.db.tasks[key] and self.db.tasks[key].state~="complete" and self.db.tasks[key].state~="skipped" and (not self.db.tasks[key].expires_at or self.db.tasks[key].expires_at>=time()) then self:Print("This route is already queued.");return end
    self.db.tasks[key]={id=key,item_id=id,name=candidate.name,from_realm=candidate.source_realm,to_realm=candidate.destination_realm,
        state="review",buy_ceiling=candidate.buyout,post_price=candidate.estimated_sale,net_profit=candidate.net_profit,created_at=time(),quantity=1,
        evidence_time=candidate.observed_at,expires_at=candidate.expires_at,risks=candidate.risks}
    self.page="queue";self:Changed()
end
function LC:TaskHint(t)
    if t.state=="review" then return "Review exact variant and binding, then acknowledge the route." end
    if t.state=="acquire" then return "Log into "..t.from_realm.." or a connected realm. Open the auction house and verify the live listing." end
    if t.state=="retrieve" then return "Open the bank on the source character. Only transfer-eligible bag items can enter the warbank." end
    if t.state=="transfer" then return "Log into "..t.to_realm.." or a connected realm. Withdraw the item from your warbank." end
    if t.state=="post" then return "Open the auction house on the destination character. Review the posting price and deposit." end
    if t.state=="collect" then return "Wait for a sale and open this character’s mailbox. Sale proceeds are separate from liquid gold until collected." end
    return "Completed from observed game events."
end
function LC:FindSaleMail(t)
    if not self.mailOpen or not GetInboxInvoiceInfo then return nil end
    local count=GetInboxNumItems()
    for index=1,count do
        local invoice,itemName=GetInboxInvoiceInfo(index)
        local _,_,_,_,money,cod=GetInboxHeaderInfo(index)
        if invoice=="seller" and itemName==t.name and money and money>0 and (not cod or cod==0) then return index,money end
    end
end
function LC:AdvanceTasks(event)
    local char=self:Current();if not char then return end
    local bagCount=function(id)return self:Count(char.storages.bags and char.storages.bags.items,id,true) end
    for _,t in pairs(self.db.tasks) do
        if t.state=="acquire" and t.baseline~=nil and self:Here(t.from_realm) and bagCount(t.item_id)>t.baseline then
            t.state="retrieve";t.character=char.name
        elseif t.state=="retrieve" and self:Here(t.from_realm) and self.db.warbank and self:Count(self.db.warbank.items,t.item_id,true)>(t.warbankBaseline or 0) then
            t.state="transfer"
        elseif t.state=="transfer" and self:Here(t.to_realm) and bagCount(t.item_id)>0 then
            t.state="post";t.character=char.name;t.auctionBaseline=self:Count(char.storages.auctions and char.storages.auctions.items,t.item_id,true)
        elseif t.state=="post" and event=="auctions" and self:Here(t.to_realm) and self:Count(char.storages.auctions.items,t.item_id,true)>(t.auctionBaseline or 0) then
            t.state="collect"
        elseif t.state=="collect" and t.pendingCollection and self:Here(t.to_realm) then
            if time()-t.pendingCollection.at<=30 and GetMoney()-t.pendingCollection.wallet>=t.pendingCollection.money and not self:FindSaleMail(t) then
                t.state="complete";t.realized_receipt=t.pendingCollection.money;t.completed_at=time();t.pendingCollection=nil
            end
        end
    end
end
function LC:SearchTask(t)
    if t.expires_at and t.expires_at<time() then self:Print("Market evidence expired. Refresh the server bundle before buying.");return end
    if self.db.activity and self.db.activity.state=="paused" then self:Print("Resume the session before searching.");return end
    if InCombatLockdown() or not self.auctionOpen or not self:Here(t.from_realm) then self:Print(self:TaskHint(t));return end
    local char=self:Current();t.baseline=t.baseline or self:Count(char.storages.bags and char.storages.bags.items,t.item_id,true)
    t.searchKey={itemID=t.item_id,itemLevel=0,itemSuffix=0,battlePetSpeciesID=0}
    if C_AuctionHouse and C_AuctionHouse.SendSearchQuery then
        if C_AuctionHouse.IsThrottledMessageSystemReady and not C_AuctionHouse.IsThrottledMessageSystemReady() then self:Print("Auction search is throttled. Try again shortly.");return end
        self:Call(C_AuctionHouse.SendSearchQuery,t.searchKey,{},true)
        self.searchingTask=t;self:Print("Search requested. Verify the live item in the auction UI; variants may need a specific item-level search.")
    end
end
function LC:TaskAction(t)
    if InCombatLockdown() then self:Print("Continue this workflow outside combat.");return end
    local char=self:Current()
    if (t.state=="acquire" or t.state=="post") and t.expires_at and time()>t.expires_at then self:Print("Price evidence expired. Review refreshed server data before spending or posting.");return end
    if t.state=="review" then
        t.state="acquire";t.warbankBaseline=self.db.warbank and self:Count(self.db.warbank.items,t.item_id,true) or 0
        self:Print("Route acknowledged. Binding and exact variant must still be verified in the live auction UI.")
    elseif t.state=="acquire" then self:SearchTask(t)
    elseif t.state=="retrieve" then
        if not self.bankOpen or not self:Here(t.from_realm) then self:Print(self:TaskHint(t));return end
        local bag,slot,info=self:FindBagItem(t.item_id)
        local location=bag and ItemLocation:CreateFromBagAndSlot(bag,slot)
        local eligible=location and C_Bank and self:Call(C_Bank.IsItemAllowedInBankType,Enum.BankType.Account,location)
        if eligible~=true then self:Print("Transfer eligibility could not be verified. This item has not been moved.");return end
        if info.stackCount~=1 then self:Print("This action transfers one item. Split this stack to one item first.");return end
        C_Container.UseContainerItem(bag,slot,Enum.BankType.Account)
    elseif t.state=="transfer" then
        if not self.bankOpen or not self:Here(t.to_realm) then self:Print(self:TaskHint(t));return end
        local ids=C_Bank and self:Call(C_Bank.FetchPurchasedBankTabIDs,Enum.BankType.Account)
        for _,bag in ipairs(ids or {}) do for slot=1,(C_Container.GetContainerNumSlots(bag) or 0) do
            local info=C_Container.GetContainerItemInfo(bag,slot)
            if info and info.itemID==t.item_id then
                if info.stackCount~=1 then self:Print("Withdraw or split one item through the bank UI.");return end
                C_Container.UseContainerItem(bag,slot);return
            end
        end end
        self:Print("The item was not found in accessible warbank tabs.")
    elseif t.state=="post" then
        if not self.auctionOpen or not self:Here(t.to_realm) then self:Print(self:TaskHint(t));return end
        local bag,slot,info=self:FindBagItem(t.item_id)
        if not bag or info.isBound then self:Print("An unbound matching bag item is required.");return end
        local location=ItemLocation:CreateFromBagAndSlot(bag,slot)
        if not C_AuctionHouse or not C_AuctionHouse.PostItem then return end
        if self.confirmPost and self.confirmPost.id==t.id then
            self:Call(C_AuctionHouse.ConfirmPostItem,location,2,1,nil,t.post_price);self.confirmPost=nil
        else
            local needs=self:Call(C_AuctionHouse.PostItem,location,2,1,nil,t.post_price)
            if needs then self.confirmPost={id=t.id};self:Print("Posting needs confirmation. Review and click Confirm posting.") end
        end
    elseif t.state=="collect" then
        if not self:Here(t.to_realm) then self:Print(self:TaskHint(t));return end
        local index,money=self:FindSaleMail(t)
        if not index then self:Print("Open the mailbox after a matching sale arrives. No unrelated mail is collected.");return end
        t.pendingCollection={wallet=GetMoney(),money=money,at=time()}
        TakeInboxMoney(index)
    end
    self:Changed()
end
function LC:ActionLabel(t)
    if t.state=="review" then return "Acknowledge route" end
    if t.state=="acquire" then return "Search live auctions" end
    if t.state=="retrieve" then return "Deposit one item" end
    if t.state=="transfer" then return "Withdraw one item" end
    if t.state=="post" then return self.confirmPost and self.confirmPost.id==t.id and "Confirm posting" or ("Post 1 @ "..self:Gold(t.post_price)) end
    if t.state=="collect" then return "Collect matching sale" end
    return "Complete"
end
function LC:Gold(copper) return string.format("%.1fg",(copper or 0)/10000) end
LC:On("ITEM_SEARCH_RESULTS_UPDATED",function() if LC.RefreshUI then LC:RefreshUI() end end)
