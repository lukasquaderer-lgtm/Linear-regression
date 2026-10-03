// Bundles the React app into one self-contained HTML page for a claude.ai Artifact.
// React is bundled inline; Plotly loads from jsDelivr (allowed by the Artifact CSP).
import { build } from "esbuild";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";

const PLOTLY = "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js";
const FONTS = "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Public+Sans:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap";

const result = await build({
  entryPoints: ["src/main.jsx"],
  bundle: true,
  minify: true,
  format: "iife",
  target: ["es2020"],
  jsx: "automatic",
  define: { "process.env.NODE_ENV": '"production"' },
  legalComments: "none",
  write: false,
  logLevel: "warning",
});
const js = result.outputFiles[0].text.replace(/<\/script/gi, "<\\/script");
const css = readFileSync("src/styles.css", "utf8");

const html = `<title>Analyst Lab</title>
<meta name="description" content="Learn to analyse banks and insurers like an equity analyst — ten guided stages from business model to investment thesis.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="${FONTS}">
<style>
${css}
</style>
<div id="root"><div class="boot"><div class="boot-mark">AL</div><p>Loading Analyst Lab…</p></div></div>
<script src="${PLOTLY}"></script>
<script>
${js}
</script>
`;
mkdirSync("dist", { recursive: true });
writeFileSync("dist/analyst-lab.html", html);
console.log(`dist/analyst-lab.html  ${(html.length / 1024).toFixed(0)} KiB`);
