dofile(LockOn_Options.script_path.."command_defs.lua")
dofile(LockOn_Options.script_path.."devices.lua")

-- · VRS Quick Start · Mi-8MTV2 (Generic) ·
-- Part of the VRS Auto Starts mod for DCS World
-- Install via OvGME: https://wiki.hoggitworld.com/view/OVGME

local t_start = 0.0
local t_stop = 0.0
local dt = 0.001 -- Default interval between commands in the stack.
local mto = 8.0 -- Default message timeout time.
local start_sequence_time = 2.1 * 60 -- Quick startup takes about 2m05s (orignal was 3m20s)
local stop_sequence_time = 60.0 -- TODO: timeout

start_sequence_full = {}
stop_sequence_full = {}

function push_command(sequence, run_t, command)
sequence[#sequence + 1] = command
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
APU_START_FAULT = 4
FUEL_PUMP_FAULT = 5
LEFT_ENGINE_START_FAULT = 6
RIGHT_ENGINE_START_FAULT = 7

alert_messages = {}
alert_messages[COLLECTIVE] = { message = _("SET THE COLLECTIVE STICK DOWN"), message_timeout = 10}
alert_messages[NO_FUEL] = 	 { message = _("CHECK FUEL QUANTITY"), message_timeout = 10}
alert_messages[BATTERY_LOW] = { message = _("POWER SUPPLY FAULT. CHECK THE BATTERY"), message_timeout = 10}
alert_messages[APU_START_FAULT] = { message = _("AI-9 NOT READY TO START ENGINE"), message_timeout = 10}
alert_messages[FUEL_PUMP_FAULT] = { message = _("FEEDING FUEL TANK PUMP FAULT"), message_timeout = 10}
alert_messages[LEFT_ENGINE_START_FAULT] = { message = _("LEFT ENGINE START FAULT"), message_timeout = 10}
alert_messages[RIGHT_ENGINE_START_FAULT] = { message = _("RIGHT ENGINE START FAULT"), message_timeout = 10}

----------------------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------

-- Function to collect all the start sequence commands.

local function doStartSequence()

push_start_command(dt, {message = _("· VRS · Quick Start · Mi-8MTV2 (Generic) ·"), message_timeout = 120})


-- Parking Brake

push_start_command(dt, {device = devices.CPT_MECH, action = device_commands.Button_17, value = 1.0}) -- Parking Brake - ON


-- Radio Selector Switch

push_start_command(dt, {device = devices.SPU_7, action = device_commands.Button_4, value = 1.0}) -- Radio Set to ICS


-- Circut Brakers

push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_22, value = 1.0}) -- CB Group 1 ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_22, value = 0.0}) -- Return
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_23, value = 1.0}) -- CB Group 2 ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_23, value = 0.0}) -- Return
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_24, value = 1.0}) -- CB Group 3 ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_24, value = 0.0}) -- Return
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_25, value = 1.0}) -- CB Group 4 ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_25, value = 0.0}) -- Return
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_26, value = 1.0}) -- CB Group 5 ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_26, value = 0.0}) -- Return
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_27, value = 1.0}) -- CB Group 6 ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_27, value = 0.0}) -- Return
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_28, value = 1.0}) -- CB Group 7 ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_28, value = 0.0}) -- Return
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_29, value = 1.0}) -- CB Group 8 ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_29, value = 0.0}) -- Return
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_30, value = 1.0}) -- CB Group 9 ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_30, value = 0.0}) -- Return


-- Battery Switches

push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_3, value = 1.0}) -- Battery 1 Switch - ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_2, value = 1.0}) -- Battery 2 Switch - ON


-- Generators and Rectifiers

push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_1, value = 1.0}) -- Standby Generator Switch - ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_9, value = 1.0}) -- Equipment Test Switch - ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_15, value = 1.0}) -- Generator 1 Switch - ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_16, value = 1.0}) -- Generator 2 Switch - ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_7, value = 1.0}) -- Rectifier 1 Switch - ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_5, value = 1.0}) -- Rectifier 2 Switch - ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_6, value = 1.0}) -- Rectifier 3 Switch - ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_8, value = 0.5}) -- DC Voltmeter Selector - ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_17, value = 1.0}) -- AC Voltmeter Selector - ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_13, value = -1.0}) -- 36V Inverter Switch - ON
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_12, value = -1.0}) -- 115V Inverter Switch - ON


-- APU - START 10.2sec

push_start_command(dt, {message = _(" "), message_timeout = 6})
push_start_command(dt, {message = _("  APU Start"), message_timeout = 6})
push_start_command(dt, {message = _(" "), message_timeout = 6})

push_start_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_12, value = 1.0}) -- APU Start Mode Switch To START
push_start_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_26, value = 1.0}) -- Press
push_start_command(0.2, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_26, value = 0.0}) -- Release


-- Lights - Brightness Knobs - All To MAX - Day Mode

push_start_command(dt, {device = devices.LIGHT_SYSTEM, action = device_commands.Button_11, value = 1.0}) -- 5.5V Lights Brightness Rheostat
push_start_command(dt, {device = devices.LIGHT_SYSTEM, action = device_commands.Button_10, value = 1.0}) -- Central Red Lights Brightness Group 2 Rheostat
push_start_command(dt, {device = devices.LIGHT_SYSTEM, action = device_commands.Button_9, value = 1.0}) -- Central Red Lights Brightness Group 1 Rheostat
push_start_command(dt, {device = devices.LIGHT_SYSTEM, action = device_commands.Button_8, value = 1.0}) -- Right Red Lights Brightness Group 2 Rheostat
push_start_command(dt, {device = devices.LIGHT_SYSTEM, action = device_commands.Button_7, value = 1.0}) -- Right Red Lights Brightness Group 1 Rheostat
push_start_command(dt, {device = devices.LIGHT_SYSTEM, action = device_commands.Button_6, value = 1.0}) -- Left Red Lights Brightness Group 2 Rheostat
push_start_command(dt, {device = devices.LIGHT_SYSTEM, action = device_commands.Button_5, value = 1.0}) -- Left Red Lights Brightness Group 1 Rheostat
push_start_command(dt, {device = devices.RECORDER_P503B, action = device_commands.Button_2, value = 1.0}) -- Recorder P-503B Backlight Brightness Knob
push_start_command(dt, {device = devices.LIGHT_SYSTEM, action = device_commands.Button_23, value = 1.0}) -- Cargo Cabin Common Lights Switch
push_start_command(dt, {device = devices.LIGHT_SYSTEM, action = device_commands.Button_2, value = 1.0}) -- Left Ceiling Light Switch
push_start_command(dt, {device = devices.LIGHT_SYSTEM, action = device_commands.Button_3, value = 1.0}) -- Right Ceiling Light Switch
push_start_command(dt, {device = devices.LIGHT_SYSTEM, action = device_commands.Button_4, value = 1.0}) -- 5.5V Lights Switch
push_start_command(dt, {device = devices.SYS_CONTROLLER, action = device_commands.Button_6, value = 1.0}) -- Transparent Switch - Warning Lights To Night
push_start_command(dt, {device = devices.NAVLIGHT_SYSTEM, action = device_commands.Button_12, value = 1.0}) -- ANO Switch - NAV Lights - Bright
push_start_command(dt, {device = devices.NAVLIGHT_SYSTEM, action = device_commands.Button_13, value = 1.0}) -- Formation Lights - BRIGHT


-- Fire Check Circuts

push_start_command(dt, {device = devices.FIRE_EXTING_INTERFACE, action = device_commands.Button_10, value = 1.0}) -- Check Fire Circuits Switch - ON


-- Turning up Main Radio, Turning Other to Half Volume

push_start_command(dt, {device = devices.R_828, action = device_commands.Button_2, value = 0.5}) -- 828 VOLUME KNOB - 30FM
push_start_command(dt, {device = devices.R_863, action = device_commands.Button_5, value = 1.00}) -- MAIN RADIO VOLUME KNOB 250AM


-- JADRO

push_start_command(dt, {device = devices.JADRO_1A, action = device_commands.Button_13, value = 1.0}) -- Jadro 1A, Power Switch - ON
push_start_command(dt, {device = devices.JADRO_1A, action = device_commands.Button_1, value = 1.0}) -- Jadro 1A, Mode Switch
push_start_command(dt, {device = devices.JADRO_1A, action = device_commands.Button_2, value = 1.0}) -- Jadro 1A, Frequency Selector


-- Pilot's Triangular Panel

push_start_command(dt, {device = devices.CPT_MECH, action = device_commands.Button_20, value = 1.0}) -- Pilot Fan
push_start_command(dt, {device = devices.AGB_3K_LEFT, action = device_commands.Button_4, value = 1.0}) -- Left Attitude Indicator Power Switch
push_start_command(dt, {device = devices.CORRECTION_INTERRUPT, action = device_commands.Button_1, value = 1.0}) -- Gyro Cutout
push_start_command(dt, {device = devices.SPUU_52, action = device_commands.Button_5, value = 1.0}) -- Pitch Limit System


-- Copilot's Triangular Panel

push_start_command(dt, {device = devices.DISS_15, action = device_commands.Button_1, value = 1.0}) -- Doppler Navigator Power Switch
push_start_command(dt, {device = devices.GMK1A, action = device_commands.Button_1, value = 1.0}) -- GMC Power Switch
push_start_command(dt, {device = devices.AGB_3K_RIGHT, action = device_commands.Button_4, value = 1.0}) -- Right Attitude Indicator Power Switch
push_start_command(dt, {device = devices.ARC_UD, action = device_commands.Button_4, value = 0.0}) -- ARC-UD, Channel Selector Switch
push_start_command(dt, {device = devices.ARC_UD, action = device_commands.Button_12, value = 1.0}) -- ARC-UD, Lock Switch
push_start_command(dt, {device = devices.CPT_MECH, action = device_commands.Button_21, value = 1.0}) -- Co Pilot Fan


-- Turn On Rocket Systems

push_start_command(dt, {device = devices.WEAPON_SYS, action = device_commands.Button_30, value = 1.0}) -- RS/GUV Selector Switch
push_start_command(dt, {device = devices.WEAPON_SYS, action = device_commands.Button_22, value = -1.0}) -- UPK/PKT/RS Switch Set to RS - Rockets
push_start_command(dt, {device = devices.WEAPON_SYS, action = device_commands.Button_20, value = -1.0}) -- 8/16/4 Switch - Set to 4
--push_start_command(dt, {device = devices.WEAPON_SYS, action = device_commands.Button_27, value = 1.0}) -- Wepons Master ARM - ON


-- Set Sight

push_start_command(dt, {device = devices.PKV, action = device_commands.Button_3, value = .215}) -- Set Sight Limb Knob - 0.3 Default


-- Fuel Tank Pumps

push_start_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_6, value = 1.0}) -- Feed Tank Pump Switch
push_start_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_3, value = 1.0}) -- Left Tank Pump Switch
push_start_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_5, value = 1.0}) -- Right Tank Pump Switch


-- UV-26 Countermeasures System

push_start_command(dt, {device = devices.UV_26, action = device_commands.Button_10, value = 1.0}) -- CMD Power ON
push_start_command(dt, {device = devices.UV_26, action = device_commands.Button_2, value = 0.5}) -- Set CMD To BOTH


-- External Lights

push_start_command(dt, {device = devices.NAVLIGHT_SYSTEM, action = device_commands.Button_14, value = 1.0}) -- Tip Lights Switch
push_start_command(dt, {device = devices.NAVLIGHT_SYSTEM, action = device_commands.Button_15, value = 1.0}) -- Strobe Light - Red Flashing Light


-- RADALT

push_start_command(dt, {device = devices.RADAR_ALTIMETER, action = device_commands.Button_3, value = 1.0}) -- RADALT ON
push_start_command(dt, {device = devices.RADAR_ALTIMETER, action = device_commands.Button_1, value = -0.80}) -- Set RADALT to 20 Meters


-- Cargo Auto Hook

push_start_command(dt, {device = devices.EXT_CARGO_EQUIPMENT, action = device_commands.Button_5, value = 1.0}) -- Auto Unhook - ON


-- Fuel Guage

push_start_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_8, value = 0.1}) -- Fuel Meter Switch, Set To ALL


-- Set QNH To FARP Height - Not Automatic - Set to SHARON

--for i = 1, 100, 1 do
--	push_start_command(0.01, {device = devices.BAR_ALTIMETER_L, action = device_commands.Button_1, value = 1}) -- Set QNH - Pilot
--end

--for i = 1, 100, 1 do
--	push_start_command(0.01, {device = devices.BAR_ALTIMETER_R, action = device_commands.Button_1, value = 1}) -- Set QNH - Copilot
--end


-- Radio Main Selector Rotary

push_start_command(dt, {device = devices.SPU_7, action = device_commands.Button_3, value = 0.0}) -- Radio Selector Rotary - R-863


-- Tune ADF

push_start_command(dt, {device = devices.ARC_9, action = device_commands.Button_3, value = 0.1}) -- ARC 9 COMP

-- Reserve - Set To 450kHz BAYWATCH

--push_start_command(dt, {device = devices.ARC_9, action = device_commands.Button_6, value = 0.5}) -- ARC 9 10KHZ DIAL
--push_start_command(dt, {device = devices.ARC_9, action = device_commands.Button_5, value = 0.15}) -- ARC 9 100KHZ DIAL

-- Main - Set To 260kHz SHARON

--push_start_command(dt, {device = devices.ARC_9, action = device_commands.Button_9, value = 0.6}) -- ARC 9 10KHZ DIAL
--push_start_command(dt, {device = devices.ARC_9, action = device_commands.Button_8, value = 0.05}) -- ARC 9 100KHZ DIAL

--push_start_command(dt, {device = devices.ARC_9, action = device_commands.Button_11, value = 1.0}) -- Main/Reserve Switch - Set To Main


-- Information Message - Current Set Up - 125.7sec to Horn

push_start_command(dt, {message = _("Radio Set To ICS To Allow Rearm And Refuel"), message_timeout = 105})
push_start_command(dt, {message = _("Rocket Systems ON, Master Arm OFF"), message_timeout = 105})


-- Wait For APU Start

push_start_command(11.0, {message = _("  APU Running"), message_timeout = 4})
push_start_command(0.0, {message = _(" "), message_timeout = 4})


-- Taxi Light

--push_start_command(dt, {device = devices.NAVLIGHT_SYSTEM, action = device_commands.Button_17, value = 1.0}) -- Taxi Light - ON


-- Power levers and throttle

push_start_command(dt, {action = Keys.iCommand_PlaneAUTDecreaseRegime}) -- ?
push_start_command(dt, {action = Keys.iCommand_PlaneAUTDecreaseRegime}) -- ?
push_start_command(dt, {action = Keys.iCommand_PlaneAUTIncreaseRegime}) -- ?
push_start_command(dt, {action = Keys.iCommand_ThrottleDecrease}) -- ?
push_start_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_69, value = -1.0}) -- ?
push_start_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_70, value = -1.0}) -- ?
push_start_command(dt, {action = Keys.iCommand_ThrottleStop}) -- ?


-- Fuel Shutoff Switches

push_start_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_11, value = 1.0}) -- Cross Feed Valve Switch Cover - Open
push_start_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_4, value = 1.0}) -- Cross Feed Valve Switch
push_start_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_11, value = 0.0}) -- Cross Feed Valve Switch Cover - Close

push_start_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_9, value = 1.0}) -- Left Shutoff Valve Switch Cover - Open
push_start_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_1, value = 1.0}) -- Left Shutoff Valve Switch
push_start_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_9, value = 0.0}) -- Left Shutoff Valve Switch Cover - Close

push_start_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_10, value = 1.0}) -- Right Shutoff Valve Switch Cover - Open
push_start_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_2, value = 1.0}) -- Right Shutoff Valve Switch
push_start_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_10, value = 0.0}) -- Right Shutoff Valve Switch Cover - Vlose


-- Blister Windows

push_start_command(dt, {device = devices.CPT_MECH, action = device_commands.Button_15, value = 0.0}) -- Pilot Blister Window Close
push_start_command(dt, {device = devices.CPT_MECH, action = device_commands.Button_16, value = 0.0}) -- Co Pilot Blister Window Close


-- Rotor Brake

push_start_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_11, value = 0.0}) -- Rotor Brake Handle - OFF


-- Left Engine - START 50sec

push_start_command(dt, {message = _("  Left Engine Start"), message_timeout = 44})
push_start_command(dt, {message = _(" "), message_timeout = 44})

push_start_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_9, value = 1.0}) -- Fuel Cutoff Lever - Left
push_start_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_27, value = 1.0}) -- Engine Start Mode Switch
push_start_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_8, value = -1.0}) -- Engine Selector Switch
push_start_command(0.2, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_5, value = 1.0}) -- Engine Start Button - Push to start engine
push_start_command(0.8, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_5, value = 0.0}) -- Relese


-- Reset G Meter

push_start_command(dt, {device = devices.CPT_MECH, action =  device_commands.Button_6, value = 1.0}) -- Press - G Meter
push_start_command(0.7, {device = devices.CPT_MECH, action = device_commands.Button_6, value = 0.0}) -- Release - G Meter


-- Throttle Up

push_start_command(0.1, {action = Keys.iCommand_ThrottleIncrease}) -- Collective Throttle To MAX
push_start_command(1.3, {action = Keys.iCommand_ThrottleStop}) -- MAX Value


-- R-828 Radio - 30FM

push_start_command(dt, {device = devices.R_828, action = device_commands.Button_5, value = 1.0}) -- 30FM Power - ON
push_start_command(dt, {device = devices.R_828, action = device_commands.Button_1, value = 0.4}) -- Channel Selector Knob

push_start_command(0.1, {device = devices.R_828, action = device_commands.Button_3, value = 1.0}) -- Press - R-828 Radio Tuner Button
push_start_command(3.0, {device = devices.R_828, action = device_commands.Button_3, value = 0.0}) -- Release - R-828 Radio Tuner Button


-- Wait For Left Engine To Start

push_start_command(43.8, {message = _("  Left Engine Running"), message_timeout = 4})


-- Right Engine START 57.2sec

push_start_command(dt, {message = _(" "), message_timeout = 4})
push_start_command(dt, {message = _("  Right Engine Start"), message_timeout = 35})
push_start_command(dt, {message = _(" "), message_timeout = 35})

push_start_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_10, value = 1.0}) -- Fuel Cutoff Lever - Right
push_start_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_8, value = 1.0}) -- Start Selector
push_start_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_5, value = 1.0}) -- Push to Start
push_start_command(1.0, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_5, value = 0.0}) -- Relese


-- Cage Gyros

push_start_command(23, {message = _("  Cage/Uncage Gyros 30sec To Align"), message_timeout = 20})
push_start_command(dt, {message = _(" "), message_timeout = 20})

push_start_command(0.1, {device = devices.AGB_3K_LEFT, action = device_commands.Button_2, value = 1.0}) -- Press - Cage Left Gyro
push_start_command(0.8, {device = devices.AGB_3K_LEFT, action = device_commands.Button_2, value = 0.0}) -- Release - Uncage Left Gyro
push_start_command(0.1, {device = devices.AGB_3K_RIGHT, action = device_commands.Button_2, value = 1.0}) -- Press - Cage Right Gryo
push_start_command(0.8, {device = devices.AGB_3K_RIGHT, action = device_commands.Button_2, value = 0.0}) -- Release - Uncage Right Gyro

push_start_command(21, {message = _("  Right Engine Running"), message_timeout = 4})
push_start_command(dt, {message = _(" "), message_timeout = 8})


-- APU Stop

push_start_command(dt, {message = _("  Stopping APU - Aprox 3min For Cool Down"), message_timeout = 12})

push_start_command(0.1, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_7, value = 1.0}) -- Press - APU Stop Button
push_start_command(0.2, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_7, value = 0.0}) -- Release - APU Start Button

push_start_command(1.0, {message = _("Stabilizing Engine RPM"), message_timeout = 8})


-- Radios

push_start_command(dt, {device = devices.SPU_7, action = device_commands.Button_4, value = 0.0}) -- Radio Set to Radio



-- Auto Pilot

push_start_command(dt, {device = devices.AUTOPILOT, action = device_commands.Button_2, value = 1.0}) -- Press
push_start_command(0.1, {device = devices.AUTOPILOT, action = device_commands.Button_2, value = 0.0}) -- Release
push_start_command(dt, {device = devices.VMS, action = device_commands.Button_6, value = 1.0}) -- Bitchin Betty - ON

push_start_command(1.0, {message = _("Autopilot Pitch/Roll Channel - ON"), message_timeout = 10})
push_start_command(dt, {message = _("ICS Off"), message_timeout = 10})
push_start_command(dt, {message = _("PTT for SRS will now transmit on 250 AM"), message_timeout = 10})
push_start_command(dt, {message = _("99.8% chance you are ready to fly"), message_timeout = 10})
push_start_command(dt, {message = _("· VRS · Quick Start Complete · Mi-8MTV2 (Generic) ·"), message_timeout = 10})


-- Toot the Horn

push_start_command(10, {device = devices.MISC_SYSTEMS_INTERFACE, action = device_commands.Button_1, value = 1.0}) -- Press
push_start_command(0.20, {device = devices.MISC_SYSTEMS_INTERFACE, action = device_commands.Button_1, value = 0.0}) -- Release
push_start_command(0.30, {device = devices.MISC_SYSTEMS_INTERFACE, action = device_commands.Button_1, value = 1.0}) -- Press
push_start_command(0.20, {device = devices.MISC_SYSTEMS_INTERFACE, action = device_commands.Button_1, value = 0.0}) -- Release
push_start_command(0.30, {device = devices.MISC_SYSTEMS_INTERFACE, action = device_commands.Button_1, value = 1.0}) -- Press
push_start_command(0.20, {device = devices.MISC_SYSTEMS_INTERFACE, action = device_commands.Button_1, value = 0.0}) -- Release


end
doStartSequence()


-----------------------------------------------------------------------------------------------------------------------------------------
-- Other Buttons And Switches


-- NAV Lights 'CODE' Button

--push_start_command(dt, {device = devices.NAVLIGHT_SYSTEM, action = device_commands.Button_16, value = 1.0}) -- ANO Code Button

-- Engine Dust Protection

--push_start_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_28, value = 1.0}) -- Left Dust Protection
--push_start_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_29, value = 1.0}) -- Right Dust Protection


--Recorder P-503B

--push_start_command(dt, {device = devices.RECORDER_P503B, action = device_commands.Button_1, value = 1.0}) -- Recorder P-503B Power Switch


-- Standby Generator Voltage Adjustment Rheostat

--push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_10, value = -1.0}) -- Standby Generator Voltage Adjustment - Set To MIN


-- Generator 1 Voltage Adjustment Rheostats

--push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_11, value = -1.0}) -- Generator 1 Voltage Adjustment - St To MIN
--push_start_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_18, value = -1.0}) -- Generator 2 Voltage Adjustment - St To MIN

-----------------------------------------------------------------------------------------------------------------------------------------

local function

doStopSequence()


-- Stop sequence

push_stop_command(dt, {message = _("· VRS · Quick Stop · Mi-8MTV2 (Generic) ·"), message_timeout = 52})


-- Parking Brake

push_stop_command(dt, {device = devices.CPT_MECH, action = device_commands.Button_17, value = 1.0}) -- Parking Brake - ON


-- Audio Warnings

push_stop_command(dt, {device = devices.VMS, action = device_commands.Button_6, value = 0.0}) -- Bitchin Betty - OFF


-- Cage Gyros

push_stop_command(0.1, {device = devices.AGB_3K_LEFT, action = device_commands.Button_2, value = 1.0}) -- Press - Cage Left Gyro
push_stop_command(1.0, {device = devices.AGB_3K_LEFT, action = device_commands.Button_2, value = 0.0}) -- Release - Uncage Left Gyro
push_stop_command(0.1, {device = devices.AGB_3K_RIGHT, action = device_commands.Button_2, value = 1.0}) -- Press - Cage Right Gryo
push_stop_command(1.0, {device = devices.AGB_3K_RIGHT, action = device_commands.Button_2, value = 0.0}) -- Release - Uncage Right Gyro


-- Set Sight

push_stop_command(0.1, {device = devices.PKV, action = device_commands.Button_3, value = 0.3}) -- Set Sight Limb Knob - 0.3 Default


-- Main Radio

push_stop_command(dt, {device = devices.SPU_7, action = device_commands.Button_4, value = -1.0}) -- Radio Set To ICS


-- Tune ADF

-- Main - Set To 150kHz

push_stop_command(dt, {device = devices.ARC_9, action = device_commands.Button_6, value = 0.5}) -- ARC 9 10KHZ DIAL
push_stop_command(dt, {device = devices.ARC_9, action = device_commands.Button_5, value = 0.0}) -- ARC 9 100KHZ DIAL


-- Reserve - Set To 150kHz

push_stop_command(dt, {device = devices.ARC_9, action = device_commands.Button_9, value = 0.5}) -- ARC 9 10KHZ DIAL
push_stop_command(dt, {device = devices.ARC_9, action = device_commands.Button_8, value = 0.0}) -- ARC 9 100KHZ DIAL

push_stop_command(dt, {device = devices.ARC_9, action = device_commands.Button_11, value = 0.0}) -- Main/Reserve Switch - Set To Reserve


-- External Lights OFF

push_stop_command(dt, {device = devices.NAVLIGHT_SYSTEM, action = device_commands.Button_18, value = 0.00}) -- Left Landing Light Switch - OFF
push_stop_command(dt, {device = devices.NAVLIGHT_SYSTEM, action = device_commands.Button_19, value = 0.00}) -- Right Landing Light Switch - OFF
push_stop_command(dt, {device = devices.NAVLIGHT_SYSTEM, action = device_commands.Button_17, value = -1.0}) -- Taxi Light - OFF
push_stop_command(dt, {device = devices.NAVLIGHT_SYSTEM, action = device_commands.Button_14, value = 0.00}) -- Tip Lights Switch - OFF
push_stop_command(dt, {device = devices.NAVLIGHT_SYSTEM, action = device_commands.Button_15, value = 0.00}) -- Strobe Light - Red Flashing Light - OFF


-- APU STOP

push_stop_command(0.1, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_7, value = 1.0}) -- Press - APU Stop Button
push_stop_command(0.2, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_7, value = 0.0}) -- Release - APU Start Button


-- Fuel Shutoff Switches

push_stop_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_11, value = 1.0}) -- Cross Feed Valve Switch Cover - Open
push_stop_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_4, value = 0.0}) -- Cross Feed Valve Switch
push_stop_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_11, value = 0.0}) -- Cross Feed Valve Switch Cover - Close

push_stop_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_9, value = 1.0}) -- Left Shutoff Valve Switch Cover - Open
push_stop_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_1, value = 0.0}) -- Left Shutoff Valve Switch
push_stop_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_9, value = 0.0}) -- Left Shutoff Valve Switch Cover - Close

push_stop_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_10, value = 1.0}) -- Right Shutoff Valve Switch Cover - Open
push_stop_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_2, value = 0.0}) -- Right Shutoff Valve Switch
push_stop_command(dt, {device = devices.FUELSYS_INTERFACE, action = device_commands.Button_10, value = 0.0}) -- Right Shutoff Valve Switch Cover - Vlose


-- Fuel Leavers

push_stop_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_9, value = 0}) -- Left Fuel Lever - OFF
push_stop_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_10, value = 0}) -- Right Fuel Lever - OFF


-- Rotor Brake

push_stop_command(dt, {device = devices.ENGINE_INTERFACE, action = device_commands.Button_11, value = 1}) -- Rotor Brake - ON


-- Throttle

push_stop_command(0.8, {action = Keys.iCommand_ThrottleDecrease}) -- Throttle Down
push_stop_command(0.5, {action = Keys.iCommand_ThrottleStop})


-- CB Pannel

for i = device_commands.Button_31, device_commands.Button_31 + 75, 1 do
	push_stop_command(0.001, {device = devices.ELEC_INTERFACE, action = i, value = 0.0}) -- Turn OFF All Circut Brakers
end


-- Battery Switches

push_stop_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_3, value = -1.0}) -- Battery 1 Switch - OFF
push_stop_command(dt, {device = devices.ELEC_INTERFACE, action = device_commands.Button_2, value = -1.0}) -- Battery 2 Switch - OFF


-- Barometric Altimeter

for i = 1, 100, 1 do
	push_stop_command(0.01, {device = devices.BAR_ALTIMETER_L, action = device_commands.Button_1, value = -1}) -- Set QNH - Pilot To STD
end

for i = 1, 100, 1 do
	push_stop_command(0.01, {device = devices.BAR_ALTIMETER_R, action = device_commands.Button_1, value = -1}) -- Set QNH - Copilot To STD
end


-- RADALT

push_stop_command(dt, {device = devices.RADAR_ALTIMETER, action = device_commands.Button_1, value = 0.80}) -- Set RADALT to STD


-- Wait For Rotor Spool Down TIME - 13 To Here

push_stop_command(8.5, {message = _("  Rotor Spool Down (40s)"), message_timeout = 19.0})
push_stop_command(dt, {message = _(" "), message_timeout = 19.0})
push_stop_command(20.0, {message = _("  Rotor Spool Down (20s)"), message_timeout = 9.0})
push_stop_command(dt, {message = _(" "), message_timeout = 9.0})
push_stop_command(10, {message = _("  Rotor Spool Down (10s)"), message_timeout = 8.0})
push_stop_command(dt, {message = _(" "), message_timeout = 8.0})


-- Blister Windows

push_stop_command(7.9, {device = devices.CPT_MECH, action = device_commands.Button_15, value = 1.0}) -- Pilots Window - OPEN
push_stop_command(0.1, {device = devices.CPT_MECH, action = device_commands.Button_16, value = 1.0}) -- Co Pilots Window - OPEN

push_stop_command(dt, {message = _("· VRS · Quick Stop Complete · Mi-8MTV2 ·"), message_timeout = 5})
end
doStopSequence()