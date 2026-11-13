# Claude Code settings for this repository

JSON has no comments, so this file explains `settings.json`.

## What this repository adds on top of user settings

| Setting | User settings (each developer) | This repository (`settings.json`) |
|---|---|---|
| Permission mode | Auto: a classifier approves routine actions | Unchanged, still Auto |
| `git push`, `gh pr create`, `gh pr merge`, GitHub MCP PR, merge and push tools | Auto mode decides, usually without asking | **`ask`**: always prompts a human, even in Auto |
| Force push, `git reset --hard`, deleting files on GitHub | Auto mode decides | **`deny`**: always refused |
| Bypass variants (`git -C . push`, `/usr/bin/git push`, `bash -c "git push -f"`) | Not matched by prefix rules | **`PreToolUse` hook** `git-guard.py` scans the whole command and asks or denies |
| Session start | Nothing | **`SessionStart` hook** `session-env.sh` reports Java, Maven and database ports |
| Reading `.env` and other secrets | Denied in user settings | Still denied; a repository cannot re-allow it |

## Why a repository can tighten but not loosen

Claude Code merges permission rules from every settings file and checks them
in a fixed order: **deny, then ask, then allow**. The first match wins, and
Auto mode's classifier only sees actions no rule matched. So:

- A repository `ask` or `deny` beats a user `allow` or Auto mode.
- A user `deny` beats a repository `allow`.
- Scalar settings (model, mode) follow scope precedence instead: managed >
  command line > `.claude/settings.local.json` > `.claude/settings.json` > user.

## In a company: managed settings via MDM

The top layer is **managed settings**, deployed by IT through MDM (a macOS
configuration profile, Windows policy, `managed-settings.json` in the system
directory) or server-managed settings from the Claude admin console. Nothing
below can override them.

By default, managed `deny` and `ask` rules are a floor nobody below can
remove, and repositories and developers can add their own `deny` and `ask`
rules on top. One caveat to "repositories can only make things stricter": a
repository *can* also add `allow` rules that skip prompts a developer would
otherwise see, as long as nothing higher denies or asks.

To close that gap, IT can set `allowManagedPermissionRulesOnly: true`. Claude
Code then ignores allow, ask and deny rules from user, project, local and
`--settings` files, so permission rules come only from the company policy,
including repository-specific restrictions like this one. `allowManagedHooksOnly`
does the same for hooks. MDM delivery: a macOS configuration profile (domain
`com.anthropic.claudecode`) or Windows registry policy via Jamf, Intune or
Group Policy; or server-managed settings from the Claude admin console, the
only managed source cloud sessions read.

Hooks and rules are guardrails for the agent, not a security boundary. Branch
protection, scoped credentials and CI checks remain the real controls.
