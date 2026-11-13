#!/usr/bin/env python3
"""PreToolUse guard for Bash: nothing leaves this checkout without a human.

Permission rules match command prefixes, so `git -C . push`, `/usr/bin/git push`
or `bash -c "git push"` can slip past `Bash(git push *)`. This hook scans the
whole command text instead:

- deny: force or destructive pushes, `git reset --hard`, `git clean -f`
- ask:  any other `git push`, `gh pr create`, `gh pr merge`, `gh api .../merge`

It prints a decision only when it matches; otherwise it stays silent and the
normal permission flow (rules, then auto mode) decides.
"""
import json
import re
import sys

# `git`, optionally with global options (-C dir, -c k=v, --git-dir=...), then a subcommand.
GIT = r"\bgit\b(?:\s+(?:-C\s+\S+|-c\s+\S+|--[\w-]+(?:=\S+)?))*\s+"
SEGMENT = r"([^;&|\n]*)"  # the rest of this shell command, up to the next separator

PUSH = re.compile(GIT + r"push(?=$|[\s;&|'\"])" + SEGMENT)
FORCE_PUSH_ARG = re.compile(
    r"(?:^|\s)(?:--force(?:-with-lease|-if-includes)?(?:=\S*)?|--mirror|--delete|--prune"
    r"|-[a-zA-Z]*[fd][a-zA-Z]*|\+\S+|:\S+)(?=\s|$|['\"])"
)
RESET_HARD = re.compile(GIT + r"reset\b[^;&|\n]*--hard")
CLEAN_FORCE = re.compile(GIT + r"clean\b[^;&|\n]*\s-[a-zA-Z]*f")
GH_PR = re.compile(r"\bgh\s+pr\s+(create|merge)\b")
GH_API_MERGE = re.compile(r"\bgh\s+api\b[^;&|\n]*/merge\b")


def decide(command: str):
    for match in PUSH.finditer(command):
        if FORCE_PUSH_ARG.search(match.group(1)):
            return "deny", "Force, mirror or delete pushes are blocked in this repository."
    if RESET_HARD.search(command):
        return "deny", "`git reset --hard` is blocked in this repository; it discards local work."
    if CLEAN_FORCE.search(command):
        return "deny", "`git clean -f` is blocked in this repository; it deletes untracked files."
    if PUSH.search(command):
        return "ask", "Repository policy: a human approves every push."
    if GH_PR.search(command) or GH_API_MERGE.search(command):
        return "ask", "Repository policy: a human approves pull request creation and merges."
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    verdict = decide(command)
    if verdict:
        decision, reason = verdict
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
