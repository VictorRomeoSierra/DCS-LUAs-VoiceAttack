dofile(LockOn_Options.script_path.."command_defs.lua")
dofile(LockOn_Options.script_path.."devices.lua")

-- · VRS Quick Start · F/A-18C ·
-- Part of the VRS Auto Starts mod for DCS World
-- Install via OvGME: https://wiki.hoggitworld.com/view/OVGME

std_message_timeout = 15

----------------------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------
local t_start = 0.0
local t_stop = 0.0
local dt = 0.2 -- Default interval between commands in the stack.
local dt_mto = 10.0 -- Default message timeout time.
local ins_align_time = 1 * 60 + 55 -- Stored heading alignment is 1m50s, add 5 seconds of slop just in case.
local start_sequence_time = 90 -- Quick startup ~1m30s (INS ground alignment skipped; uses IFA)
local stop_sequence_time = 10.0 -- TODO: timeout

local apu_start_time = 15
local engine_start_time = 40
local canopy_close_time = 8
-- APU startup = 15s
-- Align with stored heading = 1m50s
-- Close canopy = 8s
-- Right engine = 7s from crank switch to 15%, 40s to lit, 50s to warning beeps



--
start_sequence_full = {}
stop_sequence_full = {}
cockpit_illumination_full = {}

function push_command(sequence, run_t, command)
	sequence[#sequence + 1] = command
	sequence[#sequence]["time"] = run_t
end

function push_start_command(delta_t, command)
	t_start = t_start + delta_t
	push_command(start_sequence_full, t_start, command)
end

function push_stop_command(delta_t, command)
	t_stop = t_stop + delta_t
	push_command(stop_sequence_full, t_stop, command)
end

--
local count = 0
local function counter()
	count = count + 1
	return count
end

-- conditions
count = -1

F18_AD_NO_FAILURE = counter()
F18_AD_ERROR = counter()

F18_AD_WING_FOLD_HANDLE_SET_SAME_AS_POS = counter()

F18_AD_LEFT_THROTTLE_SET_TO_OFF = counter()
F18_AD_RIGHT_THROTTLE_SET_TO_OFF = counter()
F18_AD_LEFT_THROTTLE_AT_OFF = counter()
F18_AD_RIGHT_THROTTLE_AT_OFF = counter()
F18_AD_LEFT_THROTTLE_SET_TO_IDLE = counter()
F18_AD_RIGHT_THROTTLE_SET_TO_IDLE = counter()
F18_AD_LEFT_THROTTLE_AT_IDLE = counter()
F18_AD_RIGHT_THROTTLE_AT_IDLE = counter()
F18_AD_LEFT_THROTTLE_DOWN_TO_IDLE = counter()
F18_AD_RIGHT_THROTTLE_DOWN_TO_IDLE = counter()

F18_AD_APU_READY = counter()
F18_AD_LEFT_ENG_IDLE_RPM = counter()
F18_AD_RIGHT_ENG_IDLE_RPM = counter()
F18_AD_LEFT_ENG_CHECK_IDLE = counter()
F18_AD_RIGHT_ENG_CHECK_IDLE = counter()
F18_AD_ENG_CRANK_SW_CHECK_OFF = counter()
F18_AD_APU_VERIFY_OFF = counter()

F18_AD_INS_ALIGN = counter()
F18_AD_INS_STOR_HDG = counter()
F18_AD_INS_CHECK_RDY = counter()

F18_AD_HMD_BRT_KNOB = counter()
F18_AD_HMD_ALIGN = counter()

--
alert_messages = {}

alert_messages[F18_AD_ERROR] = { message = _("FM MODEL ERROR"), message_timeout = std_message_timeout}

alert_messages[F18_AD_WING_FOLD_HANDLE_SET_SAME_AS_POS] = { message = _("WING_FOLD_HANDLE - SET SAME AS WING POSITION"), message_timeout = std_message_timeout}

alert_messages[F18_AD_LEFT_THROTTLE_SET_TO_OFF] = { message = _("LEFT THROTTLE - TO OFF"), message_timeout = std_message_timeout}
alert_messages[F18_AD_RIGHT_THROTTLE_SET_TO_OFF] = { message = _("RIGHT THROTTLE - TO OFF"), message_timeout = std_message_timeout}
alert_messages[F18_AD_LEFT_THROTTLE_AT_OFF] = { message = _("LEFT THROTTLE MUST BE AT STOP"), message_timeout = std_message_timeout}
alert_messages[F18_AD_RIGHT_THROTTLE_AT_OFF] = { message = _("RIGHT THROTTLE MUST BE AT STOP"), message_timeout = std_message_timeout}
alert_messages[F18_AD_LEFT_THROTTLE_SET_TO_IDLE] = { message = _("LEFT THROTTLE - TO IDLE"), message_timeout = std_message_timeout}
alert_messages[F18_AD_RIGHT_THROTTLE_SET_TO_IDLE] = { message = _("RIGHT THROTTLE - TO IDLE"), message_timeout = std_message_timeout}
alert_messages[F18_AD_LEFT_THROTTLE_AT_IDLE] = { message = _("LEFT THROTTLE MUST BE AT IDLE"), message_timeout = std_message_timeout}
alert_messages[F18_AD_RIGHT_THROTTLE_AT_IDLE] = { message = _("RIGHT THROTTLE MUST BE AT IDLE"), message_timeout = std_message_timeout}
alert_messages[F18_AD_LEFT_THROTTLE_DOWN_TO_IDLE] = { message = _("LEFT THROTTLE - TO IDLE"), message_timeout = std_message_timeout}
alert_messages[F18_AD_RIGHT_THROTTLE_DOWN_TO_IDLE] = { message = _("RIGHT THROTTLE - TO IDLE"), message_timeout = std_message_timeout}

alert_messages[F18_AD_APU_READY] = { message = _("READY LIGHT MUST BE ON WITHIN 30 SEC"), message_timeout = std_message_timeout}
alert_messages[F18_AD_LEFT_ENG_IDLE_RPM] = { message = _("LEFT ENGINE RPM FAILURE"), message_timeout = std_message_timeout}
alert_messages[F18_AD_RIGHT_ENG_IDLE_RPM] = { message = _("RIGHT ENGINE RPM FAILURE"), message_timeout = std_message_timeout}
alert_messages[F18_AD_LEFT_ENG_CHECK_IDLE] = { message = _("LEFT ENGINE PARAMETERS FAILURE"), message_timeout = std_message_timeout}
alert_messages[F18_AD_RIGHT_ENG_CHECK_IDLE] = { message = _("RIGHT ENGINE PARAMETERS FAILURE"), message_timeout = std_message_timeout}
alert_messages[F18_AD_ENG_CRANK_SW_CHECK_OFF] = { message = _("ENG CRANK SWITCH MUST BE IN OFF POSITION"), message_timeout = std_message_timeout}
alert_messages[F18_AD_APU_VERIFY_OFF] = { message = _("APU MUST BE OFF"), message_timeout = std_message_timeout}

alert_messages[F18_AD_INS_ALIGN] = { message = _("INS ERROR"), message_timeout = std_message_timeout}
alert_messages[F18_AD_INS_STOR_HDG] = { message = _("INS STOR HDG ALIGN UNAVAILABLE"), message_timeout = std_message_timeout}
alert_messages[F18_AD_INS_CHECK_RDY] = { message = _("INS ALIGNMENT ERROR"), message_timeout = std_message_timeout}


----------------------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------
-- Start sequence
push_start_command(0, {message = _("· VRS · Quick Start · F/A-18C ·"), message_timeout = start_sequence_time})
--
-- Engine Start
push_start_command(dt, {message = _("BATT SWITCH - ON"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.ELEC_INTERFACE, action = elec_commands.BattSw, value = 1.0})
push_start_command(dt, {message = _("APU START"), message_timeout = apu_start_time})
push_start_command(dt, {message = _("APU SWITCH - ON"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.ENGINES_INTERFACE, action = engines_commands.APU_ControlSw, value = 1.0})
push_start_command(dt, {device = devices.ENGINES_INTERFACE, action = engines_commands.APU_ControlSw, value = 0.0})
push_start_command(dt, {message = _("CANOPY - CLOSE"), message_timeout = canopy_close_time})
push_start_command(dt, {device = devices.CPT_MECHANICS, action = cpt_commands.CanopySwitchClose, value = -1.0})
push_start_command(8.0, {device = devices.CPT_MECHANICS, action = cpt_commands.CanopySwitchClose, value = 0.0}) -- Turn off canopy switch 8 seconds later.
push_start_command(8.0, {message = _("READY LIGHT - CHECK"), check_condition = F18_AD_APU_READY})

push_start_command(dt, {message = _("LEFT DDI - ON"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.MDI_LEFT, action = MDI_commands.MDI_off_night_day, value = 0.2})
push_start_command(dt, {message = _("RIGHT DDI - ON"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.MDI_RIGHT, action = MDI_commands.MDI_off_night_day, value = 0.2})
push_start_command(dt, {message = _("HUD DDI - ON"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.HUD, action = HUD_commands.HUD_SymbBrightCtrl, value = 1.0})
push_start_command(dt, {message = _("AMPCD - ON"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.AMPCD, action = AMPCD_commands.AMPCD_off_brightness, value = 1.0})
push_start_command(dt, {message = _("UFC BRIGHTNESS - MAX"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.UFC, action = UFC_commands.BrtDim, value = 1.0})

push_start_command(dt, {message = _("COMM 1 AND 2 KNOBS - ON"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.UFC, action = UFC_commands.Comm1Vol, value = 0.8})
push_start_command(dt, {device = devices.UFC, action = UFC_commands.Comm2Vol, value = 0.8})
-- VRS Comms Plan tuning is deferred to end of autostart - the UFC scratchpad
-- isn't fully responsive until both engines + avionics are up.

-- RIGHT ENGINE
push_start_command(dt, {message = _("RIGHT ENGINE - START (40s)"), message_timeout = engine_start_time})
push_start_command(dt, {message = _("ENG CRANK SWITCH - R"), message_timeout = dt_mto})
push_start_command(dt, {check_condition = F18_AD_RIGHT_THROTTLE_AT_OFF})
push_start_command(dt, {device = devices.ENGINES_INTERFACE, action = engines_commands.EngineCrankRSw, value = 1.0})
push_start_command(dt, {device = devices.ENGINES_INTERFACE, action = engines_commands.EngineCrankRSw, value = 0.0})
push_start_command(dt, {message = _("RIGHT THROTTLE - IDLE (15% RPM MINIMUM)"), message_timeout = 10.0})
for i = 0, 50, 1 do
	push_start_command(0.2, {check_condition = F18_AD_RIGHT_THROTTLE_SET_TO_IDLE})
end
push_start_command(40.0, {check_condition = F18_AD_RIGHT_ENG_IDLE_RPM})
-- END RIGHT ENGINE

push_start_command(dt, {message = _("HMD SWITCH - ON"), message_timeout = dt_mto})
push_start_command(0.5, {check_condition = F18_AD_HMD_BRT_KNOB}) 
push_start_command(dt, {message = _("IFEI - CHECK"), message_timeout = dt_mto})
push_start_command(dt, {check_condition = F18_AD_RIGHT_ENG_CHECK_IDLE})
push_start_command(dt, {message = _("BLEED AIR KNOB - CYCLE THRU OFF TO NORM"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.ECS_INTERFACE, action = ECS_commands.BleedAirSw, value = 0.3})
push_start_command(dt, {device = devices.ECS_INTERFACE, action = ECS_commands.BleedAirSw, value = 0.0})
push_start_command(dt, {device = devices.ECS_INTERFACE, action = ECS_commands.BleedAirSw, value = 0.1})
push_start_command(dt, {device = devices.ECS_INTERFACE, action = ECS_commands.BleedAirSw, value = 0.2})

push_start_command(dt, {message = _("RADAR ALTIMETER - ON, SET TO 50 FT"), message_timeout = dt_mto})
-- First turn it all the way off, then back on to 50 ft.
for i = 0, 61, 1 do -- Note 0-index.  60 total steps to go from 5000 ft to 0 ft, 62 steps to turn off completely.
	push_start_command(0.01, {device = devices.ID2163A, action = id2163a_commands.ID2163A_SetMinAlt, value = -0.05}) -- value = positive number to go up, negative number to go down.  Actual number doesn't seem to make a difference, only +/-??
end
local RAsteps = 5 -- Change this value to set RA bug.  5 = 50 ft, 20 = 250 ft, experiment as needed; scale is non-linear, so same degrees of rotation gives more altitude as it goes around.
for i = 0, RAsteps, 1 do
	push_start_command(0.01, {device = devices.ID2163A, action = id2163a_commands.ID2163A_SetMinAlt, value = 0.05}) -- value = positive number to go up, negative number to go down.  Actual number doesn't seem to make a difference, only +/-.
end

push_start_command(dt, {message = _("RADAR KNOB - OPR"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.RADAR, action = RADAR_commands.RADAR_SwitchChange, value = 0.2})
push_start_command(dt, {message = _("FCS RESET BUTTON - PUSH"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.CONTROL_INTERFACE, action = ctrl_commands.ResetSw, value = 1.0})
push_start_command(dt, {device = devices.CONTROL_INTERFACE, action = ctrl_commands.ResetSw, value = 0.0})
push_start_command(dt, {message = _("FLAP SWITCH - HALF"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.CONTROL_INTERFACE, action = ctrl_commands.FlapSw, value = 0.0})
push_start_command(dt, {message = _("T/O TRIM BUTTON - PRESS UNTIL TRIM ADVISORY DISPLAYED"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.CONTROL_INTERFACE, action = ctrl_commands.TOTrimSw, value = 1.0})
-- TODO: check condition
push_start_command(dt, {device = devices.CONTROL_INTERFACE, action = ctrl_commands.TOTrimSw, value = 0.0})
push_start_command(dt, {message = _("STANDBY ATTITUDE REFERENCE INDICATOR - UNCAGE"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.SAI, action = sai_commands.SAI_rotate, value = -0.01})
push_start_command(dt, {message = _("ATT SWITCH - STBY"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.HUD, action = HUD_commands.HUD_AttitudeSelSw, value = -1.0})
push_start_command(dt, {message = _("ATT SWITCH - AUTO"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.HUD, action = HUD_commands.HUD_AttitudeSelSw, value = 0.0})
push_start_command(dt, {message = _("OBOGS CONTROL SWITCH - ON"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.OXYGEN_INTERFACE, action = oxygen_commands.OBOGS_ControlSw, value = 1.0})
push_start_command(dt, {message = _("HMD - AUTOSTART ALIGN"), message_timeout = dt_mto})
push_start_command(1.0, {check_condition = F18_AD_HMD_ALIGN})

-- VRS: Skip stored-heading ground alignment. Set INS knob directly to IFA so
-- alignment happens in flight (per Cricket). Saves ~2 minutes off taxi time.
push_start_command(dt, {message = _("· VRS · INS - IFA (in-flight alignment)"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.INS, action = INS_commands.INS_SwitchChange, value = 0.4})

push_start_command(dt, {message = _("HUD ALT SWITCH - RDR"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.HUD, action = HUD_commands.HUD_AltitudeSw, value = -1.0})
push_start_command(dt, {message = _("IR COOL SWITCH - NORM"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.SMS, action = SMS_commands.IRCoolingSw, value = 0.1})
push_start_command(dt, {message = _("DISPENSER SWITCH - ON"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.CMDS, action = cmds_commands.Dispenser, value = 0.1})
push_start_command(dt, {message = _("ECM - REC"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.ASPJ, action = ASPJ_commands.ASPJ_SwitchChange, value = 0.3})
push_start_command(dt, {message = _("RWR POWER - ON"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.RWR, action = rwr_commands.Power, value = 1.0})


-- LEFT ENGINE
push_start_command(dt, {message = _("LEFT ENGINE START (40s)"), message_timeout = engine_start_time})
push_start_command(dt, {message = _("ENG CRANK SWITCH - L"), message_timeout = dt_mto})
push_start_command(dt, {check_condition = F18_AD_LEFT_THROTTLE_AT_OFF})
push_start_command(dt, {device = devices.ENGINES_INTERFACE, action = engines_commands.EngineCrankLSw, value = -1.0})
push_start_command(dt, {device = devices.ENGINES_INTERFACE, action = engines_commands.EngineCrankLSw, value = 0.0})
push_start_command(dt, {message = _("LEFT THROTTLE - IDLE (15% RPM MINIMUM)"), message_timeout = 10.0})
for i = 0, 50, 1 do
	push_start_command(0.2, {check_condition = F18_AD_LEFT_THROTTLE_SET_TO_IDLE})
end
push_start_command(40.0, {check_condition = F18_AD_LEFT_ENG_IDLE_RPM})
push_start_command(dt, {message = _("ENG CRANK SWITCH - CHECK OFF"), message_timeout = dt_mto})
push_start_command(dt, {check_condition = F18_AD_ENG_CRANK_SW_CHECK_OFF})
push_start_command(dt, {message = _("IFEI - CHECK"), message_timeout = dt_mto})
push_start_command(dt, {check_condition = F18_AD_LEFT_ENG_CHECK_IDLE})
-- END LEFT ENGINE

-- BIT STOP
push_start_command(dt, {message = _("BIT FORMAT - STOP OSB"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.MDI_RIGHT, action = MDI_commands.MDI_PB_10, value = 1.0}) -- BIT page STOP OSB
push_start_command(dt, {device = devices.MDI_RIGHT, action = MDI_commands.MDI_PB_10, value = 0.0}) -- release

-- Dispenser mode MAN 1 and RWR to HUD
push_start_command(dt, {device = devices.MDI_RIGHT, action = MDI_commands.MDI_PB_18, value = 1.0}) -- MENU OSB
push_start_command(dt, {device = devices.MDI_RIGHT, action = MDI_commands.MDI_PB_18, value = 0.0}) -- release
push_start_command(dt, {device = devices.MDI_RIGHT, action = MDI_commands.MDI_PB_17, value = 1.0}) -- EW OSB
push_start_command(dt, {device = devices.MDI_RIGHT, action = MDI_commands.MDI_PB_17, value = 0.0}) -- release
push_start_command(dt, {device = devices.MDI_RIGHT, action = MDI_commands.MDI_PB_8, value = 1.0}) -- ALE-47 OSB
push_start_command(dt, {device = devices.MDI_RIGHT, action = MDI_commands.MDI_PB_8, value = 0.0}) -- release
push_start_command(dt, {device = devices.MDI_RIGHT, action = MDI_commands.MDI_PB_19, value = 1.0}) -- MODE OSB
push_start_command(dt, {device = devices.MDI_RIGHT, action = MDI_commands.MDI_PB_19, value = 0.0}) -- release
push_start_command(dt, {device = devices.MDI_RIGHT, action = MDI_commands.MDI_PB_14, value = 1.0}) -- HUD OSB
push_start_command(dt, {device = devices.MDI_RIGHT, action = MDI_commands.MDI_PB_14, value = 0.0}) -- release

push_start_command(dt, {message = _("SET BINGO FUEL - 3000 LBS"), message_timeout = dt_mto})
for i = 0, 29, 1 do
	push_start_command(0.05, {device = devices.IFEI, action = IFEI_commands.IFEI_BTN_UP_ARROW, value = 1.0})
	push_start_command(0.05, {device = devices.IFEI, action = IFEI_commands.IFEI_BTN_UP_ARROW, value = 0.0})
end

push_start_command(dt, {message = _("IFF - ON"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.UFC, action = UFC_commands.FuncSwIFF, value = 1.0}) -- UFC IFF button
push_start_command(dt, {device = devices.UFC, action = UFC_commands.FuncSwIFF, value = 0.0}) -- release
push_start_command(dt, {device = devices.UFC, action = UFC_commands.FuncSwOnOff, value = 1.0}) -- UFC ON/OFF button
push_start_command(1.0, {device = devices.UFC, action = UFC_commands.FuncSwOnOff, value = 0.0}) -- release

push_start_command(dt, {message = _("DATALINK - Link 4 ON"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.UFC, action = UFC_commands.FuncSwDL, value = 1.0}) -- UFC D/L button
push_start_command(dt, {device = devices.UFC, action = UFC_commands.FuncSwDL, value = 0.0}) -- release
push_start_command(dt, {device = devices.UFC, action = UFC_commands.FuncSwOnOff, value = 1.0}) -- UFC ON/OFF button
push_start_command(1.0, {device = devices.UFC, action = UFC_commands.FuncSwOnOff, value = 0.0}) -- release
push_start_command(dt, {message = _("DATALINK - Link 16 ON"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.UFC, action = UFC_commands.FuncSwDL, value = 1.0}) -- UFC D/L button, press again to go to the second D/L page
push_start_command(dt, {device = devices.UFC, action = UFC_commands.FuncSwDL, value = 0.0}) -- release
push_start_command(dt, {device = devices.UFC, action = UFC_commands.FuncSwOnOff, value = 1.0}) -- UFC ON/OFF button
push_start_command(1.0, {device = devices.UFC, action = UFC_commands.FuncSwOnOff, value = 0.0}) -- release

-- VRS: INS already set to IFA above; ground alignment wait removed for taxi-time optimization.

-- NOTE Should be done after INS alignement is complete.
push_start_command(dt, {message = _("AMPCD GAIN - DOWN 9 FOR VR"), message_timeout = dt_mto})
for i = 0, 8, 1 do
	push_start_command(0.05, {device = devices.AMPCD, action = AMPCD_commands.AMPCD_gain_DOWN, value = -1.0})
	push_start_command(0.05, {device = devices.AMPCD, action = AMPCD_commands.AMPCD_gain_DOWN, value = 0.0})
end

push_start_command(dt, {message = _("PARK BRK HANDLE - FULLY STOWED"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.GEAR_INTERFACE, action = gear_commands.EmergParkHandleSelectPark, value = 0.333})
push_start_command(dt, {device = devices.GEAR_INTERFACE, action = gear_commands.EmergParkHandleSelectPark, value = 0.0})
push_start_command(dt, {device = devices.GEAR_INTERFACE, action = gear_commands.EmergParkHandleSelectEmerg, value = -0.666})
--
push_start_command(dt, {message = _("EJECTION SEAT SAFE/ARM HANDLE - ARM"), message_timeout = dt_mto})
push_start_command(dt, {device = devices.CPT_MECHANICS, action = cpt_commands.EjectionSeatSafeArmedHandle, value = 0.0})
--

--
-- VRS Comms Plan via UFC: COMM1 -> 251.000 AM (Focus UHF), COMM2 -> 133.000 AM (General VHF AM)
-- 30 FM (CSAR) left manual - would require modulation-mode toggle.
-- Tuned at end of autostart so the UFC scratchpad is fully powered.
-- Hornet procedure: PULL the silver COMM knob (opens UFC scratchpad for that radio),
-- type the full 6-digit XXX.XXX freq, then press ENT to submit.
local function tuneHornetComm(commFcn, digits, label)
	push_start_command(dt, {message = _(label), message_timeout = 10.0})
	push_start_command(dt, {device = devices.UFC, action = commFcn, value = 1.0}) -- pull
	push_start_command(dt, {device = devices.UFC, action = commFcn, value = 0.0}) -- release pull
	for _, digit in ipairs(digits) do
		push_start_command(dt, {device = devices.UFC, action = digit, value = 1.0})
		push_start_command(dt, {device = devices.UFC, action = digit, value = 0.0})
	end
	push_start_command(dt, {device = devices.UFC, action = UFC_commands.KbdSwENT, value = 1.0}) -- submit
	push_start_command(dt, {device = devices.UFC, action = UFC_commands.KbdSwENT, value = 0.0})
end
local u = UFC_commands
tuneHornetComm(u.Comm1Fcn, {u.KbdSw2, u.KbdSw5, u.KbdSw1, u.KbdSw0, u.KbdSw0, u.KbdSw0}, "· VRS · COMM1 -> 251.000 AM")
tuneHornetComm(u.Comm2Fcn, {u.KbdSw1, u.KbdSw3, u.KbdSw3, u.KbdSw0, u.KbdSw0, u.KbdSw0}, "· VRS · COMM2 -> 133.000 AM")

push_start_command(dt, {message = _("· VRS · Quick Start Complete · F/A-18C ·"), message_timeout = 30})
--




----------------------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------
-- Stop sequence
push_stop_command(0, {message = _("· VRS · Quick Stop · F/A-18C ·"), message_timeout = stop_sequence_time})
--
push_stop_command(dt, {message = _("EJECTION SEAT SAFE/ARM HANDLE - SAFE"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.CPT_MECHANICS, action = cpt_commands.EjectionSeatSafeArmedHandle, value = 1.0})
push_stop_command(dt, {message = _("LDG GEAR HANDLE - DN"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.GEAR_INTERFACE, action = gear_commands.GearHandle, value = 0.0})
push_stop_command(dt, {message = _("FLAP SWITCH - FULL"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.CONTROL_INTERFACE, action = ctrl_commands.FlapSw, value = -1.0})
push_stop_command(dt, {message = _("T/O TRIM BUTTON - PRESS UNTIL TRIM ADVISORY DISPLAYED"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.CONTROL_INTERFACE, action = ctrl_commands.TOTrimSw, value = 1.0})
-- TODO: check condition
push_stop_command(dt, {device = devices.CONTROL_INTERFACE, action = ctrl_commands.TOTrimSw, value = 0.0})
push_stop_command(dt, {message = _("PARK BRK HANDLE - SET"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.GEAR_INTERFACE, action = gear_commands.EmergParkHandleSelectPark, value = 0.333})
push_stop_command(dt, {device = devices.GEAR_INTERFACE, action = gear_commands.EmergParkHandleSelectPark, value = 0.0})
push_stop_command(dt, {device = devices.GEAR_INTERFACE, action = gear_commands.EmergParkHandleOnOff, value = 0.1})
push_stop_command(dt, {device = devices.GEAR_INTERFACE, action = gear_commands.EmergParkHandleSelectPark, value = 0.333})
push_stop_command(dt, {device = devices.GEAR_INTERFACE, action = gear_commands.EmergParkHandleSelectPark, value = 0.0})
push_stop_command(dt, {device = devices.GEAR_INTERFACE, action = gear_commands.EmergParkHandleOnOff, value = -0.1})
push_stop_command(dt, {message = _("INS KNOB - OFF"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.INS, action = INS_commands.INS_SwitchChange, value = 0.0})
push_stop_command(dt, {message = _("STANDBY ATTITUDE REFERENCE INDICATOR - CAGE/LOCK"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.SAI, action = sai_commands.SAI_pull, value = 1.0})
push_stop_command(dt, {device = devices.SAI, action = sai_commands.SAI_rotate, value = 0.01})
push_stop_command(dt, {device = devices.SAI, action = sai_commands.SAI_pull, value = 0.0})
push_stop_command(dt, {message = _("RADAR - OFF"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.RADAR, action = RADAR_commands.RADAR_SwitchChange, value = 0.0})

push_stop_command(dt, {message = _("EXT AND INT LT KNOBS - OFF"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.EXT_LIGHTS, action = extlights_commands.Formation, value = 0.0})
push_stop_command(dt, {device = devices.EXT_LIGHTS, action = extlights_commands.Position, value = 0.0})

push_stop_command(dt, {device = devices.EXT_LIGHTS, action = extlights_commands.LdgTaxi, value = 0.0})
push_stop_command(dt, {device = devices.CPT_LIGHTS, action = cptlights_commands.Consoles, value = 0.0})
push_stop_command(dt, {device = devices.CPT_LIGHTS, action = cptlights_commands.InstPnl, value = 0.0})
push_stop_command(dt, {device = devices.CPT_LIGHTS, action = cptlights_commands.Flood, value = 0.0})
push_stop_command(dt, {device = devices.CPT_LIGHTS, action = cptlights_commands.Chart, value = 0.0})

push_stop_command(dt, {message = _("RADAR ALTIMETER - OFF, SET TO 0 FT"), message_timeout = dt_mto})
for i = 0, 61, 1 do -- Note 0-index.  60 total steps to go from 5000 ft to 0 ft, 62 steps to turn off completely.
	push_stop_command(0.01, {device = devices.ID2163A, action = id2163a_commands.ID2163A_SetMinAlt, value = -0.05}) -- value = positive number to go up, negative number to go down.  Actual number doesn't seem to make a difference, only +/-??
end

push_stop_command(dt, {message = _("HUD ALT SWITCH - BARO"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.HUD, action = HUD_commands.HUD_AltitudeSw, value = 1.0})
push_stop_command(dt, {message = _("IR COOL SWITCH - OFF"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.SMS, action = SMS_commands.IRCoolingSw, value = 0.0})
push_stop_command(dt, {message = _("DISPENSER SWITCH - OFF"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.CMDS, action = cmds_commands.Dispenser, value = 0.0})
push_stop_command(dt, {message = _("ECM - OFF"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.ASPJ, action = ASPJ_commands.ASPJ_SwitchChange, value = 0.0})
--
push_stop_command(dt, {message = _("CANOPY - OPEN"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.CPT_MECHANICS, action = cpt_commands.CanopySwitchOpen, value = 1.0})
push_stop_command(dt, {device = devices.CPT_MECHANICS, action = cpt_commands.CanopySwitchOpen, value = 0.0})
-- Engine shutdown
push_stop_command(dt, {message = _("LEFT THROTTLE - OFF"), check_condition = F18_AD_LEFT_THROTTLE_DOWN_TO_IDLE, message_timeout = dt_mto})
push_stop_command(dt, { check_condition = F18_AD_LEFT_THROTTLE_SET_TO_OFF})
push_stop_command(dt, {message = _("L(R) DDI, AMPCD, HUD AND HMD KNOBS - OFF"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.MDI_LEFT, action = MDI_commands.MDI_off_night_day, value = 0.0})
push_stop_command(dt, {device = devices.MDI_RIGHT, action = MDI_commands.MDI_off_night_day, value = 0.0})
push_stop_command(dt, {device = devices.HUD, action = HUD_commands.HUD_SymbBrightCtrl, value = 0.0})
push_stop_command(dt, {device = devices.HMD_INTERFACE, action = hmd_commands.BrtKnob, value = 0.0})
push_stop_command(dt, {device = devices.AMPCD, action = AMPCD_commands.AMPCD_off_brightness, value = 0.0})
push_stop_command(dt, {message = _("RIGHT THROTTLE - OFF"), check_condition = F18_AD_RIGHT_THROTTLE_DOWN_TO_IDLE})
push_stop_command(dt, { check_condition = F18_AD_RIGHT_THROTTLE_SET_TO_OFF})
push_stop_command(dt, {message = _("BATT SWITCH - OFF"), message_timeout = dt_mto})
push_stop_command(dt, {device = devices.ELEC_INTERFACE, action = elec_commands.BattSw, value = 0.0})
--
push_stop_command(dt, {message = _("· VRS · Quick Stop Complete · F/A-18C ·"), message_timeout = 30})
--


----------------------------------------------------------------------------------------------------
-- · VRS · Countdown timer (pattern lifted from AH-64D).
local function insertTimeRemaining(sequence, endingTime)
	if #sequence == 0 or endingTime == nil then return end
	local totalTime = math.ceil(endingTime)
	local totalTimeMins = math.floor(totalTime / 60)
	local totalTimeSecs = totalTime % 60
	-- Find first message-bearing entry (sequence[1] may be a pre-banner setup command).
	for i = 1, #sequence do
		if sequence[i].message then
			sequence[i].message = sequence[i].message..' ('..totalTimeMins..'m'..totalTimeSecs..'s)'
			sequence[i].message_timeout = endingTime
			break
		end
	end
	local minsRemaining = totalTimeMins
	local i = 1
	while sequence[i] do
		if minsRemaining ~= 0 and endingTime - sequence[i].time <= minsRemaining * 60 then
			local minutesString = minsRemaining == 1 and 'MINUTE' or 'MINUTES'
			table.insert(sequence, i, {
				message = _('· VRS · '..minsRemaining..' '..minutesString..' REMAINING ·'),
				message_timeout = 60,
				time = endingTime - minsRemaining * 60.0,
			})
			minsRemaining = minsRemaining - 1
			i = i - 1
		end
		i = i + 1
	end
end
insertTimeRemaining(start_sequence_full, t_start)
insertTimeRemaining(stop_sequence_full, t_stop)
