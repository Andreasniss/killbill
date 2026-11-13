# Claude Code settings for this repository

JSON has no comments, so both `settings.json` and the personal
`settings.local.json` (gitignored) carry one-line notes in `"//"` keys, which
Claude Code ignores as unknown properties. This file has the full reasoning.
Only add `"//"` at the top level or inside `permissions` or `sandbox`: under
`hooks` every key must be an event name, and Claude Code skips an invalid
settings file entirely.

## What this repository adds on top of user settings

| Setting | User settings (each developer) | This repository (`settings.json`) |
|---|---|---|
| Permission mode | Auto: a classifier approves routine actions | Unchanged, still Auto |
| `git push`, `gh pr create`, `gh pr merge`, GitHub MCP PR, merge and push tools | Auto mode decides, usually without asking | **`ask`**: always prompts a human, even in Auto |
| Any other GitHub MCP call, including reads (`mcp__github`) | Auto mode decides | **`ask`**: always prompts; MCP reads bypass the filesystem, so no sandbox or read block covers them |
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

## Local read isolation (`settings.local.json`)

Goal: in this checkout, Claude may read this repository and nothing else on
the machine, such as other repositories under `~/GitHub`.

### Why the sandbox alone does not do this

Enabling the sandbox (`/sandbox`) looks like it should isolate the session, but
by default it restricts **writes and network**, not reads:

- **Reads are deny-listed, not allow-listed.** The sandbox only blocks a fixed
  list of secrets (`~/.ssh`, `.env`, `*.pem`, cloud credential files). Every
  other folder in your home directory stays readable.
- **It only wraps Bash.** The sandbox is an OS-level profile applied to each
  shell command. Claude's built-in file tools (Read, Grep, Glob) and MCP tools
  do not run inside it; permission rules govern them.
- **Auto-allow hides it.** With `autoAllowBashIfSandboxed`, sandboxed commands
  run without prompting, so you only notice the sandbox when a command hits
  one of its walls.
- **Sandbox `denyRead` would cover Bash only**, and permission rule globs have
  no "everything except X" form, so `Read(...)` deny rules would need one
  entry per folder and miss folders added later.

### What does it: `permissions.blockReadsOutsideWorkingDirectories`

Set to `true`, this refuses file-tool reads outside the working directories in
every permission mode (no allow rule lifts it), **and** the sandbox then denies
the same paths to Bash. One setting, both channels, including folders created
later. Git config (`~/.gitconfig`, `~/.config/git/*`) and Claude's own folders
stay readable automatically.

### Why `~/.m2` is re-opened by hand

The read block also hides `~/.m2`, the local Maven repository, so a sandboxed
`mvn` could no longer see cached dependencies. `sandbox.filesystem.allowRead:
["~/.m2"]` re-opens it for **reading only**. It is listed by hand because it
is a deliberate exception: only what this Maven project needs, nothing else
under the home directory.

Writes to `~/.m2` are still blocked, as they were before this change (the
sandbox only allows writes inside the project and temp folders). Sandboxed
builds that download new dependencies or run `mvn install` therefore fail.
Either add `"allowWrite": ["~/.m2"]` next to `allowRead`, or run Maven yourself
with `! mvn ...`.

### Remote reads: GitHub MCP set to `ask` (committed)

The GitHub MCP server reads repositories through the GitHub API, not the
filesystem, so neither the sandbox nor the read block applies to it.
`permissions.ask: ["mcp__github"]` makes every call to it, including reads,
prompt first. The `deny` rules (e.g. `delete_file`) still win over this `ask`.
This rule is in the committed `settings.json`, since it costs teammates
nothing but a prompt.

### What is committed and what stays local

| Setting | Where | Why |
|---|---|---|
| `ask: mcp__github` | `settings.json` | Low friction, matches the existing push/PR `ask` rules |
| `blockReadsOutsideWorkingDirectories` | `settings.local.json` (opt-in) | `true` in any source wins, so committed it could not be turned off; it also stops Claude reading dependency sources or sibling repositories |
| Sandbox (`enabled`, `allowUnsandboxedCommands: false`) and `allowRead: ~/.m2` | `settings.local.json` | Sandboxed `mvn install` and dependency downloads fail (writes to `~/.m2` are blocked), so committing it would break the documented build for everyone |

To opt in, put this in your own `.claude/settings.local.json` (or run
`/sandbox` for the sandbox part and add the rest):

```json
{
  "permissions": { "blockReadsOutsideWorkingDirectories": true },
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "allowUnsandboxedCommands": false,
    "filesystem": { "allowRead": ["~/.m2"] }
  }
}
```
 A committed file is a convention, not
enforcement; anything people must not opt out of belongs in managed settings.

### Verified

| Path | Result |
|---|---|
| Other repositories under `~/GitHub` | blocked ("Operation not permitted") |
| This repository, `git status`, Homebrew `java`/`mvn` | work |
| `~/.m2/repository` | readable after the `allowRead` exception |

Side effect: Claude can no longer read the user-level `~/.claude/settings.json`
from this project. Edit it yourself, or open it to Claude explicitly.

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
