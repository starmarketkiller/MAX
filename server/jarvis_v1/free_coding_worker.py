"""Bounded LocalTaskHandler for free/local conversational coding.

The handler never selects or invokes a model. Orchestrator._run_local owns the
Ollama call, retry and escalation. This class only builds a compact prompt,
validates the structured proposal, tests it in an isolated workspace, and
returns a proposal artifact for the existing approval gate.
"""
from __future__ import annotations

import fnmatch
import hashlib
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
NEWLINE_POLICY = "preserve_proposal_bytes"


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


def file_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def proposal_digest(changes: list[dict]) -> str:
    parts = [item["content"].encode("utf-8")
             for item in sorted(changes, key=lambda row: row["path"])]
    return file_digest(b"\0".join(parts))


def baseline_digest(baselines: dict) -> str:
    blob = b"\0".join(
        f"{path}\0{digest}".encode("utf-8")
        for path, digest in sorted(baselines.items()))
    return hashlib.sha256(blob).hexdigest()


BINDING_SCHEMA = "approval-continuation-binding-v2"


def _binding_material(pairs: list[tuple[str, bytes]]) -> bytes:
    seen = set()
    for path, _data in pairs:
        if path in seen:
            raise ValueError("duplicate path")
        seen.add(path)
    parts = [BINDING_SCHEMA.encode("utf-8")]
    for path, data in sorted(pairs, key=lambda row: row[0].encode("utf-8")):
        encoded = path.encode("utf-8")
        parts.append(len(encoded).to_bytes(4, "big"))
        parts.append(encoded)
        parts.append(len(data).to_bytes(8, "big"))
        parts.append(data)
    return b"".join(parts)


def binding_digest(changes: list[dict]) -> str:
    return file_digest(_binding_material(
        [(item["path"], item["content"].encode("utf-8")) for item in changes]))


def binding_digest_bytes(pairs: list[tuple[str, bytes]]) -> str:
    return file_digest(_binding_material(pairs))


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
        rework = (task_record.get("action_params") or {}).get("rework_instructions")
        prefix = (f"{rework}\nThe file(s) below are the ORIGINAL, unmodified content - your "
                 "previous rejected attempt was never applied to them.\n\n" if rework else "")
        return (prefix +
                "Return JSON only. Propose the smallest correct patch. Do not select a provider, "
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
        # research_scripts/ and vault/ are data/notes, never imported by server
        # code or tests, but can dwarf the rest of the repo (reproduced live:
        # NEXUS TASK_6FEA7BDE04D2 spent ~7 of its ~7 total minutes copying
        # them - 5.8GB/73k files for a one-file patch). Excluding them is
        # strictly narrower than the existing exclusions, not a behavior
        # change for any task that touches server/ or frontend/ code.
        ignored = shutil.ignore_patterns(".git", "node_modules", ".pytest_cache", "__pycache__",
                                         ".nexus", "runtime_state", "*.pyc", "research_scripts",
                                         "vault")
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
            parsed.update(self._proposal_binding(task_record, changes))
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

    def _proposal_binding(self, task_record, changes) -> dict:
        baselines = {}
        root = self.project_root.resolve()
        for item in changes:
            raw = root / item["path"]
            if raw.is_symlink():
                raise ValueError("symlink baseline")
            baselines[item["path"]] = (
                file_digest(raw.read_bytes()) if raw.is_file() else "ABSENT")
        return {
            "baselines": baselines,
            "attempt": int(task_record.get("retry_count") or 0),
            "newline_policy": NEWLINE_POLICY,
            "proposal_sha256": proposal_digest(changes),
            "baseline_sha256": baseline_digest(baselines),
            "binding_schema": BINDING_SCHEMA,
            "binding_sha256": binding_digest(changes),
        }

    def apply_verified_proposal(self, task_record, before_write=None) -> dict:
        """Write a stored proposal's exact bytes, then rerun the allowlisted tests.

        Every refusal happens before the first write. A failed post-write test
        restores the captured baseline bytes and does not report success unless
        the restored bytes were read back. before_write runs after the checks
        and before the first write, while the caller holds the task lock.
        """
        prepared = self._prepare_application(task_record)
        if not prepared["ok"]:
            return prepared
        intent = prepared["intent"]
        existing = task_record.get("application_intent") or {}
        if existing and existing.get("binding_sha256") != intent["binding_sha256"]:
            return {"ok": False, "reason_class": "before_write",
                    "reason": "stored intent binding mismatch"}
        if before_write is not None:
            before_write(intent)
        planned = prepared["planned"]
        root = self.project_root.resolve()
        for path, destination, _data, current in planned:
            actual = file_digest(current) if current is not None else "ABSENT"
            if actual != intent["baselines"][path]:
                return {"ok": False, "reason_class": "before_write", "reason": "baseline changed"}
        return self._write_prepared(task_record, planned, intent, root)

    def _prepare_application(self, task_record) -> dict:
        patch = task_record.get("proposed_patch") or {}
        changes = patch.get("changes") or []
        baselines = patch.get("baselines") or {}
        grant = task_record.get("approval_grant") or {}
        try:
            attempt = int(patch.get("attempt"))
            retry_count = int(task_record.get("retry_count") or 0)
            grant_attempt = int(grant.get("attempt"))
            expected_binding = binding_digest(changes)
        except (TypeError, ValueError) as exc:
            return {"ok": False, "reason_class": "before_write", "reason": str(exc) or "attempt missing"}
        if (grant.get("task_id") != task_record.get("task_id")
                or grant_attempt != attempt
                or grant.get("proposal_sha256") != patch.get("proposal_sha256")
                or grant.get("baseline_sha256") != patch.get("baseline_sha256")
                or grant.get("binding_sha256") != patch.get("binding_sha256")
                or grant.get("binding_schema") != BINDING_SCHEMA
                or patch.get("binding_schema") != BINDING_SCHEMA
                or patch.get("binding_sha256") != expected_binding
                or patch.get("newline_policy") != NEWLINE_POLICY
                or attempt != retry_count
                or proposal_digest(changes) != patch.get("proposal_sha256")
                or baseline_digest(baselines) != patch.get("baseline_sha256")):
            return {"ok": False, "reason_class": "before_write", "reason": "approval binding mismatch"}
        manifest = task_record["manifest"]
        allowed = list(manifest.get("files_allowed") or [])
        forbidden = list(manifest.get("files_forbidden") or [])
        root = self.project_root.resolve()
        planned = []
        files = []
        for item in changes:
            if not isinstance(item, dict) or not isinstance(item.get("content"), str):
                return {"ok": False, "reason_class": "before_write", "reason": "change content missing"}
            try:
                path = _safe_relative(item.get("path", ""))
            except ValueError as exc:
                return {"ok": False, "reason_class": "before_write", "reason": str(exc)}
            if not allowed or not _matches(path, allowed) or _matches(path, forbidden):
                return {"ok": False, "reason_class": "before_write", "reason": f"path not allowed: {path}"}
            raw = root / path
            if raw.is_symlink():
                return {"ok": False, "reason_class": "before_write", "reason": "symlink destination"}
            try:
                destination = raw.resolve()
                if destination != root and root not in destination.parents:
                    raise ValueError("path escaped project")
            except (OSError, ValueError) as exc:
                return {"ok": False, "reason_class": "before_write", "reason": str(exc)}
            current = raw.read_bytes() if raw.is_file() else None
            actual = file_digest(current) if current is not None else "ABSENT"
            if actual != baselines.get(path):
                return {"ok": False, "reason_class": "before_write", "reason": "baseline changed"}
            data = item["content"].encode("utf-8")
            planned.append((path, destination, data, current))
            files.append({"path": path, "baseline_sha256": actual,
                          "proposal_content_sha256": file_digest(data)})
        if not planned:
            return {"ok": False, "reason_class": "before_write", "reason": "empty proposal"}
        intent = {
            "binding_schema": BINDING_SCHEMA,
            "task_id": task_record.get("task_id"),
            "attempt": attempt,
            "newline_policy": NEWLINE_POLICY,
            "proposal_sha256": patch["proposal_sha256"],
            "binding_sha256": expected_binding,
            "baseline_sha256": patch["baseline_sha256"],
            "baselines": baselines,
            "files": files,
        }
        return {"ok": True, "planned": planned, "intent": intent, "root": root}

    def _write_prepared(self, task_record, planned, intent, root) -> dict:
        written = []
        try:
            for path, destination, data, _current in planned:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                written.append(path)
                if destination.read_bytes() != data:
                    raise OSError("applied bytes diverged")
            verified = self._run_allowlisted(task_record, written, root)
            if not verified["ok"]:
                raise PermissionError(verified["reason"])
            test_results = verified["tests"]
        except (OSError, PermissionError, ValueError, subprocess.SubprocessError) as exc:
            report = self._restore_baseline(planned)
            verified_rollback = all(item["restored"] is True for item in report)
            return {"ok": False,
                    "reason_class": "verification_failed" if verified_rollback else "rollback_unverified",
                    "reason": str(exc), "files": report, "rollback_verified": verified_rollback}
        read_back = [(path, destination.read_bytes()) for path, destination, _data, _current in planned]
        return {"ok": True, "files": [path for path, _destination, _data, _current in planned],
                "tests": test_results, "receipt": self._receipt(intent, read_back)}

    def _run_allowlisted(self, task_record, paths, root) -> dict:
        commands = self._trusted_test_commands(task_record, paths)
        if not commands:
            return {"ok": False, "reason": "verifier missing", "tests": []}
        test_results = []
        for command in commands:
            completed = self.command_runner(
                [sys.executable, *command[1:]], cwd=root, capture_output=True,
                text=True, timeout=COMMAND_TIMEOUT_SECONDS, shell=False)
            test_results.append({"argv": ["PYTHON", *command[1:]],
                                 "returncode": completed.returncode,
                                 "stdout": (completed.stdout or "")[-2000:],
                                 "stderr": (completed.stderr or "")[-1000:]})
            if completed.returncode != 0:
                return {"ok": False, "reason": "allowlisted test failed", "tests": test_results}
        return {"ok": True, "tests": test_results}

    def _receipt(self, intent, read_back) -> dict:
        ordered = sorted(read_back, key=lambda row: row[0])
        return {
            "newline_policy": NEWLINE_POLICY,
            "binding_schema": BINDING_SCHEMA,
            "proposal_sha256": intent["proposal_sha256"],
            "applied_sha256": file_digest(b"\0".join(data for _path, data in ordered)),
            "binding_sha256": intent["binding_sha256"],
            "applied_binding_sha256": binding_digest_bytes(ordered),
            "baseline_sha256": intent["baseline_sha256"],
            "attempt": intent["attempt"],
            "paths": [path for path, _data in ordered],
        }

    def observe_application(self, task_record) -> list[dict]:
        intent = task_record.get("application_intent") or {}
        observations = []
        root = self.project_root.resolve()
        for item in intent.get("files") or []:
            path = item.get("path")
            observation = {"path": path, "observed_sha256": None, "residual": "UNKNOWN",
                           "restored": False}
            try:
                raw = root / path
                if raw.is_symlink():
                    observation["residual"] = "UNKNOWN"
                elif not raw.exists():
                    observation["residual"] = "BASELINE" if item.get("baseline_sha256") == "ABSENT" else "ABSENT"
                    observation["restored"] = observation["residual"] == "BASELINE"
                elif raw.is_file():
                    observed = file_digest(raw.read_bytes())
                    observation["observed_sha256"] = observed
                    if observed == item.get("proposal_content_sha256"):
                        observation["residual"] = "PROPOSAL"
                    elif observed == item.get("baseline_sha256"):
                        observation["residual"] = "BASELINE"
                        observation["restored"] = True
                    else:
                        observation["residual"] = "OTHER"
                else:
                    observation["residual"] = "UNKNOWN"
            except OSError:
                observation["residual"] = "UNKNOWN"
            observations.append(observation)
        return observations

    def verify_observed_proposal(self, task_record) -> dict:
        intent = task_record.get("application_intent") or {}
        root = self.project_root.resolve()
        paths = [item["path"] for item in intent.get("files") or []]
        try:
            verified = self._run_allowlisted(task_record, paths, root)
        except (OSError, PermissionError, ValueError, subprocess.SubprocessError) as exc:
            return {"ok": False, "reason": str(exc), "tests": []}
        if not verified["ok"]:
            return verified
        read_back = []
        for path in paths:
            raw = root / path
            try:
                read_back.append((path, raw.read_bytes()))
            except OSError:
                return {"ok": False, "reason": "applied bytes unreadable", "tests": verified["tests"]}
        receipt = self._receipt(intent, read_back)
        if receipt["applied_binding_sha256"] != intent.get("binding_sha256"):
            return {"ok": False, "reason": "read-back binding mismatch", "tests": verified["tests"],
                    "receipt": receipt}
        return {"ok": True, "tests": verified["tests"], "files": paths, "receipt": receipt}

    def _restore_baseline(self, planned) -> list[dict]:
        report = []
        for path, destination, _data, current in planned:
            item = {"path": path, "observed_sha256": None, "residual": "UNKNOWN", "restored": False}
            try:
                if current is None:
                    if destination.exists() and not destination.is_symlink():
                        destination.unlink()
                    if destination.exists():
                        item["residual"] = "PRESENT"
                        if destination.is_file() and not destination.is_symlink():
                            item["observed_sha256"] = file_digest(destination.read_bytes())
                    else:
                        item["residual"] = "ABSENT"
                        item["restored"] = True
                else:
                    destination.write_bytes(current)
                    observed = destination.read_bytes()
                    item["observed_sha256"] = file_digest(observed)
                    item["restored"] = observed == current
                    item["residual"] = "BASELINE" if observed == current else "OTHER"
            except OSError:
                try:
                    if destination.is_file() and not destination.is_symlink():
                        item["observed_sha256"] = file_digest(destination.read_bytes())
                        item["residual"] = "OTHER"
                except OSError:
                    item["observed_sha256"] = None
                    item["residual"] = "UNKNOWN"
                item["restored"] = False
            report.append(item)
        return report

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
            stored = {"summary": parsed["summary"], "changes": changes, "test_results": tests}
            stored.update(self._proposal_binding(task_record, changes))
            return VerifyResult(True, parsed_output=stored)
        except (ValueError, PermissionError, json.JSONDecodeError) as exc:
            return VerifyResult(False, errors=[f"{type(exc).__name__}: {exc}"],
                                is_logic_error=True)
