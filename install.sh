#!/usr/bin/env bash
# install.sh — copy the bundled skills into your Claude Code skills directory
# and install the Python dependency needed for the PDF path.
#
# Safe to re-run: it overwrites the skill copies under ~/.claude/skills and
# leaves everything else alone. It does NOT touch your Notion connector — see
# SETUP.md step 3 for that.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

echo "==> Installing skills into: $SKILLS_DEST"
mkdir -p "$SKILLS_DEST"
for skill in "$REPO_DIR"/skills/*/; do
  name="$(basename "$skill")"
  echo "    - $name"
  rm -rf "${SKILLS_DEST:?}/$name"
  cp -R "$skill" "$SKILLS_DEST/$name"
done

echo "==> Installing Python dependency for the PDF path (pypdf)"
if command -v pip3 >/dev/null 2>&1; then
  pip3 install --user -q -r "$REPO_DIR/requirements.txt" || \
    echo "    (pip install failed — install pypdf yourself, or skip if you only ingest HTML)"
else
  echo "    (pip3 not found — install pypdf yourself if you need PDF ingestion)"
fi

echo
echo "==> Verifying the fetch script runs"
if python3 "$REPO_DIR/skills/blogpost-knowledge-ingest/scripts/fetch_article.py" --help >/dev/null 2>&1; then
  echo "    OK — fetch_article.py is runnable"
else
  echo "    fetch_article.py --help returned nonzero; check your Python 3 install"
fi

echo
echo "Done. Two things remain, both in SETUP.md:"
echo "  3) Authorize the Notion connector (/mcp) and confirm the KB database is shared with it."
echo "  4) Restart Claude Code so it re-scans ~/.claude/skills, then smoke-test."
