local _,LC=...
LC.lumberIDs={}
LC.lumberProviders={}
function LC:IntegrationStatus()
    local result={LazyCrawler="v"..self.version.." / bundle: "..(self.data and self.data.generated_at or "NOT LOADED")}
    local function installed(name)
        return C_AddOns and C_AddOns.IsAddOnLoaded and C_AddOns.IsAddOnLoaded(name)
    end
    result.CraftSim=CraftSimAPI and CraftSimAPI.GetOpenRecipeData and "Supported recipe API available" or (installed("CraftSim") and "Loaded; supported API unavailable" or "Not loaded")
    result.Auctionator=Auctionator and Auctionator.API and Auctionator.API.v1 and "API v1 detected; capability checks per operation" or "Not loaded"
    result.TradeSkillMaster=TSM_API and TSM_API.GetCustomPriceValue and "Price API available" or "Not loaded"
    result.Syndicator=installed("Syndicator") and "Detected; native captures remain authoritative" or "Not loaded"
    for _,name in ipairs({"HousingLumberHelper","ThendarsLumberTracker","HousingLumberTracker"}) do
        if installed(name) then result[name]=self.lumberProviders[name] and "Registered session provider" or "Detected; no verified session adapter registered" end
    end
    return result
end
function LC:CaptureRecipes()
    if not self.db or InCombatLockdown() or not C_TradeSkillUI then return end
    local char=self:Current();if not char then return end
    local ids=self:Call(C_TradeSkillUI.GetAllRecipeIDs) or self:Call(C_TradeSkillUI.GetFilteredRecipeIDs)
    if not ids then return end
    local profession=self:Call(C_TradeSkillUI.GetBaseProfessionInfo)
    local byID={};for _,r in ipairs(char.recipes or {}) do byID[r.id]=r end
    -- Chunk work so large profession lists do not stall a frame.
    local cursor=1
    local function chunk()
        if not LC.db or InCombatLockdown() then return end
        for _=1,35 do
            local id=ids[cursor];cursor=cursor+1
            if not id then break end
            local info=LC:Call(C_TradeSkillUI.GetRecipeInfo,id)
            local schematic=LC:Call(C_TradeSkillUI.GetRecipeSchematic,id,false)
            if info and schematic then
                local old=byID[tostring(id)] or {}
                local r={id=tostring(id),name=schematic.name or info.name,profession=profession and profession.professionName or "",
                    output_item_id=schematic.outputItemID,output_quantity=schematic.quantityMin or 1,crafts=old.crafts or 0,materials={},
                    learned=info.learned,disabled=info.disabled,disabled_reason=info.disabledReason,icon=info.icon,
                    observed_at=time(),source_type=info.sourceType,skill_line_ability_id=info.skillLineAbilityID,
                    description=LC:Call(C_TradeSkillUI.GetRecipeDescription,id,{}),
                    station_requirements=LC:Call(C_TradeSkillUI.GetRecipeRequirements,id)}
                if schematic.outputItemID and C_Item and C_Item.IsDecorItem then r.is_decor=LC:Call(C_Item.IsDecorItem,schematic.outputItemID) end
                for _,slot in ipairs(schematic.reagentSlotSchematics or {}) do
                    if slot.reagents and #slot.reagents>0 and slot.quantityRequired and slot.quantityRequired>0 then
                        local choices={};for _,reagent in ipairs(slot.reagents) do
                            choices[#choices+1]=reagent.itemID
                            local name=C_Item and C_Item.GetItemInfo and C_Item.GetItemInfo(reagent.itemID)
                            if name and name:lower():find("lumber",1,true) then LC.lumberIDs[reagent.itemID]=name end
                        end
                        local owned=0
                        if #choices==1 then owned=LC:UsableCount(choices[1]) end
                        r.materials[#r.materials+1]={item_id=choices[1],quantity=slot.quantityRequired,alternatives=choices,
                            owned=#choices==1 and owned or nil,missing=#choices==1 and math.max(0,slot.quantityRequired-owned) or nil}
                    end
                end
                r.simulation=old.simulation
                byID[r.id]=r
            end
        end
        char.recipes={};for _,r in pairs(byID) do char.recipes[#char.recipes+1]=r end
        if cursor<=#ids then C_Timer.After(.01,function() LC:Run("recipes",chunk) end) else LC:CaptureSimulation();LC:Changed() end
    end
    self:Run("recipes",chunk)
end
function LC:CaptureSimulation()
    if not self.db or InCombatLockdown() or not CraftSimAPI or not CraftSimAPI.GetOpenRecipeData then return end
    local data=self:Call(CraftSimAPI.GetOpenRecipeData,CraftSimAPI)
    if not data or not data.GetAverageProfit or not data.recipeID then return end
    local profit=self:Call(data.GetAverageProfit,data)
    if type(profit)~="number" or profit~=profit then return end
    local char=self:Current();if not char then return end
    for _,recipe in ipairs(char.recipes) do
        if tonumber(recipe.id)==tonumber(data.recipeID) then recipe.simulation={profit_copper=profit,source="CraftSim GetAverageProfit",observed_at=time()};self:Changed();break end
    end
end
function LC:QueueRecipe(recipe)
    if recipe.learned==false or recipe.disabled then self:Print(recipe.disabled_reason or "This recipe is not learned on this character. Review its requirements first.");return end
    recipe.crafts=(recipe.crafts or 0)+1
    self:Changed();self:Print("Queued "..recipe.name..". Reagent quality choices stay in your profession UI.")
end
function LC:OpenRecipe(recipe)
    if InCombatLockdown() then return end
    if recipe.character and recipe.character~=self:Current().name then self:Print("Log into "..recipe.character.." to open this observed recipe.");return end
    local id=tonumber(recipe.id)
    if C_TradeSkillUI and C_TradeSkillUI.OpenRecipe then self:Call(C_TradeSkillUI.OpenRecipe,id)
    elseif ProfessionsFrame and ProfessionsFrame.CraftingPage and ProfessionsFrame.CraftingPage.SelectRecipe then
        -- Isolated default-UI compatibility fallback; no CraftSim internals are modified.
        self:Call(ProfessionsFrame.CraftingPage.SelectRecipe,ProfessionsFrame.CraftingPage,id)
        ProfessionsFrame:Show()
    else self:Print("Open "..recipe.profession.." and select "..recipe.name.." in your profession window.") end
end
function LC:MissingMaterials()
    local char=self:Current();local totals={}
    if not char then return {} end
    for _,r in ipairs(char.recipes or {}) do
        if (r.crafts or 0)>0 then
            for _,m in ipairs(r.materials) do
                -- Never silently pick a quality tier for an unresolved multi-quality slot.
                if not m.alternatives or #m.alternatives==1 then
                    totals[m.item_id]=(totals[m.item_id] or 0)+m.quantity*r.crafts
                end
            end
        end
    end
    local result={}
    for id,required in pairs(totals) do
        local owned=self:UsableCount(id)
        result[#result+1]={item_id=id,required=required,owned=owned,missing=math.max(0,required-owned),is_lumber=self.lumberIDs[id]~=nil,name=C_Item and C_Item.GetItemInfo and C_Item.GetItemInfo(id) or nil}
    end
    table.sort(result,function(a,b)return a.item_id<b.item_id end)
    return result
end
function LC:ShopMaterials()
    if InCombatLockdown() or not self.auctionOpen then self:Print("Open the auction house first.");return end
    local api=Auctionator and Auctionator.API and Auctionator.API.v1
    if not api or type(api.MultiSearch)~="function" then self:Print("Auctionator API v1 MultiSearch is unavailable. Missing quantities remain in the Materials view.");return end
    local names={}
    for _,m in ipairs(self:MissingMaterials()) do
        if m.missing>0 then
            local name=C_Item and C_Item.GetItemInfo and C_Item.GetItemInfo(m.item_id)
            if name then names[#names+1]=name end
        end
    end
    if #names==0 then self:Print("No resolved missing materials. Open recipes to resolve quality choices.");return end
    -- Supported search API only. Quantities stay in our queue rather than an unverified list format.
    self:Call(api.MultiSearch,"LazyCrawler",names)
end
function LC:StartGathering()
    self.session={started=GetTime(),zone=GetZoneText(),counts={}}
    self:Print("Gathering session started. Only your own lumber loot is counted; travel time is included.")
    if self.RefreshUI then self:RefreshUI() end
end
function LC:StopGathering()
    local session=self.session;if not session then return end
    local seconds=GetTime()-session.started
    if seconds>=10 then
        for id,count in pairs(session.counts) do
            self.db.lumber[#self.db.lumber+1]={item_id=id,quantity=count,seconds=seconds,zone=session.zone,source="LazyCrawler personal loot session"}
        end
        while #self.db.lumber>2000 do table.remove(self.db.lumber,1) end
    end
    self.session=nil;self:Changed();self:Print("Gathering session saved. Very short sessions are excluded from rate estimates.")
end
function LC:RegisterLumberProvider(name,callback)
    if type(name)~="string" or #name>150 or type(callback)~="function" then return false end
    self.lumberProviders[name]=callback;return true
end
function LC:ImportLumberProviders()
    self.db.providerSamples=self.db.providerSamples or {}
    for name,provider in pairs(self.lumberProviders) do
        local samples=self:Call(provider)
        if type(samples)=="table" then for _,sample in ipairs(samples) do
            if type(sample.id)=="string" and not self.db.providerSamples[name..":"..sample.id] and type(sample.item_id)=="number" and type(sample.quantity)=="number" and sample.quantity>0 and sample.quantity<=1000000 and type(sample.seconds)=="number" and sample.seconds>=10 and sample.seconds<=2592000 and #sample.id<=100 then
                self.db.lumber[#self.db.lumber+1]={item_id=sample.item_id,quantity=sample.quantity,seconds=sample.seconds,zone=sample.zone or "",source=name}
                self.db.providerSamples[name..":"..sample.id]=true
            end
        end end
    end
    while #self.db.lumber>2000 do table.remove(self.db.lumber,1) end
    self:Changed()
end
LC:On("TRADE_SKILL_SHOW",function() LC:CaptureRecipes() end)
LC:On("TRADE_SKILL_LIST_UPDATE",function() if LC.recipePending then return end;LC.recipePending=true;C_Timer.After(.5,function() LC.recipePending=false;LC:CaptureRecipes() end) end)
LC:On("TRADE_SKILL_ITEM_CRAFTED_RESULT",function(data)
    local char=LC:Current()
    if char and data and data.recipeID then for _,recipe in ipairs(char.recipes) do if tonumber(recipe.id)==data.recipeID then recipe.crafts=math.max(0,(recipe.crafts or 0)-1) end end end
    LC:CaptureSimulation();LC:Changed()
end)
LC:On("CHAT_MSG_LOOT",function(message)
    if not LC.session or not message then return end
    local prefix=LOOT_ITEM_SELF and LOOT_ITEM_SELF:match("^(.-)%%s")
    if not prefix or message:sub(1,#prefix)~=prefix then return end
    local id=tonumber(message:match("item:(%d+)"));if not id then return end
    local name=C_Item and C_Item.GetItemInfo and C_Item.GetItemInfo(id)
    if not LC.lumberIDs[id] and not (name and name:lower():find("lumber",1,true)) then return end
    LC.lumberIDs[id]=name or ("Item #"..id)
    local amount=tonumber(message:match("|h|r[^%d]*(%d+)")) or 1
    LC.session.counts[id]=(LC.session.counts[id] or 0)+amount
end)
