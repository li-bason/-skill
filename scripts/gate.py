#!/usr/bin/env python3
"""Run validation, regression, packaging, upload-status, and safety-scan gates."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

SKIP_PARTS = {"tasks", "sessions", "demo", "__pycache__", "dist", ".git"}
SUSPICIOUS = [
    re.compile(r"\brm\s+-rf\b", re.I),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
    re.compile(r"(api[_-]?key|secret|token)\s*[:=]\s*['\"][^'\"]+['\"]", re.I),
]


def files(skill: Path):
    for path in skill.rglob("*"):
        if path.is_file() and not any(part in SKIP_PARTS for part in path.relative_to(skill).parts):
            yield path


def frontmatter_name(skill_md: Path) -> str | None:
    if not skill_md.is_file():
        return None
    text = skill_md.read_text(encoding="utf-8")
    front = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not front:
        return None
    name = re.search(r"^name:\s*(.+)$", front.group(1), re.M)
    return name.group(1).strip() if name else None


def resolve_skill(candidate: Path) -> Path:
    """Resolve either a skill directory or a workspace containing one skill."""
    if (candidate / "SKILL.md").is_file():
        return candidate

    matches = sorted(
        path.parent
        for path in candidate.glob("*/SKILL.md")
        if path.is_file()
    )
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(f"未找到 SKILL.md：{candidate}")
    raise RuntimeError(f"发现多个 skill，请指定具体目录：{', '.join(str(path) for path in matches)}")


def validate(skill: Path) -> dict:
    errors = []
    skill_md = skill / "SKILL.md"
    if not skill_md.is_file():
        errors.append("缺少 SKILL.md")
    else:
        text = skill_md.read_text(encoding="utf-8")
        front = re.match(r"^---\n(.*?)\n---", text, re.S)
        if not front:
            errors.append("SKILL.md frontmatter 非法")
        else:
            name = frontmatter_name(skill_md)
            if not name:
                errors.append("缺少 name")
            elif not re.fullmatch(r"[a-z0-9-]+", name):
                errors.append("name 不是合法 kebab-case")
            if not re.search(r"^description:\s*", front.group(1), re.M):
                errors.append("缺少 description")
    required = [
        "templates/index.json", "references/review_lock_schema.md",
        "scripts/validate_contract.py", "scripts/validate_review.py",
        "scripts/validate_output_structure.py", "scripts/test_golden_structure.py",
        "workflows/final-exam.md", "workflows/contest-review.md",
    ]
    for relative in required:
        if not (skill / relative).is_file():
            errors.append(f"缺少必要资源：{relative}")
    return {"status": "passed" if not errors else "failed", "errors": errors}


def package(skill: Path, output_root: Path) -> dict:
    output_root.mkdir(parents=True, exist_ok=True)
    package_name = frontmatter_name(skill / "SKILL.md") or skill.name
    output = output_root / f"{package_name}.zip"
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files(skill):
            archive.write(path, (Path(package_name) / path.relative_to(skill)).as_posix())
    return {"status": "passed", "output": str(output), "bytes": output.stat().st_size}


def safety_scan(skill: Path) -> dict:
    findings = []
    for path in files(skill):
        if path.suffix.lower() not in {".md", ".py", ".yaml", ".yml", ".json", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in SUSPICIOUS:
            if pattern.search(text):
                findings.append({"file": str(path.relative_to(skill)), "pattern": pattern.pattern})
    return {"status": "passed" if not findings else "failed", "findings": findings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", nargs="?", default=".")
    args = parser.parse_args()
    candidate = Path(args.workspace).resolve()

    try:
        skill = resolve_skill(candidate)
    except (FileNotFoundError, RuntimeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    report = {
        "validate": validate(skill),
        "regression": {},
        "package": {},
        "upload": {
            "status": "not_run",
            "reason": "需要目标平台的上传接口或用户在平台执行上传；本地 gate 不伪造上传成功。",
        },
        "safety_scan": safety_scan(skill),
    }
    regression = subprocess.run(
        [sys.executable, str(skill / "scripts" / "test_golden_structure.py")],
        cwd=skill,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    report["regression"] = {
        "status": "passed" if regression.returncode == 0 else "failed",
        "output": regression.stdout.strip(),
        "error": regression.stderr.strip(),
    }
    try:
        report["package"] = package(skill, skill / "dist")
    except OSError as exc:
        report["package"] = {"status": "failed", "error": str(exc)}

    print(json.dumps(report, ensure_ascii=False, indent=2))
    required_gates = ("validate", "regression", "package", "safety_scan")
    return 0 if all(report[name].get("status") == "passed" for name in required_gates) else 1


if __name__ == "__main__":
    raise SystemExit(main())
