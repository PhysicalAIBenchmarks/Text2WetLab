"""The grader modules import each other from their own folder, as they do vendored into a task's tests/."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ul"))
