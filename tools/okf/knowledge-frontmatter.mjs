import { parseFrontmatterFields, validateOkfFrontmatter } from "./frontmatter.ts";

// Knowledge Hub uses the existing status field for its completed lifecycle state.
// Preserve upstream validation and allow only this documented local extension.
export function validateKnowledgeFrontmatter(content) {
  const result = validateOkfFrontmatter(content);
  if (result.valid || parseFrontmatterFields(content)?.status !== "completed") {
    return result;
  }
  const issues = result.issues.filter(issue => issue.code !== "invalid_status");
  return issues.length ? { valid: false, issues } : { valid: true };
}
