import type { Plugin } from "@opencode-ai/plugin";
import { $ } from "bun";

const ARTICLES_PATTERN = /^knowledge[/\\]articles[/\\].*\.json$/;

function getFilePath(args: Record<string, unknown>): string | null {
  return (args.file_path as string) || (args.filePath as string) || null;
}

const plugin: Plugin = {
  name: "validate-json",
  setup(registerEvent) {
    registerEvent("tool.execute.after", async (input) => {
      if (input.tool !== "write" && input.tool !== "edit") return;

      if (!input.args || typeof input.args !== "object") return;

      const filePath = getFilePath(input.args as Record<string, unknown>);
      if (!filePath || !ARTICLES_PATTERN.test(filePath)) return;

      try {
        const validate = await $`python3 hooks/validate_json.py ${filePath}`.nothrow();
        if (validate.exitCode !== 0) {
          console.warn(`[validate-json] FAIL: ${filePath}\n${validate.text()}`);
        }
        const quality = await $`python3 hooks/check_quality.py ${filePath}`.nothrow();
        if (quality.exitCode !== 0) {
          console.warn(`[check-quality] FAIL: ${filePath}\n${quality.text()}`);
        }
      } catch (err) {
        console.error(`[validate] ERROR: ${filePath}`, err);
      }
    });
  },
};

export default plugin;
