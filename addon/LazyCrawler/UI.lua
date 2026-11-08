local _,LC=...
local media="Interface\\AddOns\\LazyCrawler\\Media\\Circle"
local palettes={
    grove={accent={.53,.85,.77},second={.81,.74,.51},bg={.055,.067,.078},panel={.085,.103,.12},border={.18,.24,.27}},
    spectral={accent={.43,.79,.96},second={.66,.62,.96},bg={.049,.059,.082},panel={.078,.094,.13},border={.19,.24,.34}},
    ember={accent={.96,.69,.49},second={.83,.55,.69},bg={.078,.059,.067},panel={.12,.086,.10},border={.29,.20,.23}},
}
local modules={{"overview","Session",136243},{"radar","Radar",132177},{"crafting","Crafting",136241},{"inventory","Storage",133785},{"materials","Materials",134064},{"settings","Settings",134063}}
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
    text:SetFont("Fonts\\ARIALN.TTF",size or 12)
    text:SetTextColor(unpack(color or {.88,.91,.94}))
    text:SetJustifyH("LEFT");text:SetJustifyV("TOP")
    return text
end
function LC:Button(parent,label,callback,width,icon)
    local b=CreateFrame("Button",nil,parent);b:SetSize(width or 140,28)
    self:Skin(b)
    b.text=self:Text(b,12,self.theme.accent);b.text:SetPoint("CENTER",icon and 8 or 0,0);b.text:SetText(label)
    if icon then b.icon=b:CreateTexture(nil,"ARTWORK");b.icon:SetSize(16,16);b.icon:SetPoint("LEFT",9,0);b.icon:SetTexture(icon);b.icon:SetTexCoord(.08,.92,.08,.92) end
    b:SetScript("OnClick",function() self:Run("button",function() if b.action then b.action() end end) end);b.action=callback
    b:SetScript("OnEnter",function() for _,tex in ipairs(b.skinInner.parts) do tint(tex,{.14,.19,.23}) end end)
    b:SetScript("OnLeave",function() for _,tex in ipairs(b.skinInner.parts) do tint(tex,self.theme.panel) end end)
    self.ui.buttons=self.ui.buttons or {};table.insert(self.ui.buttons,b)
    return b
end
function LC:BuildUI()
    if self.ui then return end
    self.theme=palettes[self.db.settings.theme] or palettes.grove
    local f=CreateFrame("Frame","LazyCrawlerWindow",UIParent)
    f:SetSize(680,430);f:SetPoint("CENTER");f:SetClampedToScreen(true);f:SetMovable(true);f:EnableMouse(true);f:SetFrameStrata("DIALOG")
    self.ui={frame=f,rows={},used=0,nav={}}
    self:Round(f,self.theme.bg,12)
    local logo=self:Text(f,16,self.theme.accent);logo:SetPoint("TOPLEFT",18,-16);logo:SetText("LazyCrawler");self.ui.logo=logo
    local heading=self:Text(f,13);heading:SetPoint("TOPLEFT",135,-18);self.ui.heading=heading
    local sub=self:Text(f,11,{.55,.63,.71});sub:SetPoint("TOPLEFT",18,-37);sub:SetPoint("TOPRIGHT",-60,-37);sub:SetHeight(15);self.ui.sub=sub
    local clock=self:Text(f,12,self.theme.accent);clock:SetPoint("TOPRIGHT",-58,-18);self.ui.clock=clock
    local drag=CreateFrame("Frame",nil,f);drag:SetPoint("TOPLEFT");drag:SetPoint("TOPRIGHT");drag:SetHeight(52);drag:EnableMouse(true)
    drag:RegisterForDrag("LeftButton");drag:SetScript("OnDragStart",function() if not InCombatLockdown() then f:StartMoving() end end);drag:SetScript("OnDragStop",function() f:StopMovingOrSizing() end)
    local close=self:Button(f,"x",function() f:Hide() end,26);close:SetPoint("TOPRIGHT",-14,-12)
    self.ui.gold={}
    for i,label in ipairs({"CHARACTER","WARBANK","MAILBOX"}) do
        local holder=CreateFrame("Frame",nil,f);holder:SetPoint("TOPLEFT",18+(i-1)*214,-60);holder:SetSize(208,36)
        local title=self:Text(holder,10,{.55,.63,.71});title:SetPoint("TOPLEFT");title:SetText(label)
        local value=self:Text(holder,13);value:SetPoint("TOPLEFT",0,-14);value:SetWidth(208);value:SetHeight(20);self.ui.gold[i]=value
    end
    for i,module in ipairs(modules) do
        local id=module[1];local b=self:Button(f,module[2],function() self.page=id;self.listPage=1;self:RefreshUI() end,104,module[3]);b:SetPoint("TOPLEFT",18+(i-1)*108,-105);self.ui.nav[id]=b
    end
    local scroll=CreateFrame("ScrollFrame",nil,f);scroll:SetPoint("TOPLEFT",18,-145);scroll:SetPoint("BOTTOMRIGHT",-28,46)
    local content=CreateFrame("Frame",nil,scroll);content:SetSize(630,200);scroll:SetScrollChild(content);self.ui.scroll=scroll;self.ui.content=content
    local bar=CreateFrame("Slider",nil,f);bar:SetPoint("TOPRIGHT",-13,-148);bar:SetPoint("BOTTOMRIGHT",-13,49);bar:SetWidth(5);bar:SetOrientation("VERTICAL");bar:SetValueStep(1)
    local track=bar:CreateTexture(nil,"BACKGROUND");track:SetAllPoints();track:SetColorTexture(.12,.16,.20)
    local thumb=bar:CreateTexture(nil,"ARTWORK");thumb:SetTexture(media);thumb:SetSize(5,26);tint(thumb,self.theme.accent,.65);bar:SetThumbTexture(thumb)
    bar:SetScript("OnValueChanged",function(_,value) scroll:SetVerticalScroll(value) end);self.ui.bar=bar
    scroll:EnableMouseWheel(true);scroll:SetScript("OnMouseWheel",function(_,delta)
        local value=math.max(0,math.min(self.ui.scrollMax or 0,(scroll:GetVerticalScroll() or 0)-delta*36));bar:SetValue(value);scroll:SetVerticalScroll(value)
    end)
    self.ui.previous=self:Button(f,"Back",function() self.listPage=math.max(1,(self.listPage or 1)-1);self:RefreshUI() end,60);self.ui.previous:SetPoint("BOTTOMLEFT",18,12)
    self.ui.nextButton=self:Button(f,"More",function() self.listPage=(self.listPage or 1)+1;self:RefreshUI() end,60);self.ui.nextButton:SetPoint("BOTTOMLEFT",84,12)
    self.ui.pagination=self:Text(f,10,{.55,.63,.71});self.ui.pagination:SetPoint("BOTTOMLEFT",152,20)
    self.ui.pause=self:Button(f,"Pause",function() self:ToggleSessionPause() end,80);self.ui.pause:SetPoint("BOTTOMRIGHT",-108,12)
    self.ui.stop=self:Button(f,"Stop",function() self:StopActivity(false) end,80);self.ui.stop:SetPoint("BOTTOMRIGHT",-18,12)
    self.ui.help=self:Button(f,"Setup help",function() self.page="setup";self:RefreshUI() end,90);self.ui.help:SetPoint("BOTTOMRIGHT",-18,12)
    f:SetScript("OnUpdate",function(_,elapsed)
        self.ui.elapsed=(self.ui.elapsed or 0)+elapsed
        if self.ui.elapsed>=1 then self.ui.elapsed=0;self:RefreshHeader() end
    end)
    table.insert(UISpecialFrames,"LazyCrawlerWindow");f:Hide()
end
function LC:FitWindow()
    local scale=math.min(self.db.settings.scale or 1,UIParent:GetWidth()*.94/680,UIParent:GetHeight()*.94/350)
    self.ui.frame:SetScale(scale)
end
function LC:RefreshHeader()
    if not self.ui or not self.db then return end
    local char=self:Current();if not char then return end
    local function balance(capture)
        if not capture then return "Unknown - open this container" end
        return self:Gold(capture.money)..(capture.complete==false and " (partial)" or "").." |cff8295a6"..date("%H:%M",capture.observed_at).."|r"
    end
    self.ui.gold[1]:SetText(self:Gold(GetMoney()).." |cff8295a6live|r")
    self.ui.gold[2]:SetText(balance(self.db.warbank));self.ui.gold[3]:SetText(balance(char.storages.mail))
    local session=self.db.activity;local active=session and (session.state=="running" or session.state=="paused")
    local seconds=math.floor(self:SessionElapsed())
    self.ui.clock:SetText(session and self.page~="discover" and string.format("%s  %02d:%02d:%02d",session.state,math.floor(seconds/3600),math.floor(seconds/60)%60,seconds%60) or "")
    self.ui.pause:SetShown(active);self.ui.stop:SetShown(active);self.ui.help:SetShown(not active)
    self.ui.pause.text:SetText(session and session.state=="paused" and "Resume" or "Pause")
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
    local pages=math.max(1,math.ceil(#rows/30));self.listPage=math.max(1,math.min(self.listPage or 1,pages))
    for _,row in ipairs(ui.rows) do row:Hide() end
    local width=ui.frame:GetWidth()-46;ui.content:SetWidth(width)
    local count,offset=0,0
    for index=(self.listPage-1)*30+1,math.min(#rows,self.listPage*30) do
        count=count+1;local data=rows[index];local row=ui.rows[count]
        if not row then
            row=CreateFrame("Frame",nil,ui.content);self:Skin(row)
            row.title=self:Text(row,14);row.detail=self:Text(row,12,{.62,.69,.77})
            row.button=self:Button(row,"",nil,150);row.second=self:Button(row,"",nil,150);ui.rows[count]=row
        end
        row:SetWidth(width);row:ClearAllPoints();row:SetPoint("TOPLEFT",0,-offset)
        row.title:ClearAllPoints();row.title:SetPoint("TOPLEFT",12,-9);row.title:SetWidth(width-24);row.title:SetText(tostring(data.title));row.title:SetHeight(row.title:GetStringHeight())
        local titleHeight=math.max(16,row.title:GetStringHeight())
        row.detail:ClearAllPoints();row.detail:SetPoint("TOPLEFT",12,-12-titleHeight);row.detail:SetWidth(width-24);row.detail:SetText(tostring(data.detail or ""));row.detail:SetHeight(row.detail:GetStringHeight())
        local height=titleHeight+math.max(14,row.detail:GetStringHeight())+24+((data.action or data.second) and 34 or 0)
        row:SetHeight(height);offset=offset+height+6
        if data.action then row.button:ClearAllPoints();row.button:SetPoint("BOTTOMLEFT",12,8);row.button.text:SetText(data.action.text);row.button.action=data.action.fn;row.button:Show() else row.button:Hide() end
        if data.second then row.second:ClearAllPoints();row.second:SetPoint("BOTTOMLEFT",data.action and 168 or 12,8);row.second.text:SetText(data.second.text);row.second.action=data.second.fn;row.second:Show() else row.second:Hide() end
        row:Show()
    end
    local maxHeight=math.min(570,UIParent:GetHeight()*.90/math.min(self.db.settings.scale or 1,UIParent:GetWidth()*.94/680,UIParent:GetHeight()*.94/350))
    ui.frame:SetHeight(math.max(350,math.min(offset+196,maxHeight)))
    ui.content:SetHeight(math.max(1,offset));ui.scrollMax=math.max(0,offset-(ui.frame:GetHeight()-191));ui.bar:SetMinMaxValues(0,ui.scrollMax)
    ui.bar:SetShown(ui.scrollMax>1)
    if ui.scrollMax<=1 then ui.scroll:SetVerticalScroll(0);ui.bar:SetValue(0) end
    ui.previous:SetShown(pages>1);ui.nextButton:SetShown(pages>1);ui.pagination:SetText(pages>1 and (self.listPage.." / "..pages) or ("v"..self.version.."  /lc"))
    ui.pagination:ClearAllPoints();ui.pagination:SetPoint("BOTTOMLEFT",pages>1 and 152 or 18,20)
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
    self.ui.heading:SetText(({queue="Session",setup="Setup",discover="Explore crafting",requirements="Requirements",session_options="Session options",housing="Decor workshop"})[page] or page)
    for _,module in ipairs(modules) do if module[1]==page then self.ui.heading:SetText(module[2]) end end
    self.ui.sub:SetText(char.name.." - "..char.realm.."  /  "..(self.auctionOpen and "Auction house" or self.bankOpen and "Bank" or self.mailOpen and "Mailbox" or "Ready"))
    self:RefreshHeader()
    for id,b in pairs(self.ui.nav) do b.text:SetTextColor(unpack(id==page and self.theme.accent or {.62,.69,.77})) end
    local function action(text,fn) return {text=text,fn=fn} end
    if page=="overview" or page=="queue" then
        local session=self.db.activity
        if session and (session.state=="running" or session.state=="paused") then
            self:AddRow((self.modeNames[session.mode] or "Session").." / "..session.phase:upper(),self:SessionHint(),action(session.phase=="undercuts" and "Confirm scan reviewed" or "Continue phase",function() self:SessionNext() end),action("Session options",function() self.page="session_options";self:RefreshUI() end))
            if session.phase=="deposit" or session.phase=="withdraw" or session.phase=="craft_deposit" then
                self:AddRow("Warbank preparation",session.phase=="withdraw" and (session.stock.." of each planned item / "..session.gold.."g wallet target. Each click moves one stack; oversized stacks are split into a free bag slot.") or "Move planned trade/crafted items, then deposit wallet gold. Personal supplies are left for your review.",action("Move next items",function() self:SessionBankAction(false) end),action(session.phase=="withdraw" and "Top up wallet" or "Deposit wallet gold",function() self:SessionBankAction(true) end))
            end
            if session.mode=="craft" then
                for _,r in ipairs(self:SessionCrafts()) do local recipe=r;self:AddRow(r.name.." / "..(r.crafts or 0).." queued",(self:RecipeProfit(r) and self:Gold(self:RecipeProfit(r)).." observed profit per craft" or "Simulation expired - refresh CraftSim"),action("Open in profession",function() self:OpenRecipe(recipe) end),action("Shop materials",function() self:ShopMaterials() end)) end
            else
                local realm=self:SessionRealm();local alts={}
                for _,c in pairs(self.db.characters) do if (self:Here(realm) and c.realm==char.realm) or (self:Cluster(c.realm) and self:Cluster(c.realm)==self:Cluster(realm)) then alts[#alts+1]=c.name end end
                self:AddRow("Current market / "..tostring(realm),#alts>0 and ("Known characters: "..table.concat(alts,", ")) or "No character observed here. Create a posting alt on this realm and log in to discover it.")
                for _,t in ipairs(self:SessionItems()) do local task=t;self:AddRow(t.name.." / target "..(session.phase=="buy" and session.bulk or session.stock),t.from_realm.." > "..t.to_realm.." / "..(t.net_profit and ("estimated "..self:Gold(t.net_profit).." each") or "Profit not estimated; use live TSM pricing")..". Verify live price and transfer eligibility.",session.phase=="buy" and action("Search this item",function() self:SearchTask(task) end) or session.phase=="undercuts" and action("Scan posted variant",function() self:CheckUndercut(task) end) or nil,action("Skip this route",function() self:SkipSessionRoute(task.id) end)) end
                if session.phase=="undercuts" then for _,result in pairs(session.undercuts or {}) do self:AddRow("Item #"..result.item_id.." / "..result.status,"Own: "..self:Gold(result.own_price).." / lowest competitor: "..(result.competitor_price and self:Gold(result.competitor_price) or "Not present").." / "..date("%H:%M:%S",result.observed_at)..". Check exact variants and ties in TSM.") end end
                if session.phase=="post" or session.phase=="undercuts" then self:AddRow("TSM handoff",self:IntegrationStatus().TradeSkillMaster..". Open TSM Auctioning at the auction house; use Post Scan or Cancel Scan. LazyCrawler does not invoke private TSM UI internals.") end
            end
        else
            if session then self:AddRow(session.name.." / "..session.state,"Elapsed active play: "..math.floor(self:SessionElapsed()/60).." min. Your route queue is retained.") end
            self:AddRow("Realm flip run","Buy across suggested source markets, consolidate in your warbank, then supply posting alts and review undercuts.",action("Start realm flipping",function() self:StartActivity("flip") end),action("Start posting only",function() self:StartActivity("posting") end))
            self:AddRow("Crafting run","Craft available profitable recipes to minimum stock, then consolidate outputs and gold. Posting is a separate session.",action("Start crafting",function() self:StartActivity("craft") end),action("Explore all recipes",function() self:StartActivity("discover") end))
            self:AddRow("Data connection",self.data.generated_at and ("Bundle loaded: "..self.data.generated_at..". "..#(self.data.opportunities or {}).." verified route candidates.") or "No server bundle loaded. In the desktop app check Companion and run a region refresh. After a bundle is published, /reload in WoW.",action("Capture & diagnose",function() self:CaptureBags();self:CaptureBank();self:CaptureMail();self:CaptureAuctions();self.page="settings";self:RefreshUI() end))
        end
    elseif page=="session_options" then
        local session=self.db.activity
        if session then
            self:AddRow("Minimum posting/crafting stock / "..session.stock,"Applies to upcoming withdrawals and the current crafting plan. Default 1; maximum 200.",action("Decrease stock",function() session.stock=math.max(1,session.stock-1);self.db.settings.minimumStock=session.stock;if session.mode=="craft" then self:PlanSessionCrafts() end;self:Changed() end),action("Increase stock",function() session.stock=math.min(200,session.stock+1);self.db.settings.minimumStock=session.stock;if session.mode=="craft" then self:PlanSessionCrafts() end;self:Changed() end))
            self:AddRow("Bulk buying quantity / "..session.bulk,"Target per item on each source realm. Default 3.",action("Decrease quantity",function() session.bulk=math.max(1,session.bulk-1);self.db.settings.bulkQuantity=session.bulk;self:Changed() end),action("Increase quantity",function() session.bulk=math.min(200,session.bulk+1);self.db.settings.bulkQuantity=session.bulk;self:Changed() end))
            self:AddRow("Posting wallet / "..session.gold.."g","Only the difference between the current wallet and this target is withdrawn. Default 500g.",action("- 100g",function() session.gold=math.max(0,session.gold-100);self.db.settings.postingGold=session.gold;self:Changed() end),action("+ 100g",function() session.gold=math.min(1000000,session.gold+100);self.db.settings.postingGold=session.gold;self:Changed() end))
            self:AddRow("Return to run","Targets are saved with this session.",action("Current task",function() self.page="queue";self:RefreshUI() end))
        end
    elseif page=="setup" then
        self:Tutorial()
        self:AddRow("Ready for a working session","Start Realm flip, Posting, or Craft available from Session. If market evidence is missing, Settings shows capture and synchronization issues.",action("Choose a mode",function() self.page="overview";self:RefreshUI() end))
    elseif page=="radar" then
        if #(self.data.opportunities or {})==0 then self:AddRow("Waiting for the first market bundle","The server scans all unique auction houses. Character captures identify the home markets; no realm-selection list is needed.") end
        for _,candidate in ipairs(self.data.opportunities or {}) do
            local item=candidate
            self:AddRow(item.name.."  ·  +"..self:Gold(item.net_profit).." estimated",item.source_realm.." → "..item.destination_realm.."   |   "..tostring(item.roi).."% ROI. Base-item estimate; verify live variant and binding.",action("Review & queue",function() self:QueueCandidate(item) end))
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
    elseif page=="requirements" then
        local r=self.selectedRecipe
        if r then
            self:AddRow(r.name.." / requirements",(r.profession or "Profession unknown").." / "..(r.learned==false and "Recipe not learned" or "Learned by "..(r.character or char.name))..". "..(r.disabled_reason or "").."\n"..(r.requirements or "Minimum skill, recipe acquisition and specialization requirements were not supplied by this client. Open the recipe in the profession UI to inspect its source and locked requirements."),action("Open recipe details",function() self:OpenRecipe(r) end))
            if r.description then self:AddRow("Recipe description",r.description) end
            for _,requirement in ipairs(r.station_requirements or {}) do self:AddRow(requirement.name,requirement.met and "Requirement met when captured" or "Requirement not met when captured") end
            for _,m in ipairs(r.materials or {}) do self:AddRow("Material #"..m.item_id,m.quantity.." per craft / "..#(m.alternatives or {}).." reagent quality choices") end
        end
    elseif page=="discover" or page=="crafting" or page=="housing" then
        self:AddRow(page=="discover" and "Explore crafting / no timer" or "Crafting workspace","Available recipes come from professions you have opened. Unknown unlocks, specializations and profit are shown explicitly.",action("Refresh profession",function() self:CaptureRecipes() end),action(page=="housing" and "All recipes" or "Decor only",function() self.page=page=="housing" and "crafting" or "housing";self:RefreshUI() end))
        if page=="crafting" then self:AddRow("Craft now or research next","Craft available uses learned recipes and fresh character simulations. Explore includes unlearned recipes captured from opened professions across your characters.",action("Start craft session",function() self:StartActivity("craft") end),action("Explore crafting",function() self.page="discover";self:RefreshUI() end)) end
        local shown=0
        local recipes=page=="discover" and self.data.crafting_discovery or char.recipes
        for _,r in ipairs(recipes or {}) do
            if (page~="housing" or r.is_decor) and (page=="discover" or r.learned~=false) then
                local recipe=r;shown=shown+1
                local profit
                if page=="discover" then if not r.expires_at or r.expires_at>=time() then profit=r.profit_copper end else profit=self:RecipeProfit(r) end
                local description=page=="discover" and ((r.market_status or "No market estimate").." / "..(profit and (self:Gold(profit).." estimated per craft on "..tostring(r.destination_realm)) or "Potential profit unknown").." / sold/day: "..tostring(r.sold_day or "unknown").." / "..(r.character or "")..". "..(r.assumptions or "")) or (r.profession.." / "..(profit and (self:Gold(profit).." CraftSim profit / craft") or "Fresh simulation not observed"))
                self:AddRow(r.name..((r.crafts or 0)>0 and (" · "..r.crafts.." queued") or ""),description,action(page=="discover" and "Requirements" or "Open recipe",function() if page=="discover" then self.selectedRecipe=recipe;self.page="requirements";self:RefreshUI() else self:OpenRecipe(recipe) end end),page~="discover" and action("Queue +1",function() self:QueueRecipe(recipe) end) or nil)
            end
        end
        if shown==0 then self:AddRow("No matching recipes observed",page=="discover" and "No crafting discovery bundle loaded. Open professions (including unlearned recipes), /reload to export, wait for Companion to publish, then /reload again. No global recipe catalog is fabricated." or "Open the relevant profession. Housing classification uses the client's decor-item API when available.") end
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
        self:AddRow("Synchronization",self.data.generated_at and ("Loaded bundle "..self.data.generated_at) or "ISSUE: No server bundle. Publish data from Companion in the desktop app, then /reload.")
        for _,scope in ipairs({"bags","bank","mail","auctions"}) do local capture=char.storages[scope];if not capture then self:AddRow("Missing capture / "..scope,"Open this interface on this character. Wait for loading, then /reload to save and send the capture.") end end
        if not self.db.warbank then self:AddRow("Missing capture / warbank","Open a purchased warbank tab and allow its data to load. Unknown gold is never replaced by zero.") end
        self:AddRow("Color palette",self.db.settings.theme.." / neutral surfaces, rounded controls and adaptive height.",action("Change palette",function()
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
    self:FitWindow()
end
LC:On("PLAYER_REGEN_DISABLED",function() if LC.ui and LC.ui.frame:IsShown() and LC.db.settings.hideInCombat then LC.hiddenForCombat=true;LC.ui.frame:Hide() end end)
LC:On("PLAYER_REGEN_ENABLED",function() if LC.hiddenForCombat then LC.hiddenForCombat=false;LC:ShowUI() end end)
