local addonName, LC = ...
_G.LazyCrawler = LC
LC.version = "0.4.0"
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
        loaded_bundle=self.data and self.data.generated_at,loaded_transport=self.data and self.data.importedLive and "clipboard" or "file",characters=self.db.characters,warbank=self.db.warbank,warbank_group=self.db.warbankGroup,lumber=self.db.lumber,
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
    if type(d.importedBundle)=="table" and d.importedBundle.schema_version==2 and d.importedBundle.origin=="live" and (d.importedBundle.generated_epoch or 0)>(self.data.generated_epoch or 0) then self.data=d.importedBundle end
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
    elseif command=="import" then LC:ShowUI();LC.page="data_import";LC:RefreshUI()
    elseif command=="export" then LC:ShowUI();LC.page="data_export";LC:RefreshUI()
    elseif command=="help" then LC.db.settings.help=true;LC.db.tutorialStep=1;LC.db.tutorialReplay=true;LC:ShowUI()
    else LC:ShowUI() end
end

-- Bounded JSON decoding for explicit clipboard imports. Never evaluates Lua/code.
function LC:DecodeDataJSON(text)
    if type(text)~="string" or #text>4*1024*1024 then error("Import exceeds 4 MB") end
    local position,nodes=1,0
    local function skip() local _,last=text:find("^[ \t\r\n]*",position);position=(last or position-1)+1 end
    local function utf8(code)
        if code<128 then return string.char(code) end
        if code<2048 then return string.char(192+math.floor(code/64),128+code%64) end
        if code<65536 then return string.char(224+math.floor(code/4096),128+math.floor(code/64)%64,128+code%64) end
        return string.char(240+math.floor(code/262144),128+math.floor(code/4096)%64,128+math.floor(code/64)%64,128+code%64)
    end
    local function stringValue()
        position=position+1;local parts={};local start=position
        while position<=#text do
            local c=text:sub(position,position)
            if c=='"' then parts[#parts+1]=text:sub(start,position-1);position=position+1;return table.concat(parts) end
            if c=='\\' then
                parts[#parts+1]=text:sub(start,position-1);position=position+1;c=text:sub(position,position)
                local escaped={['"']='"',['\\']='\\',['/']='/',b='\b',f='\f',n='\n',r='\r',t='\t'}
                if c=='u' then
                    local hex=text:sub(position+1,position+4);if #hex~=4 or hex:find('[^%x]') then error("Invalid Unicode escape") end
                    local code=tonumber(hex,16);position=position+4
                    if code>=55296 and code<=56319 then
                        if text:sub(position+1,position+2)~='\\u' then error("Missing Unicode surrogate") end
                        local low=tonumber(text:sub(position+3,position+6),16)
                        if not low or low<56320 or low>57343 then error("Invalid Unicode surrogate") end
                        code=65536+(code-55296)*1024+low-56320;position=position+6
                    elseif code>=56320 and code<=57343 then error("Invalid Unicode surrogate") end
                    parts[#parts+1]=utf8(code)
                elseif escaped[c] then parts[#parts+1]=escaped[c] else error("Invalid JSON escape") end
                position=position+1;start=position
            else if c:byte()<32 then error("Invalid string character") end;position=position+1 end
        end
        error("Truncated string")
    end
    local parse
    parse=function(depth)
        nodes=nodes+1;if depth>24 or nodes>250000 then error("Import is too complex") end
        skip();local c=text:sub(position,position)
        if c=='"' then return stringValue() end
        if c=='{' or c=='[' then
            local object=c=='{';local close=object and '}' or ']';local value={};local count=0
            position=position+1;skip();if text:sub(position,position)==close then position=position+1;return value end
            while true do
                skip();local key
                if object then if text:sub(position,position)~='"' then error("Expected object key") end;key=stringValue();skip();if text:sub(position,position)~=':' then error("Expected colon") end;position=position+1
                else count=count+1;key=count end
                value[key]=parse(depth+1);skip();c=text:sub(position,position);position=position+1
                if c==close then return value end
                if c~=',' then error("Expected separator") end
            end
        end
        for _,entry in ipairs({{'true',true},{'false',false},{'null',nil}}) do
            if text:sub(position,position+#entry[1]-1)==entry[1] then position=position+#entry[1];return entry[2] end
        end
        local token=text:sub(position):match('^-?%d+%.?%d*[eE]?[+-]?%d*')
        local number=token and tonumber(token)
        if not number or number~=number or number==math.huge or number==-math.huge or token:match('^-?0%d') or token:match('%.$') or token:match('%.[eE]') then error("Invalid JSON value") end
        position=position+#token;return number
    end
    local value=parse(0);skip();if position<=#text then error("Unexpected trailing content") end
    return value
end
function LC:ImportMarketData(text)
    if InCombatLockdown() then self:Print("Import data outside combat.");return false end
    local ok,result=pcall(function()
        if text:sub(1,4)~='LC1:' then error("Copy market data from the desktop app first") end
        local data=self:DecodeDataJSON(text:sub(5))
        if type(data)~='table' or data.schema_version~=2 or data.origin~='live' then error("Unsupported data bundle") end
        local char=self:Current()
        if data.region~=char.region then error("Bundle region does not match this character") end
        if type(data.generated_epoch)~='number' or data.generated_epoch>time()+600 or type(data.generated_at)~='string' then error("Invalid generation time") end
        if self.data.generated_epoch and data.generated_epoch<self.data.generated_epoch then error("This bundle is older than the loaded data") end
        if type(data.catalog)~='table' or #data.catalog>1000 or type(data.opportunities)~='table' or #data.opportunities>500 then error("Invalid market lists") end
        for _,candidate in ipairs(data.opportunities) do
            for _,key in ipairs({'name','item_key','source_realm','destination_realm'}) do if type(candidate[key])~='string' then error("Invalid route identity") end end
            for _,key in ipairs({'buyout','estimated_sale','net_profit','roi'}) do if type(candidate[key])~='number' then error("Invalid route price") end end
            if candidate.expires_at and type(candidate.expires_at)~='number' then error("Invalid route expiry") end
        end
        for _,market in ipairs(data.catalog) do
            if type(market)~='table' or type(market.realms)~='table' then error("Invalid realm catalog") end
            for _,realm in ipairs(market.realms) do if type(realm)~='table' or type(realm.slug)~='string' or type(realm.name)~='string' then error("Invalid realm identity") end end
        end
        for _,key in ipairs({'crafting','crafting_discovery'}) do if data[key]~=nil and type(data[key])~='table' then error("Invalid crafting list") end end
        if data.market_diagnostics~=nil then
            local d=data.market_diagnostics;if type(d)~='table' then error("Invalid market diagnostics") end
            for _,key in ipairs({'region','title','message','action'}) do if type(d[key])~='string' then error("Invalid diagnostic text") end end
            for _,key in ipairs({'fresh_markets','total_markets','fresh_owned_markets','owned_markets','fresh_regional_rows'}) do if type(d[key])~='number' then error("Invalid diagnostic count") end end
            if d.source_errors~=nil and type(d.source_errors)~='table' then error("Invalid source errors") end
            for _,source in ipairs(d.source_errors or {}) do if type(source)~='table' or type(source.id)~='string' or type(source.error)~='string' then error("Invalid source issue") end end
        end
        for _,recipe in ipairs(data.crafting_discovery or {}) do
            if type(recipe)~='table' or type(recipe.name)~='string' or type(recipe.profession)~='string' or type(recipe.materials)~='table' then error("Invalid recipe data") end
            for _,material in ipairs(recipe.materials) do if type(material)~='table' or type(material.item_id)~='number' or type(material.quantity)~='number' then error("Invalid material data") end end
        end
        data.importedLive=true;self.data=data;self.db.importedBundle=data;self:Changed()
        return true
    end)
    if not ok then self.lastImportError=tostring(result):gsub("^.-:%d+:%s*","");self:Print("Import failed: "..self.lastImportError);return false end
    self.lastImportError=nil
    self:Print("Market data applied immediately. No reload needed.");return result
end
