import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { posix as path } from "node:path";
import { validateKnowledgeFrontmatter } from "./knowledge-frontmatter.mjs";

const files = new Set(git("ls-files", "--cached", "-z").split("\0").filter(Boolean));
const markdown = [...files].filter(file => file.startsWith("openwiki/") && file.endsWith(".md") && !file.endsWith(".log.md"));
const directories = new Map([["openwiki", new Set()]]);
const rootHeader = '---\nokf_version: "0.2"\n---\n\n';

for (const file of markdown) {
  if (!["index.md", "log.md"].includes(path.basename(file))) {
    addEntry(path.dirname(file), path.basename(file));
  }
  let directory = path.dirname(file);
  while (directory !== "openwiki") {
    addEntry(path.dirname(directory), path.basename(directory) + "/");
    directory = path.dirname(directory);
  }
}

let concepts = 0;
for (const file of markdown) {
  if (["index.md", "log.md"].includes(path.basename(file))) continue;
  const content = git("show", ":" + file);
  const result = validateKnowledgeFrontmatter(content);
  assert.ok(result.valid, file + ": " + JSON.stringify(result.issues));
  for (const [, target] of content.matchAll(/\]\(([^)]+)\)/g)) {
    if (/^(?:[a-z]+:|#)/i.test(target)) continue;
    const destination = path.join(path.dirname(file), target.split("#")[0]);
    assert.ok(files.has(destination) || files.has(path.join(destination, "index.md")),
      file + ": broken staged link to " + target);
  }
  concepts++;
}

for (const [directory, expected] of directories) {
  const file = path.join(directory, "index.md");
  assert.ok(files.has(file), "Missing staged index: " + file);
  const content = git("show", ":" + file).replaceAll("\r\n", "\n");
  if (directory === "openwiki") assert.ok(content.startsWith(rootHeader), file + ": missing OKF v0.2 declaration");
  const body = directory === "openwiki" ? content.slice(rootHeader.length) : content;
  assert.match(body, /^# .+/, file + ": missing heading");
  const entries = [...body.matchAll(/^[*-] \[[^\]]+\]\(([^)]+)\)/gm)].map(match => match[1]);
  assert.deepEqual(entries.sort(), [...expected].sort(), file + ": entries differ from staged pages");
}

console.log(`OKF: ${concepts} staged concepts and ${directories.size} indexes passed.`);

function git(...args) {
  return execFileSync("git", args, { encoding: "utf8" });
}

function addEntry(directory, entry) {
  if (!directories.has(directory)) directories.set(directory, new Set());
  directories.get(directory).add(entry);
}
