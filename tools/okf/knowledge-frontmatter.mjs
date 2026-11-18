import { parseFrontmatterFields, validateOkfFrontmatter } from "./frontmatter.ts";

// Knowledge Hub uses the existing status field for completed and in_progress lifecycle states.
// Preserve upstream validation and allow only this documented local extension.
export function validateKnowledgeFrontmatter(content) {
  const result = validateOkfFrontmatter(content);
  if (result.valid || !["completed", "in_progress"].includes(parseFrontmatterFields(content)?.status)) {
    return result;
  }
  const issues = result.issues.filter(issue => issue.code !== "invalid_status");
  return issues.length ? { valid: false, issues } : { valid: true };
}
