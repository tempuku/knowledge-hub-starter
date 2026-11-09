#!/bin/sh
set -eu
cd "$(dirname "$0")"
npm ci --ignore-scripts --no-audit --no-fund
blob=b0094f720dafa8c5c24a305b635c8104507bc1eb
temporary=$(mktemp ./validator.XXXXXX)
trap 'rm -f "$temporary"' EXIT
revision=b7027e3299c666e426cf218b3412a05767f702b6
curl -fsSL "https://raw.githubusercontent.com/langchain-ai/openwiki/$revision/src/okf/frontmatter.ts" -o "$temporary"
test "$(git hash-object "$temporary")" = "$blob"
mv "$temporary" frontmatter.ts
