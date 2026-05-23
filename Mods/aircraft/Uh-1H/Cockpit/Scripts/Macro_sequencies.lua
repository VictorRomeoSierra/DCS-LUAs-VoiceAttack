dofile(LockOn_Options.script_path.."command_defs.lua")
dofile(LockOn_Options.script_path.."devices.lua")

-- · VRS Quick Start · UH-1H Huey ·
-- Part of the VRS Auto Starts mod for DCS World
-- Install via OvGME: https://wiki.hoggitworld.com/view/OVGME

mto = 10

local t_start = 0.0
local t_stop = 0.0
local dt = 0.001

start_sequence_full = {}
stop_sequence_full = {}

function push_command(sequence, run_t, command)
	sequence[#sequence + 1] =  command
	sequence[#sequence]["time"] = run_t
end

function push_start_command(delta_t, command)
	t_start = t_start + delta_t
	push_command(start_sequence_full,t_start, command)
end

function push_stop_command(delta_t, command)
	t_stop = t_stop + delta_t
	push_command(stop_sequence_full,t_stop, command)
end

NO_FUEL = 1
COLLECTIVE = 2
BATTERY_LOW	= 3

alert_messages = {}
alert_messages[COLLECTIVE] 	= { message = _("SET THE COLLECTIVE STICK DOWN"), message_timeout = 10}
alert_messages[NO_FUEL] 	= { message = _("CHECK FUEL QUANTITY"), message_timeout = 10}
alert_messages[BATTERY_LOW] = { message = _("CHECK THE BATTERY"), message_timeout = 10}


-- Standard Auto Start Was 2min 30sec
-- Quick Auto Start Is 1min 0sec


---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------




push_start_command(dt, {message = _("· VRS · Quick Start · UH-1H ·"), message_timeout = 55})



-- Cockpit Doors

push_start_command(dt,{device = devices.CPT_MECH,action = device_commands.Button_7,value = 0.0}) -- Cockpit Doors - CLOSED


-- Reset Engine Start Switch

push_start_command(0.01,{device = devices.ENGINE_INTERFACE,action = device_commands.Button_12,value = 0.0})
--push_start_command(dt,{action = 97,value = 1.0,message = _("RESET CONTROLS TO NULL"),message_timeout = mto})


for i = 0.0, 4.0, 0.1 do
	--push_start_command(0.1,{action = 632})
end


--Reset Circuit Breakers

for i = cb_start_cmd, cb_end_cmd, 1 do
	push_start_command(0.01,{device = devices.ELEC_INTERFACE, action = i, value  = 1.0})
end


--Lights

push_start_command(dt,{device = devices.NAVLIGHT_SYSTEM,action = device_commands.Button_21,value = -1.0}) -- Dome Light Switch - GREEN

push_start_command(dt,{device = devices.NAVLIGHT_SYSTEM,action = device_commands.Button_15,value = 1.0}) -- Overhead Console Panel Lights Brightness - MAX
push_start_command(dt,{device = devices.NAVLIGHT_SYSTEM,action = device_commands.Button_16,value = 1.0}) -- Pedestal Lights Brightness - MAX
push_start_command(dt,{device = devices.NAVLIGHT_SYSTEM,action = device_commands.Button_17,value = 1.0}) -- Secondary Instrument Lights Brightness - MAX
push_start_command(dt,{device = devices.NAVLIGHT_SYSTEM,action = device_commands.Button_18,value = 1.0}) -- Engine Instrument Lights Brightness - MAX
push_start_command(dt,{device = devices.NAVLIGHT_SYSTEM,action = device_commands.Button_19,value = 1.0}) -- Copilot Instrument Lights Brightness - MAX
push_start_command(dt,{device = devices.NAVLIGHT_SYSTEM,action = device_commands.Button_20,value = 1.0}) -- Pilot Instrument Lights Brightness - MAX


-- AC/DC Selectors - Inverter

push_start_command(dt,{device = devices.ELEC_INTERFACE,action = device_commands.Button_7,value = 0.1}) -- AC Selector Switch - AC PHASE
push_start_command(dt,{device = devices.ELEC_INTERFACE,action = device_commands.Button_8,value = 0.0}) -- Inverter Switch - OFF
push_start_command(dt,{device = devices.ELEC_INTERFACE,action = device_commands.Button_4,value = 0.3}) -- DC Selector - ESS BUS


-- Main Generator

push_start_command(dt,{device = devices.ELEC_INTERFACE,action = device_commands.Button_19,value = 1.0}) -- Main Gen Switch Cover - OPEN
push_start_command(dt,{device = devices.ELEC_INTERFACE,action = device_commands.Button_2,value = -1.0}) -- Main Gen - RESET
push_start_command(dt,{device = devices.ELEC_INTERFACE,action = device_commands.Button_19,value = 0.0}) -- Main Gen Switch Cover - CLOSED


-- Starter Generator

push_start_command(dt,{device = devices.ELEC_INTERFACE,action = device_commands.Button_3,value = 1.0}) -- Starter Gen - START


-- Battery Switch

push_start_command(dt,{device = devices.ELEC_INTERFACE,action = device_commands.Button_1,value = 0.0}) -- Battery Switch - ON
push_start_command(dt,{device = devices.ENGINE_INTERFACE,action = device_commands.Button_21,value = 0.0}) -- Low RPM Warning Switch - OFF


-- RPM Govenor

push_start_command(dt,{device = devices.ENGINE_INTERFACE,action = device_commands.Button_14,value = 1.0}) -- RPM Govenor Switch - ON


-- De Ice

push_start_command(dt,{device = devices.ENGINE_INTERFACE,action = device_commands.Button_2,value = 0.0}) -- De Ice Switch - OFF


-- Main Fuel

push_start_command(dt,{device = devices.FUELSYS_INTERFACE,action = device_commands.Button_1,value = 1.0}) -- Main Fuel Switch - ON


-- HydRraulic Control

push_start_command(dt,{device = devices.HYDRO_SYS_INTERFACE,action = device_commands.Button_3,value = 1.0}) -- HydRraulic Control Switch - ON


-- Force Trim

push_start_command(dt,{device = devices.HYDRO_SYS_INTERFACE,action = device_commands.Button_4,value = 1.0}) -- Force Trim Switch - ON


-- IFF

push_start_command(dt,{device = devices.IFF,action = device_commands.Button_8,value = 0.3}) -- IFF - NORM


-- Chip Detector

push_start_command(dt,{device = devices.ENGINE_INTERFACE,action = device_commands.Button_13,value = 0.0}) -- Chip Detector - BOTH


-- Radios

push_start_command(dt, {device = devices.UHF_ARC_51, action = device_commands.Button_6, value = 0.1}) -- ARC-51CX UHF - T/R
push_start_command(dt, {device = devices.VHF_ARC_134, action = device_commands.Button_4, value = 0.1}) -- ARC-134 VHF FM - T/R
push_start_command(dt, {device = devices.VHF_ARC_131, action = device_commands.Button_7, value = 0.1}) -- ARC-131 VHF FM - T/R
push_start_command(dt, {device = devices.WEAPON_SYS, action = device_commands.Button_8, value = 1.0}) -- Master Arm - ON
	

-- Engine Throttle

for i = 0.0, 20.0, 0.1 do
	push_start_command(dt,{device = devices.ENGINE_INTERFACE,action = device_commands.Button_24,value = 0.0}) -- Throttle - START
end


-- Engine Start

push_start_command(dt,{device = devices.ENGINE_INTERFACE,action = device_commands.Button_12,value = 1.0}) -- Engine Start Button - PRESS
push_start_command(35.0,{device = devices.ENGINE_INTERFACE,action = device_commands.Button_12,value = 0.0}) -- Engine Start Button - RELEASE


-- RADALT


push_start_command(dt, {device = devices.RADAR_ALTIMETER, action = device_commands.Button_7, value = 1.0}) -- RADALT - ON

push_start_command(dt, {device = devices.RADAR_ALTIMETER, action = device_commands.Button_2, value = 0.6}) -- RADALT - LOW



push_start_command(dt, {device = devices.RADAR_ALTIMETER, action = device_commands.Button_3, value = 1.0}) -- RADALT - HIGH
push_start_command(dt, {device = devices.RADAR_ALTIMETER, action = device_commands.Button_3, value = 1.0})
push_start_command(dt, {device = devices.RADAR_ALTIMETER, action = device_commands.Button_3, value = 0.5})


-- Inverter

push_start_command(dt,{device = devices.ELEC_INTERFACE,action = device_commands.Button_8,value = -1.0}) -- Inverter Switch - ON


-- Standby Generater

push_start_command(dt,{device = devices.ELEC_INTERFACE,action = device_commands.Button_3,value = 0.0}) -- Standby Generater - GEN


-- Engine Throttle

for i = 0.0, 20.0, 0.1 do
	push_start_command(0.05,{device = devices.ENGINE_INTERFACE,action = device_commands.Button_25,value = 0.5}) -- Throttle - MAX
end


-- Master Caution

push_start_command(dt, {device = devices.SYS_CONTROLLER, action = device_commands.Button_1, value = 1.0})
push_start_command(dt, {device = devices.SYS_CONTROLLER, action = device_commands.Button_1, value = 0.0})


-- Intercom Mode

push_start_command(dt,{device = devices.INTERCOM,action = device_commands.Button_8,value = 0.2}) -- Intercom Mode - 1
push_start_command(dt, {device = devices.XM_130, action = device_commands.Button_5, value = 1.0}) -- Arm Flares

for i = 1, 30, 1 do
	push_start_command(0.01, {device = devices.XM_130, action = device_commands.Button_4, value = 0.1}) -- Flare Counter - 30
end


push_start_command(12, {message = _("· VRS · Quick Start Complete · UH-1H ·"), message_timeout = 10})
push_start_command(dt, {message = _("Remember to check compass sync."), message_timeout = 10})