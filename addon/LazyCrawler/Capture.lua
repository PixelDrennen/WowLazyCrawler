local _,LC=...
local function ready() return LC.db and not InCombatLockdown() end
local function storage(items,money,complete,note)
    return {observed_at=time(),items=items or {},money=money or 0,complete=complete~=false,note=note or ""}
end
function LC:BagItems(ids, requireSlots)
    if not C_Container or not C_Container.GetContainerNumSlots then return nil end
    local items={}
    for _,bag in ipairs(ids) do
        local slots=self:Call(C_Container.GetContainerNumSlots,bag)
        if type(slots)~="number" or (requireSlots and slots==0) then return nil end
        for slot=1,slots do
            local info=self:Call(C_Container.GetContainerItemInfo,bag,slot)
            if info and info.itemID and info.stackCount and info.stackCount>0 then
                local transferable
                if C_Bank and C_Bank.IsItemAllowedInBankType and ItemLocation and Enum and Enum.BankType then
                    local location=ItemLocation:CreateFromBagAndSlot(bag,slot)
                    transferable=self:Call(C_Bank.IsItemAllowedInBankType,Enum.BankType.Account,location)
                end
                items[#items+1]={item_id=info.itemID,count=info.stackCount,link=info.hyperlink or "",bound=info.isBound,transferable=transferable}
            end
        end
    end
    return items
end
function LC:CaptureBags()
    if not ready() then self.captureDeferred=true;return end
    local char=self:Current();if not char then return end
    local ids={0,1,2,3,4}
    if NUM_TOTAL_EQUIPPED_BAG_SLOTS and NUM_TOTAL_EQUIPPED_BAG_SLOTS>=5 then ids[#ids+1]=5 end
    local items=self:BagItems(ids)
    if not items then return end
    char.storages.bags=storage(items,GetMoney(),true,"Bags and wallet observed in game")
    if self.AdvanceTasks then self:AdvanceTasks("bags") end
    self:Changed()
end
function LC:CaptureEquipped()
    if not ready() then return end
    local char=self:Current();if not char then return end
    local items={}
    for slot=1,19 do
        local link=GetInventoryItemLink("player",slot)
        if link then local id=tonumber(link:match("item:(%d+)"));if id then items[#items+1]={item_id=id,count=1,link=link,bound=true,transferable=false} end end
    end
    char.storages.equipped=storage(items,0,true,"Equipped items; excluded from tradable stock")
    self:Changed()
end
function LC:CaptureBank()
    if not ready() or not self.bankOpen then return end
    local char=self:Current();if not char then return end
    local modern=C_Bank and C_Bank.FetchPurchasedBankTabIDs and Enum and Enum.BankType
    if modern then
        for _,entry in ipairs({{kind=Enum.BankType.Character,scope="bank"},{kind=Enum.BankType.Account,scope="warbank"}}) do
            local viewable=self:Call(C_Bank.CanViewBank,entry.kind)
            if viewable then
                local ids=self:Call(C_Bank.FetchPurchasedBankTabIDs,entry.kind)
                if ids then
                    local items=self:BagItems(ids,true)
                    if items then
                        local money=self:Call(C_Bank.FetchDepositedMoney,entry.kind) or 0
                        local result=storage(items,money,true,"Accessible purchased bank tabs observed")
                        if entry.scope=="warbank" then self.db.warbank=result else char.storages.bank=result end
                    end
                end
            end
        end
    else
        local ids={BANK_CONTAINER or -1}
        for bag=6,12 do ids[#ids+1]=bag end
        local items=self:BagItems(ids)
        if items then char.storages.bank=storage(items,0,true,"Legacy accessible bank containers") end
        local reagents=self:BagItems({REAGENTBANK_CONTAINER or -3})
        if reagents then char.storages.reagents=storage(reagents,0,true,"Legacy reagent bank") end
    end
    self:CaptureBags();self:Changed()
end
function LC:CaptureMail()
    if not ready() or not self.mailOpen or not GetInboxNumItems then return end
    local char=self:Current();if not char then return end
    local count,total=GetInboxNumItems()
    if type(count)~="number" then return end
    local items,money={},0
    for index=1,count do
        local _,_,_,_,cash,cod,_,attachments=GetInboxHeaderInfo(index)
        if cash and (not cod or cod==0) then money=money+cash end
        if attachments and (type(attachments)~="number" or attachments>0) then
            for attachment=1,(ATTACHMENTS_MAX_RECEIVE or 16) do
                local link=GetInboxItemLink(index,attachment)
                local _,id,_,amount=GetInboxItem(index,attachment)
                id=id or (link and tonumber(link:match("item:(%d+)")))
                if id and amount and amount>0 then items[#items+1]={item_id=id,count=amount,link=link or "",cod=cod and cod>0 or false} end
            end
        end
    end
    char.storages.mail=storage(items,money,count>=(total or count),"Uncollected mailbox gold; COD attachments are not usable stock")
    if self.AdvanceTasks then self:AdvanceTasks("mail") end
    self:Changed()
end
function LC:CaptureAuctions()
    if not ready() or not self.auctionOpen or not C_AuctionHouse then return end
    local char=self:Current();if not char then return end
    local count=self:Call(C_AuctionHouse.GetNumOwnedAuctions)
    if type(count)~="number" then return end
    local items={}
    for index=1,count do
        local item=self:Call(C_AuctionHouse.GetOwnedAuctionInfo,index)
        if item and item.itemKey and item.itemKey.itemID and item.quantity and item.quantity>0 then
            items[#items+1]={item_id=item.itemKey.itemID,count=item.quantity,link=item.itemLink or ""}
        end
    end
    char.storages.auctions=storage(items,0,true,"Owned auction snapshot; listed value is not liquid gold")
    if self.AdvanceTasks then self:AdvanceTasks("auctions") end
    self:Changed()
end
function LC:CaptureGuildBank()
    if not ready() or not self.guildOpen or not GetCurrentGuildBankTab then return end
    local char=self:Current();if not char then return end
    local tab=GetCurrentGuildBankTab();if not tab then return end
    local items={}
    for slot=1,(MAX_GUILDBANK_SLOTS_PER_TAB or 98) do
        local link=GetGuildBankItemLink(tab,slot)
        local _,count=GetGuildBankItemInfo(tab,slot)
        local id=link and tonumber(link:match("item:(%d+)"))
        if id and count and count>0 then items[#items+1]={item_id=id,count=count,link=link} end
    end
    char.storages.guild_bank=storage(items,GetGuildBankMoney() or 0,false,"Viewed guild tab "..tab.." only. Guild assets are excluded from personal inventory and capital.")
    self:Changed()
end
LC:On("BAG_UPDATE_DELAYED",function() LC:CaptureBags();if LC.bankOpen then LC:CaptureBank() end end)
LC:On("PLAYER_MONEY",function() LC:CaptureBags() end)
LC:On("PLAYER_EQUIPMENT_CHANGED",function() LC:CaptureEquipped() end)
LC:On("PLAYER_REGEN_ENABLED",function() if LC.captureDeferred then LC.captureDeferred=false;LC:CaptureBags() end end)
LC:On("BANKFRAME_OPENED",function() LC.bankOpen=true;C_Timer.After(.3,function() LC:Run("bank",function() LC:CaptureBank() end) end) end)
LC:On("PLAYERBANKSLOTS_CHANGED",function() LC:CaptureBank() end)
LC:On("BANKFRAME_CLOSED",function() LC.bankOpen=false end)
LC:On("MAIL_SHOW",function() LC.mailOpen=true;LC:CaptureMail() end)
LC:On("MAIL_INBOX_UPDATE",function() LC:CaptureMail() end)
LC:On("MAIL_CLOSED",function() LC.mailOpen=false end)
LC:On("AUCTION_HOUSE_SHOW",function() LC.auctionOpen=true;if C_AuctionHouse then LC:Call(C_AuctionHouse.QueryOwnedAuctions,{}) end end)
LC:On("OWNED_AUCTIONS_UPDATED",function() LC:CaptureAuctions() end)
LC:On("AUCTION_HOUSE_CLOSED",function() LC.auctionOpen=false end)
LC:On("GUILDBANKFRAME_OPENED",function() LC.guildOpen=true;LC:CaptureGuildBank() end)
LC:On("GUILDBANKBAGSLOTS_CHANGED",function() LC:CaptureGuildBank() end)
LC:On("GUILDBANK_UPDATE_MONEY",function() LC:CaptureGuildBank() end)
LC:On("GUILDBANKFRAME_CLOSED",function() LC.guildOpen=false end)
