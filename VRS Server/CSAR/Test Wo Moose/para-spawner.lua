

--[[
2 October 2020
FrozenDroid:
- Added error handling to all event handler and scheduled functions. Lua script errors can no longer bring the server down.
- Added some extra checks to which weapons to handle, make sure they actually have a warhead (how come S-8KOM's don't have a warhead field...?)
28 October 2020
FrozenDroid:
- Uncommented error logging, actually made it an error log which shows a message box on error.
- Fixed the too restrictive weapon filter (took out the HE warhead requirement)
--]]

para = {}

paraTable = {
	["PARATROOP"]	=	1,
}

local weaponDamageEnable = 1
paraHandler = {}
tracked_para = {}
paraRefreshRate = 0.1

local function getDistance(point1, point2)
  local x1 = point1.x
  local y1 = point1.y
  local z1 = point1.z
  local x2 = point2.x
  local y2 = point2.y
  local z2 = point2.z
  local dX = math.abs(x1-x2)
  local dZ = math.abs(z1-z2)
  local distance = math.sqrt(dX*dX + dZ*dZ)
  return distance
end

local function getDistance3D(point1, point2)
  local x1 = point1.x
  local y1 = point1.y
  local z1 = point1.z
  local x2 = point2.x
  local y2 = point2.y
  local z2 = point2.z
  local dX = math.abs(x1-x2)
  local dY = math.abs(y1-y2)
  local dZ = math.abs(z1-z2)
  local distance = math.sqrt(dX*dX + dZ*dZ + dY*dY)
  return distance
end

local function vec3Mag(speedVec)

	mag = speedVec.x*speedVec.x + speedVec.y*speedVec.y+speedVec.z*speedVec.z
	mag = math.sqrt(mag)
	--trigger.action.outText("X = " .. speedVec.x ..", y = " .. speedVec.y .. ", z = "..speedVec.z, 10)
	--trigger.action.outText("Speed = " .. mag, 1)
	return mag

end

local function lookahead(speedVec)

	speed = vec3Mag(speedVec)
	dist = speed * paraRefreshRate * 1.5
	return dist

end

function para.spawnpara(x, z)
	local _id = mist.getNextGroupId()
	local _groupName = "Para #" .. _id
	local _group = {
			["visible"] = true,
			["groupId"] = _id,
			["hidden"] = false,
			["route"]  = {},
			["units"] = {},
			["name"] = _groupName,
			["task"] = {},
			["start_time"] = 0,
			["country"] = 'CJTF_BLUE',
	}
	local randomUnit = mist.random(3)
	if randomUnit == 1 then
  	--_group.units[1] = para.createUnit(x + 5, z + 5, 1, "2B11 mortar")
		_group.units[1] = para.createUnit(x + 5, z + 5, 1, "Paratrooper RPG-16")
	elseif randomUnit == 2 then
		_group.units[1] = para.createUnit(x + 5, z + 5, 1, "Paratrooper RPG-16")
	else
		_group.units[1] = para.createUnit(x + 5, z + 5, 1, "Paratrooper RPG-16")
	end
	_group.category = Group.Category.GROUND;
	--timer.scheduleFunction(mist.dynAdd, _group, timer.getTime() + 2)
	mist.dynAdd(_group)
	--trigger.action.outText("Spawn:\nGrp: " .. _group.name .. "\nUnit: " .. _group.units[1].name, 2)
	return _group
end

function para.createUnit(_x, _y, _heading, _type)

    local _id = mist.getNextUnitId();

    local _name = string.format("Paratroop #%s", _id)

    local _newUnit = {
        ["y"] = _y,
        ["type"] = _type,
        ["name"] = _name,
        ["unitId"] = _id,
        ["heading"] = _heading,
        ["playerCanDrive"] = false,
        ["skill"] = "Excellent",
        ["x"] = _x,
    }

    return _newUnit
end

local function track_para()
--  env.info("Weapon Track Start")
	for para_id_, paraData in pairs(tracked_para) do
		if paraData.para:isExist() then  -- just update speed, position and direction.
			paraData.pos = paraData.para:getPosition().p
			paraData.dir = paraData.para:getPosition().x
			paraData.speed = paraData.para:getVelocity()
      --paraData.lastIP = land.getIP(paraData.pos, paraData.dir, 50)
		else -- para no longer exists, must be dead.
--      trigger.action.outText("Weapon impacted, mass of weapon warhead is " .. paraData.exMass, 2)
			local ip = land.getIP(paraData.pos, paraData.dir, lookahead(paraData.speed))  -- terrain intersection point with weapon's nose.  Only search out 20 meters though.
			local impactPoint
			if not ip then -- use last calculated IP
				impactPoint = paraData.pos
	      	--trigger.action.outText("(not ip)Impact Point:\nPos X: " .. impactPoint.x .. "\nPos Z: " .. impactPoint.z, 2)
			else -- use intersection point
				impactPoint = ip
	        --trigger.action.outText("Impact Point:\nPos X: " .. impactPoint.x .. "\nPos Z: " .. impactPoint.z, 2)
			end
			--env.info("Weapon is gone") -- Got to here --
			--trigger.action.outText("Weapon Type was: ".. paraData.name, 20)
			if paraTable[paraData.name] then
					--env.info("triggered explosion size: "..paraTable[paraData.name])
					--Hammer
					--trigger.action.explosion(impactPoint, paraTable[paraData.name])
					--replace with a unit spawn
					para.spawnpara(impactPoint.x, impactPoint.z)
					--trigger.action.smoke(impactPoint, 0)
			end
			tracked_para[para_id_] = nil -- remove from tracked weapons first.
		end
	end
--  env.info("Weapon Track End")
end

function onparaEvent(event)
  if event.id == world.event.S_EVENT_SHOT then
    if event.weapon then
      local ordnance = event.weapon
      local weapon_desc = ordnance:getDesc()
      if (weapon_desc.category ~= 0) and event.initiator then
		if (weapon_desc.category == 1) then
			if (weapon_desc.MissileCategory ~= 1 and weapon_desc.MissileCategory ~= 2) then
				tracked_para[event.weapon.id_] = { para = ordnance, init = event.initiator:getName(), pos = ordnance:getPoint(), dir = ordnance:getPosition().x, name = ordnance:getTypeName(), speed = ordnance:getVelocity() }
			end
		else
			tracked_para[event.weapon.id_] = { para = ordnance, init = event.initiator:getName(), pos = ordnance:getPoint(), dir = ordnance:getPosition().x, name = ordnance:getTypeName(), speed = ordnance:getVelocity() }
		end
      end
    end
  end
end

local function protectedCall(...)
  local status, retval = pcall(...)
  if not status then
    env.warning("Splash damage script error... gracefully caught! " .. retval, true)
  end
end


function paraHandler:onEvent(event)
  protectedCall(onparaEvent, event)
end

if (weaponDamageEnable == 1) then
  timer.scheduleFunction(function()
      protectedCall(track_para)
      return timer.getTime() + paraRefreshRate
    end,
    {},
    timer.getTime() + paraRefreshRate
  )
  world.addEventHandler(paraHandler)
end
