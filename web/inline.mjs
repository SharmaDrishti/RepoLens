import { createHash } from "node:crypto";
import { readdir, readFile, writeFile } from "node:fs/promises";

const dist = new URL("./dist/", import.meta.url);
const target = new URL("../repolens/page_template.html", import.meta.url);
const input = await readFile(new URL("index.html", dist), "utf8");
const scripts = [...input.matchAll(/<script\b[^>]*src="([^"]+)"[^>]*><\/script>/g)];
const styles = [...input.matchAll(/<link\b[^>]*rel="stylesheet"[^>]*href="([^"]+)"[^>]*>/g)];
if (scripts.length !== 1) throw new Error("Expected exactly one bundled script.");

let output = input;
for (const [tag, path] of scripts) {
  const code = await readFile(new URL(path.replace(/^\//, ""), dist), "utf8");
  output = output.replace(tag, () => "<script type=\"module\">" + code.replace(/<\/script/gi, "<\\/script") + "</script>");
}
for (const [tag, path] of styles) {
  const css = await readFile(new URL(path.replace(/^\//, ""), dist), "utf8");
  output = output.replace(tag, () => "<style>" + css + "</style>");
}
const root = new URL("./", import.meta.url);
const sources = (await readdir(new URL("./src/", root), { recursive: true }))
  .map(path => "src/" + path.replaceAll("\\", "/"));
const inputs = [...sources, "index.html", "inline.mjs", "package.json", "tsconfig.json", "vite.config.ts"].sort();
const digest = createHash("sha256");
for (const path of inputs) {
  let content;
  try {
    content = await readFile(new URL(path, root));
  } catch (error) {
    if (error.code === "EISDIR") continue;
    throw error;
  }
  digest.update(path + "\0").update(content).update("\0");
}
const fontLicense = await readFile(new URL("./src/print-studio/fonts/OFL.txt", root), "utf8");
output = output.replace("</head>", () => "<!--\n" + fontLicense + "--></head>");
output = output.replace("</head>", "<!-- repolens-frontend:" + digest.digest("hex") + " --></head>");
await writeFile(target, output);
console.log("Offline template: " + Buffer.byteLength(output) + " bytes");
