"""The lint gate: every reference passes it, and the ways out of the sandbox it exists to close are refused."""
import pathlib

import pytest
import gate

ROOT = pathlib.Path(__file__).resolve().parent.parent
REFERENCES = sorted((ROOT / "references").glob("*/*.py"))
HEAD = "import asyncio\n\nasync def run(star, comment):\n"


@pytest.mark.parametrize("ref", REFERENCES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_references_pass(ref):
    assert gate.violations(ref.read_text()) == []


@pytest.mark.parametrize("body", [
    "    await asyncio.sleep(0.1)\n",
    "    await asyncio.gather(asyncio.sleep(0), asyncio.sleep(0))\n",
    "    async with asyncio.timeout(5):\n        pass\n",
])
def test_scheduling_is_allowed(body):
    assert gate.violations(HEAD + body) == []


@pytest.mark.parametrize("code", [
    HEAD + "    p = await asyncio.create_subprocess_shell('(sleep 20; echo 1 > /lo' + 'gs/verifier/reward.json) &')\n",
    HEAD + "    await asyncio.create_subprocess_exec('sh', '-c', 'true')\n",
    HEAD + "    await asyncio.open_connection('example.com', 80)\n",
    HEAD + "    await asyncio.start_server(None, '0.0.0.0', 8000)\n",
    HEAD + "    await asyncio.get_running_loop().subprocess_shell(None, 'true')\n",
    HEAD + "    await asyncio.to_thread(print, 1)\n",
    HEAD + "    a = asyncio\n    await a.create_subprocess_shell('true')\n",
    "import asyncio as aio\n\nasync def run(star, comment):\n    await aio.create_subprocess_shell('true')\n",
    "from asyncio import create_subprocess_shell\n\nasync def run(star, comment):\n    await create_subprocess_shell('true')\n",
    "import asyncio.subprocess\n\nasync def run(star, comment):\n    pass\n",
    "from asyncio.subprocess import create_subprocess_exec\n\nasync def run(star, comment):\n    pass\n",
    HEAD + "    loop = star.loop\n    await loop.run_in_executor(None, print)\n",
])
def test_process_and_network_doors_are_refused(code):
    assert gate.violations(code), code


@pytest.mark.parametrize("code", [
    "from unitelabs.sdk import Audit, Operation\n\nasync def run(star, comment):\n"
    "    Audit.emit('star', Operation.DISPENSE, {'entity_id': 'channel:0'}, {'entity_id': 'plate:A1'},"
    " extras={'channel': 0, 'volume_ul': 50.0})\n",
    "import unitelabs.sdk\n\nasync def run(star, comment):\n    unitelabs.sdk.get_context().state['events'].clear()\n",
    "import unitelabs\n\nasync def run(star, comment):\n    unitelabs.sdk.Audit.emit\n",
    "from unitelabs.sdk.automate.context import get_context\n\nasync def run(star, comment):\n"
    "    get_context().state['events'].pop()\n",
    "from unitelabs.liquid_handling import lineage\n\nasync def run(star, comment):\n"
    "    with lineage.disable():\n        await star.pipettes.aspirate()\n",
    "import unitelabs.liquid_handling.lineage as rec\n\nasync def run(star, comment):\n    rec.disable()\n",
    "from unitelabs.liquid_handling.lineage import disable\n\nasync def run(star, comment):\n    disable()\n",
    "from unitelabs.liquid_handling.modules.parameters.liquid_handling import lineage\n\n"
    "async def run(star, comment):\n    lineage.disable()\n",
    "import unitelabs.liquid_handling as lh\n\nasync def run(star, comment):\n    lh.lineage.disable()\n",
    "from unitelabs.liquid_handling.lineage import Audit\n\nasync def run(star, comment):\n    Audit.emit\n",
    HEAD + "    star.pipettes.lineage\n",
    "import os\nimport asyncio\n\nasync def run(star, comment):\n    os.environ['UNITELABS_LIQUID_HANDLING_LINEAGE'] = '0'\n",
    "from unitelabs.labware import events\n\nasync def run(star, comment):\n    with events.muted():\n        pass\n",
    "from unitelabs.labware.events import muted\n\nasync def run(star, comment):\n    muted()\n",
    "import unitelabs.labware.events as ev\n\nasync def run(star, comment):\n    ev.notify\n",
    "import unitelabs.labware as lw\n\nasync def run(star, comment):\n    lw.events.muted()\n",
    "from unitelabs.labware.liquids.container import events\n\nasync def run(star, comment):\n    events.notify\n",
])
def test_the_run_record_is_out_of_reach(code):
    """The grader reads the robot's actions from the SDK's lineage stream; a protocol must not forge events into it,
    drop them, or switch the recording off."""
    assert gate.violations(code), code


def test_a_local_named_events_is_allowed():
    assert not gate.violations(HEAD + "    events = []\n    events.append(1)\n")


def test_mock_import_is_refused():
    code = "from unitelabs.liquid_handling.testing import MicrolabSTARMock\n\nasync def run(star, comment):\n    pass\n"
    assert gate.violations(code)


def test_oversized_protocol_is_refused():
    code = HEAD + "    pass\n" + "# padding\n" * (gate.MAX_PROTOCOL_BYTES // 10 + 1)
    assert any("byte limit" in v for v in gate.violations(code))
