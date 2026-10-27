import json
import os
import re
import tomllib
from pathlib import Path
from urllib.parse import unquote

LAB = Path(__file__).resolve().parents[1]
MARKDOWN = [p for p in LAB.rglob("*.md") if not {".venv", "out", "node_modules", ".pytest_cache"} & set(p.relative_to(LAB).parts)]


def exact_exists(path: Path) -> bool:
    absolute = Path(os.path.abspath(path))
    if not absolute.exists():
        return False
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        if part not in {child.name for child in current.iterdir()}:
            return False
        current /= part
    return True


def test_markdown_links_resolve_inside_the_lab():
    errors = []
    for path in MARKDOWN:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^(<<<<<<< |=======\s*$|>>>>>>> )", text, re.MULTILINE), path
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", re.sub(r"```.*?```", "", text, flags=re.DOTALL)):
            target = unquote(target.strip("<>").split("#", 1)[0])
            if not target or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            destination = (path.parent / target).resolve()
            if not destination.is_relative_to(LAB):
                errors.append(f"{path.relative_to(LAB)} escapes the lab: {target}")
            elif not exact_exists(destination):
                errors.append(f"{path.relative_to(LAB)} broken link: {target}")
    assert not errors, "\n".join(errors)


def test_screenshot_placeholders_are_named_and_unique():
    names = []
    for path in MARKDOWN:
        names += re.findall(r"Screenshot to add:\*\* `(images/[a-z0-9-]+\.png)`", path.read_text(encoding="utf-8"))
    assert len(names) >= 15
    assert len(names) == len(set(names)), "Each placeholder needs its own file name"


def test_only_the_simple_cast_remains():
    banned = re.compile(r"\b(Aster|Juniper|Linden|Moorland|Cedar|Northstar|Maya|Jordan|healthcare_intelligence|Cosmos)\b", re.I)
    offenders = [str(p.relative_to(LAB)) for p in LAB.rglob("*")
                 if p.is_file() and p.suffix in {".md", ".py", ".json", ".html", ".bicep", ".ps1", ".yaml", ".yml"}
                 and not {".venv", "out"} & set(p.relative_to(LAB).parts) and p.name != "test_content.py"
                 and banned.search(p.read_text(encoding="utf-8"))]
    assert not offenders, offenders


def test_readme_covers_every_part_of_the_case_overview():
    readme = (LAB / "README.md").read_text(encoding="utf-8")
    for phrase in [
        "Regulatory Web & Change Monitor", "Document & Citation Agent", "Obligation & Impact Extractor",
        "Regulatory Q&A Assistant", "Executive Briefing", "regulations", "guidance", "safety alerts",
        "enforcement letters", "coverage decisions", "pricing rules", "effective dates", "geographies",
        "clinical", "labelling", "manufacturing", "vigilance", "market access", "products", "studies",
        "submissions", "standard operating procedures", "quality records", "histories", "owners",
        "drafts emails", "change requests", "label updates", "by region and portfolio", "deadlines",
        "progress tracking", "approval", "audit", "events", "de-duplicate", "normalise", "metadata enrichment",
        "citation anchoring", "Regulatory affairs", "quality leadership", "pharmacovigilance", "post-market surveillance",
    ]:
        assert phrase.lower() in readme.lower(), phrase


def test_no_em_dashes_anywhere():
    offenders = [f"{p.relative_to(LAB)}:{n}" for p in LAB.rglob("*")
                 if p.is_file() and p.suffix in {".md", ".py", ".json", ".html", ".bicep", ".ps1", ".yaml", ".yml", ".toml", ".txt"}
                 and not {".venv", "out"} & set(p.relative_to(LAB).parts)
                 for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if "\u2014" in line]
    assert not offenders, offenders


def test_platform_automation_layout():
    assert {p.name for p in (LAB / "labautomation").iterdir()} == {"deploy-lab.ps1", "lab-defaults.json", "README.md"}
    defaults = json.loads((LAB / "labautomation" / "lab-defaults.json").read_text(encoding="utf-8"))
    assert defaults["deploymentType"] in {"resourcegroup", "subscription", "resourcegroup-with-subscriptionowner"}
    assert defaults["$schema"].endswith("/lab-defaults-schema.json")


def test_containers_and_dependencies_are_reproducible():
    project = tomllib.loads((LAB / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["dependencies"] == []
    assert project["tool"]["uv"]["index"][0]["url"] == "https://packagefeedproxy.microsoft.io/pypi/simple/"
    pins = (LAB / "orchestrator" / "requirements.txt").read_text(encoding="utf-8").split()
    assert pins == project["project"]["optional-dependencies"]["orchestrator"]
    local = json.loads((LAB / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8"))
    repository = json.loads((LAB / ".devcontainer" / "repository" / "devcontainer.json").read_text(encoding="utf-8"))
    assert "target=/workspaces/regulatory-intelligence," in local["workspaceMount"]
    assert repository["workspaceFolder"].endswith("/03-Azure/01-04-AI/11_Healthcare_Regulatory_Intelligence")
    for key in ("features", "postCreateCommand", "waitFor", "forwardPorts", "portsAttributes", "customizations", "remoteUser"):
        assert repository[key] == local[key], key
    assert local["postCreateCommand"] == "uv sync --frozen --all-extras && uv run --frozen --all-extras pytest -q"
    assert all(port["visibility"] == "private" for port in local["portsAttributes"].values())
    assert "out/" in (LAB / ".gitignore").read_text(encoding="utf-8").splitlines()
