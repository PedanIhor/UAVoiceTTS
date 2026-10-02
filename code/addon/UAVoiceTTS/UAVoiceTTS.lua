-- UAVoiceTTS 0.4: Ukrainian quest voiceover in the background, with a queue.
-- Quest accepted → the quest giver reads the description; quest turned in → the turn-in NPC reads the completion text.
-- Several quests in a row are read one after another while the player does whatever they want.
-- Sound: Sounds\<file from Index.lua>, "Dialog" channel (if disabled — Master).
local ADDON = ...
local PATH = "Interface\\AddOns\\" .. ADDON .. "\\Sounds\\"
local DEFAULTS = { enabled = true, subtitles = true, accept = true, complete = true, panel = true, point = nil }
local HISTORY_MAX = 200

local queue, cur = {}, nil      -- cur = { quest, part, v, title, npc, started, handle, timer, cueTimers }
local npcName = nil             -- NPC name from the open quest window (for the panel)
local last = nil                -- last played line (for reports, even after it finished)
local lastLine = ""            -- sentence that was playing
local db

------------------------------------------------------------------ panel
local panel = CreateFrame("Frame", "UAVoiceTTSPanel", UIParent, "BackdropTemplate")
panel:SetSize(340, 86); panel:SetPoint("TOP", UIParent, "TOP", 0, -120); panel:Hide()
panel:SetBackdrop({ bgFile = "Interface\\Tooltips\\UI-Tooltip-Background", edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border",
                    tile = true, tileSize = 16, edgeSize = 14, insets = { left = 3, right = 3, top = 3, bottom = 3 } })
panel:SetBackdropColor(0, 0, 0, 0.75); panel:SetBackdropBorderColor(0.6, 0.6, 0.6, 0.9)
panel:SetMovable(true); panel:EnableMouse(true); panel:RegisterForDrag("LeftButton"); panel:SetClampedToScreen(true)
panel:SetScript("OnDragStart", panel.StartMoving)
panel:SetScript("OnDragStop", function(self)
    self:StopMovingOrSizing(); local p, _, rp, x, y = self:GetPoint(); db.point = { p, rp, x, y }
end)

local icon = panel:CreateTexture(nil, "ARTWORK"); icon:SetSize(36, 36); icon:SetPoint("TOPLEFT", 8, -8)
icon:SetTexture("Interface\\Icons\\INV_Misc_Note_01")
local title = panel:CreateFontString(nil, "OVERLAY", "GameFontNormal")
title:SetPoint("TOPLEFT", icon, "TOPRIGHT", 8, -1); title:SetPoint("RIGHT", panel, "RIGHT", -96, 0); title:SetJustifyH("LEFT"); title:SetWordWrap(false)
local who = panel:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
who:SetPoint("TOPLEFT", title, "BOTTOMLEFT", 0, -3); who:SetPoint("RIGHT", panel, "RIGHT", -96, 0); who:SetJustifyH("LEFT"); who:SetWordWrap(false)
local subtitle = panel:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
subtitle:SetPoint("TOPLEFT", icon, "BOTTOMLEFT", 0, -6); subtitle:SetPoint("RIGHT", panel, "RIGHT", -10, 0)
subtitle:SetJustifyH("LEFT"); subtitle:SetJustifyV("TOP"); subtitle:SetWordWrap(true)
local progress = panel:CreateTexture(nil, "OVERLAY"); progress:SetColorTexture(1, 0.82, 0, 0.8); progress:SetHeight(2)
progress:SetPoint("BOTTOMLEFT", 4, 4)

local function Button(tex, tip, x, onClick)
    local b = CreateFrame("Button", nil, panel); b:SetSize(20, 20); b:SetPoint("TOPRIGHT", x, -8)
    b:SetNormalTexture(tex); b:SetHighlightTexture("Interface\\Buttons\\ButtonHilight-Square", "ADD")
    b:SetScript("OnClick", onClick)
    b:SetScript("OnEnter", function(self) GameTooltip:SetOwner(self, "ANCHOR_TOP"); GameTooltip:SetText(tip); GameTooltip:Show() end)
    b:SetScript("OnLeave", GameTooltip_Hide)
    return b
end

------------------------------------------------------------------ playback
local Stop, PlayNext, Layout

local function Channel()
    local en = GetCVar and GetCVar("Sound_EnableDialog")
    local vol = tonumber(GetCVar and GetCVar("Sound_DialogVolume")) or 1
    return (en == "0" or vol < 0.05) and "Master" or "Dialog"
end

local function Entry(questID, part)
    local q = UAVoiceTTS_Index and UAVoiceTTS_Index[questID]
    local e = q and q[part]
    if not e then return nil end
    local v = e.x or (UnitSex("player") == 3 and e.f or e.m)
    return v, q.t
end

function Stop(keepPanel)
    if cur then
        if cur.handle then StopSound(cur.handle, 400) end
        if cur.timer then cur.timer:Cancel() end
        for _, t in ipairs(cur.cueTimers or {}) do t:Cancel() end
        cur = nil
    end
    if not keepPanel then Layout() end
end

local function Start(item)
    local willPlay, h = PlaySoundFile(PATH .. item.v.f, Channel())
    if not willPlay then return false end
    cur = item; cur.handle = h; cur.started = GetTime(); cur.cueTimers = {}; last = item; lastLine = ""
    db.history = db.history or {}
    local top = db.history[1]
    if not (top and top.q == item.quest and top.p == item.part) then
        table.insert(db.history, 1, { q = item.quest, p = item.part, f = item.v.f, t = item.title, n = item.npc, time = date("%d.%m %H:%M") })
        while #db.history > HISTORY_MAX do table.remove(db.history) end
    end
    if UAVoiceTTS_RefreshHistory then UAVoiceTTS_RefreshHistory() end
    subtitle:SetText("")
    if item.v.c then
        for _, cue in ipairs(item.v.c) do
            table.insert(cur.cueTimers, C_Timer.NewTimer(cue[1], function() if cur == item then subtitle:SetText(cue[2]); lastLine = cue[2]; Layout() end end))
        end
    end
    cur.timer = C_Timer.NewTimer(item.v.d + 0.6, function() if cur == item then cur = nil; PlayNext() end end)
    Layout()
    return true
end

function PlayNext()
    while #queue > 0 do
        local item = table.remove(queue, 1)
        if Start(item) then return end
    end
    Layout()
end

local function Enqueue(questID, part)
    if not db.enabled or not questID or questID <= 0 then return end
    if (part == "a" and not db.accept) or (part == "c" and not db.complete) then return end
    local v, t = Entry(questID, part)
    if not v then return end
    if cur and cur.quest == questID and cur.part == part then return end
    for _, it in ipairs(queue) do if it.quest == questID and it.part == part then return end end
    table.insert(queue, { quest = questID, part = part, v = v, title = t, npc = npcName })
    if not cur then PlayNext() else Layout() end
end

local function Skip() Stop(true); PlayNext() end
local function ClearAll() wipe(queue); Stop() end
local function Replay()
    if not cur then return end
    local item = { quest = cur.quest, part = cur.part, v = cur.v, title = cur.title, npc = cur.npc }
    Stop(true); Start(item)
end

Button("Interface\\Buttons\\UI-SpellbookIcon-NextPage-Up", "Наступний", -8, Skip)
Button("Interface\\Buttons\\UI-RefreshButton", "Повторити", -30, Replay)
Button("Interface\\Buttons\\UI-GroupLoot-Pass-Up", "Зупинити й очистити чергу", -52, ClearAll)
local OpenReport  -- defined below
Button("Interface\\Buttons\\UI-GuildButton-PublicNote-Up", "Поскаржитися на озвучку", -74, function() OpenReport() end)
-- replay a history entry (now, bypassing the queue)
local function PlayHistory(h)
    local v, t = Entry(h.q, h.p)
    if not v then return end
    Stop(true); Start({ quest = h.q, part = h.p, v = v, title = t or h.t, npc = h.n })
end

function Layout()
    if not cur or not db.panel then
        if not cur then panel:Hide() end
        if not db.panel then panel:Hide() end
        return
    end
    local partName = cur.part == "a" and "Завдання" or "Завдання виконано"
    title:SetText(cur.title or ("Квест " .. cur.quest))
    who:SetText(partName .. (cur.npc and (" · " .. cur.npc) or "") .. (#queue > 0 and ("   |cffffd100ще " .. #queue .. " у черзі|r") or ""))
    if not db.subtitles then subtitle:SetText("") end
    local h = 54 + (db.subtitles and math.max(subtitle:GetStringHeight(), 14) + 8 or 0)
    panel:SetHeight(h)
    panel:Show()
end

panel:SetScript("OnUpdate", function()
    if not cur then return end
    local f = math.min(1, (GetTime() - cur.started) / math.max(cur.v.d, 0.1))
    progress:SetWidth(math.max(1, (panel:GetWidth() - 8) * f))
end)


------------------------------------------------------------------ reports
-- The addon cannot send anything to the internet: a report is stored in UAVoiceTTSDB.reports (SavedVariables file,
-- written on exit / /reload) and shown as a line to copy — it can be sent to the author.
local REASONS = { "наголос", "пауза або затягування", "обірвано / недоговорено", "зайві звуки", "не той голос", "текст не збігається", "інше" }
local rep = CreateFrame("Frame", "UAVoiceTTSReport", UIParent, "BackdropTemplate")
rep:SetSize(380, 330); rep:SetPoint("CENTER"); rep:SetFrameStrata("DIALOG"); rep:Hide()
rep:SetBackdrop({ bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background", edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
                  tile = true, tileSize = 32, edgeSize = 24, insets = { left = 8, right = 8, top = 8, bottom = 8 } })
rep:EnableMouse(true); rep:SetMovable(true); rep:RegisterForDrag("LeftButton")
rep:SetScript("OnDragStart", rep.StartMoving); rep:SetScript("OnDragStop", rep.StopMovingOrSizing)
tinsert(UISpecialFrames, "UAVoiceTTSReport")   -- closes with Esc
local rTitle = rep:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge"); rTitle:SetPoint("TOP", 0, -16); rTitle:SetText("Поскаржитися на озвучку")
local rWhat = rep:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall"); rWhat:SetPoint("TOPLEFT", 20, -42); rWhat:SetPoint("RIGHT", -20, 0)
rWhat:SetJustifyH("LEFT"); rWhat:SetWordWrap(true)
local checks, chosen = {}, 1
for i, r in ipairs(REASONS) do
    local c = CreateFrame("CheckButton", nil, rep, "UICheckButtonTemplate"); c:SetSize(22, 22)
    c:SetPoint("TOPLEFT", 18 + ((i - 1) % 2) * 172, -86 - math.floor((i - 1) / 2) * 24)
    local t = c:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall"); t:SetPoint("LEFT", c, "RIGHT", 2, 0); t:SetText(r)
    c:SetScript("OnClick", function() chosen = i; for j, o in ipairs(checks) do o:SetChecked(j == i) end end)
    checks[i] = c
end
local function Input(label, y)
    local l = rep:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall"); l:SetPoint("TOPLEFT", 22, y); l:SetText(label)
    local e = CreateFrame("EditBox", nil, rep, "InputBoxTemplate"); e:SetSize(330, 20); e:SetPoint("TOPLEFT", 26, y - 14); e:SetAutoFocus(false)
    e:SetScript("OnEscapePressed", function() rep:Hide() end)
    return e
end
local eWord = Input("Слово з помилкою (ударну голосну — великою: впОрався):", -190)
local eNote = Input("Коментар (необов'язково):", -232)
local eCopy = CreateFrame("EditBox", nil, rep, "InputBoxTemplate"); eCopy:SetSize(330, 20); eCopy:SetPoint("BOTTOM", 0, 48); eCopy:SetAutoFocus(false); eCopy:Hide()
local rHint = rep:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall"); rHint:SetPoint("BOTTOM", eCopy, "TOP", 0, 3); rHint:SetText("Збережено. Скопіюйте (Ctrl+C) і вставте в Discord-канал скарг:"); rHint:Hide()
local target
local bSend = CreateFrame("Button", nil, rep, "UIPanelButtonTemplate"); bSend:SetSize(120, 22); bSend:SetPoint("BOTTOMRIGHT", -20, 16); bSend:SetText("Зберегти")
local bClose = CreateFrame("Button", nil, rep, "UIPanelButtonTemplate"); bClose:SetSize(100, 22); bClose:SetPoint("BOTTOMLEFT", 20, 16); bClose:SetText("Закрити")
bClose:SetScript("OnClick", function() rep:Hide() end)
local function clean(s) return ((s or ""):gsub("[|;]", "/"):gsub("^%s+", ""):gsub("%s+$", "")) end
-- Report line for Discord: UAV#1;quest;part;sex;file;reason;word;comment
-- (no "|" character — it is reserved in WoW; fields are separated by ";" so they can be parsed from chat)
local function ReportCode(r)
    return string.format("UAV#1;%s;%s;%s;%s;%s;%s;%s", r.q, r.p, r.sex or "", r.s or "", clean(r.reason), clean(r.word), clean(r.note))
end
UAVoiceTTS_ReportCode = ReportCode
bSend:SetScript("OnClick", function()
    if not target then return end
    local r = { q = target.quest, p = target.part, s = target.v.f, reason = REASONS[chosen], word = clean(eWord:GetText()),
                note = clean(eNote:GetText()), time = date("%Y-%m-%d %H:%M"), sex = UnitSex("player") == 3 and "f" or "m" }
    db.reports = db.reports or {}; table.insert(db.reports, r)
    local code = ReportCode(r)
    eCopy:SetText(code); eCopy:Show(); rHint:Show(); eCopy:SetFocus(); eCopy:HighlightText()
    print("|cff1177eeUA|r|cffffdd00VoiceTTS|r: скаргу збережено (усього " .. #db.reports .. "). Дякуємо!")
end)
-- it: a line from the queue/last playback ({quest, part, v}) or a history entry ({q, p, f, t}); line — the sentence that was playing
function OpenReport(it, line)
    if not it then it = cur or last; line = lastLine end
    if not it then print("|cff1177eeUA|r|cffffdd00VoiceTTS|r: ще нічого не звучало — відкрийте історію: /uavoice history"); return end
    if it.q then it = { quest = it.q, part = it.p, v = { f = it.f }, title = it.t } end
    line = line or ""
    target = { quest = it.quest, part = it.part, v = it.v, line = line }
    rWhat:SetText((it.title or ("Квест " .. it.quest)) .. (it.part == "a" and " — завдання" or " — здача") ..
                  "")
    chosen = 1; for j, o in ipairs(checks) do o:SetChecked(j == 1) end
    eWord:SetText(""); eNote:SetText(""); eCopy:Hide(); rHint:Hide(); rep:Show()
end


------------------------------------------------------------------ settings and history (Settings → AddOns)
local opt = CreateFrame("Frame", "UAVoiceTTSOptions"); opt.name = "UAVoiceTTS"; opt:Hide()
local oTitle = opt:CreateFontString(nil, "ARTWORK", "GameFontNormalLarge"); oTitle:SetPoint("TOPLEFT", 16, -16)
oTitle:SetText("|cff1177eeUA|r|cffffdd00VoiceTTS|r — українська озвучка квестів")
local OPTS = { { "enabled", "Озвучка увімкнена" }, { "accept", "Читати опис, коли квест узято" }, { "complete", "Читати текст, коли квест здано" },
               { "subtitles", "Субтитри" }, { "panel", "Панель під час читання" } }
local optChecks = {}
for i, o in ipairs(OPTS) do
    local c = CreateFrame("CheckButton", nil, opt, "UICheckButtonTemplate"); c:SetSize(24, 24)
    c:SetPoint("TOPLEFT", 16 + ((i - 1) % 3) * 210, -46 - math.floor((i - 1) / 3) * 26)
    local t = c:CreateFontString(nil, "OVERLAY", "GameFontHighlight"); t:SetPoint("LEFT", c, "RIGHT", 2, 0); t:SetText(o[2])
    c:SetScript("OnClick", function(self) db[o[1]] = self:GetChecked() and true or false; if o[1] == "enabled" and not db.enabled then ClearAll() end; Layout() end)
    optChecks[o[1]] = c
end
local hHead = opt:CreateFontString(nil, "ARTWORK", "GameFontNormal"); hHead:SetPoint("TOPLEFT", 18, -110)
hHead:SetText("Історія прослуханого (нове — зверху). «Слухати» — ще раз, «Скарга» — повідомити про проблему.")
local ROWS, page = 14, 0
local rows = {}
for i = 1, ROWS do
    local r = CreateFrame("Frame", nil, opt); r:SetSize(620, 22); r:SetPoint("TOPLEFT", 16, -130 - (i - 1) * 24)
    r.bg = r:CreateTexture(nil, "BACKGROUND"); r.bg:SetAllPoints(); r.bg:SetColorTexture(1, 1, 1, i % 2 == 0 and 0.04 or 0)
    r.text = r:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall"); r.text:SetPoint("LEFT", 4, 0); r.text:SetPoint("RIGHT", -170, 0)
    r.text:SetJustifyH("LEFT"); r.text:SetWordWrap(false)
    r.play = CreateFrame("Button", nil, r, "UIPanelButtonTemplate"); r.play:SetSize(76, 20); r.play:SetPoint("RIGHT", -86, 0); r.play:SetText("Слухати")
    r.rep = CreateFrame("Button", nil, r, "UIPanelButtonTemplate"); r.rep:SetSize(80, 20); r.rep:SetPoint("RIGHT", -2, 0); r.rep:SetText("Скарга")
    rows[i] = r
end
local pageText = opt:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall"); pageText:SetPoint("TOPLEFT", 20, -130 - ROWS * 24 - 8)
local bPrev = CreateFrame("Button", nil, opt, "UIPanelButtonTemplate"); bPrev:SetSize(110, 22); bPrev:SetPoint("TOPLEFT", 200, -130 - ROWS * 24 - 4); bPrev:SetText("Новіші")
local bNext = CreateFrame("Button", nil, opt, "UIPanelButtonTemplate"); bNext:SetSize(110, 22); bNext:SetPoint("LEFT", bPrev, "RIGHT", 8, 0); bNext:SetText("Старіші")
local repCount = opt:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall"); repCount:SetPoint("LEFT", bNext, "RIGHT", 16, 0)
-- all saved reports as one text — copy and paste into Discord
local all = CreateFrame("Frame", "UAVoiceTTSAllReports", UIParent, "BackdropTemplate")
all:SetSize(560, 300); all:SetPoint("CENTER"); all:SetFrameStrata("DIALOG"); all:Hide(); tinsert(UISpecialFrames, "UAVoiceTTSAllReports")
all:SetBackdrop({ bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background", edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
                  tile = true, tileSize = 32, edgeSize = 24, insets = { left = 8, right = 8, top = 8, bottom = 8 } })
local allT = all:CreateFontString(nil, "OVERLAY", "GameFontNormal"); allT:SetPoint("TOP", 0, -16)
allT:SetText("Скарги для Discord: Ctrl+A, Ctrl+C — і вставте в канал")
local sf = CreateFrame("ScrollFrame", nil, all, "UIPanelScrollFrameTemplate"); sf:SetPoint("TOPLEFT", 18, -40); sf:SetPoint("BOTTOMRIGHT", -36, 48)
local allBox = CreateFrame("EditBox", nil, sf); allBox:SetMultiLine(true); allBox:SetFontObject(ChatFontNormal); allBox:SetWidth(490); allBox:SetAutoFocus(false)
allBox:SetScript("OnEscapePressed", function() all:Hide() end); sf:SetScrollChild(allBox)
local allClose = CreateFrame("Button", nil, all, "UIPanelButtonTemplate"); allClose:SetSize(100, 22); allClose:SetPoint("BOTTOMRIGHT", -18, 16); allClose:SetText("Закрити")
allClose:SetScript("OnClick", function() all:Hide() end)
local function ShowAllReports()
    local lines = {}
    for _, r in ipairs(db.reports or {}) do lines[#lines + 1] = UAVoiceTTS_ReportCode(r) end
    allBox:SetText(#lines > 0 and table.concat(lines, "\n") or "Скарг ще немає.")
    all:Show(); allBox:SetFocus(); allBox:HighlightText()
end
local bAll = CreateFrame("Button", nil, opt, "UIPanelButtonTemplate"); bAll:SetSize(150, 22); bAll:SetPoint("TOPLEFT", 20, -130 - ROWS * 24 - 32)
bAll:SetText("Скарги для Discord"); bAll:SetScript("OnClick", ShowAllReports)
function UAVoiceTTS_RefreshHistory()
    if not db or not opt:IsShown() then return end
    for k, c in pairs(optChecks) do c:SetChecked(db[k]) end
    local h = db.history or {}
    local pages = math.max(1, math.ceil(#h / ROWS)); page = math.min(page, pages - 1)
    for i = 1, ROWS do
        local e = h[page * ROWS + i]; local r = rows[i]
        if e then
            r.text:SetText(string.format("|cff888888%s|r  %s  |cffaaaaaa%s%s|r", e.time or "", e.t or ("Квест " .. e.q),
                           e.p == "a" and "завдання" or "здача", e.n and (" · " .. e.n) or ""))
            r.play:SetScript("OnClick", function() PlayHistory(e) end)
            r.rep:SetScript("OnClick", function() OpenReport(e) end)
            r:Show()
        else r:Hide() end
    end
    pageText:SetText(#h == 0 and "Ще нічого не прослухано." or string.format("сторінка %d з %d · записів %d", page + 1, pages, #h))
    bPrev:SetEnabled(page > 0); bNext:SetEnabled(page < pages - 1)
    repCount:SetText("скарг збережено: " .. #(db.reports or {}))
end
bPrev:SetScript("OnClick", function() page = math.max(0, page - 1); UAVoiceTTS_RefreshHistory() end)
bNext:SetScript("OnClick", function() page = page + 1; UAVoiceTTS_RefreshHistory() end)
opt:SetScript("OnShow", function() page = 0; UAVoiceTTS_RefreshHistory() end)
local optCategory
if Settings and Settings.RegisterCanvasLayoutCategory then
    optCategory = Settings.RegisterCanvasLayoutCategory(opt, opt.name); Settings.RegisterAddOnCategory(optCategory)
elseif InterfaceOptions_AddCategory then
    InterfaceOptions_AddCategory(opt)
end
local function OpenOptions()
    if optCategory and Settings and Settings.OpenToCategory then Settings.OpenToCategory(optCategory:GetID())
    elseif InterfaceOptionsFrame_OpenToCategory then InterfaceOptionsFrame_OpenToCategory(opt); InterfaceOptionsFrame_OpenToCategory(opt) end
end


------------------------------------------------------------------ "Listen" button in quest windows
-- Manual start: plays immediately (even if auto-reading is off); whatever was playing goes back to the front of the queue.
local function PlayNow(questID, part)
    local v, t = Entry(questID, part)
    if not v then return false end
    for i = #queue, 1, -1 do if queue[i].quest == questID and queue[i].part == part then table.remove(queue, i) end end
    if cur then
        if cur.quest == questID and cur.part == part then return true end
        table.insert(queue, 1, { quest = cur.quest, part = cur.part, v = cur.v, title = cur.title, npc = cur.npc })
        Stop(true)
    end
    table.insert(queue, 1, { quest = questID, part = part, v = v, title = t, npc = npcName })
    PlayNext()
    return true
end
local function ListenButton(parent, point, rel, relPoint, x, y)
    local b = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate"); b:SetSize(104, 22); b:SetPoint(point, rel, relPoint, x, y)
    b:SetText("Прослухати"); b:SetFrameLevel(parent:GetFrameLevel() + 10)
    b:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_TOP")
        GameTooltip:SetText(self:IsEnabled() and "Прочитати текст квесту голосом NPC" or "Для цього квесту озвучки ще немає")
        GameTooltip:Show()
    end)
    b:SetScript("OnLeave", GameTooltip_Hide); b:SetMotionScriptsWhileDisabled(true)
    return b
end
-- NPC window: description (accept) or turn-in text
local qfButton, qfPart
if QuestFrame then
    qfButton = ListenButton(QuestFrame, "TOPRIGHT", QuestFrame, "TOPRIGHT", -44, -48); qfButton:Hide()
    qfButton:SetScript("OnClick", function() local id = GetQuestID and GetQuestID(); if id then PlayNow(id, qfPart) end end)
end
local function ShowQuestFrameButton(part)
    if not qfButton then return end
    qfPart = part
    local id = GetQuestID and GetQuestID()
    qfButton:SetEnabled(id and Entry(id, part) ~= nil); qfButton:Show()
end
-- quest log: description of the selected quest. In WoW Forever the log is part of the map ("Map & Quest Log", QuestMapFrame);
-- in the old UI it is a separate QuestLogFrame window. We support both.
local logButton
local function LogQuestID()
    if QuestMapFrame and QuestMapFrame.DetailsFrame and QuestMapFrame.DetailsFrame:IsVisible() then
        local id = QuestMapFrame.DetailsFrame.questID or (C_QuestLog and C_QuestLog.GetSelectedQuest and C_QuestLog.GetSelectedQuest())
        if id and id > 0 then return id end
    end
    local idx = GetQuestLogSelection and GetQuestLogSelection()
    if not idx or idx == 0 then return nil end
    if C_QuestLog and C_QuestLog.GetQuestIDForLogIndex then return C_QuestLog.GetQuestIDForLogIndex(idx) end
    return select(8, GetQuestLogTitle(idx))
end
local function UpdateLogButton()
    if not logButton then return end
    local id = LogQuestID(); logButton:SetEnabled(id and Entry(id, "a") ~= nil)
end
local function MakeLogButton()
    if logButton then return end
    local df = QuestMapFrame and QuestMapFrame.DetailsFrame
    if df then
        local back = (df.BackFrame and df.BackFrame.BackButton) or df.BackButton
        if back then logButton = ListenButton(df, "LEFT", back, "RIGHT", 8, 0)
        else logButton = ListenButton(df, "TOPRIGHT", df, "TOPRIGHT", -8, -8) end
        df:HookScript("OnShow", function() C_Timer.After(0, UpdateLogButton) end)
        if QuestMapFrame_ShowQuestDetails then hooksecurefunc("QuestMapFrame_ShowQuestDetails", function() C_Timer.After(0, UpdateLogButton) end) end
    elseif QuestLogFrame then
        logButton = ListenButton(QuestLogFrame, "TOPRIGHT", QuestLogFrame, "TOPRIGHT", -56, -46)
        QuestLogFrame:HookScript("OnShow", UpdateLogButton)
        if SelectQuestLogEntry then hooksecurefunc("SelectQuestLogEntry", UpdateLogButton) end
        if QuestLog_Update then hooksecurefunc("QuestLog_Update", UpdateLogButton) end
    end
    if logButton then logButton:SetScript("OnClick", function() local id = LogQuestID(); if id then PlayNow(id, "a") end end) end
end
MakeLogButton()   -- if the map isn't loaded yet — retry on login

------------------------------------------------------------------ events
local ev = CreateFrame("Frame")
ev:RegisterEvent("ADDON_LOADED"); ev:RegisterEvent("QUEST_DETAIL"); ev:RegisterEvent("QUEST_COMPLETE")
ev:RegisterEvent("QUEST_ACCEPTED"); ev:RegisterEvent("QUEST_TURNED_IN")
ev:RegisterEvent("QUEST_PROGRESS"); ev:RegisterEvent("QUEST_GREETING"); ev:RegisterEvent("QUEST_FINISHED"); ev:RegisterEvent("PLAYER_LOGIN")
ev:SetScript("OnEvent", function(_, e, a, b)
    if e == "ADDON_LOADED" and a == ADDON then
        UAVoiceTTSDB = UAVoiceTTSDB or {}; db = UAVoiceTTSDB
        for k, v in pairs(DEFAULTS) do if db[k] == nil then db[k] = v end end
        if db.point then panel:ClearAllPoints(); panel:SetPoint(db.point[1], UIParent, db.point[2], db.point[3], db.point[4]) end
    elseif e == "ADDON_LOADED" and (a == "Blizzard_WorldMap" or a == "Blizzard_QuestLog") then MakeLogButton()
    elseif e == "PLAYER_LOGIN" then MakeLogButton()
    elseif not db then return
    elseif e == "QUEST_DETAIL" or e == "QUEST_COMPLETE" then
        npcName = UnitName("npc")
        ShowQuestFrameButton(e == "QUEST_DETAIL" and "a" or "c")
    elseif e == "QUEST_PROGRESS" or e == "QUEST_GREETING" or e == "QUEST_FINISHED" then
        if qfButton then qfButton:Hide() end
    elseif e == "QUEST_ACCEPTED" then
        local questID = b or a                      -- classic: (quest log index, questID)
        C_Timer.After(0.2, function() Enqueue(questID, "a") end)
    elseif e == "QUEST_TURNED_IN" then
        Enqueue(a, "c")
    end
end)

------------------------------------------------------------------ commands
local function Say(s) print("|cff1177eeUA|r|cffffdd00VoiceTTS|r: " .. s) end
local function onoff(v) return v and "увімкнено" or "вимкнено" end
SLASH_UAVOICETTS1 = "/uavoice"
SlashCmdList.UAVOICETTS = function(msg)
    local m = (msg or ""):lower():match("^%s*(%S*)")
    if m == "off" then db.enabled = false; ClearAll(); Say("озвучку вимкнено")
    elseif m == "on" then db.enabled = true; Say("озвучку увімкнено")
    elseif m == "sub" then db.subtitles = not db.subtitles; Layout(); Say("субтитри " .. onoff(db.subtitles))
    elseif m == "accept" then db.accept = not db.accept; Say("опис при взятті " .. onoff(db.accept))
    elseif m == "complete" then db.complete = not db.complete; Say("текст при здачі " .. onoff(db.complete))
    elseif m == "panel" then db.panel = not db.panel; Layout(); Say("панель " .. onoff(db.panel))
    elseif m == "skip" or m == "next" then Skip()
    elseif m == "stop" or m == "clear" then ClearAll(); Say("зупинено, чергу очищено")
    elseif m == "reset" then db.point = nil; panel:ClearAllPoints(); panel:SetPoint("TOP", UIParent, "TOP", 0, -120); Say("панель на місці")
    elseif m == "report" then
        local n = tonumber((msg or ""):match("report%s+(%d+)"))
        if n then local e = (db.history or {})[n]; if e then OpenReport(e) else Say("у історії немає запису №" .. n) end else OpenReport() end
    elseif m == "history" or m == "menu" or m == "config" or m == "" then OpenOptions()
    elseif m == "list" then
        for i = 1, math.min(10, #(db.history or {})) do local e = db.history[i]; Say(string.format("%d. %s — %s", i, e.t or e.q, e.p == "a" and "завдання" or "здача")) end
    elseif m == "discord" then ShowAllReports()
    elseif m == "reports" then Say("скарг збережено: " .. #(db.reports or {}) .. " (файл WTF\\Account\\…\\SavedVariables\\UAVoiceTTS.lua)")
    elseif m == "test" then
        local q = next(UAVoiceTTS_Index or {}); if q then Enqueue(q, "a") else Say("озвучених квестів немає") end
    else
        Say("/uavoice — меню з історією; on|off — озвучка; skip — наступний; stop — зупинити й очистити чергу; sub — субтитри; " ..
            "accept / complete — читати опис при взятті / текст при здачі; panel — панель; reset — повернути панель; " ..
            "report — скарга на останню репліку; report N — на N-ту з історії; list — 10 останніх; discord — усі скарги для Discord; reports — скільки скарг; test — перевірка")
    end
end
