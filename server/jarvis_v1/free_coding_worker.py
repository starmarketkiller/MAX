"""Bounded LocalTaskHandler for free/local conversational coding.

The handler never selects or invokes a model. Orchestrator._run_local owns the
Ollama call, retry and escalation. This class only builds a compact prompt,
validates the structured proposal, tests it in an isolated workspace, and
returns a proposal artifact for the existing approval gate.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

SERVER = Path(__file__).resolve().parents[1]
ORCH = SERVER / "orchestrator_v1"
if str(ORCH) not in sys.path:
    sys.path.insert(0, str(ORCH))

from core.orchestrator import ApplyResult, LocalTaskHandler, VerifyResult
from path_resolver import resolve_project_root

MAX_CHANGED_FILES = 4
MAX_TOTAL_BYTES = 80_000
MAX_TEST_COMMANDS = 2
COMMAND_TIMEOUT_SECONDS = 120


def _json_object(text: str) -> dict:
    value = (text or "").strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
        value = re.sub(r"\s*```$", "", value)
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("worker output must be a JSON object")
    return parsed


def _safe_relative(path: str) -> str:
    normalized = str(PurePosixPath(str(path).replace("\\", "/")))
    candidate = PurePosixPath(normalized)
    if candidate.is_absolute() or ".." in candidate.parts or normalized in ("", "."):
        raise ValueError("path outside task workspace")
    return normalized


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) or
               (pattern.endswith("/**") and path.startswith(pattern[:-3].rstrip("/") + "/"))
               for pattern in patterns)


class FreeCodingWorkerHandler(LocalTaskHandler):
    def __init__(self, *, project_root=None, workspace_root=None, command_runner=None):
        self.project_root = Path(project_root or resolve_project_root(__file__)).resolve()
        self.workspace_root = Path(workspace_root or
                                   self.project_root / ".nexus" / "coding_workspaces").resolve()
        self.command_runner = command_runner or subprocess.run

    def build_prompt(self, task_record) -> str:
        manifest = task_record["manifest"]
        plan = (task_record.get("action_params") or {}).get("execution_plan") or {}
        allowed = list(manifest.get("files_allowed") or [])
        context = []
        for pattern in allowed:
            if any(char in pattern for char in "*?["):
                continue
            try:
                relative = _safe_relative(pattern)
                full = (self.project_root / relative).resolve()
                if full.is_file() and self.project_root in full.parents and not full.is_symlink():
                    context.append({"path": relative,
                                    "content": full.read_text(encoding="utf-8")[:20_000]})
            except (OSError, UnicodeDecodeError, ValueError):
                continue
        contract = {
            "objective": manifest["objective"], "intent": plan.get("intent"),
            "allowed_paths": allowed, "forbidden_paths": manifest.get("files_forbidden", []),
            "max_changed_files": MAX_CHANGED_FILES, "max_total_bytes": MAX_TOTAL_BYTES,
            "files": context,
            "output_contract": {"summary": "string", "changes": [{"path": "repo-relative",
                                                                       "content": "full file"}]},
        }
        return ("Return JSON only. Propose the smallest correct patch. Do not select a provider, "
                "run commands, push, deploy, or access paths outside allowed_paths.\n" +
                json.dumps(contract, ensure_ascii=False))

    def _validate_changes(self, task_record, parsed: dict) -> list[dict]:
        if set(parsed) != {"summary", "changes"}:
            raise ValueError("worker output may contain only summary and changes")
        changes = parsed.get("changes")
        if not isinstance(parsed.get("summary"), str) or not parsed["summary"].strip():
            raise ValueError("summary missing")
        if not isinstance(changes, list) or not 1 <= len(changes) <= MAX_CHANGED_FILES:
            raise ValueError("changes count outside bounded policy")
        manifest = task_record["manifest"]
        allowed = list(manifest.get("files_allowed") or [])
        forbidden = list(manifest.get("files_forbidden") or [])
        if not allowed:
            raise ValueError("files_allowed is empty; coding execution is fail-closed")
        clean, total = [], 0
        for item in changes:
            if not isinstance(item, dict) or set(item) != {"path", "content"}:
                raise ValueError("each change requires only path and content")
            path = _safe_relative(item["path"])
            content = item["content"]
            if not isinstance(content, str):
                raise ValueError("file content must be text")
            if not _matches(path, allowed) or _matches(path, forbidden):
                raise PermissionError(f"path not allowed: {path}")
            source = (self.project_root / path).resolve()
            if source.exists() and source.is_symlink():
                raise PermissionError(f"symlink target denied: {path}")
            if self.project_root not in source.parents:
                raise PermissionError(f"path escaped repository: {path}")
            total += len(content.encode("utf-8"))
            clean.append({"path": path, "content": content})
        if total > MAX_TOTAL_BYTES:
            raise ValueError("patch exceeds byte limit")
        return clean

    @staticmethod
    def _trusted_test_commands(task_record, changed_paths: list[str]) -> list[list[str]]:
        configured = (task_record.get("action_params") or {}).get("test_commands") or []
        if not configured:
            python_files = [path for path in changed_paths if path.endswith(".py")]
            # A changed file that is itself an allowlisted test target IS the
            # verifier - run it for real with pytest, not just py_compile.
            # py_compile only proves the file parses; it would pass a test
            # with a wrong import or a call with the wrong number of
            # arguments, since neither is a syntax error (reproduced live:
            # NEXUS TASK_6FEA7BDE04D2, rejected by human review for exactly
            # this - py_compile alone is not sufficient).
            test_files = [path for path in python_files
                         if _matches(path, ["server/tests/**", "scripts/tests/**"])]
            if test_files:
                return [["PYTHON", "-m", "pytest", *test_files, "-q"]]
            return [["PYTHON", "-m", "py_compile", *python_files]] if python_files else []
        if not isinstance(configured, list) or len(configured) > MAX_TEST_COMMANDS:
            raise ValueError("test command count outside policy")
        commands = []
        allowed_flags = {"-q", "-x", "--disable-warnings", "--maxfail=1"}
        for command in configured:
            if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
                raise ValueError("test commands must be argv arrays")
            if len(command) < 4 or command[0] != "PYTHON" or command[1:3] != ["-m", "pytest"]:
                raise PermissionError("only PYTHON -m pytest is allowlisted")
            if any(part in {";", "&&", "||", "|"} for part in command):
                raise PermissionError("shell operators are forbidden")
            targets = []
            for argument in command[3:]:
                if argument.startswith("-"):
                    if argument not in allowed_flags:
                        raise PermissionError(f"pytest flag not allowlisted: {argument}")
                    continue
                target = _safe_relative(argument.split("::", 1)[0])
                if not (_matches(target, ["server/tests/**", "scripts/tests/**"]) or
                        (target.startswith("frontend/src/") and
                         (".test." in target or ".spec." in target))):
                    raise PermissionError(f"pytest target not allowlisted: {target}")
                targets.append(target)
            if not targets:
                raise PermissionError("pytest command requires an allowlisted test target")
            commands.append(command)
        return commands

    def _prepare_workspace(self, task_id: str) -> Path:
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        target = self.workspace_root / task_id
        if target.exists():
            shutil.rmtree(target)
        ignored = shutil.ignore_patterns(".git", "node_modules", ".pytest_cache", "__pycache__",
                                         ".nexus", "runtime_state", "*.pyc")
        shutil.copytree(self.project_root, target, ignore=ignored)
        return target

    def verify(self, task_record, response_text) -> VerifyResult:
        try:
            parsed = _json_object(response_text)
            changes = self._validate_changes(task_record, parsed)
            workspace = self._prepare_workspace(task_record["task_id"])
            for item in changes:
                destination = workspace / item["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(item["content"], encoding="utf-8")
            commands = self._trusted_test_commands(task_record, [item["path"] for item in changes])
            test_results = []
            for command in commands:
                argv = [sys.executable, *command[1:]]
                completed = self.command_runner(argv, cwd=workspace, capture_output=True,
                                                text=True, timeout=COMMAND_TIMEOUT_SECONDS,
                                                shell=False)
                test_results.append({"argv": ["PYTHON", *command[1:]],
                                     "returncode": completed.returncode,
                                     "stdout": completed.stdout[-2000:],
                                     "stderr": completed.stderr[-1000:]})
                if completed.returncode != 0:
                    return VerifyResult(False, errors=["allowlisted test failed"],
                                        is_logic_error=True)
            parsed["changes"] = changes
            parsed["workspace"] = str(workspace)
            parsed["test_results"] = test_results
            return VerifyResult(True, parsed_output=parsed)
        except (ValueError, PermissionError, OSError, json.JSONDecodeError,
                subprocess.SubprocessError) as exc:
            return VerifyResult(False, errors=[f"{type(exc).__name__}: {exc}"],
                                is_logic_error=True)

    def apply(self, task_record, verify_result: VerifyResult) -> ApplyResult:
        parsed = verify_result.parsed_output
        paths = [item["path"] for item in parsed["changes"]]
        return ApplyResult(files_changed=[], artifacts_created=[parsed["workspace"], *paths],
                           touches_real_repo_files=True, proposal_only=True)

    def verify_bridge_submission(self, task_record, response_text, verification) -> VerifyResult:
        """Validate a client-side bounded verification receipt without executing commands.

        The local client already ran this same handler in an isolated workspace.
        The backend revalidates the patch bounds and the shape of every test receipt;
        it never accepts a command string or an unverified/failed result.
        """
        try:
            parsed = _json_object(response_text)
            changes = self._validate_changes(task_record, parsed)
            if not isinstance(verification, dict) or verification.get("passed") is not True:
                raise ValueError("client verifier did not pass")
            tests = verification.get("test_results")
            if not isinstance(tests, list):
                raise ValueError("test receipt missing")
            for item in tests:
                if not isinstance(item, dict) or not isinstance(item.get("argv"), list):
                    raise ValueError("invalid test receipt")
                if item.get("returncode") != 0:
                    raise ValueError("client test failed")
                argv = item["argv"]
                if not argv or argv[0] != "PYTHON":
                    raise PermissionError("non-allowlisted test receipt")
                if any(part in {"git", "push", "deploy", ";", "&&", "|"} for part in argv):
                    raise PermissionError("forbidden operation in test receipt")
            return VerifyResult(True, parsed_output={"summary": parsed["summary"],
                                "changes": changes, "test_results": tests})
        except (ValueError, PermissionError, json.JSONDecodeError) as exc:
            return VerifyResult(False, errors=[f"{type(exc).__name__}: {exc}"],
                                is_logic_error=True)
