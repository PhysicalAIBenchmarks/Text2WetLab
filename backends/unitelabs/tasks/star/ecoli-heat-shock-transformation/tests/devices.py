"""The liquid handlers of the UniteLabs SDK, as the benchmark sees them: one profile per device.

A profile is plain data and duck-typed helpers, so brief.py and make_tasks.py can use it on a machine without the
SDK; only runner.py imports the SDK (it builds the mock from `mock` by name). The task is the same on every device;
the profile only says how to ready the mock, which modules the benchmark takes away, and how to name a deck position.
"""
import dataclasses


def _track_site(lh, labware, site) -> str:
    """Hamilton and Tecan decks: carriers on tracks, labware on carrier sites -> "<first track>.<site index>"."""
    carrier = site.parent
    track = min(lh.deck.get_tracks_for_carrier(carrier))
    return f"{track}.{site.identifier.rsplit(':', 1)[1]}"


def _bravo(lh, labware, holder) -> str:
    """Labware sits on a deck location (1-9), directly or on a platepad there: the location of the nearest ancestor
    the deck knows. Parent links are weakref proxies, so the deck matches by identifier."""
    node = labware
    while node is not None:
        location = lh.deck.get_location_number(node)
        if location is not None:
            return str(location)
        node = getattr(node, "parent", None)
    raise RuntimeError(f"{labware.identifier!r} is not on a Bravo deck location")


def _biomek(lh, labware, holder) -> str:
    """Labware sits directly on the deck; the deck knows the named position (P1, TL1, ...) of each labware."""
    position = lh.deck.get_position_for_labware(labware)
    if position is None:
        raise RuntimeError(f"{labware.identifier!r} is not on a Biomek deck position")
    return position


@dataclasses.dataclass(frozen=True)
class Device:
    key: str                      # task folder and runner argument
    name: str                     # as the brief and the judge name it
    var: str                      # the protocol's parameter name in the contract: `run(star, comment)`
    mock: str                     # unitelabs.liquid_handling.testing class
    setup: str                    # how runner.py readies the mock: "initialize" or "configure-initialize-activate"
    pipetting: tuple[str, ...]    # module attributes that pipette (for naming channels/nozzles in events)
    disabled: tuple[str, ...]     # module attributes the benchmark takes away (their pipetting/transfer methods raise)
    position: object              # (lh, labware, holder) -> the deck position string in the device's own terms
    config_note: str = ""         # anything the brief must say about configuration the harness did

    def instrument(self, module_attr: str, index: int) -> str:
        return f"{'channel' if module_attr == 'pipettes' else 'nozzle'}_{index}"


DEVICES = {d.key: d for d in [
    Device(key="star", name="Hamilton Microlab STAR", var="star", mock="MicrolabSTARMock", setup="initialize",
           pipetting=("pipettes",), disabled=("core96", "iswap", "core_gripper", "autoload"), position=_track_site),
    Device(key="vantage", name="Hamilton Vantage", var="vantage", mock="VantageMock", setup="initialize",
           pipetting=("pipettes",), disabled=("pipettes_xl", "idl", "ipg", "core_gripper"), position=_track_site),
    Device(key="bravo", name="Agilent Bravo", var="bravo", mock="BravoMock", setup="configure-initialize-activate",
           pipetting=("pipette_head",), disabled=("gripper",), position=_bravo),
    Device(key="biomek", name="Beckman Biomek i-Series", var="biomek", mock="BiomekMock", setup="configure-initialize",
           pipetting=("pipette_head",), disabled=("gripper",), position=_biomek,
           config_note="The deck positions are already configured (plate positions P1.., tip positions TL1.., waste TR1)."),
    Device(key="evo", name="Tecan Freedom EVO", var="evo", mock="TecanFreedomEvoMock", setup="configure-initialize-activate",
           pipetting=("mca", "pipette_head"), disabled=("roma", "gripper"), position=_track_site,
           config_note="`mca_discard_location` is already configured, so `discard_tips()` works."),
]}
