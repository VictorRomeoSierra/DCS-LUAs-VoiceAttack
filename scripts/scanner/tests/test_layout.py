"""Layout resolver tests.

The resolver has to cope with every shape a livery upload arrives in.
These cases mirror the real backlog the pipeline had to drain:

  - Death Dealers : <wrapper>/Liveries/FA-18C_hornet/<slug>/  (OvGME)
  - Ryot 2024     : Liveries/Mi-24P/... + Liveries/mi-8mt/...  (multi, junk)
  - VFA-103       : bare <slug>/  inferred from texture names
  - UH-60L Latvian: bare <slug>/  inferred from the folder name

plus the reject paths (ambiguous, unresolved, mixed, unknown folder).
"""

from __future__ import annotations

import zipfile

from scripts.scanner import layout

_LUA = b"livery = {\n}\n"


def _resolve(tmp_path, name, files, extra=None):
    zp = tmp_path / name
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as zf:
        for n, d in files.items():
            zf.writestr(n, d)
    with zipfile.ZipFile(zp, "r") as zf:
        return layout.resolve(zf, extra_signals=extra or [])


# ----- structural shapes ---------------------------------------------


def test_ovgme_wrapper_liveries(tmp_path):
    """Wrapper folder != aircraft; the Liveries/<X>/ component wins."""
    r = _resolve(tmp_path, "death-dealers.zip", {
        "Death Dealers - Chaos/Liveries/FA-18C_hornet/Chaos 1/description.lua": _LUA,
        "Death Dealers - Chaos/Liveries/FA-18C_hornet/Chaos 1/F18C_1_DIFF.dds": b"DDS\0",
    })
    assert not r.findings
    assert r.aircraft == ["FA-18C_hornet"]
    assert len(r.liveries) == 1
    lv = r.liveries[0]
    assert (lv.aircraft, lv.dest_folder, lv.slug, lv.method) == (
        "FA-18C_hornet", "FA-18C_hornet", "Chaos 1", "structural_liveries")
    assert lv.zip_prefix == "Death Dealers - Chaos/Liveries/FA-18C_hornet/Chaos 1/"


def test_liveries_root_multi_aircraft_with_junk(tmp_path):
    """Liveries/ at root, two aircraft, lowercase folder, junk file."""
    r = _resolve(tmp_path, "ryot.zip", {
        "Liveries/Mi-24P/Loco/description.lua": _LUA,
        "Liveries/Mi-24P/Loco/tex.dds": b"DDS\0",
        "Liveries/mi-8mt/ShortBus/description.lua": _LUA,
        "ReadMe.txt": b"hi\n",
    })
    assert not r.findings
    assert r.aircraft == ["Mi-24P", "Mi-8MT"]
    dests = sorted((l.aircraft, l.dest_folder, l.slug) for l in r.liveries)
    assert dests == [
        ("Mi-24P", "Mi-24P", "Loco"),
        ("Mi-8MT", "Mi-8MT", "ShortBus"),   # mi-8mt -> canonical Mi-8MT
    ]


def test_aircraft_folder_shape(tmp_path):
    """<Aircraft>/<slug>/ -- the classic single-livery upload."""
    r = _resolve(tmp_path, "single.zip", {
        "FA-18C_hornet/VRS-001/description.lua": _LUA,
        "FA-18C_hornet/VRS-001/tex.dds": b"DDS\0",
    })
    assert not r.findings
    assert r.aircraft == ["FA-18C_hornet"]
    assert r.liveries[0].method == "structural_folder"


def test_cockpit_folder_routes_to_cockpit_dest(tmp_path):
    r = _resolve(tmp_path, "cockpit.zip", {
        "Liveries/Cockpit_Mi-24P/Pit-A/description.lua": _LUA,
    })
    assert not r.findings
    lv = r.liveries[0]
    assert lv.aircraft == "Mi-24P"
    assert lv.dest_folder == "Cockpit_Mi-24P"


def test_dedup_multiple_files_one_slug(tmp_path):
    r = _resolve(tmp_path, "dup.zip", {
        "A-10C_2/Skin-1/description.lua": _LUA,
        "A-10C_2/Skin-1/a.dds": b"DDS\0",
        "A-10C_2/Skin-1/b.dds": b"DDS\0",
    })
    assert not r.findings
    assert len(r.liveries) == 1


# ----- bare uploads: inference ---------------------------------------


def test_bare_infer_from_texture_name(tmp_path):
    """VFA-103: folder name has no aircraft, but textures say f18c."""
    r = _resolve(tmp_path, "vfa103.zip", {
        "_VFA-103 Jolly Rogers - CAG/description.lua":
            b'livery = {\n  {"F18C_1", 0 ,"F18C_1_DIFF",true};\n}\n',
        "_VFA-103 Jolly Rogers - CAG/F18C_1_DIFF.dds": b"DDS\0",
    })
    assert not r.findings, [f.reason for f in r.findings]
    assert r.aircraft == ["FA-18C_hornet"]
    assert r.liveries[0].method == "inferred"


def test_bare_infer_from_folder_name(tmp_path):
    """UH-60L: textures are BH_* (no UH-60 token); folder name saves it."""
    r = _resolve(tmp_path, "uh60l.zip", {
        "UH_60L_Latvian_Air_Force_105/description.lua":
            b'livery = {\n  {"BH_Base", 0 ,"BH_Base_LAT",true};\n}\n',
        "UH_60L_Latvian_Air_Force_105/BH_Base_LAT.dds": b"DDS\0",
    })
    assert not r.findings, [f.reason for f in r.findings]
    assert r.aircraft == ["UH-60L"]


def test_bare_infer_from_original_filename(tmp_path):
    """No internal signal; the original upload filename carries it."""
    r = _resolve(tmp_path, "blob.zip", {
        "Latvian-105/description.lua":
            b'livery = {\n  {"BH_Base", 0 ,"BH_Base_LAT",true};\n}\n',
        "Latvian-105/BH_Base_LAT.dds": b"DDS\0",
    }, extra=["UH_60L_Latvian_Air_Force.zip"])
    assert not r.findings, [f.reason for f in r.findings]
    assert r.aircraft == ["UH-60L"]


def test_bare_unresolved_goes_to_staff(tmp_path):
    r = _resolve(tmp_path, "mystery.zip", {
        "Mystery Skin/description.lua": _LUA,
        "Mystery Skin/diffuse.dds": b"DDS\0",
    })
    assert r.liveries == []
    assert any(f.reason == "layout_unresolved_aircraft" for f in r.findings)


def test_bare_ambiguous_goes_to_staff(tmp_path):
    r = _resolve(tmp_path, "ambig.zip", {
        "Combo/description.lua": b"-- hornet and tomcat textures\n",
        "Combo/x.dds": b"DDS\0",
    })
    assert r.liveries == []
    assert any(f.reason == "layout_ambiguous_aircraft" for f in r.findings)


# ----- hard rejects --------------------------------------------------


def test_mixed_shapes_reject(tmp_path):
    r = _resolve(tmp_path, "mixed.zip", {
        "Liveries/FA-18C_hornet/A/description.lua": _LUA,
        "BareSlug-f18c/description.lua": _LUA,
    })
    assert r.liveries == []
    assert any(f.reason == "layout_mixed_shapes" for f in r.findings)


def test_unknown_aircraft_folder_reject(tmp_path):
    r = _resolve(tmp_path, "unknown.zip", {
        "Liveries/F-22A_Raptor/A/description.lua": _LUA,
    })
    assert any(
        f.reason.startswith("layout_unknown_aircraft_folder")
        for f in r.findings
    )


def test_no_liveries_reject(tmp_path):
    r = _resolve(tmp_path, "empty.zip", {
        "readme.txt": b"no liveries here\n",
    })
    assert r.liveries == []
    assert any(f.reason == "layout_no_liveries" for f in r.findings)


# ----- datamine recognition (new airframes) --------------------------


def test_recognized_new_airframe_shape_d(tmp_path):
    """C-130J-30 isn't hosted, but it's a real DCS type (datamine), so a
    shape-D upload resolves and can be bootstrapped."""
    r = _resolve(tmp_path, "c130.zip", {
        "C-130J-30/C-130J Spirit Airlines/description.lua": _LUA,
        "C-130J-30/C-130J Spirit Airlines/C-130J_ext_01.dds": b"DDS\0",
    })
    assert not r.findings, [f.reason for f in r.findings]
    assert r.aircraft == ["C-130J-30"]
    lv = r.liveries[0]
    assert (lv.aircraft, lv.dest_folder, lv.method) == (
        "C-130J-30", "C-130J-30", "structural_folder")


def test_recognized_new_airframe_liveries_wrapper(tmp_path):
    r = _resolve(tmp_path, "c130w.zip", {
        "Pack/Liveries/C-130J-30/Spirit/description.lua": _LUA,
    })
    assert not r.findings
    assert r.aircraft == ["C-130J-30"]
    assert r.liveries[0].method == "structural_liveries"


def test_alias_routes_datamine_name_to_hosted(tmp_path):
    """Upload under the DCS type name CH-47Fbl1 routes to the hosted
    CH-47F pack instead of bootstrapping a duplicate."""
    r = _resolve(tmp_path, "chinook.zip", {
        "Liveries/CH-47Fbl1/Desert/description.lua": _LUA,
    })
    assert not r.findings
    assert r.aircraft == ["CH-47F"]
    assert r.liveries[0].dest_folder == "CH-47F"


def test_unrecognized_wrapper_still_rejects(tmp_path):
    """A non-aircraft wrapper folder must not be mistaken for an airframe;
    falls to inference, which finds nothing -> reject."""
    r = _resolve(tmp_path, "wrap.zip", {
        "Random Skin Pack/Cool Skin/description.lua": _LUA,
        "Random Skin Pack/Cool Skin/tex.dds": b"DDS\0",
    })
    assert r.liveries == []
    assert any(f.reason == "layout_unresolved_aircraft" for f in r.findings)
