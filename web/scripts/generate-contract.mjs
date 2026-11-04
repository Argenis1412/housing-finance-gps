import {mkdtemp, readFile, writeFile, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join, resolve} from "node:path";
import {pathToFileURL} from "node:url";
import {execFileSync} from "node:child_process";
import openapiTS, {astToString} from "openapi-typescript";
import ts from "typescript";

const temporary = await mkdtemp(join(tmpdir(), "housing-openapi-"));
try {
  const output = execFileSync("uv", ["run", "--frozen", "python", "-m", "scripts.export_openapi"], {cwd: resolve(".."), encoding: "utf8"});
  const schema = join(temporary, "openapi.json");
  await writeFile(schema, output);
  // A named recursive alias avoids TS2502 for indexed recursive union members.
  // It represents only the transport codec, never a financial schema.
  const generated = "export type ClosedJsonValue = { [key: string]: ClosedJsonValue } | ClosedJsonValue[] | string | number | boolean | null;\n\n" + astToString(await openapiTS(pathToFileURL(schema), {
    transform(_schema, context) {
      if (/\/ClosedJsonValue-(Input|Output)$/.test(context.path)) return ts.factory.createTypeReferenceNode("ClosedJsonValue");
    },
  }));
  const destination = "lib/api.generated.ts";
  if (process.argv.includes("--check")) {
    if (await readFile(destination, "utf8") !== generated) throw new Error("Generated API types differ; run npm run contract:generate.");
  } else await writeFile(destination, generated);
} finally {await rm(temporary, {recursive: true, force: true});}
