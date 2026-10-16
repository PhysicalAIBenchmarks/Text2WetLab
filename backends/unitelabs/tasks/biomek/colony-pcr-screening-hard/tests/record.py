"""What the runner reports besides the robot's actions: the deck, the comments and the protocol's commands.

The actions themselves (pick, drop, aspirate, dispense, mix, one event per channel or nozzle, with the physical tip)
come from the SDK's lineage stream (lineage_events.py); this module describes the deck those events refer to, in
eval/runlog.py's terms. Labware is "<identifier> on <position>", with the position in the device's own terms
(Device.position), and every labware on the deck is listed, whether or not the protocol pipetted from it, with its
geometry (SDK base class, rows x columns, well volume) so the checks can tell a 96-well plate from a 384-well one by
shape, not name. `entities()` maps the SDK's entity ids for wells, compartments and tubes to those names.
"""
import asyncio
import contextlib

from unitelabs.labware import Container, Plate, Spot, Tip, TipRack, Trough, Tube, TubeRack, parse_number
from unitelabs.labware.carriers import Carrier, CarrierSite
from unitelabs.labware.resource import Labware
from unitelabs.liquid_handling.modules import Pipette    # channels are Pipettes; head nozzles are TipSpots


def _walk(resource):
    yield resource
    for child in getattr(resource, "children", None) or []:
        if child is not None:
            yield from _walk(child)


FAMILIES = ((Plate, "plate"), (Trough, "trough"), (TubeRack, "tube_rack"), (Tube, "tube"), (TipRack, "tip_rack"))


def geometry(labware) -> dict:
    """What the labware is, from the SDK rather than its class name: base class family, how many separate wells
    (liquid containers) it has, and their distinct volumes in µL. A trough's rows x columns are access points for the
    channels, not wells, so the well count is what tells a single-well reservoir from a plate."""
    cls = labware.__class__
    family = next((name for base, name in FAMILIES if issubclass(cls, base)), "other")
    containers = {}
    if family != "tip_rack":
        for res in _walk(labware):
            c = getattr(res, "container", None)
            if isinstance(c, Container):
                containers[id(c)] = c
    volumes = set()
    for c in containers.values():
        with contextlib.suppress(Exception):
            volumes.add(float(parse_number(c.max_volume)))
    return {"class": cls.__name__, "family": family, "wells": len(containers), "volumes": sorted(volumes)}


COMMANDS = ("aspirate", "dispense", "mix", "transfer", "pick_up_tips", "pick_up_tips_from", "put_down_tips",
            "put_down_tips_to", "discard_tips", "drop_tips", "empty_tips")
# A crude time model for comparing protocols, not a prediction: seconds per top-level command.
COMMAND_SECONDS = {"aspirate": 5, "dispense": 5, "mix": 8, "transfer": 12}
TIP_SECONDS = 6


class Recorder:
    def __init__(self, lh, device) -> None:
        self.lh, self.device = lh, device
        self.labware: dict[str, str] = {}
        self.geometry: dict[str, dict] = {}
        self.comments: list[str] = []
        self._patched: list[tuple[object, str, object]] = []
        self.commands: dict[str, int] = {}
        self._depth = 0

    # -- what the protocol touched --------------------------------------------------------------------------------

    def _is_deck(self, obj) -> bool:
        return obj is not None and obj.__class__ is self.lh.deck.__class__ and obj.identifier == self.lh.deck.identifier

    def _site_of(self, resource):
        """(labware, holder) for the thing placed on the deck that holds `resource`: the holder is a carrier site
        (Hamilton, Tecan), the deck itself (Bravo, Biomek), or a carrier's own spot (a tube in a sample carrier).
        Parent links are weakref proxies, so types are read from `__class__`, never with isinstance."""
        node = resource
        while node is not None:
            parent = getattr(node, "parent", None)
            if parent is None:
                return None, None
            if issubclass(node.__class__, Labware):
                if issubclass(parent.__class__, CarrierSite) or self._is_deck(parent):
                    return node, parent
                if issubclass(parent.__class__, Spot) and not issubclass(parent.__class__, Pipette):
                    grand = getattr(parent, "parent", None)
                    if grand is not None and issubclass(grand.__class__, Carrier) \
                            and self._is_deck(getattr(grand, "parent", None)):
                        return node, parent          # a tube in a sample carrier's own spot (not a rack on the deck)
            node = parent
        return None, None

    def _position(self, labware, holder) -> str:
        if issubclass(holder.__class__, CarrierSite) or self._is_deck(holder):
            return self.device.position(self.lh, labware, holder)
        carrier = holder.parent                   # a tube spot on a carrier
        track = min(self.lh.deck.get_tracks_for_carrier(carrier))
        return f"{track}.{holder.identifier.rsplit(':', 1)[1]}"

    def _labware_name(self, resource) -> tuple[str, str]:
        labware, holder = self._site_of(resource)
        if labware is None:
            raise RuntimeError(f"{resource!r} is not on the deck")
        name = f"{labware.identifier} on {self._position(labware, holder)}"
        self.labware[name] = labware.__class__.__name__
        self.geometry.setdefault(name, geometry(labware))
        try:
            label = getattr(resource, "label", None)      # Tube.label raises outside a rack
        except Exception:  # noqa: BLE001
            label = None
        return name, label or "A1"

    # -- commands (efficiency) ------------------------------------------------------------------------------------

    def _patch(self, obj, name, fn) -> None:
        self._patched.append((obj, name, getattr(obj, name)))
        setattr(obj, name, fn)

    def install(self) -> None:
        """Count the protocol's pipetting commands (efficiency); the actions come from the lineage stream."""
        for attr in self.device.pipetting:
            module = getattr(self.lh, attr, None)
            for name in COMMANDS:
                fn = getattr(module, name, None)
                if module is not None and asyncio.iscoroutinefunction(fn):
                    self._patch(module, name, self._counted(name, fn))

    def _counted(self, name: str, fn):
        """Count the protocol's own pipetting commands, not the ones a command issues internally."""
        rec = self

        async def counted(*args, **kwargs):
            if rec._depth == 0:
                rec.commands[name] = rec.commands.get(name, 0) + 1
            rec._depth += 1
            try:
                return await fn(*args, **kwargs)
            finally:
                rec._depth -= 1
        return counted

    def efficiency(self, events: list[dict]) -> dict:
        tips = len({e["tip"] for e in events if e["kind"] == "pick" and e.get("tip")})
        tip_moves = sum(n for c, n in self.commands.items() if "tip" in c)
        seconds = sum(COMMAND_SECONDS.get(c, 0) * n for c, n in self.commands.items()) + TIP_SECONDS * tip_moves
        return {"commands": dict(sorted(self.commands.items())), "tips_used": tips, "est_seconds": seconds}

    def uninstall(self) -> None:
        for obj, name, original in reversed(self._patched):
            setattr(obj, name, original)
        self._patched.clear()

    # -- deck ---------------------------------------------------------------------------------------------------

    def comment(self, text: str) -> None:
        self.comments.append(str(text))

    def deck_labware(self) -> None:
        """Every labware on a carrier/deck site, like eval/runlog.py lists every loaded labware."""
        for res in _walk(self.lh.deck):
            parent = getattr(res, "parent", None)
            if issubclass(res.__class__, Labware) and parent is not None \
                    and (issubclass(parent.__class__, CarrierSite) or self._is_deck(parent)):
                with contextlib.suppress(Exception):
                    name = f"{res.identifier} on {self._position(res, parent)}"
                    self.labware[name] = res.__class__.__name__
                    self.geometry[name] = geometry(res)

    def entities(self) -> dict[str, list[str]]:
        """Every well, trough compartment and tube on the deck, by the identifier the SDK's lineage events name it
        with, -> [labware name, well label] as the events here name them (see lineage_events.py)."""
        out = {}
        for res in _walk(self.lh.deck):
            if isinstance(getattr(res, "container", None), Container) and not isinstance(res, Tip):
                with contextlib.suppress(Exception):          # not on a carrier site or the deck: never pipetted
                    out[res.identifier] = list(self._labware_name(res))
        return out

    def result(self, events: list[dict]) -> dict:
        self.deck_labware()
        return {"ok": True, "events": events, "labware": self.labware, "geometry": self.geometry,
                "comments": self.comments, "efficiency": self.efficiency(events)}
