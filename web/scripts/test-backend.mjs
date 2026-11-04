import {mkdtemp, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {spawn, spawnSync} from "node:child_process";

const directory = await mkdtemp(join(tmpdir(), "hfgps-browser-"));
const env = {...process.env, HFGPS_DB_PATH: join(directory, "synthetic.sqlite3")};
const migration = spawnSync("uv", ["run", "--frozen", "--directory", "..", "python", "-m", "scripts.migrate_comparisons"], {env, stdio: "inherit"});
if (migration.status !== 0) {await rm(directory, {recursive: true, force: true}); process.exit(migration.status ?? 1);}
const child = spawn("uv", ["run", "--frozen", "--directory", "..", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000", "--no-access-log"], {env, stdio: "inherit"});
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => child.kill(signal));
child.on("error", async () => {await rm(directory, {recursive: true, force: true}); process.exit(1);});
child.on("close", async code => {await rm(directory, {recursive: true, force: true}); process.exit(code ?? 0);});
