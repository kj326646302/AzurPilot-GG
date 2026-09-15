function Main1()
	SN = gg.choice({
		"修改面板",
		"还原面板",
		"退出",
	}, nil, "倍率面板")
	if SN==1 then
		HS9()
	end
	if SN==2 then
		HS666()
	end
	if SN==3 then
		exit()
	end
	FX=false
end

function writeStatus(status, count)
    local file = io.open("/sdcard/Notes/multiplier.status", "w")
    if file ~= nil then
        file:write(status .. ":" .. tostring(count or 0))
        file:close()
    end
end

function HS9()
    x = gg.prompt({"伤害倍数(默认200倍)"},{"200"},{number})
    if x == nil then
        writeStatus("cancel", 0)
        gg.setVisible(false)
        return
    end
    n = x[1]
    os.remove("/sdcard/Notes/multiplier.status")

	-- 第一次搜索（DOUBLE）
	gg.clearResults()
	gg.setRanges(32)
	gg.searchNumber("0.0001;1::30", gg.TYPE_DOUBLE, false, gg.SIGN_EQUAL, 0, -1, 0)
	gg.refineNumber("1", gg.TYPE_DOUBLE, false, gg.SIGN_EQUAL, 0, -1, 0)
	local results = gg.getResultCount()
	if results > 0 then
		gg.getResults(math.min(results, 100))
		gg.editAll(n, gg.TYPE_DOUBLE)
	else
		-- 第一种类型无结果时才尝试 DWORD。旧代码调用
		-- gg.getResultCount(results) 却没有接收返回值，results 永远为 nil，
		-- 导致每次都无条件执行第二轮搜索。
		gg.clearResults()
		gg.setRanges(32)
		gg.searchNumber("0.0001E;1D::30", gg.TYPE_DWORD, false, gg.SIGN_EQUAL, 0, -1)
		gg.refineNumber("1D", gg.TYPE_DWORD, false, gg.SIGN_EQUAL, 0, -1, 0)
		results = gg.getResultCount()
		if results > 0 then
			gg.getResults(math.min(results, 100))
			gg.editAll(n, gg.TYPE_DWORD)
		end
	end

	gg.clearResults()
	if results > 0 then
		writeStatus("ok", results)
		gg.toast("修改成功")
	else
		writeStatus("not_found", 0)
		gg.toast("未找到倍率数据，请确认已进入游戏")
	end
	-- Always hide GameGuardian after the script completes. Android Back returns
	-- from the result layer to the Execute Script dialog and leaves GG covering
	-- the game, so Alas sees the game screenshot but every tap is intercepted.
	gg.setVisible(false)
end

function HS666()
    x = gg.prompt({"还原倍数(默认200倍)"},{"200"},{number})
    if x == nil then
        writeStatus("cancel", 0)
        gg.setVisible(false)
        return
    end
    n = x[1]

	gg.clearResults()
	gg.setRanges(32)
	gg.searchNumber("0.0001;"..n.."::30", gg.TYPE_DOUBLE, false, gg.SIGN_EQUAL, 0, -1, 0)
	gg.refineNumber(n, gg.TYPE_DOUBLE, false, gg.SIGN_EQUAL, 0, -1, 0)
	local results = gg.getResultCount()
	if results > 0 then
		gg.getResults(math.min(results, 100))
		gg.editAll("1", gg.TYPE_DOUBLE)
	else
		gg.clearResults()
		gg.setRanges(32)
		gg.searchNumber("0.0001E;"..n.."::30", gg.TYPE_DWORD, false, gg.SIGN_EQUAL, 0, -1)
		gg.refineNumber(n, gg.TYPE_DWORD, false, gg.SIGN_EQUAL, 0, -1)
		results = gg.getResultCount()
		if results > 0 then
			gg.getResults(math.min(results, 100))
			gg.editAll("1", gg.TYPE_DWORD)
		end
	end

	gg.clearResults()
	if results > 0 then
		writeStatus("restore_ok", results)
		gg.toast("还原成功")
	else
		writeStatus("restore_not_found", 0)
	end
	gg.setVisible(false)
end

function exit()
    gg.alert("退出成功")
	os.exit()
end

-- 循环
-- while true do
--	if gg.isVisible(true) then
--		FX=true
--		gg.setVisible(false)
--	end
	gg.clearResults()
--	if FX==true then
		Main1()
--	end
-- end
