import importlib.util
from pathlib import Path
from types import ModuleType


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_links", Path(__file__).with_name("check_links.py")
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_links = _load()

TRACKED = {"README.md", "docs/guide.md", "docs/assets/banner.png", "LICENSE"}


def test_finds_a_broken_relative_link() -> None:
    text = "See [the guide](docs/guide.md) and [the plan](docs/plan.md)."
    assert check_links.broken_links("README.md", text, TRACKED) == ["docs/plan.md"]


def test_resolves_links_from_the_file_folder() -> None:
    text = "[Up](../README.md) · ![banner](assets/banner.png) · [missing](../NOTICE.md)"
    assert check_links.broken_links("docs/guide.md", text, TRACKED) == ["../NOTICE.md"]


def test_ignores_external_links_anchors_and_mail() -> None:
    text = (
        "[site](https://example.com/x.md) [top](#install) [mail](mailto:a@b.c) "
        "<http://localhost:8765> [section](docs/guide.md#install)"
    )
    assert check_links.broken_links("README.md", text, TRACKED) == []


def test_a_file_that_exists_only_locally_is_broken() -> None:
    # Notes kept only on this machine are not in the repository: on GitHub the link is dead.
    assert check_links.broken_links("README.md", "[notes](NOTES.md)", TRACKED) == ["NOTES.md"]


def test_folders_count_when_they_hold_tracked_files() -> None:
    assert check_links.broken_links("README.md", "[docs](docs/) [art](docs/assets)", TRACKED) == []


def test_html_images_are_checked() -> None:
    text = '<img src="docs/assets/banner.png" alt=""> <img src="docs/assets/gone.gif">'
    assert check_links.broken_links("README.md", text, TRACKED) == ["docs/assets/gone.gif"]


def test_code_is_not_a_link() -> None:
    text = "```md\n[x](nowhere.md)\n```\nAnd `[y](also-nowhere.md)` inline."
    assert check_links.broken_links("README.md", text, TRACKED) == []


def test_the_repository_has_no_broken_links() -> None:
    assert check_links.repo_problems() == []


def test_a_leading_slash_starts_at_the_repository_root() -> None:
    text = "[root](/) [guide](/docs/guide.md) [gone](/docs/gone.md)"
    assert check_links.broken_links("docs/guide.md", text, TRACKED) == ["/docs/gone.md"]
