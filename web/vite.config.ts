import { defineConfig } from "vite";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";

const clickReport = fileURLToPath(new URL("../.repolens-cache/preview/click.html", import.meta.url));

const studioReport = fileURLToPath(new URL("../.repolens-cache/preview/p-limit.html", import.meta.url));

export default defineConfig({
  plugins: [tailwindcss(), {
    name: "repolens-report-preview",
    apply: "serve",
    configureServer(server) {
      server.watcher.add([clickReport, studioReport]);
      const reload = (path: string) => {
        if (path === clickReport || path === studioReport) server.ws.send({ type: "full-reload" });
      };
      server.watcher.on("add", reload).on("change", reload);
    },
    async transformIndexHtml(html, context) {
      const route = new URL(context.originalUrl ?? context.path, "http://localhost").pathname;
      const previewReport = route.replace(/\/$/, "") === "/print-studio" ? studioReport : clickReport;
      let generated: string;
      try {
        generated = await readFile(previewReport, "utf8");
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code === "ENOENT") return html;
        throw error;
      }
      const payload = generated.match(/<script type="application\/json" id="repolens-data">([\s\S]*?)<\/script>/)?.[1];
      return payload?.startsWith("{") ? html.replace("__REPOLENS_DATA__", () => payload) : html;
    },
  }],
  build: { assetsInlineLimit: Infinity, modulePreload: false },
});
