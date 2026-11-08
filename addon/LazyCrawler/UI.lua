local _,LC=...
local media="Interface\\AddOns\\LazyCrawler\\Media\\Circle"
local palettes={
    grove={accent={.77,.94,.55},second={.5,.85,.8},bg={.055,.082,.067},panel={.085,.12,.095},border={.22,.30,.18}},
    spectral={accent={.52,.89,.91},second={.77,.94,.55},bg={.045,.075,.08},panel={.065,.12,.12},border={.18,.32,.31}},
    ember={accent={.94,.71,.49},second={.76,.60,.89},bg={.085,.066,.075},panel={.13,.10,.12},border={.35,.25,.23}},
}
local modules={{"overview","Command center"},{"radar","Opportunity radar"},{"queue","Guided workflow"},{"inventory","Inventory & gold"},{"crafting","Crafting"},{"housing","Housing workshop"},{"materials","Materials & lumber"},{"settings","Settings & diagnostics"}}
local function tint(texture,color,alpha) texture:SetVertexColor(color[1],color[2],color[3],alpha or 1) end
function LC:Round(parent,color,radius,layer)
    radius=radius or 8;layer=layer or "BACKGROUND"
    local holder=CreateFrame("Frame",nil,parent);holder:SetAllPoints()
    holder.parts={};holder.role=color==self.theme.bg and 'bg' or (color==self.theme.border and 'border' or 'panel')
    self.ui.skins=self.ui.skins or {};table.insert(self.ui.skins,holder)
    local center=holder:CreateTexture(nil,layer);center:SetColorTexture(1,1,1,1);tint(center,color);table.insert(holder.parts,center)
    center:SetPoint("TOPLEFT",radius,0);center:SetPoint("BOTTOMRIGHT",-radius,0)
    for _,side in ipairs({"LEFT","RIGHT"}) do
        local tex=holder:CreateTexture(nil,layer);tex:SetColorTexture(1,1,1,1);tint(tex,color);table.insert(holder.parts,tex)
        tex:SetPoint("TOP"..side,0,-radius);tex:SetPoint("BOTTOM"..side,0,radius);tex:SetWidth(radius)
    end
    local corners={{"TOPLEFT",0,.5,0,.5},{"TOPRIGHT",.5,1,0,.5},{"BOTTOMLEFT",0,.5,.5,1},{"BOTTOMRIGHT",.5,1,.5,1}}
    for _,corner in ipairs(corners) do
        local tex=holder:CreateTexture(nil,layer);tex:SetTexture(media);tex:SetSize(radius,radius)
        tex:SetPoint(corner[1]);tex:SetTexCoord(corner[2],corner[3],corner[4],corner[5]);tint(tex,color);table.insert(holder.parts,tex)
    end
    holder:SetFrameLevel(parent:GetFrameLevel())
    return holder
end
function LC:Skin(frame)
    if frame.skinOuter then frame.skinOuter:Hide();frame.skinInner:Hide() end
    -- Reuse skin holders rather than allocating textures on every data refresh.
    if not frame.skinOuter then
        frame.skinOuter=self:Round(frame,self.theme.border,9)
        local inner=CreateFrame("Frame",nil,frame);inner:SetFrameLevel(frame:GetFrameLevel());inner:SetPoint("TOPLEFT",1,-1);inner:SetPoint("BOTTOMRIGHT",-1,1)
        frame.skinInner=self:Round(inner,self.theme.panel,8)
        frame.skinInner.container=inner
        local shine=frame:CreateTexture(nil,"OVERLAY");shine:SetHeight(1);shine:SetPoint("TOPLEFT",10,-1);shine:SetPoint("TOPRIGHT",-10,-1)
        if shine.SetGradient and CreateColor then shine:SetColorTexture(1,1,1);shine:SetGradient("HORIZONTAL",CreateColor(self.theme.accent[1],self.theme.accent[2],self.theme.accent[3],.4),CreateColor(self.theme.second[1],self.theme.second[2],self.theme.second[3],.04)) end
    end
    frame.skinOuter:Show();frame.skinInner:Show()
end
function LC:Text(parent,size,color)
    local text=parent:CreateFontString(nil,"OVERLAY")
    text:SetFont(STANDARD_TEXT_FONT,size or 12)
    text:SetTextColor(unpack(color or {.82,.88,.81}))
    text:SetJustifyH("LEFT");text:SetJustifyV("TOP")
    return text
end
function LC:Button(parent,label,callback,width)
    local b=CreateFrame("Button",nil,parent);b:SetSize(width or 136,30)
    b.bg=b:CreateTexture(nil,"BACKGROUND");b.bg:SetAllPoints();b.bg:SetColorTexture(.19,.27,.16,.95)
    b.text=self:Text(b,11,self.theme.accent);b.text:SetPoint("CENTER");b.text:SetText(label)
    b:SetScript("OnClick",function() self:Run("button",function() if b.action then b.action() end end) end);b.action=callback
    b:SetScript("OnEnter",function() b.bg:SetColorTexture(.25,.34,.2,1) end)
    b:SetScript("OnLeave",function() b.bg:SetColorTexture(.19,.27,.16,.95) end)
    self.ui.buttons=self.ui.buttons or {};table.insert(self.ui.buttons,b)
    return b
end
function LC:BuildUI()
    if self.ui then return end
    self.theme=palettes[self.db.settings.theme] or palettes.grove
    local f=CreateFrame("Frame","LazyCrawlerWindow",UIParent)
    f:SetSize(math.min(1100,UIParent:GetWidth()*.9),math.min(760,UIParent:GetHeight()*.9))
    f:SetPoint("CENTER");f:SetClampedToScreen(true);f:SetMovable(true);f:SetResizable(true);f:EnableMouse(true)
    if f.SetResizeBounds then f:SetResizeBounds(math.min(800,UIParent:GetWidth()*.9),math.min(540,UIParent:GetHeight()*.9),UIParent:GetWidth(),UIParent:GetHeight()) end
    f:SetFrameStrata("DIALOG")
    self.ui={frame=f,rows={},used=0,nav={}}
    self:Round(f,self.theme.bg,12)
    local title=self:Text(f,19,self.theme.accent);title:SetPoint("TOPLEFT",24,-22);title:SetText("LAZYCRAWLER");self.ui.logo=title
    local subtitle=self:Text(f,8,{.48,.61,.46});subtitle:SetPoint("TOPLEFT",25,-47);subtitle:SetText("YOUR GOLD. YOUR GUILD OF ONE.")
    local drag=CreateFrame("Frame",nil,f);drag:SetPoint("TOPLEFT");drag:SetPoint("TOPRIGHT");drag:SetHeight(65);drag:EnableMouse(true)
    drag:RegisterForDrag("LeftButton");drag:SetScript("OnDragStart",function() if not InCombatLockdown() then f:StartMoving() end end)
    drag:SetScript("OnDragStop",function() f:StopMovingOrSizing() end)
    local close=self:Button(f,"×",function() f:Hide() end,30);close:SetPoint("TOPRIGHT",-16,-16)
    for i,module in ipairs(modules) do
        local id=module[1]
        local b=self:Button(f,module[2],function() self.page=id;self.listPage=1;self:RefreshUI() end,168)
        b:SetPoint("TOPLEFT",18,-80-(i-1)*39);self.ui.nav[id]=b
    end
    local help=self:Button(f,"?  Contextual help",function() self.db.settings.help=not self.db.settings.help;self:RefreshUI() end,168)
    help:SetPoint("BOTTOMLEFT",18,48)
    local version=self:Text(f,9,{.43,.57,.43});version:SetPoint("BOTTOMLEFT",22,25);version:SetText("v"..self.version.."  ·  /lc")
    local h=self:Text(f,23);h:SetPoint("TOPLEFT",215,-25);h:SetPoint("TOPRIGHT",f,"TOPRIGHT",-65,-25);h:SetHeight(30);self.ui.heading=h
    local sub=self:Text(f,10,{.55,.67,.54});sub:SetPoint("TOPLEFT",215,-56);sub:SetPoint("TOPRIGHT",f,"TOPRIGHT",-30,-56);sub:SetHeight(18);self.ui.sub=sub
    local scroll=CreateFrame("ScrollFrame",nil,f,"UIPanelScrollFrameTemplate");scroll:SetPoint("TOPLEFT",212,-87);scroll:SetPoint("BOTTOMRIGHT",-36,55)
    local content=CreateFrame("Frame",nil,scroll);content:SetSize(700,600);scroll:SetScrollChild(content)
    self.ui.scroll=scroll;self.ui.content=content
    local previous=self:Button(f,"← Previous",function() self.listPage=math.max(1,(self.listPage or 1)-1);self:RefreshUI() end,100);previous:SetPoint("BOTTOMLEFT",214,16)
    local nextButton=self:Button(f,"Next →",function() self.listPage=(self.listPage or 1)+1;self:RefreshUI() end,100);nextButton:SetPoint("BOTTOMRIGHT",-38,16)
    self.ui.pagination=self:Text(f,9,{.52,.66,.50});self.ui.pagination:SetPoint("BOTTOM",50,24)
    local resize=self:Button(f,"◢",function() end,22);resize:SetPoint("BOTTOMRIGHT",-5,5);resize:SetScript("OnMouseDown",function() if not InCombatLockdown() then f:StartSizing("BOTTOMRIGHT") end end);resize:SetScript("OnMouseUp",function() f:StopMovingOrSizing();self:RefreshUI() end)
    f:SetScript("OnSizeChanged",function()
        if self.ui.layoutPending then return end;self.ui.layoutPending=true
        C_Timer.After(.05,function() self.ui.layoutPending=false;if f:IsShown() then self:RefreshUI() end end)
    end)
    table.insert(UISpecialFrames,"LazyCrawlerWindow")
    f:Hide()
end
function LC:FitWindow()
    local f=self.ui.frame
    local scale=math.min(self.db.settings.scale or 1,UIParent:GetWidth()*.94/650,UIParent:GetHeight()*.94/480)
    f:SetScale(scale)
    local availableW,availableH=UIParent:GetWidth()*.94/scale,UIParent:GetHeight()*.94/scale
    f:SetSize(math.min(f:GetWidth(),availableW),math.min(f:GetHeight(),availableH))
    if f.SetResizeBounds then f:SetResizeBounds(math.min(800,availableW),math.min(540,availableH),availableW,availableH) end
end
function LC:ShowUI()
    if InCombatLockdown() then self:Print("Open LazyCrawler outside combat.");return end
    self:BuildUI()
    self:FitWindow()
    self.ui.frame:Show();self:RefreshUI()
end
function LC:AddRow(title,detail,action,second)
    self.renderRows[#self.renderRows+1]={title=title,detail=detail,action=action,second=second}
end
function LC:RenderRows()
    local ui=self.ui;local rows=self.renderRows
    local pages=math.max(1,math.ceil(#rows/50));self.listPage=math.max(1,math.min(self.listPage or 1,pages))
    for _,row in ipairs(ui.rows) do row:Hide() end
    local width=math.max(320,ui.scroll:GetWidth()-8)
    ui.content:SetWidth(width)
    local count=0;local offset=0
    for index=(self.listPage-1)*50+1,math.min(#rows,self.listPage*50) do
        count=count+1;local data=rows[index];local row=ui.rows[count]
        if not row then
            row=CreateFrame("Frame",nil,ui.content);self:Skin(row)
            row.title=self:Text(row,13);row.detail=self:Text(row,10,{.53,.66,.54})
            row.button=self:Button(row,"",nil,145);row.second=self:Button(row,"",nil,100)
            ui.rows[count]=row
        end
        row:SetSize(width,86);row:ClearAllPoints();row:SetPoint("TOPLEFT",0,-offset)
        row.title:ClearAllPoints();row.title:SetPoint("TOPLEFT",15,-13);row.title:SetPoint("TOPRIGHT",row,"TOPRIGHT",data.action and -172 or -15,-13);row.title:SetHeight(30);row.title:SetText(tostring(data.title))
        row.detail:ClearAllPoints();row.detail:SetPoint("TOPLEFT",15,-43);row.detail:SetWidth(width-(data.action and 187 or 30));row.detail:SetText(tostring(data.detail or ""));row.detail:SetHeight(math.max(30,row.detail:GetStringHeight()))
        local height=math.max(86,row.detail:GetStringHeight()+58);row:SetHeight(height);offset=offset+height+10
        if data.action then
            row.button:SetPoint("TOPRIGHT",-12,-14);row.button.text:SetText(data.action.text);row.button.action=data.action.fn;row.button:Show()
        else row.button:Hide() end
        if data.second then row.second:SetPoint("BOTTOMRIGHT",-12,11);row.second.text:SetText(data.second.text);row.second.action=data.second.fn;row.second:Show() else row.second:Hide() end
        row:Show()
    end
    ui.content:SetHeight(math.max(1,offset));ui.pagination:SetText("Page "..self.listPage.." / "..pages.."   ·   "..#rows.." entries")
end
function LC:Tutorial()
    local char=self:Current();if not char then return end
    local definitions={
        {title="Your character is already known",text="Login captures this character, its wallet, and accessible bags. No setup form is needed.",done=char.storages.bags~=nil,page="inventory"},
        {title="Visit your bank and warbank",text="Open the bank to observe loaded tabs and shared gold. Inaccessible tabs remain unknown.",done=char.storages.bank~=nil or self.db.warbank~=nil,page="inventory"},
        {title="Open your mailbox",text="Mailbox captures distinguish uncollected gold, attachments, COD, and partially loaded mail.",done=char.storages.mail~=nil,page="inventory"},
        {title="Visit the auction house",text="Owned auctions update there. Your guided route verifies live prices before player-controlled actions.",done=char.storages.auctions~=nil,page="radar"},
        {title="Open a profession",text="Known recipes appear here. Open CraftSim for character-specific simulation, and queue décor in the housing workshop.",done=#(char.recipes or {})>0,page="crafting"},
    }
    local step=self.db.tutorialStep or 1
    self.db.tutorialSkipped=self.db.tutorialSkipped or {}
    if not self.db.tutorialReplay then
        while step<=#definitions and (definitions[step].done or self.db.tutorialSkipped[step]) do step=step+1 end
    end
    self.db.tutorialStep=step
    if step>#definitions then self.db.tutorialReplay=false;return end
    local guide=definitions[step]
    self:AddRow("Guided setup "..step.." / "..#definitions.." · "..guide.title,guide.text,
        {text=self.db.tutorialReplay and "Next explanation" or "Show related view",fn=function()
            if self.db.tutorialReplay then self.db.tutorialStep=step+1 else self.page=guide.page end
            self:RefreshUI()
        end},
        {text="Skip step",fn=function() self.db.tutorialSkipped[step]=true;self.db.tutorialStep=step+1;self:RefreshUI() end})
end
function LC:RefreshUI()
    if not self.ui or not self.ui.frame:IsShown() or not self.db or InCombatLockdown() then return end
    self.page=self.page or "overview";self.renderRows={}
    local page=self.page
    if self.ui.lastPage~=page or self.ui.lastListPage~=(self.listPage or 1) then self.ui.scroll:SetVerticalScroll(0) end
    self.ui.lastPage=page;self.ui.lastListPage=self.listPage or 1
    local char=self:Current()
    if not char then return end
    for _,module in ipairs(modules) do if module[1]==page then self.ui.heading:SetText(module[2]) end end
    self.ui.sub:SetText((self.auctionOpen and "Auction house open" or "Player-controlled workflows").."  ·  "..char.name.." — "..char.realm)
    for id,b in pairs(self.ui.nav) do b.text:SetTextColor(unpack(id==page and self.theme.accent or {.62,.72,.6})) end
    local function action(text,fn) return {text=text,fn=fn} end
    if page=="overview" then
        if self.db.settings.help then self:Tutorial() end
        self:AddRow("Your portfolio, automatically observed",self:Gold(char.storages.bags and char.storages.bags.money).." in this wallet. Banks, mailbox, auctions and professions update as their interfaces become accessible.")
        if self.db.settings.help then self:AddRow("A guided start · no manual character setup","1. Visit your bank and mailbox. 2. Open auctions and professions. 3. Reload/logout to send captures. Server data returns safely at the next client start.",action("Scan accessible data",function() self:CaptureBags();self:CaptureEquipped() end)) end
        self:AddRow("The server’s opportunity radar",#(self.data.opportunities or {}).." candidates loaded. Exact variants, live prices and transfer checks belong to the in-game review.",action("Review candidates",function() self.page="radar";self:RefreshUI() end))
        self:AddRow("Housing crafting and lumber","Queue known décor recipes, consolidate missing materials, and estimate gathering time from your own measured sessions.",action("Housing workshop",function() self.page="housing";self:RefreshUI() end))
        self:AddRow("Desktop synchronization",self.data.generated_at and ("Market bundle: "..self.data.generated_at) or "No server bundle yet. Choose your WoW folder in the desktop administration app.")
    elseif page=="radar" then
        if #(self.data.opportunities or {})==0 then self:AddRow("Waiting for the first market bundle","The server scans all unique auction houses. Character captures identify the home markets; no realm-selection list is needed.") end
        for _,candidate in ipairs(self.data.opportunities or {}) do
            local item=candidate
            self:AddRow(item.name.."  ·  +"..self:Gold(item.net_profit).." estimated",item.source_realm.." → "..item.destination_realm.."   |   "..tostring(item.roi).."% ROI. Base-item estimate; verify live variant and binding.",action("Review & queue",function() self:QueueCandidate(item) end))
        end
    elseif page=="queue" then
        local tasks={};for _,t in pairs(self.db.tasks) do tasks[#tasks+1]=t end;table.sort(tasks,function(a,b)return a.created_at<b.created_at end)
        if #tasks==0 then self:AddRow("Your next route starts in Opportunity radar","The workflow observes acquisition, retrieval, transfer, posting, and collection. A click authorizes each supported action; state advances from game evidence.") end
        for _,t in ipairs(tasks) do
            local task=t
            self:AddRow(task.name.."  ·  "..task.state:upper(),self:TaskHint(task),task.state~="complete" and action(self:ActionLabel(task),function() self:TaskAction(task) end) or nil)
        end
    elseif page=="inventory" then
        for key,c in pairs(self.db.characters) do
            self:AddRow(c.name.." — "..c.realm,self:Gold(c.storages.bags and c.storages.bags.money).." wallet. "..table.concat(c.professions or {}," / "))
            for _,scope in ipairs({"bags","bank","reagents","mail","auctions","equipped","guild_bank"}) do
                local capture=c.storages[scope]
                local count=0;if capture then for _,i in ipairs(capture.items) do count=count+i.count end end
                self:AddRow("   "..scope,capture and (count.." items · "..self:Gold(capture.money).." · observed "..date("%d %b %H:%M",capture.observed_at)..(capture.complete and "" or " · partial")) or "Not observed. Open this container on the character to capture it.")
            end
        end
        self:AddRow("Shared warband bank",self.db.warbank and (self:Gold(self.db.warbank.money).." · captured once per account") or "Not observed; open your warbank.")
    elseif page=="crafting" or page=="housing" then
        if self.db.settings.help then self:AddRow(page=="housing" and "A focused décor workshop" or "Character-specific crafting","Open a profession to capture known recipes. Open a recipe in CraftSim for simulation evidence. Quality choices are never silently substituted.",action("Refresh profession",function() self:CaptureRecipes() end)) end
        local shown=0
        for _,r in ipairs(char.recipes or {}) do
            if page~="housing" or r.is_decor then
                local recipe=r;shown=shown+1
                local profit=r.simulation and r.simulation.profit_copper
                self:AddRow(r.name..((r.crafts or 0)>0 and (" · "..r.crafts.." queued") or ""),r.profession.." · "..(profit and (self:Gold(profit).." CraftSim profit / craft") or "Simulation not yet observed"),action("Open recipe",function() self:OpenRecipe(recipe) end),action("Queue +1",function() self:QueueRecipe(recipe) end))
            end
        end
        if shown==0 then self:AddRow("No matching recipes observed","Open the relevant profession. Housing classification uses the client’s decor-item API when available.") end
    elseif page=="materials" then
        self:AddRow("Gathering session",self.session and ("Running in "..self.session.zone..". Personal lumber loot only; travel time included.") or "Start a session while gathering. External providers can supply validated sessions through the registered-provider API.",action(self.session and "Stop & save" or "Start gathering",function() if self.session then self:StopGathering() else self:StartGathering() end end),action("Read providers",function() self:ImportLumberProviders() end))
        self:AddRow("Consolidated material requirements","Inventory is deducted once across this character’s crafting queue. Unresolved reagent qualities are excluded rather than guessed.",action("Shop in Auctionator",function() self:ShopMaterials() end))
        for _,m in ipairs(self:MissingMaterials()) do
            local name=C_Item and C_Item.GetItemInfo and C_Item.GetItemInfo(m.item_id) or ("Item #"..m.item_id)
            local total,seconds=0,0
            for _,sample in ipairs(self.db.lumber) do if sample.item_id==m.item_id then total=total+sample.quantity;seconds=seconds+sample.seconds end end
            local eta=total>0 and (" · ~"..math.ceil(m.missing/(total/seconds)/60).." min observed gathering time") or ""
            self:AddRow(name,m.required.." required · "..m.owned.." observed stock · "..m.missing.." missing"..eta)
        end
    elseif page=="settings" then
        self:AddRow("Color palette",self.db.settings.theme.." · rounded panels, gradient highlights and flexible resizing.",action("Change palette",function()
            local order={grove="spectral",spectral="ember",ember="grove"};self.db.settings.theme=order[self.db.settings.theme] or "grove";self.db.settings.themeUserSet=true
            self.theme=palettes[self.db.settings.theme]
            for _,skin in ipairs(self.ui.skins or {}) do for _,tex in ipairs(skin.parts) do tint(tex,self.theme[skin.role]) end end
            for _,button in ipairs(self.ui.buttons or {}) do button.text:SetTextColor(unpack(self.theme.accent)) end
            self.ui.logo:SetTextColor(unpack(self.theme.accent));self:Changed()
        end))
        self:AddRow("Contextual guidance",self.db.settings.help and "Enabled" or "Hidden",action("Toggle guidance",function() self.db.settings.help=not self.db.settings.help;self:RefreshUI() end))
        self:AddRow("Window scale",string.format("%.0f%%",(self.db.settings.scale or 1)*100),action("Cycle scale",function() local nextScale=(self.db.settings.scale or 1)+.1;if nextScale>1.21 then nextScale=.8 end;self.db.settings.scale=nextScale;self:FitWindow();self:RefreshUI() end))
        for name,state in pairs(self:IntegrationStatus()) do self:AddRow(name,state) end
        self:AddRow("Last export",self.db.exportedAt and date("%d %b %H:%M:%S",self.db.exportedAt)..". Reload or logout flushes it to disk." or "Not yet generated.")
        for label,err in pairs(self.errors) do self:AddRow("Diagnostic · "..label,tostring(err)) end
    end
    self:RenderRows()
end
LC:On("PLAYER_REGEN_DISABLED",function() if LC.ui and LC.ui.frame:IsShown() and LC.db.settings.hideInCombat then LC.hiddenForCombat=true;LC.ui.frame:Hide() end end)
LC:On("PLAYER_REGEN_ENABLED",function() if LC.hiddenForCombat then LC.hiddenForCombat=false;LC:ShowUI() end end)
