NOW=1770000000
COMBAT=false
MONEY=1000000
TIMERS={}
TAKEN_MAIL=nil
BAG_DATA={[0]={{itemID=2008,stackCount=3,hyperlink="item:2008",isBound=false,transferable=true}},[1]={},[2]={},[3]={},[4]={},[5]={},[100]={{itemID=2008,stackCount=7,hyperlink="item:2008",transferable=true}}}
MAILS={{money=20000,cod=0,name="Decor",item=777,quantity=2},{money=0,cod=50000,name="COD Decor",item=778,quantity=1}}
local Frame={}
Frame.__index=function(self,key)
    if Frame[key] then return Frame[key] end
    if key:match("^%u") then return function() end end
    return nil
end
function Frame:GetFrameLevel() return self.level or 1 end
function Frame:SetFrameLevel(level) self.level=level end
function Frame:SetSize(w,h) assert(type(w)=='number' and type(h)=='number');self.width=w;self.height=h end
function Frame:SetShown(value) self.shown=not not value end
function Frame:SetHeight(h) self.height=h end
function Frame:SetVerticalScroll(value) self.scroll=value end
function Frame:GetVerticalScroll() return self.scroll or 0 end
function Frame:SetWidth(w) self.width=w end
function Frame:GetWidth() return self.width or 850 end
function Frame:GetHeight() return self.height or 700 end
function Frame:SetScript(event,callback) self.scripts=self.scripts or {};self.scripts[event]=callback end
function Frame:IsShown() return self.shown end
function Frame:Show() self.shown=true end
function Frame:Hide() self.shown=false end
function Frame:SetText(text) self.text=tostring(text) end
function Frame:GetStringHeight() return math.max(12,math.ceil(#(self.text or "")/math.max(20,(self.width or 400)/6))*12) end
function Frame:CreateTexture() return setmetatable({},Frame) end
function Frame:CreateFontString() return setmetatable({},Frame) end
function CreateFrame(kind,name,parent,template) local f=setmetatable({name=name,parent=parent},Frame);if name then _G[name]=f end;return f end
UIParent=CreateFrame('Frame');UIParent:SetSize(1280,900)
STANDARD_TEXT_FONT='font'
UISpecialFrames={};SlashCmdList={}
function CreateColor(...) return {...} end
function time() return NOW end
function date(format,value) return os.date(format,value) end
function GetTime() return NOW end
function InCombatLockdown() return COMBAT end
function UnitFullName() return 'Hanami','Gurubashi' end
function GetRealmName() return 'Gurubashi' end
function UnitClass() return 'Hunter','HUNTER' end
function UnitLevel() return 90 end
function GetCurrentRegion() return 1 end
function BNGetInfo() return 123 end
function GetProfessions() return 1,2 end
function GetProfessionInfo(id) return id==1 and 'Alchemy' or 'Leatherworking' end
function GetMoney() return MONEY end
function GetInventoryItemLink() return nil end
function GetZoneText() return 'Eversong Woods' end
function GetInboxNumItems() return #MAILS,5 end
function GetInboxHeaderInfo(i) local m=MAILS[i];return nil,nil,'Auction House',m.name,m.money,m.cod,30,1 end
function GetInboxItemLink(i,slot) if slot==1 then return 'item:'..MAILS[i].item end end
function GetInboxItem(i,slot) if slot==1 then local m=MAILS[i];return m.name,m.item,nil,m.quantity end end
function GetInboxInvoiceInfo(i) return 'seller',MAILS[i].name end
function TakeInboxMoney(i) TAKEN_MAIL=i;MONEY=MONEY+MAILS[i].money;MAILS[i].money=0 end
C_Timer={After=function(_,callback) TIMERS[#TIMERS+1]=callback end}
function DrainTimers() local count=0;while #TIMERS>0 and count<1000 do count=count+1;local fn=table.remove(TIMERS,1);fn() end;assert(count<1000,'timer loop') end
NUM_TOTAL_EQUIPPED_BAG_SLOTS=5
C_Container={
 GetContainerNumSlots=function(bag) return #(BAG_DATA[bag] or {}) end,
 GetContainerItemInfo=function(bag,slot) return (BAG_DATA[bag] or {})[slot] end,
 UseContainerItem=function(bag,slot,kind) LAST_MOVE={bag,slot,kind} end,
}
ItemLocation={CreateFromBagAndSlot=function(_,bag,slot)return {bag=bag,slot=slot}end}
Enum={BankType={Character=1,Account=2}}
C_Bank={CanUseBank=function()return true end,CanViewBank=function()return true end,FetchPurchasedBankTabIDs=function(kind)return kind==2 and {100} or {} end,FetchDepositedMoney=function()return 500000 end,
 IsItemAllowedInBankType=function(kind,loc)local i=BAG_DATA[loc.bag][loc.slot];return i.transferable end}
C_AuctionHouse={GetNumOwnedAuctions=function()return 0 end,QueryOwnedAuctions=function()end,SendSearchQuery=function()end}
C_AddOns={IsAddOnLoaded=function()return false end}
C_Item={GetItemInfo=function(id)return id==2008 and 'Thalassian Lumber' or ('Item '..id) end,IsDecorItem=function(id)return id==777 end}
C_TradeSkillUI={GetAllRecipeIDs=function()return {42} end,GetRecipeInfo=function()return {learned=true,name='Decor'}end,
 GetBaseProfessionInfo=function()return {professionName='Alchemy'}end,
 GetRecipeSchematic=function()return {name='Decor',outputItemID=777,reagentSlotSchematics={{quantityRequired=4,reagents={{itemID=2008}}}}}end}
LOOT_ITEM_SELF='You receive loot: %s.'
LC={}
