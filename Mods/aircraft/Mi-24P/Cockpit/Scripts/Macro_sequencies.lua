dofile(LockOn_Options.script_path.."command_defs.lua")
dofile(LockOn_Options.script_path.."devices.lua")

-- · VRS Quick Start · Mi-24P ·
-- Part of the VRS Auto Starts mod for DCS World
-- Install via OvGME: https://wiki.hoggitworld.com/view/OVGME

std_message_timeout = 8

local t_start = 0.0
local t_stop = 0.0
local dt = 0.07 -- Default Interval Between Commands In The stack


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
APU_START_FAULT = 4
FUEL_PUMP_FAUL = 5
LEFT_ENGINE_START_FAULT = 6
RIGHT_ENGINE_START_FAULT = 7

alert_messages = {}
alert_messages[COLLECTIVE] = { message = _("SET THE COLLECTIVE STICK DOWN"), message_timeout = 10}
alert_messages[NO_FUEL] = 	 { message = _("CHECK FUEL QUANTITY"), message_timeout = 10}
alert_messages[BATTERY_LOW] = { message = _("POWER SUPPLY FAULT. CHECK THE BATTERY"), message_timeout = 10}
alert_messages[APU_START_FAULT] = { message = _("AI-9 NOT READY TO START ENGINE"), message_timeout = 10}
alert_messages[FUEL_PUMP_FAUL] = { message = _("FEEDING FUEL TANK PUMP FAULT"), message_timeout = 10}
alert_messages[LEFT_ENGINE_START_FAULT] = { message = _("LEFT ENGINE START FAULT"), message_timeout = 10}
alert_messages[RIGHT_ENGINE_START_FAULT] = { message = _("RIGHT ENGINE START FAULT"), message_timeout = 10}

-----------------------------------------------------------------------------------------------------------------------

-- Barometric Pressure Set
for i = 1, 158.0, 1 do
	push_start_command(0.01, {device = devices.BAROALT_P, action = baroaltimeter_commands.CMD_ADJUST_PRESSURE, value = 1}) -- Set QNH - Pilot
end
for i = 1, 158.0, 1 do
	push_stop_command(0.01, {device = devices.BAROALT_P, action = baroaltimeter_commands.CMD_ADJUST_PRESSURE, value = -1}) -- Set QNH - Pilot
end

-- RADALT
for i = 1, 20, 1 do
	push_start_command(0.01, {device = devices.RADAR_ALTIMETER, action = ralt_commands.ROTARY, value = -1}) -- RADALT Set To 0m
end
for i = 1, 20, 1 do
	push_stop_command(0.01, {device = devices.RADAR_ALTIMETER, action = ralt_commands.ROTARY, value = -1}) -- RADALT Set To 0m

end

-- Primary 370kHz - Left
for i = 1, 1, 1 do
	push_start_command(0.01, {device = devices.ARC_15_PANEL_P, action = arc15_commands.PRIMARY_10KHz, value = 0.8}) -- ADF 10kHz
end
for i = 1, 1, 1 do
	push_start_command(0.01, {device = devices.ARC_15_PANEL_P, action = arc15_commands.PRIMARY_100KHz, value = 0.15}) -- ADF 100kHz
end

-- Backup 840kHz - Right
for i = 1, 1, 1 do
	push_start_command(0.01, {device = devices.ARC_15_PANEL_P, action = arc15_commands.BACKUP_10KHz, value = 0.4}) -- ADF 10kHz
end
for i = 1, 1, 1 do
	push_start_command(0.01, {device = devices.ARC_15_PANEL_P, action = arc15_commands.BACKUP_100KHz, value = 0.45}) -- ADF 100kHz
end
push_start_command(0.0, {message = _("· VRS · Quick Start · Mi-24P ·"), message_timeout = 125})
push_start_command(0.0, {message = _("## START WARMING WEAPONS!! ##"), message_timeout = 125})

-----------------------------------------------------------------------------------------------------------------------
	

-- Parking Brake

push_start_command(dt,{device = devices.CPT_MECH, action =  cockpit_mechanics_commands.Command_CPT_MECH_ParkingBrake, value = 1.0}) -- Parking Brake - ON


-- Hide Seat

--push_start_command(dt,{device = devices.CPT_MECH, action =  cockpit_mechanics_commands.Command_CPT_MECH_Elements_Hide, value = 1.0}) -- Turn Seat OFF


-- Close Doors

push_start_command(dt,{device = devices.CPT_MECH, action =  cockpit_mechanics_commands.Command_CPT_MECH_GENERAL_DOORS_CLOSE, value = 0.0}) -- Closes The Doors


-- Sight Reflector

push_start_command(dt,{device = devices.ASP_17V,action =  asp_commands.Reflector_Fix, value = 1.0}) -- Sight Reflector - UNFIX

push_start_command(dt,{device = devices.ASP_17V,action =  asp_commands.Reflector_Move, value = 0.0}) -- Sight Reflector - MOVE
push_start_command(dt,{device = devices.ASP_17V,action =  asp_commands.Reflector_Move, value = 0.0}) -- Sight Reflector - MOVE
push_start_command(dt,{device = devices.ASP_17V,action =  asp_commands.Reflector_Move, value = 0.0}) -- Sight Reflector - MOVE
push_start_command(dt,{device = devices.ASP_17V,action =  asp_commands.Reflector_Move, value = 0.0}) -- Sight Reflector - MOVE
push_start_command(dt,{device = devices.ASP_17V,action =  asp_commands.Reflector_Move, value = 0.0}) -- Sight Reflector - MOVE
push_start_command(dt,{device = devices.ASP_17V,action =  asp_commands.Reflector_Move, value = 0.0}) -- Sight Reflector - MOVE
push_start_command(dt,{device = devices.ASP_17V,action =  asp_commands.Reflector_Move, value = 0.0}) -- Sight Reflector - MOVE

push_start_command(dt,{device = devices.ASP_17V,action =  asp_commands.Reflector_Fix, value = 0.0}) -- Sight Reflector - FIX


-- Main Radio Selector Switch

push_start_command(dt,{device = devices.SPU_8, action =  SPU_8_Mi24_commands.CMD_SPU8_P_ICS_RADIO, value = 0.0}) -- Main Radio - ICS


for i = 1, 1, 1 do
	push_start_command(0.01, {device = devices.ARC_15_PANEL_P, action = arc15_commands.MODE, value = 0.1}) -- ADF MODE Switch - COMP
end


-- Door Seal Rotary

push_start_command(0.3,{device = devices.ECS_INTERFACE,action =  ecs_commands.Sealing_valve, value = 0.0,}) -- Seal The Doors


-- Collective

push_start_command(0.5,{device = devices.ENGINE_INTERFACE, action = engine_commands.COLLECTIVE, value = -1.0,}) -- Collective Set To Down


-- Battery Switches

push_start_command(dt,{device = devices.ELEC_INTERFACE,action =  elec_commands.BatteryRight, value = 1.0}) -- Right Battery Switch - ON
push_start_command(dt,{device = devices.ELEC_INTERFACE,action =  elec_commands.BatteryLeft, value = 1.0}) -- Left Battery Switch - ON


-- Network To Batteries Switch

push_start_command(dt,{device = devices.ELEC_INTERFACE,action =  elec_commands.NetworkToBatteriesCover, value = 1.0}) -- Network To Batteries Cover - OPEN
push_start_command(0.1,{device = devices.ELEC_INTERFACE,action =  elec_commands.NetworkToBatteries, value = 1.0}) -- Network To Batteries Switch - ON

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty




-- Circut Breakers

push_start_command(dt,{device = devices.ELEC_INTERFACE,action =  elec_commands.CB_FRAME_LEFT, value = 1.0}) -- Turn Left CBs - ON
push_start_command(0.5,{device = devices.ELEC_INTERFACE,action =  elec_commands.CB_FRAME_LEFT, value = 0.0}) -- Release

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty

push_start_command(dt,{device = devices.ELEC_INTERFACE,action =  elec_commands.CB_FRAME_RIGHT, value = 1.0}) -- Turn Right CBs - ON
push_start_command(0.5,{device = devices.ELEC_INTERFACE,action =  elec_commands.CB_FRAME_RIGHT, value = 0.0}) -- Release


-- Voice Warnings

push_start_command(0.0,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty

push_start_command(0.0,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty

push_start_command(0.0,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty


-- Rectifiers - Generators - Transformers - Invertors

push_start_command(dt,{device = devices.ELEC_INTERFACE,action = elec_commands.RectifierLeft, value = 1.0,}) -- Left Rectifier Set - ON
push_start_command(dt,{device = devices.ELEC_INTERFACE,action = elec_commands.RectifierRight, value = 1.0,}) -- Right Rectifier Set - ON

push_start_command(dt,{device = devices.ELEC_INTERFACE,action = elec_commands.ACGeneratorLeft, value = 1.0}) -- Left Generator Set - ON
push_start_command(dt,{device = devices.ELEC_INTERFACE,action = elec_commands.ACGeneratorRight, value = 1.0}) -- Right Generator Set - ON

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty

push_start_command(dt,{device = devices.ELEC_INTERFACE,action =  elec_commands.Transformer115vMainBackup, value = 1.0}) -- Left Transformer Set - MAIN
push_start_command(dt,{device = devices.ELEC_INTERFACE,action =  elec_commands.Transformer36vMainBackup, value = 1.0}) -- Right Transformer Set - MAIN

push_start_command(dt,{device = devices.ELEC_INTERFACE,action =  elec_commands.Rotary115vConverterCover, value = 1.0}) -- Inverter PO-750A Cover (115v)  - OPEN
push_start_command(0.1,{device = devices.ELEC_INTERFACE,action =  elec_commands.Rotary115vConverter, value = 1.0}) -- Inverter PO-750A Cover Set (115v) - ON

push_start_command(dt,{device = devices.ELEC_INTERFACE,action =  elec_commands.Rotary36vConverterCover, value = 1.0}) -- Inverter PT-125Ts Cover (36v) - OPEN
push_start_command(0.1,{device = devices.ELEC_INTERFACE,action =  elec_commands.Rotary36vConverter, value = 1.0}) -- Inverter PT-125Ts Set (36v) - ON

push_start_command(0.0,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.5,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty


-- Instrument Backing Lights

push_start_command(dt,{device = devices.INT_LIGHTS_SYSTEM,action =  int_lights_commands.RedLightsPilotInstrumentPanelRightPanel_1, value = 1.0,}) -- Red Lights Right And Pilot Panel Set - MAX
push_start_command(dt,{device = devices.INT_LIGHTS_SYSTEM,action =  int_lights_commands.RedLightsPilotInstrumentPanelRightPanel_2, value = 1.0,}) -- Red Lights Right And Pilot Panel Set - MAX
push_start_command(dt,{device = devices.INT_LIGHTS_SYSTEM,action =  int_lights_commands.RedLightsPilotLeftPanel_1, value = 1.0}) -- Red Lights Left Pilot Panel Set - MAX
push_start_command(dt,{device = devices.INT_LIGHTS_SYSTEM,action =  int_lights_commands.RedLightsPilotLeftPanel_2, value = 1.0}) -- Red Lights Left Pilot Panel Set - MAX
push_start_command(dt,{device = devices.INT_LIGHTS_SYSTEM,action =  int_lights_commands.RedLightsOperatorPanel_1, value = 1.0}) -- Red Lights Left And Operator Panel Set - MAX
push_start_command(dt,{device = devices.INT_LIGHTS_SYSTEM,action =  int_lights_commands.Transformer36vMainBackup, value = 1.0}) -- Red Lights Left And Operator Panel Set - MAX
push_start_command(dt,{device = devices.INT_LIGHTS_SYSTEM,action =  int_lights_commands.RedLightsPilotBuiltInRedLights, value = 1.0}) -- Builtin Red Lights Transformer Set - MAX


-- Voice Warnings

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty


-- Fire Extinguisher Circuts

push_start_command(dt,{device = devices.FIRE_EXTING_INTERFACE,action =  fire_commands.SensorControl, value = 1.0}) -- Extinguisher Control Switch - EXING
push_start_command(dt,{device = devices.FIRE_EXTING_INTERFACE,action =  fire_commands.Power, value = 1.0}) -- Fire Extinguisher Power - ON


-- Fuel Cutoff Switches

push_start_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveTank1, value = 1.0}) -- Tank 1 Cutoff Switch Set - ON
push_start_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveTank2, value = 1.0}) -- Tank 2 Cutoff Switch Set - ON

push_start_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.Tank4Pump, value = 1.0}) -- Tank Pump 4 Set - ON
push_start_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.Tank5Pump, value = 1.0}) -- Tank Pump 5 Set - ON
push_start_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.Tank1Pump, value = 1.0}) -- Tank Pump 1 Set - ON
push_start_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.Tank2Pump, value = 1.0}) -- Tank Pump 2 Set - ON

push_start_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveDelimiter, value = 1.0}) -- Fuel Delimiter Valve Set - ON


-- APU Start START 15sec

push_start_command(dt, {message = _("  APU Start"), message_timeout = 10})

push_start_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_APU_Launch_Method, value = -1.0}) -- APU Selector Switch - START
push_start_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_APU_StartUp, value = 1.0}) -- APU Start Button - Press
push_start_command(0.3,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_APU_StartUp, value = 0.0}) -- APU Start Button - Release


-- Voice Warnings

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty


-- Lights And Radio Switches

push_start_command(0.1,{device = devices.SPU_8,action =  SPU_8_Mi24_commands.CMD_SPU8_NETWORK_1, value = 1.0}) -- Switch SPU-8 NET-1 - ON
push_start_command(dt,{device = devices.SPU_8,action =  SPU_8_Mi24_commands.CMD_SPU8_NETWORK_2, value = 1.0}) -- Switch SPU-8 NET-2 - ON
push_start_command(dt,{device = devices.R_863,action =  r863_commands.POWER, value = 1.0}) -- R-863 Power Switch - ON
push_start_command(dt,{device = devices.JADRO_1I,action =  jadro_commands.POWER, value = 1.0}) -- JADRO Power Switch - ON
push_start_command(dt,{device = devices.JADRO_1I,action =  jadro_commands.MODE, value = 0.3}) -- JADRO Mode Switch - AM
push_start_command(dt,{device = devices.EUCALYPT_M24,action =  eucalypt_commands.POWER_ON_OFF2, value = 1.0}) -- R-828 Power Switch - ON
push_start_command(dt,{device = devices.RADAR_ALTIMETER,action =  ralt_commands.POWER, value = 1.0}) -- RADALT Power Switch - ON
push_start_command(dt,{device = devices.DISS_15,action =  diss_commands.POWER, value = 1.0}) -- Doppler System Switch - ON
push_start_command(dt,{device = devices.MGV1SU_1,action =  mgv1su_commands.POWER, value = 1.0}) -- Gyro 1 Power Switch - ON
push_start_command(dt,{device = devices.MGV1SU_2,action =  mgv1su_commands.POWER, value = 1.0}) -- Gyro 2 Power Switch - ON
push_start_command(dt,{device = devices.GREBEN,action =  greben_commands.POWER, value = 1.0}) -- Greben Power Switch - ON
push_start_command(dt,{device = devices.SPO_10,action =  SPO_commands.Command_SPO_POWER, value = 1.0}) -- RWR Power Switch - ON
push_start_command(dt,{device = devices.IFF,action =  IFF_6201_commands.CMD_IFF_Power_Sw, value = 1.0}) -- IFF Power Switch - ON
push_start_command(dt,{device = devices.CPT_MECH,action =  cockpit_mechanics_commands.Command_CPT_MECH_FAN_PILOT, value = 1.0}) -- Pilots Fan Power Switch - ON
push_start_command(dt,{device = devices.EXT_LIGHTS_SYSTEM,action =  ext_lights_commands.StrobeLight, value = 1.0}) -- Strobe Light Power Switch - ON
push_start_command(dt,{device = devices.EXT_LIGHTS_SYSTEM,action =  ext_lights_commands.TipLights, value = 1.0}) -- Blade Tip Lights Power Switch - ON

push_start_command(dt,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty

push_start_command(dt,{device = devices.EXT_LIGHTS_SYSTEM,action =  ext_lights_commands.FormationLights, value = 1.0}) -- Formation Lights Power Switch - BRIGHT
push_start_command(dt,{device = devices.MAP_DISPLAY,action =  map_display_commands.Power, value = 1.0}) -- Map Power Switch - ON
push_start_command(dt,{device = devices.EXT_CARGO_EQUIPMENT,action =  ext_cargo_equipment_commands.CMD_AutoReleaseSw, value = 1.0}) -- External Cargo Hook - AUTOMATIC
push_start_command(dt,{device = devices.EXT_CARGO_EQUIPMENT,action =  ext_cargo_equipment_commands.CMD_RemoveRelease, value = 1.0}) -- External Cargo Remove Release - ON

push_start_command(4.0,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 1.0}) -- Betty
push_start_command(0.2,{device = devices.VMS,action =  RI65_commands.CMD_RI_Mi24_Off, value = 0.0}) -- Betty


-- APU Generator Switch

push_start_command(7,{device = devices.ELEC_INTERFACE,action =  elec_commands.DCGenerator, value = 1.0}) -- APU Gen Set - ON


-- Fuel Control Valves

push_start_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveLeftEngineCover, value = 1.0}) -- Left Engine Fire Valve Cover - OPEN
push_start_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveLeftEngine, value = 1.0}) -- Left Engine Fire Valve - ON
push_start_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveLeftEngineCover, value = 0.0}) -- Left Engine Fire Valve Cover - CLOSE

push_start_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveRightEngineCover, value = 1.0}) -- Right Engine Fire Valve Cover - OPEN
push_start_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveRightEngine, value = 1.0}) -- Right Engine Fire Valve - ON
push_start_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveRightEngineCover, value = 0.0}) -- Right Engine Fire Valve Cover - CLOSE


-- Fuel Shutoff Valves

push_start_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.LEVER_Left_Engine_Lock, value = 0.0}) -- Left Engine Fuel Shutoff Valve - ON
push_start_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.LEVER_Right_Engine_Lock, value = 0.0}) -- Right Engine Fuel Shutoff Valve - ON


-- Collective

push_start_command(1.0,{device = devices.ENGINE_INTERFACE,action =  engine_commands.OP_COLLECTIVE, value = 0.0}) -- Collective - DOWN


-- Rotor Brake

push_start_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.LEVER_Rotor_Lock, value = 0.0}) -- Rotor Brake - OFF

-- Left Engine Start TIME 48sec

push_start_command(dt, {message = _("  Left Engine START"), message_timeout = 40})

push_start_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_Engine_Launch_Method, value = 0.0}) -- Mode Selector Switch - START
push_start_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_Engine_Select, value = 1.0}) -- Engine Select Switch - LEFT

push_start_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_Engine_StartUp, value = 1.0}) -- Engine Start Button - PRESS
push_start_command(0.3,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_Engine_StartUp, value = 0.0}) -- Engine Start Button - RELEASE
push_start_command(0.1,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_Engine_StartUp, value = 1.0}) -- Engine Start Button - PRESS
push_start_command(0.3,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_Engine_StartUp, value = 0.0}) -- Engine Start Button - RELEASE


-- Weapons Systems

push_start_command(dt,{device = devices.INT_LIGHTS_SYSTEM,action =  int_lights_commands.SpecialEquipmentPanelRedLights, value = 1.0}) -- Armament Panel Red Lights Switch - ON
push_start_command(dt,{device = devices.WEAP_SYS,action = weapon_commands.Pilot_FKP_CAMERA, value = 1.0}) -- Weapon Camera - ON
push_start_command(dt,{device = devices.ASP_17V,action = asp_commands.Power, value = 1.0}) -- Pilot Sight Power Switch - ON
push_start_command(dt,{device = devices.ASP_17V,action = asp_commands.Power, value = 1.0}) -- CPG Sight Power Switch - ON
push_start_command(dt,{device = devices.ASP_17V,action = asp_commands.Manual_Auto, value = 1.0}) -- Sight Mode Switch - AUTO
push_start_command(dt,{device = devices.ASP_17V,action = asp_commands.Sync_Async, value = 1.0}) -- Sight Sync Switch - SYNC
push_start_command(dt,{device = devices.WEAP_SYS,action =  weapon_commands.Pilot_NPU_CHAIN, value = 0.0}) -- Burst Length - LONG
push_start_command(dt,{device = devices.ASP_17V,action =  asp_commands.Range_Auto_Manual, value = 1.0}) -- Sight AUTO/MANUAL - AUTO
push_start_command(dt,{device = devices.WEAP_SYS,action =  weapon_commands.Pilot_SWITCHER_FIRE_CONTROL, value = 1.0}) -- Pilot Master Arm - ON
push_start_command(dt,{device = devices.WEAP_SYS,action =  weapon_commands.Pilot_TEMP_NPU30, value = 1.0}) -- Cannon Fire Rate - FAST
push_start_command(dt,{device = devices.WEAP_SYS,action =  weapon_commands.Pilot_EMERG_EXPLODE_COVER, value = 1.0}) -- Explosion on Jettison Cover - OPEN
push_start_command(dt,{device = devices.WEAP_SYS,action =  weapon_commands.Pilot_EMERG_RELEASE_COVER, value = 1.0}) -- Jettison Pylons Cover - OPEN
push_start_command(dt,{device = devices.WEAP_SYS,action =  weapon_commands.Pilot_EMERG_RELEASE_PU_COVER, value = 1.0}) -- Jettison Launcher Cover - OPEN
push_start_command(dt,{device = devices.I9K113,action =  i9K113_commands.Command_9k113_Backlight, value = 1.0}) -- CPG Backlight Switch - ON
--push_start_command(dt,{device = devices.WEAP_SYS,action =  weapon_commands.Pilot_SWITCHER_OFF_GM_URS_NPU, value = 0.0}) -- Weapons Select - Missile/Off
push_start_command(dt,{device = devices.ECS_INTERFACE,action =  ecs_commands.HeatingAirFlowSight, value = 1.0}) -- Sight Fan Power Switch - ON
push_start_command(dt,{device = devices.CPT_MECH,action =  cockpit_mechanics_commands.Command_CPT_MECH_FAN_OPERATOR, value = 1.0}) -- Co Pilots Fan Power Switch - ON
--push_start_command(dt,{device = devices.WEAP_SYS,action =  weapon_commands.Operator_SWITCHER_SAFE_WEAP, value = 1.0}) -- CPG Master ARM - ON
--push_start_command(dt,{device = devices.WEAP_SYS,action =  weapon_commands.Operator_URS_POWER, value = 1.0}) -- Missiles Power - ON
--push_start_command(dt,{device = devices.WEAP_SYS,action =  weapon_commands.Pilot_PUS_ARMING, value = 1.0}) -- Arm Rockets
--push_start_command(dt,{device = devices.PKP72M_INTERFACE,action =  pkp72m_interface_commands.PKP72MoperatorSwitch, value = 1.0}) -- ADI Power Switch - ON
--push_start_command(dt,{device = devices.WEAP_SYS,action =  weapon_commands.Operator_POWER_SHO_SWITCHER, value = 1.0}) -- SCHO Power Switch - ON
--push_start_command(dt,{device = devices.WEAP_SYS,action =  weapon_commands.Operator_CHECK_LAMPS_9C475, value = 1.0}) -- SCHO Lamps Check Switch - ON
--push_start_command(dt,{device = devices.CPT_MECH,action =  cockpit_mechanics_commands.Command_CPT_MECH_PitotTotalAndAoASideslip, value = 1.0}) -- Heating DUAS Power Switch - ON




-- Right Engine Start TIME 48sec

push_start_command(50, {message = _("  Right Engine START"), message_timeout = 40})

push_start_command(0.1,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_Engine_Launch_Method, value = 0.0}) -- Mode Selector Switch To START
push_start_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_Engine_Select, value = -1.0}) -- Engine Select Switch - RIGHT

push_start_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_Engine_StartUp, value = 1.0}) -- Engine Start Button - PRESS
push_start_command(0.3,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_Engine_StartUp, value = 0.0}) -- Engine Start Button - RELEASE
push_start_command(0.1,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_Engine_StartUp, value = 1.0}) -- Engine Start Button - PRESS
push_start_command(0.3,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_Engine_StartUp, value = 0.0}) -- Engine Start Button - RELEASE

-- Throttle Up
push_start_command(40, {message = _("  Throttle Up"), message_timeout = 30})
push_start_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.OP_CONTROL_CORRECTION, value = 1.0}) -- Collective Throttle To MAX

-- Inverters

push_start_command(20,{device = devices.ELEC_INTERFACE,action =  elec_commands.Rotary115vConverterCover, value = 0.0}) -- Inverter PO-750A Cover (115v) - CLOSED
push_start_command(dt,{device = devices.ELEC_INTERFACE,action =  elec_commands.Rotary36vConverterCover, value = 0.0}) -- Inverter PT-125Ts Cover (36v) - CLOSED
push_start_command(dt,{device = devices.ELEC_INTERFACE,action =  elec_commands.NetworkToBatteriesCover, value = 0.0}) -- Network To Batteries Cover - CLOSED

push_start_command(dt,{device = devices.ELEC_INTERFACE,action =  elec_commands.Transformer115vMainBackup, value = 0.0}) -- Left Transformer Set - AUTO
push_start_command(dt,{device = devices.ELEC_INTERFACE,action =  elec_commands.Transformer36vMainBackup, value = 0.0}) -- Right Transformer Set - AUTO

push_start_command(0.1,{device = devices.ELEC_INTERFACE,action =  elec_commands.Transformer115vMainBackup, value = 1.0}) -- Left Transformer Set - MAIN
push_start_command(0.1,{device = devices.ELEC_INTERFACE,action =  elec_commands.Transformer36vMainBackup, value = 1.0}) -- Right Transformer Set - MAIN

-- Cage Gyros

push_start_command(dt,{device = devices.MGV1SU_1,action =  mgv1su_commands.CAGE, value = 1.0}) -- Left Gyro Cage - PRESS
push_start_command(1.0,{device = devices.MGV1SU_1,action =  mgv1su_commands.CAGE, value = 0.0}) -- Left Gyro Cage - RELEASE

push_start_command(dt,{device = devices.MGV1SU_2,action =  mgv1su_commands.CAGE, value = 1.0}) -- Right Gyro Cage - PRESS
push_start_command(1.0,{device = devices.MGV1SU_2,action =  mgv1su_commands.CAGE, value = 0.0}) -- Right Gyro Cage - RELEASE

-- APU Stop

push_start_command(20, {message = _("  APU Stop"), message_timeout = 20})

push_start_command(0.0,{device = devices.ELEC_INTERFACE,action =  elec_commands.DCGenerator, value = 0.0}) -- APU Gen Set - OFF

push_start_command(0.0,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_APU_Stop, value = 1.0}) -- APU Stop Button - Press
push_start_command(0.3,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_APU_Stop, value = 0.0}) -- APU Stop Button - Release

push_start_command(0.0, {message = _("  Stabilizing Engine RPM"), message_timeout = 10.4})


-- Auto Pilot


push_start_command(0.1,{device = devices.AUTOPILOT,action =  autopilot_commands.ButtonKon, value = 1.0}) -- Autopilot K Channel (ROLL) - ON
push_start_command(0.1,{device = devices.AUTOPILOT,action =  autopilot_commands.ButtonKon, value = 0.0}) -- Release
push_start_command(0.1,{device = devices.AUTOPILOT,action =  autopilot_commands.ButtonTon, value = 1.0}) -- Autopilot T Channel (PITCH) - ON 
push_start_command(0.1,{device = devices.AUTOPILOT,action =  autopilot_commands.ButtonTon, value = 0.0}) -- Release

push_start_command(0.1,{device = devices.SPUU_52,action =  spuu_commands.On_Off, value = 1.0}) -- SPUU Power Switch - ON


-- CPG Master ARM

push_start_command(dt,{device = devices.WEAP_SYS,action =  weapon_commands.Operator_SWITCHER_SAFE_WEAP, value = 1.0}) -- CPG Master ARM - ON


-- Main Radio Selector Switch

--push_start_command(dt,{device = devices.SPU_8, action =  SPU_8_Mi24_commands.CMD_SPU8_P_ICS_RADIO, value = 1.0}) -- Main Radio - RADIO


-- Finish Message

push_start_command(11.0, {message = _("· VRS · Quick Start Complete · Mi-24P ·"), message_timeout = 10})


------------------------------------------------------------------------------------------------------------------------------------------
------------------------------------------------------------------------------------------------------------------------------------------


-- Auto Stop 36sec


-- Parking Brake

push_stop_command(dt,{device = devices.CPT_MECH, action =  cockpit_mechanics_commands.Command_CPT_MECH_ParkingBrake, value = 1.0}) -- Parking Brake - ON


-- Cage Gyros

push_stop_command(1.0,{device = devices.MGV1SU_1,action =  mgv1su_commands.CAGE, value = 1.0}) -- Left Gyro Cage - PRESS
push_stop_command(1.0,{device = devices.MGV1SU_1,action =  mgv1su_commands.CAGE, value = 0.0}) -- Left Gyro Cage - RELEASE

push_stop_command(dt,{device = devices.MGV1SU_2,action =  mgv1su_commands.CAGE, value = 1.0}) -- Right Gyro Cage - PRESS
push_stop_command(1.0,{device = devices.MGV1SU_2,action =  mgv1su_commands.CAGE, value = 0.0}) -- Right Gyro Cage - RELEASE


-- Battery Switches

push_stop_command(0.1,{device = devices.ELEC_INTERFACE,action =  elec_commands.BatteryRight, value = -1.0}) -- Right Battery Switch - OFF
push_stop_command(0.1,{device = devices.ELEC_INTERFACE,action =  elec_commands.BatteryLeft, value = -1.0}) -- Left Battery Switch - OFF


-- AC Generators

push_stop_command(dt,{device = devices.ELEC_INTERFACE,action = elec_commands.ACGeneratorLeft, value = 0.0}) -- Left Generator Set - OFF
push_stop_command(dt,{device = devices.ELEC_INTERFACE,action = elec_commands.ACGeneratorRight, value = 0.0}) -- Right Generator Set - OFF


-- Fuel Shutoff Valves

push_stop_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.LEVER_Left_Engine_Lock, value = 1.0}) -- Left Engine Fuel Shutoff Valve - OFF
push_stop_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.LEVER_Right_Engine_Lock, value = 1.0}) -- Right Engine Fuel Shutoff Valve - OFF


-- APU Stop

push_stop_command(1.0,{device = devices.ELEC_INTERFACE,action =  elec_commands.DCGenerator, value = 0.0}) -- APU Gen Set - OFF

push_stop_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_APU_Stop, value = 1.0}) -- APU Stop Button - Press
push_stop_command(0.3,{device = devices.ENGINE_INTERFACE,action =  engine_commands.STARTUP_APU_Stop, value = 0.0}) -- APU Stop Button - Release


-- Throttle

push_stop_command(0.1,{device = devices.ENGINE_INTERFACE,action =  engine_commands.OP_CONTROL_CORRECTION, value = -1.0}) -- Collective Throttle To MIN


-- Fuel Control Valves

push_stop_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveLeftEngineCover, value = 1.0}) -- Left Engine Fire Valve Cover - OPEN
push_stop_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveLeftEngine, value = 0.0}) -- Left Engine Fire Valve - OFF
push_stop_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveLeftEngineCover, value = 0.0}) -- Left Engine Fire Valve Cover - CLOSE

push_stop_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveRightEngineCover, value = 1.0}) -- Right Engine Fire Valve Cover - OPEN
push_stop_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveRightEngine, value = 0.0}) -- Right Engine Fire Valve - OFF
push_stop_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveRightEngineCover, value = 0.0}) -- Right Engine Fire Valve Cover - CLOSE


-- Fuel Shutoff Valves

push_stop_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.LEVER_Left_Engine_Lock, value = 1.0}) -- Left Engine Fuel Shutoff Valve - OFF
push_stop_command(dt,{device = devices.ENGINE_INTERFACE,action =  engine_commands.LEVER_Right_Engine_Lock, value = 1.0}) -- Right Engine Fuel Shutoff Valve - OFF


-- Rotor Brake

push_stop_command(1.0,{device = devices.ENGINE_INTERFACE,action =  engine_commands.LEVER_Rotor_Lock, value = 1.0}) -- Rotor Brake - ON


-- Fire Extinguisher Circuts

push_stop_command(2.0,{device = devices.FIRE_EXTING_INTERFACE,action =  fire_commands.SensorControl, value = 1.0}) -- Extinguisher Control Switch - EXING
push_stop_command(dt,{device = devices.FIRE_EXTING_INTERFACE,action =  fire_commands.Power, value = 1.0}) -- Fire Extinguisher Power - ON


-- Fuel Cutoff Switches

push_stop_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveTank1, value = 0.0}) -- Tank 1 Cutoff Switch Set - OFF
push_stop_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveTank2, value = 0.0}) -- Tank 2 Cutoff Switch Set - OFF

push_stop_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.Tank4Pump, value = 0.0}) -- Tank Pump 4 Set - OFF
push_stop_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.Tank5Pump, value = 0.0}) -- Tank Pump 5 Set - OFF
push_stop_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.Tank1Pump, value = 0.0}) -- Tank Pump 1 Set - OFF
push_stop_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.Tank2Pump, value = 0.0}) -- Tank Pump 2 Set - OFF

push_stop_command(dt,{device = devices.FUELSYS_INTERFACE,action =  fuel_commands.ValveDelimiter, value = 0.0}) -- Fuel Delimiter Valve Set - OFF


-- Open Doors

push_stop_command(25,{device = devices.CPT_MECH, action =  cockpit_mechanics_commands.Command_CPT_MECH_GENERAL_DOORS_CLOSE, value = 1.0}) -- Opens The Doors



