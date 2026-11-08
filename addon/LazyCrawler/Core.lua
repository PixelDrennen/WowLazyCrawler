local addonName, LC = ...
_G.LazyCrawler = LC
LC.version = "0.3.0"
LC.events = {}
LC.dirty = false
LC.errors = {}
LC.regions = {[1]="us",[2]="kr",[3]="eu",[4]="tw"}

function LC:Array(values) return values or {} end
function LC:Print(message) print("|cffc5ef8bLazyCrawler:|r "..tostring(message)) end
function LC:Run(label, fn, ...)
    local ok, result = pcall(fn, ...)
    if not ok then
        self.errors[label] = tostring(result)
        if self.db then self.db.lastError = label..": "..tostring(result) end
        return nil
    end
    return result
end
function LC:Call(fn, ...)
    if type(fn) ~= "function" then return nil end
    local ok, result = pcall(fn, ...)
    if ok then return result end
    self.errors["API call"]=tostring(result)
    return nil
end
function LC:On(event, fn)
    self.events[event] = self.events[event] or {}
    table.insert(self.events[event], fn)
    local ok,err=pcall(self.frame.RegisterEvent, self.frame, event)
    if not ok then self.errors["Event "..event]=tostring(err) end
end
function LC:Changed()
    self.dirty = true
    if self.flushPending then return end
    self.flushPending = true
    C_Timer.After(1, function()
        self.flushPending = false
        self:Run("export",function() self:Export() end)
        if self.RefreshUI then self:Run("refresh",function() self:RefreshUI() end) end
    end)
end
local arrays={items=true,professions=true,recipes=true,lumber=true,tasks=true,materials=true,alternatives=true,quality_choices=true,material_plan=true}
local function quote(value)
    return '"'..value:gsub('[%z\1-\31\\"]', function(c)
        local map={['"']='\\"',['\\']='\\\\',['\n']='\\n',['\r']='\\r',['\t']='\\t'}
        return map[c] or string.format('\\u%04x',string.byte(c))
    end)..'"'
end
function LC:JSON(value, key, depth)
    depth = depth or 0
    if depth > 24 then error("Export is too deeply nested") end
    local kind = type(value)
    if kind == "nil" then return "null" end
    if kind == "string" then return quote(value) end
    if kind == "boolean" then return value and "true" or "false" end
    if kind == "number" then
        if value ~= value or value == math.huge or value == -math.huge then error("Invalid number") end
        return tostring(value)
    end
    if kind ~= "table" then error("Unsupported export type: "..kind) end
    local parts = {}
    if arrays[key] or #value > 0 then
        for i=1,#value do parts[#parts+1]=self:JSON(value[i],nil,depth+1) end
        return "["..table.concat(parts,",").."]"
    end
    for k,v in pairs(value) do parts[#parts+1]=quote(tostring(k))..":"..self:JSON(v,tostring(k),depth+1) end
    return "{"..table.concat(parts,",").."}"
end
function LC:Current()
    if not self.db then return nil end
    local name, realm = UnitFullName("player")
    realm = realm or GetRealmName()
    if not name or not realm then return nil end
    local region = self.regions[GetCurrentRegion()]
    if not region then self:Print("This client region is not supported yet."); return nil end
    local key=name.."-"..realm
    local className=select(2,UnitClass("player")) or ""
    local char=self.db.characters[key] or {storages={},recipes={}}
    char.name=name;char.realm=realm;char.region=region;char.class_name=className;char.level=UnitLevel("player")
    char.professions={}
    if GetProfessions and GetProfessionInfo then
        local profs={GetProfessions()}
        for i=1,2 do
            if profs[i] then local title=GetProfessionInfo(profs[i]);if title then table.insert(char.professions,title) end end
        end
    end
    self.db.characters[key]=char;self.characterKey=key
    return char
end
function LC:Export()
    if not self.db then return end
    local char=self:Current()
    if char and self.MissingMaterials then char.material_plan=self:MissingMaterials() end
    local tasks={}
    for _,task in pairs(self.db.tasks) do tasks[#tasks+1]=task end
    if self.CheckpointSession then self:CheckpointSession() end
    if self.db.activity then tasks[#tasks+1]=self.db.activity end
    local payload={schema_version=2,account_id=self.db.accountID,addon_version=self.version,
        characters=self.db.characters,warbank=self.db.warbank,warbank_group=self.db.warbankGroup,lumber=self.db.lumber,
        integrations=self:IntegrationStatus(),tasks=tasks}
    self.db.exportJSON=self:JSON(payload)
    self.db.exportedAt=time()
    self.dirty=false
end
function LC:Initialize()
    LazyCrawlerDB=type(LazyCrawlerDB)=="table" and LazyCrawlerDB or {}
    local d=LazyCrawlerDB
    if d.schemaVersion and d.schemaVersion>2 then self:Print("Newer SavedVariables schema; update this addon before continuing.");return end
    d.schemaVersion=2;d.characters=d.characters or {};d.tasks=d.tasks or {};d.lumber=d.lumber or {}
    d.settings=d.settings or {help=true,scale=1,hideInCombat=true}
    d.accountID=d.accountID or tostring(time()).."-"..tostring(math.random(100000,999999))
    self.db=d
    local bnet=self:Call(BNGetInfo)
    if type(bnet)=='number' and bnet>0 then d.warbankGroup='bn:'..tostring(bnet) end
    self.data=type(LazyCrawlerData)=="table" and LazyCrawlerData.schema_version==2 and LazyCrawlerData.origin=="live" and LazyCrawlerData or {opportunities={},crafting={},catalog={}}
    if not d.settings.themeUserSet then d.settings.theme=self.data.theme or d.settings.theme or "grove" end
    self.activityTick=GetTime()
    self:Current()
    self:CaptureBags()
    self:CaptureEquipped()
    self:Export()
end
LC.frame=CreateFrame("Frame")
LC.frame:SetScript("OnEvent",function(_,event,...)
    if event=="ADDON_LOADED" then
        local name=...
        if name==addonName then LC:Run("initialize",function() LC:Initialize() end) end
    end
    for _,fn in ipairs(LC.events[event] or {}) do LC:Run(event,fn,...) end
end)
LC.frame:RegisterEvent("ADDON_LOADED")
LC:On("PLAYER_LOGIN",function() if LC.db then LC:Current();LC:CaptureBags();LC:CaptureEquipped();LC:Changed() end end)
LC:On("PLAYER_LOGOUT",function() if LC.db then if LC.session then LC:StopGathering() end;LC:Export() end end)
SLASH_LAZYCRAWLER1="/lazycrawler";SLASH_LAZYCRAWLER2="/lc"
SlashCmdList.LAZYCRAWLER=function(command)
    if not LC.db then return end
    command=(command or ""):lower()
    if command=="capture" then LC:CaptureBags();LC:CaptureEquipped();LC:Changed();LC:Print("Accessible data captured. Reload or log out to flush the export.")
    elseif command=="gather" then if LC.session then LC:StopGathering() else LC:StartGathering() end
    elseif command=="help" then LC.db.settings.help=true;LC.db.tutorialStep=1;LC.db.tutorialReplay=true;LC:ShowUI()
    else LC:ShowUI() end
end
