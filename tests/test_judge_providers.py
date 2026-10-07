"""The judge runs on ANTHROPIC_API_KEY, or on OPENROUTER_API_KEY (same Claude model via OpenRouter) when that is the only
key. No network: this only checks which endpoint, auth header and model name each grader would use."""
import importlib.util
import pathlib
import tomllib

import pytest

ROOT = pathlib.Path(__file__).parent.parent
TASKS = sorted(p for p in (ROOT / "tasks").iterdir() if (p / "task.toml").exists())
JUDGES = sorted(ROOT.glob("tasks/*/tests/judge_layer.py")) + sorted(ROOT.glob("tasks/opentrons-rna-extraction*/tests/grade.py"))


def load(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(f"judge_{path.parent.parent.name}_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    import sys
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(path.parent))
    return mod


@pytest.fixture
def keys(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "JUDGE_MODEL"):
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


@pytest.mark.parametrize("path", JUDGES, ids=lambda p: p.parent.parent.name)
def test_anthropic_key_wins(path, keys):
    pytest.importorskip("anthropic")
    keys.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    keys.setenv("OPENROUTER_API_KEY", "sk-or-test")
    client, model, provider = load(path).judge_client()
    assert (provider, model) == ("anthropic", "claude-sonnet-5-5")
    assert "api.anthropic.com" in str(client.base_url)


@pytest.mark.parametrize("path", JUDGES, ids=lambda p: p.parent.parent.name)
def test_openrouter_key_alone_uses_openrouter(path, keys):
    pytest.importorskip("anthropic")
    keys.setenv("ANTHROPIC_API_KEY", "")            # what Harbor passes for "${ANTHROPIC_API_KEY:-}" when unset
    keys.setenv("OPENROUTER_API_KEY", "sk-or-test")
    client, model, provider = load(path).judge_client()
    assert (provider, model) == ("openrouter", "anthropic/claude-sonnet-5.5")
    assert str(client.base_url).rstrip("/") == "https://openrouter.ai/api"
    assert client.auth_headers.get("Authorization") == "Bearer sk-or-test"


@pytest.mark.parametrize("path", JUDGES, ids=lambda p: p.parent.parent.name)
def test_no_key_is_a_judge_error_not_a_crash(path, keys):
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        load(path).judge_client()


@pytest.mark.parametrize("task", TASKS, ids=lambda p: p.name)
def test_either_key_reaches_the_sandbox(task):
    meta = tomllib.loads((task / "task.toml").read_text())
    env = meta["verifier"]["env"]
    assert env["ANTHROPIC_API_KEY"] == "${ANTHROPIC_API_KEY:-}" and env["OPENROUTER_API_KEY"] == "${OPENROUTER_API_KEY:-}"
    assert "openrouter.ai" in meta["environment"]["allowed_hosts"]
