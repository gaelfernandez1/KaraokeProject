"""The repo-wide test policy in conftest.py: what the CI may skip, and the `models` marker."""

from pathlib import Path

import pytest

ROOT_CONFTEST = (Path(__file__).resolve().parents[1] / "conftest.py").read_text(encoding="utf-8")

SUITE = """
import pytest

def test_needs_ffmpeg(ffmpeg):
    pass

@pytest.mark.skipif(True, reason="needs a CUDA GPU")
def test_needs_a_gpu():
    pass

def test_needs_torch():
    # What pytest.importorskip("torch") says on a machine without the ml extra.
    pytest.skip("could not import 'torch': No module named 'torch'")
"""


@pytest.fixture
def suite(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> pytest.Pytester:
    pytester.makeconftest(ROOT_CONFTEST)
    pytester.makepyfile(test_suite=SUITE)
    # No ffmpeg on the PATH inside the inner run.
    monkeypatch.setenv("PATH", str(pytester.path))
    return pytester


def test_ci_refuses_ffmpeg_skips(suite: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KARAOKE_STRICT_SKIPS", "1")
    result = suite.runpytest_inprocess("-p", "no:cacheprovider")
    # Skips happen while setting the test up, so a refused one shows as an error.
    result.assert_outcomes(errors=1, skipped=2)
    result.stdout.fnmatch_lines(["*test_needs_ffmpeg*", "*must not be skipped*ffmpeg*"])


def test_gpu_and_missing_ml_libraries_may_skip_in_ci(
    suite: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KARAOKE_STRICT_SKIPS", "1")
    result = suite.runpytest_inprocess("-p", "no:cacheprovider", "-k", "not ffmpeg")
    result.assert_outcomes(skipped=2)


def test_skips_are_plain_skips_outside_the_ci(
    suite: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KARAOKE_STRICT_SKIPS", raising=False)
    result = suite.runpytest_inprocess("-p", "no:cacheprovider")
    result.assert_outcomes(skipped=3)


def test_model_tests_are_left_out_unless_asked_for(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(ROOT_CONFTEST)
    pytester.makepyfile(
        test_models="""
import pytest

@pytest.mark.models
def test_loads_a_model():
    pass

def test_plain():
    pass
"""
    )
    pytester.makeini('[pytest]\naddopts = -m "not models"\nmarkers =\n    models: real models\n')
    pytester.runpytest_inprocess("-p", "no:cacheprovider").assert_outcomes(passed=1, deselected=1)
    pytester.runpytest_inprocess("-p", "no:cacheprovider", "-m", "models").assert_outcomes(
        passed=1, deselected=1
    )
