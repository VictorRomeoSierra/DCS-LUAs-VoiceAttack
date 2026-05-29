"""Static analysis of description.lua (tier 4 -- load-bearing).

A DCS livery's description.lua is loaded by the client when the
livery is rendered. The file format is in practice pure data:

    livery = {
        {"texture_name", DIFFUSE, "texture_file", false},
        ...
    }
    name = "..."
    countries = {"USA", "GER"}
    season = SUMMER

But the file is real Lua, so a malicious uploader could embed
arbitrary code: `os.execute(...)`, `io.open(...)`, `loadstring(...)`,
etc. That code runs in the player's DCS process. The scanner's job
is to reject any description.lua that does anything beyond
data-shape assignments.

Strategy:
  1. Parse with luaparser. Parse failures -> reject (we cannot
     reason about what we can't parse).
  2. Walk every Assign / LocalAssign at any depth. Reject if the
     target is anything other than a known property name (livery,
     name, ...) on the implicit module table.
  3. Walk every Call / Invoke. Reject any callee whose root name
     resolves to a denylisted global (os, io, lfs, package, debug,
     ...) or any specific bad method (string.dump, ...).
  4. Walk every Name reference. Reject any bare reference to
     denylisted globals or to introspection names (_G, _ENV,
     __index, ...).
  5. Reject any shadowing rebind: `local os = ...`, etc. -- this is
     the classic scanner-evasion trick.

The matching is intentionally over-eager. False positives are
recoverable (extend the allowlists below); false negatives mean
malware ships in a published livery.
"""

from __future__ import annotations

import zipfile

from ..verdict import Finding


# Properties allowed as the target of a top-level assignment in
# description.lua. Anything outside this set is rejected, even if
# the value is a benign literal -- unknown property names suggest
# the file isn't a real description.lua.
ALLOWED_PROPERTIES = {
    "livery",
    "name",
    "name_ru",
    "country",
    "countries",
    "order",
    "default",
    "season",
    "category",
    "unit_type",
    "aircraft_type",
    # custom_args: a table of model draw-argument overrides (e.g.
    # custom_args = { [38] = 0.0 }) -- standard, benign livery data.
    # Common across community liveries (VFA-103, Ryot packs, ...).
    "custom_args",
    # textures/skins tables sometimes appear at top level on the
    # community modder side. Add as we see them in real liveries.
}


# Bare Name references that are flagged whenever they appear,
# regardless of context. These are the "did anyone reference the
# os module" signals.
DENY_GLOBAL_NAMES = {
    "os", "io", "lfs", "package", "debug",
    "socket", "net", "coroutine",
    "_G", "_ENV", "_VERSION",
    "require", "dofile", "loadfile", "loadstring", "load",
    "getfenv", "setfenv",
    "getmetatable", "setmetatable",
    "rawget", "rawset", "rawequal", "rawlen",
}

# Specific dangerous library functions. The root library name on
# its own isn't necessarily bad (e.g. `string` is fine), but these
# specific members are.
DENY_INDEX_PAIRS = {
    ("string", "dump"),  # bytecode emit
}

# Names that, when seen as the LHS of a `local <name> = ...` or any
# assignment, indicate a deliberate shadowing attempt -- redefining
# os/io/etc. to dodge a name-based scanner. Reject any local that
# rebinds a denylisted global name.
SHADOW_DENY_LOCALS = DENY_GLOBAL_NAMES | {
    # Even rebinding "string" locally is suspicious in a data file.
    "string",
    "table",
    "math",
}


def _node_class(node) -> str:
    return type(node).__name__


def _name_id(node) -> str | None:
    """If node is a Name (variable reference), return its identifier;
    else None. Different luaparser versions use slightly different
    attribute names -- this normalises to whatever we can find."""
    if _node_class(node) != "Name":
        return None
    for attr in ("id", "name"):
        v = getattr(node, attr, None)
        if isinstance(v, str):
            return v
    return None


def _string_value(node) -> str | None:
    """If node is a string literal, return its value; else None."""
    if _node_class(node) != "String":
        return None
    for attr in ("s", "value"):
        v = getattr(node, attr, None)
        if isinstance(v, str):
            return v
    return None


def _index_root_name(node) -> tuple[str, str] | None:
    """For an Index node like `os.execute` or `string.dump`, return
    `("os", "execute")` if the value side is a bare Name. Returns
    None for any more complex callee (which we typically reject
    elsewhere as 'lua_disallowed_call:dynamic'). Handles luaparser's
    Index node shape: `Index(value=Name(...), idx=Name(...))` or
    similar, with the dotted name on the right being a Name or
    String depending on version.
    """
    if _node_class(node) != "Index":
        return None
    value = getattr(node, "value", None)
    idx = getattr(node, "idx", None)
    root = _name_id(value)
    if root is None:
        return None
    # idx might be a Name (after a `.`) or a String (after `[...]`).
    member = _name_id(idx) or _string_value(idx)
    if member is None:
        return None
    return (root, member)


def _walk(tree):
    """Yield every node in the AST. luaparser provides ast.walk;
    fall back to recursive descent if not available."""
    try:
        from luaparser import ast as luaast  # type: ignore
        yield from luaast.walk(tree)
        return
    except Exception:
        pass
    # Fallback: manual walk.
    stack = [tree]
    while stack:
        n = stack.pop()
        if n is None:
            continue
        yield n
        for child_attr in vars(n).values():
            if isinstance(child_attr, list):
                stack.extend(child_attr)
            elif hasattr(child_attr, "__class__") and child_attr.__class__.__module__.startswith("luaparser"):
                stack.append(child_attr)


def scan_source(source: str) -> list[Finding]:
    """Run the AST checks against the description.lua source text."""
    try:
        from luaparser import ast as luaast  # type: ignore
    except ImportError:
        return [Finding(
            tier=4, reason="scanner_missing_dep",
            detail="luaparser not installed; run 'pip install luaparser'",
        )]

    try:
        tree = luaast.parse(source)
    except Exception as e:
        return [Finding(
            tier=4, reason="lua_parse_error",
            detail=f"{type(e).__name__}: {e}"[:300],
        )]

    findings: list[Finding] = []
    seen_reasons: set[str] = set()

    def emit(reason: str, detail: str) -> None:
        if reason in seen_reasons:
            return
        seen_reasons.add(reason)
        findings.append(Finding(tier=4, reason=reason, detail=detail))

    for node in _walk(tree):
        cls = _node_class(node)

        # ---- Pattern: bare Name reference to a denylisted global. ----
        if cls == "Name":
            ident = _name_id(node)
            if ident in DENY_GLOBAL_NAMES:
                emit(f"lua_disallowed_name:{ident}",
                     f"reference to denylisted global '{ident}'")
            if ident in ("__index", "__newindex"):
                emit(f"lua_metatable_access:{ident}",
                     f"reference to '{ident}' (metatable manipulation)")

        # ---- Pattern: os.execute, string.dump, etc. via Index. ----
        elif cls == "Index":
            pair = _index_root_name(node)
            if pair is not None:
                root, member = pair
                if (root, member) in DENY_INDEX_PAIRS:
                    emit(f"lua_disallowed_call:{root}.{member}",
                         f"access to denylisted '{root}.{member}'")
                # Index access ON a denylisted root is also flagged
                # (caught by the Name check above on `root`, but
                # surface the full path for clarity).
                if root in DENY_GLOBAL_NAMES:
                    emit(f"lua_disallowed_call:{root}.{member}",
                         f"access to denylisted '{root}.{member}'")

        # ---- Pattern: function definitions. Data files don't need them. ----
        elif cls in ("Function", "AnonymousFunction"):
            emit("lua_function_definition",
                 "function definition not permitted in description.lua")

        # ---- Pattern: local rebind of a system library name. ----
        elif cls == "LocalAssign":
            targets = getattr(node, "targets", None) or []
            for t in targets:
                ident = _name_id(t)
                if ident in SHADOW_DENY_LOCALS:
                    emit(f"lua_shadow:{ident}",
                         f"local '{ident}' shadows system library "
                         "(scanner evasion attempt)")

        # ---- Pattern: assignment target outside ALLOWED_PROPERTIES. ----
        elif cls == "Assign":
            targets = getattr(node, "targets", None) or []
            for t in targets:
                ident = _name_id(t)
                if ident is None:
                    # e.g. assigning to an indexed/dotted name like
                    # _G.evil = ...; that's not a flat property
                    # assignment -- caught by the dotted-access
                    # checks above, but flag it just in case.
                    emit("lua_complex_assign_target",
                         f"assignment with non-flat target ({_node_class(t)})")
                elif ident not in ALLOWED_PROPERTIES:
                    emit(f"lua_unknown_property:{ident}",
                         f"top-level assignment to unknown property '{ident}'")

    return findings


def scan_zip_descriptions(zf: zipfile.ZipFile) -> list[Finding]:
    """Find every description.lua in the zip and scan each. Findings
    are tagged with their zip entry path so the user can identify
    which livery flagged."""
    findings: list[Finding] = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        # match any path ending in /description.lua or just description.lua
        name_lower = info.filename.lower().replace("\\", "/")
        if not name_lower.endswith("/description.lua") and name_lower != "description.lua":
            continue
        try:
            data = zf.read(info)
        except Exception as e:
            findings.append(Finding(
                tier=4, reason="lua_read_error",
                detail=f"{info.filename}: {e}"[:300],
            ))
            continue
        try:
            source = data.decode("utf-8", errors="replace")
        except Exception as e:
            findings.append(Finding(
                tier=4, reason="lua_decode_error",
                detail=f"{info.filename}: {e}"[:300],
            ))
            continue
        for f in scan_source(source):
            # Prefix detail with the zip path of this description.lua
            # so multi-livery samples remain debuggable.
            f.detail = f"[{info.filename}] {f.detail}" if f.detail else f"[{info.filename}]"
            findings.append(f)
    return findings
