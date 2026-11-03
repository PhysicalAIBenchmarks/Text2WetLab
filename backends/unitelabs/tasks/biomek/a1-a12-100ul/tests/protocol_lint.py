"""Static check on a protocol file before the grader runs it. A protocol is plain Opentrons API code and needs very
little of Python, so anything that could touch the harness is refused instead of detected afterwards.

    violations(source) -> list[str]        empty means the file may be simulated

Why static: the protocol runs in the same process as the code that reports what it did. Without this, a protocol
could print a forged result and exit, patch the log parser, read the grader's files, or write the answer key.
This is a filter, not a sandbox; the real isolation is that Harbor copies the grader in only after the agent has
finished, and the container has no network except the model API.
"""
import ast

ALLOWED_IMPORTS = {"opentrons", "math", "typing", "itertools", "string", "collections", "functools", "dataclasses", "__future__"}
BANNED_NAMES = {"open", "exec", "eval", "compile", "globals", "locals", "vars", "getattr", "setattr", "delattr", "hasattr",
                "__import__", "SystemExit", "KeyboardInterrupt", "BaseException", "input", "breakpoint", "exit", "quit", "type", "memoryview", "help", "dir"}
BANNED_ATTRS = {"os", "sys", "subprocess", "builtins", "importlib", "system", "popen", "modules", "environ", "stdout", "stderr",
                "stdin", "write", "writelines", "exit", "environ", "getenv", "open", "read_text", "write_text", "unlink", "remove"}


FLOW_RATE_FIELDS = {"aspirate", "dispense", "blow_out"}
# Settable properties of a pipette (InstrumentContext) in the Opentrons API docs: ordinary protocol code, not patching.
PIPETTE_SETTINGS = {"tip_racks", "starting_tip", "default_speed"}
CLEARANCE_FIELDS = {"aspirate", "dispense"}


def _is_flow_rate(t: ast.Attribute) -> bool:
    """A documented pipette setting on a local variable: p.flow_rate.aspirate/dispense/blow_out,
    p.well_bottom_clearance.aspirate/dispense, p.tip_racks, p.starting_tip, p.default_speed. Assigning to anything else,
    or to these on a module or class (protocol_api.InstrumentContext.tip_racks = ...), is still refused."""
    if isinstance(t.value, ast.Name):
        return t.attr in PIPETTE_SETTINGS
    return (isinstance(t.value, ast.Attribute) and isinstance(t.value.value, ast.Name)
            and ((t.value.attr == "flow_rate" and t.attr in FLOW_RATE_FIELDS)
                 or (t.value.attr == "well_bottom_clearance" and t.attr in CLEARANCE_FIELDS)))


def violations(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [f"syntax error: {e.msg} (line {e.lineno})"]
    out = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", 0) or getattr(getattr(node, "context_expr", None), "lineno", 0)
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in ALLOWED_IMPORTS:
                    out.append(f"line {line}: import {a.name}")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_IMPORTS or node.level:
                out.append(f"line {line}: from {node.module} import ...")
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            out.append(f"line {line}: name {node.id}")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_") or node.attr in BANNED_ATTRS:
                out.append(f"line {line}: attribute .{node.attr}")
        elif isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Delete, ast.For, ast.withitem)):
            targets = (node.targets if isinstance(node, (ast.Assign, ast.Delete))
                       else [node.optional_vars] if isinstance(node, ast.withitem) else [node.target])
            attrs = [a for t in targets if t is not None for a in ast.walk(t) if isinstance(a, ast.Attribute) and not isinstance(a.ctx, ast.Load)]
            if any(not (isinstance(node, ast.Assign) and _is_flow_rate(a)) for a in attrs):
                out.append(f"line {line}: assignment to an attribute")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and any(
                s in node.value for s in ("/tests", "/logs", "/solution")):
            out.append(f"line {line}: path to the grader in a string")
    return sorted(set(out))
