"""
Minimal, lossless parser/writer for SCS Software's plain-text SII format, as used by
ETS2/ATS save files (game.sii).

The format, confirmed against a real decrypted save (see docs/design-decisions.md):

    SiiNunit\r\n
    {\r\n
    <unit type> : <unit id> {\r\n
     <key>: <value>\r\n
     <key>: <value>\r\n
    }\r\n
    \r\n
    <unit type> : <unit id> {\r\n
     ...
    }\r\n
    \r\n
    }\r\n

Units are always a flat, top-level sequence (never nested inside each other) and
cross-reference each other by id string (e.g. `bank: _nameless.17b.5b3c.a458` inside the
`economy` unit points at the top-level unit with that id). Field lines carry a single
leading space and are not parsed further than key/raw-value splitting -- values (quoted
strings, hex-encoded floats like `&3dcccccd`, bare tokens, unit-id references, array
elements like `foo[0]`) are kept as opaque strings so editing one field can never corrupt
another we don't understand yet.

This module intentionally does not model per-key semantics (arrays, references, etc.) --
each `key[n]` is just its own independent (key, value) pair in document order, which is
enough to find and edit a specific field without needing to understand the whole schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class SiiParseError(ValueError):
    pass


@dataclass
class SiiUnit:
    type: str
    id: str
    fields: list[tuple[str, str]] = field(default_factory=list)

    def get(self, key: str) -> str | None:
        for k, v in self.fields:
            if k == key:
                return v
        return None

    def set(self, key: str, value: str) -> None:
        for i, (k, _v) in enumerate(self.fields):
            if k == key:
                self.fields[i] = (key, value)
                return
        raise KeyError(f"No existing field {key!r} on unit {self.type}:{self.id} "
                        "(this module only edits existing fields, not add new ones)")


@dataclass
class SiiFile:
    units: list[SiiUnit] = field(default_factory=list)

    def find(self, unit_id: str) -> SiiUnit | None:
        for u in self.units:
            if u.id == unit_id:
                return u
        return None

    def find_all(self, unit_type: str) -> list[SiiUnit]:
        return [u for u in self.units if u.type == unit_type]


def parse(text: str) -> SiiFile:
    lines = text.split("\n")
    lines = [ln[:-1] if ln.endswith("\r") else ln for ln in lines]

    if len(lines) < 3 or lines[0] != "SiiNunit" or lines[1] != "{":
        raise SiiParseError("Not a SiiNunit text file (bad header)")

    result = SiiFile()
    current: SiiUnit | None = None

    # lines[0:2] are the SiiNunit/{ header; the matching final "}" is handled implicitly
    # by finishing the loop with current is None.
    for lineno, raw in enumerate(lines[2:], start=3):
        if raw == "":
            continue
        if raw.startswith(" "):
            if current is None:
                raise SiiParseError(f"Line {lineno}: field line outside any unit: {raw!r}")
            key, sep, value = raw[1:].partition(": ")
            if not sep:
                raise SiiParseError(f"Line {lineno}: malformed field line: {raw!r}")
            current.fields.append((key, value))
            continue
        if raw == "}":
            if current is None:
                # closes the outer SiiNunit wrapper -- nothing meaningful should follow
                break
            result.units.append(current)
            current = None
            continue
        # unit-start line: "<type> : <id> {"
        head, sep, brace = raw.rpartition(" {")
        if not sep or brace != "":
            raise SiiParseError(f"Line {lineno}: expected unit start, got: {raw!r}")
        utype, sep, uid = head.partition(" : ")
        if not sep:
            raise SiiParseError(f"Line {lineno}: malformed unit header: {raw!r}")
        if current is not None:
            raise SiiParseError(f"Line {lineno}: nested unit start (not supported): {raw!r}")
        current = SiiUnit(type=utype, id=uid, fields=[])

    return result


def serialize(sii: SiiFile) -> str:
    out = ["SiiNunit", "{"]
    for unit in sii.units:
        out.append(f"{unit.type} : {unit.id} {{")
        for key, value in unit.fields:
            out.append(f" {key}: {value}")
        out.append("}")
        out.append("")
    out.append("}")
    return "\r\n".join(out) + "\r\n"
