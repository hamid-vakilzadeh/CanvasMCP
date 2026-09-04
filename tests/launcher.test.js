import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, realpathSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { once } from "node:events";
import test from "node:test";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const launcher = join(root, "bin", "canvas-mcp.js");

function fixture(t, script) {
  const directory = mkdtempSync(join(tmpdir(), "canvas-mcp-launcher-"));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  if (script) {
    symlinkSync(process.execPath, join(directory, "node"));
    writeFileSync(join(directory, "uv"), `#!/usr/bin/env node\n${script}`, { mode: 0o755 });
  }
  return directory;
}

test("missing uv gives actionable stderr without polluting stdout", (t) => {
  const directory = fixture(t);
  const result = spawnSync(process.execPath, [launcher], {
    env: { ...process.env, PATH: directory }, encoding: "utf8",
  });
  assert.equal(result.status, 1);
  assert.equal(result.stdout, "");
  assert.match(result.stderr, /requires uv/);
});

test("forwards stdio, credentials, cwd and exit status", { skip: process.platform === "win32" }, (t) => {
  const directory = fixture(t, `
    console.error(JSON.stringify({args: process.argv.slice(2), cwd: process.cwd(), token: process.env.CANVAS_ACCESS_TOKEN, venv: process.env.UV_PROJECT_ENVIRONMENT}));
    process.stdin.pipe(process.stdout);
    process.stdin.on('end', () => { process.exitCode = 7; });
  `);
  const cwd = join(directory, "working directory");
  mkdirSync(cwd);
  const result = spawnSync(process.execPath, [launcher], {
    cwd, env: { ...process.env, PATH: directory, CANVAS_ACCESS_TOKEN: "test-token", UV_PROJECT_ENVIRONMENT: join(directory, "venv") },
    input: '{"jsonrpc":"2.0"}\n', encoding: "utf8",
  });
  assert.equal(result.status, 7, result.stderr);
  assert.equal(result.stdout, '{"jsonrpc":"2.0"}\n');
  const info = JSON.parse(result.stderr);
  assert.deepEqual(info.args, ["run", "--project", root, "--frozen", "--no-dev", "python", join(root, "src", "local.py")]);
  assert.equal(info.cwd, realpathSync(cwd));
  assert.equal(info.token, "test-token");
  assert.equal(info.venv, join(directory, "venv"));
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  test(`forwards ${signal} through the launcher to its descendant`, { skip: process.platform === "win32", timeout: 10000 }, async (t) => {
    const directory = fixture(t, `
      const { spawn } = require('node:child_process');
      // Model uv's behavior: the intermediate process does not forward signals.
      process.on('SIGINT', () => {});
      process.on('SIGTERM', () => {});
      const descendant = spawn(process.execPath, ['-e', \`
        // Model a Python stdin reader that does not finish after SIGINT.
        process.on('SIGINT', () => {});
        process.on('SIGTERM', () => { console.error('terminated'); process.exit(0); });
        console.error('ready');
        setTimeout(() => process.exit(88), 5000);
      \`], { stdio: 'inherit' });
      descendant.on('exit', (code) => process.exit(code ?? 1));
    `);
    const child = spawn(process.execPath, [launcher], { env: { ...process.env, PATH: directory } });
    t.after(() => { if (child.exitCode === null) child.kill("SIGKILL"); });
    let stderr = "";
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    await once(child.stderr, "data");
    const exited = once(child, "exit");
    child.kill(signal);
    const [code] = await exited;
    assert.equal(code, 0);
    assert.match(stderr, /terminated/);
  });
}
