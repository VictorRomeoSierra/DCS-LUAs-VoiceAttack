r"""Generate a VoiceAttack .vap profile from the VRS F10 menu tree.

Mirrors the static menu structure of `VRS master files/shared/modules/players/menus.lua`
plus the CTLD vehicle and troop catalogs from `ctldMooseAdapter.lua`.

Run from this directory:
    python generate_vrs_vap.py
Produces `VRS AI v0.3-Profile.vap` next to the script.

Key sequence assumptions
------------------------
Each VAP command opens the DCS comm menu with `\` (backslash, VK 220), navigates
to the mission-scripting submenu with F10 (VK 121), then drills down with one
F-key per level. The user's DCS keybinding for "Pilot - Comms Menu" must remain
the default backslash for these sequences to work.

Tree ordering
-------------
Two ordering modes match the Lua side:
* `static` -- `addGroupTree` registers commands first, then child submenus.
* `submenus_first` -- `buildCtldMooseMenuFor` registers child submenus first,
  then leaf commands. Applies to the entire CTLD subtree.

Pagination
----------
DCS pages F10 menus at 10 items. The current tree fits within 10 per level
(SAM LR is at exactly 10). If a future menu overflows, the generator raises
so we can add F11=Next handling explicitly.
"""

from __future__ import annotations

import uuid
import xml.sax.saxutils as xml_utils
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

OPEN_KEY = 220
OTHER_KEY = 121  # F10
F_KEYS = {
    1: 112, 2: 113, 3: 114, 4: 115, 5: 116,
    6: 117, 7: 118, 8: 119, 9: 120, 10: 121,
}
F11_KEY = 122
F12_KEY = 123
KEY_NAME = {
    220: "\\ |",
    112: "F1", 113: "F2", 114: "F3", 115: "F4", 116: "F5",
    117: "F6", 118: "F7", 119: "F8", 120: "F9", 121: "F10",
    122: "F11", 123: "F12",
}

OUTPUT_FILE = "VRS AI v0.3-Profile.vap"
PROFILE_NAME = "VRS AI"
PROFILE_ID = "ca158b5b-e504-4f98-975f-84b4f6124d04"


@dataclass
class Cmd:
    label: str
    say: list[str] | None = None  # alias phrases; default = [label]


@dataclass
class Node:
    name: str
    commands: list[Cmd | str] = field(default_factory=list)
    children: list["Node"] = field(default_factory=list)
    order: str = "static"  # "static" or "submenus_first"


# --------------------------------------------------------------------------- #
# Menu data -- mirrors players/menus.lua at module version 0.3.19              #
# --------------------------------------------------------------------------- #

# CTLD vehicle catalog from ctldMooseAdapter.lua VEHICLE_CATALOG (lines 163-222).
# Buckets keyed by subcategory in SUBCATEGORY_ORDER (menus.lua line 170).
CTLD_VEHICLES = {
    "Support": [
        "Factory Crate (5)",
        "M1025 HMMV CP",
        "M978 HEMTT tanker (4)",
        "M-818 Ammo Truck (2)",
        "Repair crate",
        "Fat Cow crate",
        "FOB crate large (2)",
    ],
    "Artillery": [
        "M109 (3)",
        "MLRS (4)",
        "Himars guided cluster (3)",
        "Himars guided HE (3)",
        "T155 Firtnia (3)",
        "SpGH Dana (3)",
    ],
    "Light Armor": [
        "MATV",
        "ATGM M1045 HMMWV TOW",
        "M2 Bradley (3)",
        "M1130 Stryker CV (3)",
        "M1134 Stryker ATGM (3)",
        "M1128 Stryker MGS (3)",
        "Marder (2)",
        "MCV-80 Warrior (2)",
        "LAV-25 (2)",
    ],
    "Heavy Armor": [
        "Challenger (6)",
        "Leopard (6)",
        "M-1 Abrams (6)",
        "Chieftain (6)",
    ],
    "SAM IR/AAA": [
        "AAA Vulcan M163 (2)",
        "Gepard (3)",
        "SAM Chaparral M48 (2)",
        "SAM Avenger M1097 (2)",
        "M6 Linebacker (3)",
        "LPWS C-ram (4)",
    ],
    "SAM SR/MR": [
        "Roland ADS (3)",
        "Roland EWR (2)",
        "Rapier launcher",
        "Rapier blindfire TR",
        "Rapier optical tracker",
        "IRIS-T SLM command post",
        "IRIS-T SLM launcher",
        "IRIS-T SLM SR/TR",
    ],
    "SAM LR": [
        "Patriot SR/TR",
        "Patriot ECS",
        "Patriot EPP",
        "Patriot CP",
        "Patriot AMG",
        "Patriot Launcher",
        "NASAMS SR/TR",
        "NASAMS LauncherC",
        "NASAMS CP",
        "NASAMS LauncherB",
    ],
}

CTLD_TROOPS = [
    "Load in: VRS unit (8)",
    "Load in: VRS platoon (24)",
    "Load in: VRS Anti-air (4)",
    "Load in: VRS Anti-tank (4)",
    "Load in: VRS Mortar squad (4)",
    "Load in: VRS JTAC (1)",
    "Load in: JTAC and guards (4)",
    "Load in: VRS Engineers (4)",
]


def _crate_subcategory_node(name: str) -> Node:
    return Node(
        name=name,
        commands=[Cmd(label=label) for label in CTLD_VEHICLES[name]],
    )


CTLD_NODE = Node(
    name="CTLD",
    order="submenus_first",
    children=[
        Node(
            name="Manage Troops",
            order="submenus_first",
            children=[
                Node(
                    name="Load Troops",
                    commands=[Cmd(label=t) for t in CTLD_TROOPS],
                ),
            ],
            commands=[
                Cmd(label="Drop all troops",        say=["Drop all troops", "Unload troops"]),
                Cmd(label="Extract nearby troops",  say=["Extract nearby troops", "Pick up troops"]),
            ],
        ),
        Node(
            name="Manage Crates",
            order="submenus_first",
            children=[
                Node(
                    name="Get Crates",
                    order="submenus_first",
                    children=[
                        _crate_subcategory_node("Support"),
                        _crate_subcategory_node("Artillery"),
                        _crate_subcategory_node("Light Armor"),
                        _crate_subcategory_node("Heavy Armor"),
                        _crate_subcategory_node("SAM IR/AAA"),
                        _crate_subcategory_node("SAM SR/MR"),
                        _crate_subcategory_node("SAM LR"),
                    ],
                ),
            ],
            commands=[
                Cmd(label="Load nearby crates",  say=["Load nearby crates", "Load crate"]),
                Cmd(label="Drop loaded crates",  say=["Drop loaded crates", "Drop crates"]),
                Cmd(label="Build nearby crates", say=["Build nearby crates", "Build crate"]),
                Cmd(label="Pack nearest unit",   say=["Pack nearest unit", "Pack crate"]),
                Cmd(label="Remove nearby crates",say=["Remove nearby crates", "Destroy crate"]),
                Cmd(label="List nearby crates",  say=["List nearby crates", "List crates"]),
            ],
        ),
    ],
    commands=[
        Cmd(label="List boarded cargo", say=["List boarded cargo", "Cargo status"]),
        Cmd(label="Inventory"),
    ],
)


PERSONAL_NODE = Node(
    name="Personal Menu",
    commands=[
        Cmd(label="Toggle Rescue Duty",  say=["Toggle Rescue Duty", "On duty", "Off duty"]),
        Cmd(label="Show Airframe Lives", say=["Show Airframe Lives", "Lives summary"]),
        Cmd(label="Report a bug",        say=["Report a bug", "Submit bug report"]),
    ],
    children=[
        Node(
            name="Intel Reporting",
            commands=[
                Cmd(label="Repeat your mission brief."),
                Cmd(label="Get last intel report.", say=["Get last intel report", "Last intel"]),
            ],
            children=[
                Node(
                    name="Intel reporting (detail)",  # disambiguated; parent is "Intel Reporting"
                    commands=[
                        Cmd(label="Share last report with all"),
                        Cmd(label="REDFOR runway status (15i).",
                            say=["REDFOR runway status", "Red runway status"]),
                        Cmd(label="REDFOR base report (50i).",
                            say=["REDFOR base report", "Red base report"]),
                        Cmd(label="REDFOR base summary (20i).",
                            say=["REDFOR base summary", "Red base summary"]),
                        Cmd(label="War report (30i).", say=["War report"]),
                        Cmd(label="Get tasking report.", say=["Get tasking report", "Tasking"]),
                        Cmd(label="Get BLUFOR AA systems report (15i).",
                            say=["BLUFOR AA report", "Blue AA report"]),
                    ],
                ),
            ],
        ),
        Node(
            name="Spend your Credits",
            children=[
                Node(
                    name="Other cool stuffs",
                    commands=[
                        Cmd(label="Flare QShot: 5Cr.",         say=["Flare QShot"]),
                        Cmd(label="Flare Prancing Pony: 20Cr.",say=["Flare Prancing Pony"]),
                        Cmd(label="Illuminate the area: 5Cr.", say=["Illuminate the area"]),
                        Cmd(label="Illuminate the country: 15Cr.", say=["Illuminate the country"]),
                        Cmd(label="Place mine field: 80Cr.",   say=["Place mine field"]),
                    ],
                ),
                Node(
                    name="Personal Escorts",
                    commands=[
                        Cmd(label="F-16A (CAP): 300 Cr.", say=["F-16A escort", "F-16 escort"]),
                        Cmd(label="F-18C (CAP): 350 Cr.", say=["F-18C escort", "F-18 escort"]),
                    ],
                ),
            ],
        ),
        Node(
            name="General Info",
            commands=[
                Cmd(label="Detailed Score",       say=["Detailed Score", "Show score detail"]),
                Cmd(label="Score Summary",        say=["Score Summary", "Show score"]),
                Cmd(label="Whats my crosswind?",  say=["Crosswind", "Show Crosswind", "What's my crosswind"]),
                Cmd(label="See active players",   say=["See active players", "Show players"]),
                Cmd(label="Show Standard Frequencies",
                    say=["Standard frequencies", "Show frequencies"]),
            ],
        ),
        Node(
            name="-- Patreons Only",
            children=[
                Node(
                    name="-- Early access",
                    commands=[Cmd(label="Patreon API Vector (test)")],
                ),
                Node(
                    name="-- Reporting",
                    commands=[
                        Cmd(label="Red runway report"),
                        Cmd(label="Summary report"),
                        Cmd(label="Get War Report"),
                        Cmd(label="Get Detailed Report"),
                    ],
                ),
                Node(
                    name="-- Patreon Perks",
                    commands=[
                        Cmd(label="Your Reward Status"),
                        Cmd(label="Collect your reward"),
                        Cmd(label="Collect all rewards"),
                    ],
                ),
                Node(
                    name="-- Stupid Stuffs",
                    commands=[
                        Cmd(label="Funny ha ha..."),
                        Cmd(label="Dink..."),
                        Cmd(label="SelfDestruct..."),
                    ],
                ),
            ],
        ),
        Node(
            name="-- opLead Menus",
            children=[
                Node(
                    name="-- Module & Config",
                    commands=[
                        Cmd(label="Move AWACS"),
                        Cmd(label="Move AWACS - Explain"),
                    ],
                ),
                Node(
                    name="-- Troubleshooting",
                    commands=[
                        Cmd(label="Turn airbase red (Haifa)"),
                        Cmd(label="Clear AI threads"),
                        Cmd(label="Free CPU time"),
                        Cmd(label="Clear all red_air on ground", say=["Clear red air on ground"]),
                        Cmd(label="Clear all blue_air on ground", say=["Clear blue air on ground"]),
                        Cmd(label="Clear map junk"),
                    ],
                ),
                Node(
                    name="-- Mission Spawning",
                    commands=[
                        Cmd(label="Random Air Spawn (v3)"),
                        Cmd(label="Increase plyr v air strength"),
                        Cmd(label="Reduce plyr v air strength"),
                    ],
                ),
                Node(
                    name="-- Mission Reports",
                    commands=[
                        Cmd(label="Red runway report (opLead)"),  # disambiguated from Patreon
                        Cmd(label="Players Online"),
                        Cmd(label="Air Stats report"),
                    ],
                ),
                Node(
                    name="-- Admin & cApi",
                    commands=[
                        Cmd(label="SC Elevator toggle"),
                        Cmd(label="Stop red ground"),
                        Cmd(label="Stop blue ground"),
                        Cmd(label="Fix ground pathing"),
                        Cmd(label="Spawn Nearby SAL"),
                        Cmd(label="Cleanup All Red Forces"),
                        Cmd(label="BenGur Warehouse Contents"),
                        Cmd(label="Check Persistence Files"),
                    ],
                ),
                Node(
                    name="-- Self made man",
                    commands=[Cmd(label="Light Orb")],
                ),
            ],
        ),
    ],
)

CSAR_NODE = Node(
    name="CSAR",
    commands=[
        Cmd(label="List Active Pickups",    say=["List Active Pickups", "List rescues"]),
        Cmd(label="Show Pickups on Map",    say=["Show Pickups on Map", "CSAR on map"]),
        Cmd(label="Pick up nearby rescue",  say=["Pick up nearby rescue", "Pickup rescue"]),
        Cmd(label="Check Onboard",          say=["Check Onboard", "Who is onboard"]),
        Cmd(label="Offload Pickups",        say=["Offload Pickups", "Offload rescue"]),
        Cmd(label="Request Signal Flare (blue only)", say=["Request signal flare", "Pop flare"]),
        Cmd(label="Request Smoke (blue only)", say=["Request smoke", "Pop smoke"]),
    ],
)

SALVAGE_NODE = Node(
    name="Salvage",
    commands=[
        Cmd(label="Pick up nearby (250 kg)",  say=["Pick up salvage 250", "Salvage 250"]),
        Cmd(label="Pick up nearby (500 kg)",  say=["Pick up salvage 500", "Salvage 500"]),
        Cmd(label="Pick up nearby (1000 kg)", say=["Pick up salvage 1000", "Salvage 1000"]),
        Cmd(label="Pick up nearby (All remaining)", say=["Pick up all salvage", "Salvage all"]),
        Cmd(label="Drop off",                 say=["Drop off salvage", "Deliver salvage"]),
        Cmd(label="Emergency Jett!",          say=["Emergency jettison", "Jettison salvage"]),
        Cmd(label="List salvage jobs map wide", say=["List salvage", "Salvage jobs"]),
        Cmd(label="Show Salvage on Map",      say=["Show salvage on map", "Salvage map"]),
    ],
)

INTERROGATION_NODE = Node(
    name="Interrogation",
    commands=[
        Cmd(label="Request status",                say=["Interrogation status", "Pow status"]),
        Cmd(label="Request collected info",        say=["Collected intel", "Pow intel"]),
        Cmd(label="Initiate 'mind games'",         say=["Mind games"]),
        Cmd(label="Initiate 'chat with knuckles'", say=["Chat with knuckles"]),
        Cmd(label="Initiate 'hydro-persuation'",   say=["Hydro persuasion"]),
        Cmd(label="Initiate 'oil planking'",       say=["Oil planking"]),
    ],
)

FACTORY_NODE = Node(
    name="Factory Menu",
    commands=[
        Cmd(label="What does the pot look like?",
            say=["What does the pot look like", "Factory pot", "Show factory pot"]),
        Cmd(label="Register nearby factory (fallback)",
            say=["Register nearby factory", "Register factory"]),
    ],
    # Children intentionally omitted: Airframes/Weapons/Fuel content is
    # runtime-driven from factoryProduction and not safe to hard-code here.
)


# Top-level F10 registration order (menus.lua lines 604-617):
#   F1 Personal, F2 CSAR, F3 CTLD, F4 Salvage, F5 Interrogation, F6 Factory
# Diag (F7) is gated by VRS.config.diag.menuEnabled, excluded by default.
TOP_LEVEL = [PERSONAL_NODE, CSAR_NODE, CTLD_NODE, SALVAGE_NODE, INTERROGATION_NODE, FACTORY_NODE]


# --------------------------------------------------------------------------- #
# Spoken-phrase aliases                                                        #
# --------------------------------------------------------------------------- #
# Maps current VRS menu label -> ordered list of natural-speech aliases.
# Sourced from the user's prior XSAF profile ("VRS AI - XSAF-Profile.vap") with
# adjustments where the menu wording moved between XSAF and VRS. The label
# itself is NOT auto-included -- if you want the literal menu text recognised,
# put it first in the alias list (the rest are alternatives joined with `;`).
ALIASES: dict[str, list[str]] = {
    # ---- Personal -> General Info / top-level ------------------------------
    "Toggle Rescue Duty": [
        "Toggle Rescue Duty", "Rescue On Duty", "Rescue Off Duty", "Rescue Toggle",
        "See SAR On Duty", "See SAR Off Duty", "See SAR Toggle",
        "Sign up for SAR", "Sign up for SAL", "Unregister for All Work",
    ],
    "Show Airframe Lives": ["Show Airframe Lives", "Lives summary", "Airframe lives"],
    "Report a bug": ["Report a bug", "Submit bug report"],
    "Detailed Score": ["Detailed Score", "Show Score"],
    "Score Summary": ["Score Summary", "Score", "Brief Score"],
    "Whats my crosswind?": ["Crosswind", "Show Crosswind", "What's my crosswind"],
    "See active players": ["Active Players", "Players", "See active players"],
    "Show Standard Frequencies": ["Standard frequencies", "Show frequencies"],

    # ---- Personal -> Escorts -----------------------------------------------
    "F-16A (CAP): 300 Cr.": [
        "Request F-16", "Request Eff Sixteens", "Request Eff Sixteen Backup",
        "F-16 escort",
    ],
    "F-18C (CAP): 350 Cr.": [
        "Request F-18", "Request Eff Eighteens", "Request Eff Eighteen Backup",
        "F-18 escort",
    ],

    # ---- CSAR ---------------------------------------------------------------
    "List Active Pickups": ["List Rescues", "See SAR List", "List Active Pickups"],
    "Show Pickups on Map": ["Show Rescues on Map", "See SAR Map", "CSAR on map"],
    "Pick up nearby rescue": ["Pick up nearby rescue", "Pickup rescue"],
    "Check Onboard": [
        "Rescues onboard", "See SAR Onboard", "Who's in the back",
        "Check Onboard",
    ],
    "Offload Pickups": [
        "Offload Rescues", "See SAR Offload", "Out you get",
        "Offload Pickups",
    ],
    "Request Signal Flare (blue only)": [
        "Rescue Flare", "See SAR Flare", "Request signal flare", "Pop flare",
    ],
    "Request Smoke (blue only)": [
        "Rescue Smoke", "See SAR Smoke", "Request smoke", "Pop smoke",
    ],

    # ---- CTLD -- crate management ------------------------------------------
    "List boarded cargo": ["Cargo Status", "Troops Onboard", "Squad Onboard", "List boarded cargo"],
    "Inventory": ["Inventory", "Show inventory"],
    "Load nearby crates": ["Load Crate", "Load nearby crates"],
    "Drop loaded crates": ["Unload Crate", "Extract Crate", "Drop Crate", "Drop loaded crates"],
    "Build nearby crates": ["Unpack", "Unpack Crate", "Build nearby crates"],
    "Pack nearest unit": ["Pack Unit", "Pack Unit for Transport", "Pack nearest unit"],
    "Remove nearby crates": ["Destroy Crate", "Return Crate", "Remove nearby crates"],
    "List nearby crates": ["Nearby Crates", "List Crates", "List nearby crates"],

    # ---- CTLD -- troops -----------------------------------------------------
    "Drop all troops": ["Troops Unload", "Unload Troops", "Squad Unload", "Drop all troops"],
    "Extract nearby troops": ["Extract nearby troops", "Pick up troops"],
    "Load in: VRS unit (8)": ["Troops VRS", "VRS Troops", "VRS Squad", "VRS Soldier", "VRS Troop"],
    "Load in: VRS platoon (24)": ["Troops Platoon", "Platoon Troops", "Platoon Squad"],
    "Load in: VRS Anti-air (4)": ["Troops Anti-Air", "Anti-Air Troops", "Anti-Air Squad"],
    "Load in: VRS Anti-tank (4)": ["Troops Anti-Tank", "Anti-Tank Troops", "Anti-Tank Squad"],
    "Load in: VRS Mortar squad (4)": ["Troops Mortar", "Mortar Troops", "Mortar Boys", "Mortar Squad"],
    "Load in: VRS JTAC (1)": [
        "Troops JTAC", "JTAC Troops", "JTAC Squad",
        "Troops Jay Tack", "Jay Tack Troops", "Jay Tack Squad",
    ],
    "Load in: JTAC and guards (4)": [
        "Troops JTAC with Guards", "JTAC with Guards", "JTAC with Guards Squad",
        "Troops Jay Tack with Guards", "Jay Tack with Guards", "Jay Tack with Guards Squad",
    ],
    "Load in: VRS Engineers (4)": ["Troops Engineers", "Engineers", "Engineers Squad"],

    # ---- CTLD -- Support crates --------------------------------------------
    "Factory Crate (5)": ["Factory Crate"],
    "M1025 HMMV CP": ["Command Post Hummer Crate", "Command Post Hum-Vee Crate"],
    "M978 HEMTT tanker (4)": ["Tanker Crate", "HEMMIT Tanker Crate", "HEMTT Tanker Crate"],
    "M-818 Ammo Truck (2)": ["Ammo Crate", "Ammo Truck Crate"],
    "Repair crate": ["Repair Crate"],
    "Fat Cow crate": ["Fat Cow Crate"],
    "FOB crate large (2)": ["FOB Crate", "FOB Crate Large", "Large FOB Crate"],

    # ---- CTLD -- Artillery --------------------------------------------------
    "M109 (3)": ["Paladin Crate", "M-109 Crate", "M109 Crate"],
    "MLRS (4)": ["MLRS Crate", "M-270 Crate"],
    "Himars guided cluster (3)": ["Himars Cluster Crate", "High Mars Cluster Crate"],
    "Himars guided HE (3)": ["Himars HE Crate", "High Mars HE Crate"],
    "T155 Firtnia (3)": ["Firtina Crate", "T-155 Crate"],
    "SpGH Dana (3)": ["Dana Crate", "SPGH Crate"],

    # ---- CTLD -- Light Armor ------------------------------------------------
    "MATV": ["MATV Crate", "M-ATV Crate"],
    "ATGM M1045 HMMWV TOW": [
        "TOW Hummer", "TOW Hum-Vee", "TOW Hummer Crate", "TOW Hum-Vee Crate",
    ],
    "M2 Bradley (3)": ["Bradley Crate"],
    "M1130 Stryker CV (3)": ["Stryker ICV Crate", "Stryker CV Crate"],
    "M1134 Stryker ATGM (3)": ["Stryker ATGM Crate"],
    "M1128 Stryker MGS (3)": ["Stryker MGS Crate"],
    "Marder (2)": ["Marder Crate"],
    "MCV-80 Warrior (2)": ["Warrior Crate"],
    "LAV-25 (2)": ["L A V Crate", "LAV Crate", "LAV-25 Crate"],

    # ---- CTLD -- Heavy Armor ------------------------------------------------
    "Challenger (6)": ["Challenger Crate"],
    "Leopard (6)": ["Leopard Crate", "Leo Crate"],
    "M-1 Abrams (6)": ["Abrams Crate"],
    "Chieftain (6)": ["Chieftain Crate", "Chieftan Crate"],

    # ---- CTLD -- SAM IR/AAA -------------------------------------------------
    "AAA Vulcan M163 (2)": ["Vulcan Crate", "Vulkan Crate"],
    "Gepard (3)": ["Gepard Crate"],
    "SAM Chaparral M48 (2)": ["Chaparral Crate"],
    "SAM Avenger M1097 (2)": ["Avenger Crate"],
    "M6 Linebacker (3)": ["Linebacker Crate", "Line Backer Crate"],
    "LPWS C-ram (4)": ["C-RAM Crate", "C Ram Crate"],

    # ---- CTLD -- SAM SR/MR --------------------------------------------------
    "Roland ADS (3)": ["Roland Crate", "Roland ADS Crate"],
    "Roland EWR (2)": ["Roland Early Warning Crate", "Roland EWR Crate"],
    "Rapier launcher": ["Rapier Launcher Crate"],
    "Rapier blindfire TR": [
        "Rapier Radar Crate", "Rapier Track Radar Crate", "Rapier Blindfire Crate",
    ],
    "Rapier optical tracker": ["Rapier Tracker Crate", "Rapier Optical Tracker Crate"],
    "IRIS-T SLM command post": ["Iris T Command Post Crate", "Iris T CP Crate"],
    "IRIS-T SLM launcher": ["Iris T Launcher Crate"],
    "IRIS-T SLM SR/TR": ["Iris T Radar Crate", "Iris T SR Crate"],

    # ---- CTLD -- SAM LR (Patriot + NASAMS) ----------------------------------
    "Patriot SR/TR": [
        "Patriot Search Radar Crate", "Patriot Track Radar Crate", "Patriot Radar Crate",
    ],
    "Patriot ECS": ["Patriot ECS Crate"],
    "Patriot EPP": ["Patriot EPP Crate"],
    "Patriot CP": ["Patriot CP Crate", "Patriot Command Post Crate"],
    "Patriot AMG": ["Patriot AMG Crate"],
    "Patriot Launcher": ["Patriot Launcher Crate"],
    "NASAMS SR/TR": ["Nasams Radar Crate", "Nay Sams Radar Crate"],
    "NASAMS LauncherC": [
        "Nasams Launcher Crate", "Nay Sams Launcher Crate",
        "Nasams C Launcher Crate", "Nay Sams C Launcher Crate",
    ],
    "NASAMS CP": [
        "Nasams CP Crate", "Nay Sams CP Crate",
        "Nasams Command Post Crate", "Nay Sams Command Post Crate",
    ],
    "NASAMS LauncherB": [
        "Nasams B Launcher Crate", "Nay Sams B Launcher Crate",
    ],

    # ---- Salvage ------------------------------------------------------------
    "Pick up nearby (250 kg)":  ["Pick up salvage 250", "Salvage 250"],
    "Pick up nearby (500 kg)":  ["Pick up salvage 500", "Salvage 500"],
    "Pick up nearby (1000 kg)": ["Pick up salvage 1000", "Salvage 1000"],
    "Pick up nearby (All remaining)": [
        "Pick Up Salvage", "Pick up all salvage", "Salvage all",
    ],
    "Drop off": ["Drop Off Salvage", "Drop off salvage", "Deliver salvage"],
    "Emergency Jett!": ["Emergency Jettison Salvage", "Jettison salvage"],
    "List salvage jobs map wide": ["List Salvage", "Salvage jobs", "List salvage jobs"],
    "Show Salvage on Map": ["Salvage on Map", "Show salvage on map", "Salvage map"],

    # ---- Factory ------------------------------------------------------------
    "What does the pot look like?": [
        "What does the pot look like", "Factory pot", "Show factory pot",
    ],
    "Register nearby factory (fallback)": [
        "Register Factory", "Register nearby factory",
    ],

    # ---- Interrogation ------------------------------------------------------
    "Request status": ["Interrogation status", "Pow status", "Prisoner status"],
    "Request collected info": ["Collected intel", "Pow intel", "Prisoner intel"],
    "Initiate 'mind games'": ["Mind games"],
    "Initiate 'chat with knuckles'": ["Chat with knuckles"],
    "Initiate 'hydro-persuation'": ["Hydro persuasion", "Hydro persuation"],
    "Initiate 'oil planking'": ["Oil planking"],
}


# Raw single-key utilities -- handy for navigating menus when no named command
# fits (e.g. MOOSE auto-menus, mid-screen prompts). Lifted from the XSAF
# profile.
UTILITY_KEYS = {
    "Select F1":  [F_KEYS[1]],
    "Select F2":  [F_KEYS[2]],
    "Select F3":  [F_KEYS[3]],
    "Select F4":  [F_KEYS[4]],
    "Select F5":  [F_KEYS[5]],
    "Select F6":  [F_KEYS[6]],
    "Select F7":  [F_KEYS[7]],
    "Select F8":  [F_KEYS[8]],
    "Select F9":  [F_KEYS[9]],
    "Select F10": [F_KEYS[10]],
    "Select F11": [F11_KEY],
    "Select F12": [F12_KEY],
}


# --------------------------------------------------------------------------- #
# Tree walk -- yield (key_sequence, command, category_label) for every leaf    #
# --------------------------------------------------------------------------- #

def _registration_order(node: Node) -> list[tuple[str, object]]:
    """Return entries in DCS registration order ('child', Node) or ('cmd', Cmd)."""
    cmds = [("cmd", c if isinstance(c, Cmd) else Cmd(label=c)) for c in node.commands]
    children = [("child", c) for c in node.children]
    if node.order == "submenus_first":
        ordered = children + cmds
    else:
        ordered = cmds + children
    if len(ordered) > 10:
        raise ValueError(f"Submenu '{node.name}' has {len(ordered)} entries; DCS caps at 10. "
                         "Generator needs F11=Next pagination.")
    return ordered


def _walk(node: Node, prefix_keys: list[int], category: str) -> Iterable[tuple[list[int], Cmd, str]]:
    for slot, (kind, entry) in enumerate(_registration_order(node), start=1):
        keys = prefix_keys + [F_KEYS[slot]]
        if kind == "cmd":
            yield keys, entry, category
        else:
            yield from _walk(entry, keys, category)


def collect_commands() -> list[tuple[list[int], Cmd, str]]:
    base = [OPEN_KEY, OTHER_KEY]
    out: list[tuple[list[int], Cmd, str]] = []
    for slot, top in enumerate(TOP_LEVEL, start=1):
        keys = base + [F_KEYS[slot]]
        category = top.name
        out.extend(_walk(top, keys, category))
    return out


# --------------------------------------------------------------------------- #
# XML emission                                                                 #
# --------------------------------------------------------------------------- #

def _esc(s: str) -> str:
    return xml_utils.escape(s, {'"': "&quot;", "'": "&apos;"})


def _key_caption(keys: list[int]) -> str:
    names = [KEY_NAME[k] for k in keys]
    return "Press " + ", ".join(names) + " keys in sequence"


def render_action(key: int, ordinal: int) -> str:
    caption = f"Press {KEY_NAME[key]} key and hold for 0.1 seconds and release"
    return f"""        <CommandAction>
          <_caption>{_esc(caption)}</_caption>
          <PairingSet>false</PairingSet>
          <PairingSetElse>false</PairingSetElse>
          <Ordinal>{ordinal}</Ordinal>
          <ConditionMet xsi:nil="true" />
          <IndentLevel>0</IndentLevel>
          <ConditionSkip>false</ConditionSkip>
          <IsSuffixAction>false</IsSuffixAction>
          <DecimalTransient1>0</DecimalTransient1>
          <Caption>{_esc(caption)}</Caption>
          <Id>{uuid.uuid4()}</Id>
          <ActionType>PressKey</ActionType>
          <Duration>0.1</Duration>
          <Delay>0</Delay>
          <KeyCodes>
            <unsignedShort>{key}</unsignedShort>
          </KeyCodes>
          <Context />
          <X>0</X>
          <Y>0</Y>
          <Z>0</Z>
          <InputMode>0</InputMode>
          <ConditionPairing>0</ConditionPairing>
          <ConditionGroup>0</ConditionGroup>
          <ConditionStartOperator>0</ConditionStartOperator>
          <ConditionStartValue>0</ConditionStartValue>
          <ConditionStartValueType>0</ConditionStartValueType>
          <ConditionStartType>0</ConditionStartType>
          <DecimalContext1>0</DecimalContext1>
          <DecimalContext2>0</DecimalContext2>
          <DateContext1>0001-01-01T00:00:00</DateContext1>
          <DateContext2>0001-01-01T00:00:00</DateContext2>
          <Disabled>false</Disabled>
          <RandomSounds />
          <IntegerContext1>0</IntegerContext1>
          <IntegerContext2>0</IntegerContext2>
        </CommandAction>"""


def _spoken_phrase(cmd: Cmd) -> str:
    # ALIASES table wins -- it's the canonical voice-phrase source. Inline
    # `Cmd.say` is the fallback for entries not yet aliased. Last fallback
    # is the cleaned label.
    if cmd.label in ALIASES:
        phrases = ALIASES[cmd.label]
    elif cmd.say:
        phrases = cmd.say
    else:
        cleaned = cmd.label
        if cleaned.startswith("-- "):
            cleaned = cleaned[3:]
        phrases = [cleaned]
    return "; ".join(phrases)


def render_command(keys: list[int], cmd: Cmd, category: str) -> str:
    actions = "\n".join(render_action(k, i) for i, k in enumerate(keys))
    cmd_id = uuid.uuid4()
    base_id = uuid.uuid4()
    last_action_id = uuid.uuid4()
    phrase = _spoken_phrase(cmd)
    return f"""    <Command>
      <Referrer xsi:nil="true" />
      <ExecType>3</ExecType>
      <Confidence>0</Confidence>
      <PrefixActionCount>0</PrefixActionCount>
      <IsDynamicallyCreated>false</IsDynamicallyCreated>
      <TargetProcessSet>false</TargetProcessSet>
      <TargetProcessType>0</TargetProcessType>
      <TargetProcessLevel>0</TargetProcessLevel>
      <CompareType>0</CompareType>
      <ExecFromWildcard>false</ExecFromWildcard>
      <IsSubCommand>false</IsSubCommand>
      <IsOverride>false</IsOverride>
      <BaseId>{base_id}</BaseId>
      <OriginId>00000000-0000-0000-0000-000000000000</OriginId>
      <SessionEnabled>true</SessionEnabled>
      <DoubleTapInvoked>false</DoubleTapInvoked>
      <SingleTapDelayedInvoked>false</SingleTapDelayedInvoked>
      <LongTapInvoked>false</LongTapInvoked>
      <ShortTapDelayedInvoked>false</ShortTapDelayedInvoked>
      <SleepFlag>0</SleepFlag>
      <Id>{cmd_id}</Id>
      <CommandString>{_esc(phrase)}</CommandString>
      <ActionSequence>
{actions}
      </ActionSequence>
      <Async>true</Async>
      <Enabled>true</Enabled>
      <Category>{_esc(category)}</Category>
      <UseShortcut>false</UseShortcut>
      <keyValue>0</keyValue>
      <keyShift>0</keyShift>
      <keyAlt>0</keyAlt>
      <keyCtrl>0</keyCtrl>
      <keyWin>0</keyWin>
      <keyPassthru>true</keyPassthru>
      <UseSpokenPhrase>true</UseSpokenPhrase>
      <onlyKeyUp>false</onlyKeyUp>
      <RepeatNumber>2</RepeatNumber>
      <RepeatType>0</RepeatType>
      <CommandType>0</CommandType>
      <SourceProfile>00000000-0000-0000-0000-000000000000</SourceProfile>
      <UseConfidence>false</UseConfidence>
      <minimumConfidenceLevel>0</minimumConfidenceLevel>
      <UseJoystick>false</UseJoystick>
      <joystickNumber>0</joystickNumber>
      <joystickButton>0</joystickButton>
      <joystickNumber2>0</joystickNumber2>
      <joystickButton2>0</joystickButton2>
      <joystickUp>false</joystickUp>
      <KeepRepeating>false</KeepRepeating>
      <UseProcessOverride>false</UseProcessOverride>
      <ProcessOverrideActiveWindow>true</ProcessOverrideActiveWindow>
      <LostFocusStop>false</LostFocusStop>
      <PauseLostFocus>false</PauseLostFocus>
      <LostFocusBackCompat>true</LostFocusBackCompat>
      <UseMouse>false</UseMouse>
      <Mouse1>false</Mouse1>
      <Mouse2>false</Mouse2>
      <Mouse3>false</Mouse3>
      <Mouse4>false</Mouse4>
      <Mouse5>false</Mouse5>
      <Mouse6>false</Mouse6>
      <Mouse7>false</Mouse7>
      <Mouse8>false</Mouse8>
      <Mouse9>false</Mouse9>
      <MouseUpOnly>false</MouseUpOnly>
      <MousePassThru>true</MousePassThru>
      <joystickExclusive>false</joystickExclusive>
      <lastEditedAction>{last_action_id}</lastEditedAction>
      <UseProfileProcessOverride>false</UseProfileProcessOverride>
      <ProfileProcessOverrideActiveWindow>false</ProfileProcessOverrideActiveWindow>
      <RepeatIfKeysDown>false</RepeatIfKeysDown>
      <RepeatIfMouseDown>false</RepeatIfMouseDown>
      <RepeatIfJoystickDown>false</RepeatIfJoystickDown>
      <AH>0</AH>
      <CL>0</CL>
      <HasMB>false</HasMB>
      <UseVariableHotkey>false</UseVariableHotkey>
      <CLE>0</CLE>
      <EX1>false</EX1>
      <EX2>false</EX2>
      <InternalId xsi:nil="true" />
      <HasInput>true</HasInput>
      <HotkeyDoubleTapLevel>0</HotkeyDoubleTapLevel>
      <MouseDoubleTapLevel>0</MouseDoubleTapLevel>
      <JoystickDoubleTapLevel>0</JoystickDoubleTapLevel>
      <HotkeyLongTapLevel>0</HotkeyLongTapLevel>
      <MouseLongTapLevel>0</MouseLongTapLevel>
      <JoystickLongTapLevel>0</JoystickLongTapLevel>
      <AlwaysExec>false</AlwaysExec>
      <ResourceBalance>0</ResourceBalance>
      <PreventExec>false</PreventExec>
      <ExternalEventsEnabled>false</ExternalEventsEnabled>
      <ExcludeExecOnRecognized>false</ExcludeExecOnRecognized>
      <UseVariableMouseShortcut>false</UseVariableMouseShortcut>
      <UseVariableJoystickShortcut>false</UseVariableJoystickShortcut>
    </Command>"""


PROFILE_HEAD = f"""<?xml version="1.0" encoding="utf-8"?>
<Profile xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <HasMB>false</HasMB>
  <Id>{PROFILE_ID}</Id>
  <Name>{PROFILE_NAME}</Name>
  <Commands>
"""

PROFILE_TAIL = """  </Commands>
  <OverrideGlobal>false</OverrideGlobal>
  <GlobalHotkeyIndex>0</GlobalHotkeyIndex>
  <GlobalHotkeyEnabled>false</GlobalHotkeyEnabled>
  <GlobalHotkeyValue>0</GlobalHotkeyValue>
  <GlobalHotkeyShift>0</GlobalHotkeyShift>
  <GlobalHotkeyAlt>0</GlobalHotkeyAlt>
  <GlobalHotkeyCtrl>0</GlobalHotkeyCtrl>
  <GlobalHotkeyWin>0</GlobalHotkeyWin>
  <GlobalHotkeyPassThru>false</GlobalHotkeyPassThru>
  <OverrideMouse>false</OverrideMouse>
  <MouseIndex>0</MouseIndex>
  <OverrideStop>false</OverrideStop>
  <StopCommandHotkeyEnabled>false</StopCommandHotkeyEnabled>
  <StopCommandHotkeyValue>0</StopCommandHotkeyValue>
  <StopCommandHotkeyShift>0</StopCommandHotkeyShift>
  <StopCommandHotkeyAlt>0</StopCommandHotkeyAlt>
  <StopCommandHotkeyCtrl>0</StopCommandHotkeyCtrl>
  <StopCommandHotkeyWin>0</StopCommandHotkeyWin>
  <StopCommandHotkeyPassThru>false</StopCommandHotkeyPassThru>
  <DisableShortcuts>false</DisableShortcuts>
  <UseOverrideListening>false</UseOverrideListening>
  <OverrideJoystickGlobal>false</OverrideJoystickGlobal>
  <GlobalJoystickIndex>0</GlobalJoystickIndex>
  <GlobalJoystickButton>0</GlobalJoystickButton>
  <GlobalJoystickNumber>0</GlobalJoystickNumber>
  <GlobalJoystickButton2>0</GlobalJoystickButton2>
  <GlobalJoystickNumber2>0</GlobalJoystickNumber2>
  <ReferencedProfile xsi:nil="true" />
  <ExportVAVersion>2.1.5</ExportVAVersion>
  <ExportOSVersionMajor>10</ExportOSVersionMajor>
  <ExportOSVersionMinor>0</ExportOSVersionMinor>
  <OverrideConfidence>false</OverrideConfidence>
  <Confidence>0</Confidence>
  <CatchAllEnabled>false</CatchAllEnabled>
  <CatchAllId xsi:nil="true" />
  <InitializeCommandEnabled>false</InitializeCommandEnabled>
  <InitializeCommandId xsi:nil="true" />
  <UseProcessOverride>false</UseProcessOverride>
  <ProcessOverrideAciveWindow>true</ProcessOverrideAciveWindow>
  <DictationCommandEnabled>false</DictationCommandEnabled>
  <DictationCommandId xsi:nil="true" />
  <EnableProfileSwitch>false</EnableProfileSwitch>
  <CategoryGroups />
  <GroupCategory>false</GroupCategory>
  <LastEditedCommand>00000000-0000-0000-0000-000000000000</LastEditedCommand>
  <IS>0</IS>
  <IO>0</IO>
  <IP>0</IP>
  <BE>0</BE>
  <UnloadCommandEnabled>false</UnloadCommandEnabled>
  <UnloadCommandId xsi:nil="true" />
  <BlockExternal>false</BlockExternal>
  <AuthorID xsi:nil="true" />
  <ProductID xsi:nil="true" />
  <CR>0</CR>
  <InternalID xsi:nil="true" />
  <PR>0</PR>
  <CO>0</CO>
  <OP>0</OP>
  <CV>0</CV>
  <PD>0</PD>
  <PE>0</PE>
  <ExecOnRecognizedEnabled>false</ExecOnRecognizedEnabled>
  <ExecOnRecognizedId xsi:nil="true" />
  <ExecOnRecognizedRejected>false</ExecOnRecognizedRejected>
  <ExcludeGlobalProfiles>false</ExcludeGlobalProfiles>
  <DisableAdvancedTTS>false</DisableAdvancedTTS>
  <RPR>0</RPR>
  <Deleted>false</Deleted>
</Profile>
"""


def main() -> None:
    leaves = collect_commands()
    utility = [
        (keys, Cmd(label=phrase), "Utility")
        for phrase, keys in UTILITY_KEYS.items()
    ]
    all_leaves = leaves + utility
    commands_xml = "\n".join(render_command(k, c, cat) for k, c, cat in all_leaves)
    output = PROFILE_HEAD + commands_xml + "\n" + PROFILE_TAIL
    out_path = Path(__file__).with_name(OUTPUT_FILE)
    out_path.write_text(output, encoding="utf-8", newline="\r\n")

    # Summary
    print(f"Wrote {out_path} ({len(all_leaves)} commands)")
    by_cat: dict[str, int] = {}
    for _, _, cat in all_leaves:
        by_cat[cat] = by_cat.get(cat, 0) + 1
    for cat, n in by_cat.items():
        print(f"  {cat}: {n}")


if __name__ == "__main__":
    main()
