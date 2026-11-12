#!/bin/sh
# SessionStart: summarize the local Kill Bill dev environment.
# Hooks run in a non-interactive sh, so shell rc files aren't loaded; add Homebrew's keg-only JDK explicitly.
PATH="/opt/homebrew/opt/openjdk@21/bin:/opt/homebrew/bin:$PATH"; export PATH
if java -version >/dev/null 2>&1; then
  j=$(java -version 2>&1 | head -1 | sed 's/"/\\"/g')
else
  j="not found"
fi
m=$(mvn -v 2>/dev/null | head -1 | sed 's/"/\\"/g'); [ -n "$m" ] || m="not found on PATH"
p() { nc -z -G 1 localhost "$1" >/dev/null 2>&1 && echo up || echo down; }
msg="Kill Bill env | Java: $j | Maven: $m | MySQL:3306 $(p 3306) | Postgres:5432 $(p 5432)"
echo "$(date '+%F %T') $msg" >> "$(dirname "$0")/session-env.log"
printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$msg" "$msg"
