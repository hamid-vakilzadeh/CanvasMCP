#!/usr/bin/env node

import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { constants, homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const project = dirname(dirname(fileURLToPath(import.meta.url)));
const lockHash = createHash("sha256")
  .update(readFileSync(join(project, "uv.lock")))
  .digest("hex")
  .slice(0, 16);
const cacheRoot = process.platform === "win32"
  ? process.env.LOCALAPPDATA || join(homedir(), "AppData", "Local")
  : process.platform === "darwin"
    ? join(homedir(), "Library", "Caches")
    : process.env.XDG_CACHE_HOME || join(homedir(), ".cache");

// A user-owned environment also works with read-only global npm installations.
const child = spawn("uv", [
  "run", "--project", project, "--frozen", "--no-dev",
  "python", join(project, "src", "local.py"),
  ...process.argv.slice(2),
], {
  stdio: "inherit",
  // On POSIX, give uv and Python their own process group so signals reach both.
  // Keep the child referenced: this launcher still waits for the server to exit.
  detached: process.platform !== "win32",
  env: {
    ...process.env,
    UV_PROJECT_ENVIRONMENT: process.env.UV_PROJECT_ENVIRONMENT
      || join(cacheRoot, "canvas-mcp", "venvs", lockHash),
  },
});

// stdout belongs exclusively to MCP JSON-RPC. uv diagnostics use stderr.
child.on("error", (error) => {
  if (error.code === "ENOENT") {
    console.error("Canvas MCP requires uv. Install it from https://docs.astral.sh/uv/getting-started/installation/ and ensure uv is on your MCP client's PATH.");
  } else {
    console.error("Canvas MCP could not start uv. Check the installation and executable permissions.");
  }
  process.exitCode = 1;
});

function forwardSignal(signal) {
  if (!child.pid || child.exitCode !== null || child.signalCode !== null) return;
  if (process.platform === "win32") {
    child.kill(signal);
    return;
  }
  try {
    // uv may ignore the first SIGINT sent only to its PID. Signal the group
    // so the Python process also receives it, including when sent by a client.
    process.kill(-child.pid, signal);
  } catch (error) {
    if (error.code !== "ESRCH") throw error;
  }
}

let interruptTimer;
process.on("SIGINT", () => {
  forwardSignal("SIGINT");
  // Python's async stdin reader can keep shutdown waiting while the client
  // leaves stdin open. Give it a grace period, then terminate the process group.
  interruptTimer ??= setTimeout(() => forwardSignal("SIGTERM"), 1000);
  interruptTimer.unref();
});
process.on("SIGTERM", () => forwardSignal("SIGTERM"));

child.on("exit", (code, signal) => {
  clearTimeout(interruptTimer);
  process.exitCode = code ?? (128 + (constants.signals[signal] || 1));
});
