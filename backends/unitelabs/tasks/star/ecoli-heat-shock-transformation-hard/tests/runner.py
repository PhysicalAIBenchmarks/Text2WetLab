"""Run a protocol headless on the simulated liquid handler of any device in the UniteLabs SDK and report what the
robot did, in the shape eval/spec_check.check() reads: the SDK's own lineage stream (captured with
`unitelabs.sdk.Audit.capture()`, turned into run-log events by lineage_events.py) and the deck (record.py).

    python runner.py <device> protocol.py result.json        device: star | vantage | bravo | biomek | evo

A protocol is a file with `async def run(lh, comment)`: `lh` is the initialized device (the mock, but the protocol
should not care) with an empty deck; `comment(text)` records a step that cannot be simulated. Modules the benchmark
takes away (Device.disabled) raise on use.

The result is {"ok", "events", "labware", "geometry", "comments", "efficiency", "lineage_errors", "lineage_audit"}
or {"ok": False, "error", "traceback"}: `lineage_errors` are the stream's "error" events (channels that failed),
`lineage_audit` its "audit" events (a container's volume corrected outside a robot action, e.g. liquid the protocol
removed through the liquid model).
"""
import asyncio
import importlib.util
import json
import os
import pathlib
import sys
import traceback
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lineage_events  # noqa: E402
from devices import DEVICES  # noqa: E402
from record import Recorder  # noqa: E402


TAKEN_AWAY = ("aspirate", "dispense", "mix", "pick_up_tips", "pick_up_tips_from", "pick_up_tips_from_anywhere",
              "transfer", "transfer_from", "pick_up", "pick_up_from", "put_down", "put_down_to", "load", "unload")


def disable(lh, attr: str) -> None:
    """Take a module away from the protocol: its pipetting and transfer methods raise. The object itself stays,
    because other modules consult it (the STAR channels check the CoRe gripper when they activate)."""
    module = getattr(lh, attr, None)
    if module is None:
        return

    def refused(*_args, **_kwargs):
        raise RuntimeError(f"the {attr} module is not available in this benchmark")

    async def refused_async(*_args, **_kwargs):
        refused()

    for name in TAKEN_AWAY:
        fn = getattr(module, name, None)
        if callable(fn):
            setattr(module, name, refused_async if asyncio.iscoroutinefunction(fn) else refused)


async def make_device(device):
    """The mock, readied the way its docs say, with the benchmark's configuration where the device needs one."""
    import unitelabs.liquid_handling.testing as testing

    if device.key == "evo":
        from unitelabs.labware import Vector
        from unitelabs.liquid_handling.tecan import TecanFreedomEvoConfiguration
        lh = testing.TecanFreedomEvoMock(configuration=TecanFreedomEvoConfiguration(
            model="EVO150", mca_discard_location=Vector(x=1000, y=100, z=100)))
    else:
        lh = getattr(testing, device.mock)()
    for step in device.setup.split("-"):
        await getattr(lh, step)()
    for attr in device.disabled:
        disable(lh, attr)
    return lh


async def execute(device_key: str, path: str, raw: bool = False) -> dict:
    """Run the protocol; `raw` also returns the lineage stream, the entity map and the comment positions."""
    device = DEVICES[device_key]
    spec = importlib.util.spec_from_file_location("protocol", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["protocol"] = module          # dataclasses resolve annotations through sys.modules[cls.__module__]
    spec.loader.exec_module(module)
    if not asyncio.iscoroutinefunction(getattr(module, "run", None)):
        raise TypeError(f"the protocol must define `async def run({device.var}, comment)`")
    from unitelabs.sdk import Audit, get_context

    os.environ["UNITELABS_LIQUID_HANDLING_LINEAGE"] = "1"     # the SDK's lineage recording, whatever the caller set
    lh = await make_device(device)
    rec = Recorder(lh, device)
    comments: list[tuple[int, str]] = []
    rec.install()
    try:
        with Audit.capture() as ctx:
            def comment(text) -> None:
                comments.append((len(ctx.state.get("events", [])), str(text)))
                rec.comment(text)

            await module.run(lh, comment)
            if get_context() is not ctx:          # the protocol's actions went to a context of its own
                raise RuntimeError("the protocol replaced the run context the robot's actions are recorded in")
    finally:
        rec.uninstall()
    lineage = [{k: e[k] for k in ("type", "operation", "inputs", "outputs", "extras") if k in e}
               for e in ctx.state.get("events", [])]
    asked = {k: n for k, n in rec.commands.items() if k in ("aspirate", "dispense", "mix", "transfer")}
    if asked and not any(e.get("operation") in ("aspirate", "dispense") for e in lineage):
        raise RuntimeError(f"the protocol pipetted ({asked}) but the SDK recorded no aspirate or dispense")
    entities = rec.entities()
    events, errors = lineage_events.to_events(lineage, entities, comments)
    audit = [e for e in lineage if e.get("type") == "audit"]
    result = rec.result(events) | {"lineage_errors": errors, "lineage_audit": audit}
    if raw:
        result |= {"lineage": lineage, "lineage_comments": comments, "entities": entities}
    return result



def main(device_key: str, path: str, raw: bool = False) -> dict:
    warnings.simplefilter("ignore")           # the liquid model warns on every over-volume request; the checks judge those
    try:
        return asyncio.run(execute(device_key, path, raw))
    except BaseException as exc:  # noqa: BLE001 - every failure of the protocol is a result, not a crash
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[-3000:], "traceback": traceback.format_exc()[-4000:]}


if __name__ == "__main__":
    out = json.dumps(main(sys.argv[1], sys.argv[2]))
    with open(sys.argv[3], "w") as handle:     # a file, not stdout: the protocol can print
        handle.write(out)
