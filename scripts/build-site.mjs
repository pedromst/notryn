import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const files = ['graph.js', 'hierarchy.js', 'theme-core.js', 'icons.svg', 'glass.css', 'themes.css', 'notebook.css'];
const check = process.argv.includes('--check');
await mkdir(path.join(root, 'site/assets/runtime'), { recursive: true });
for (const file of files) {
  const source = path.join(root, 'web', file);
  const target = path.join(root, 'site/assets/runtime', file);
  if (check) {
    if (!(await readFile(source)).equals(await readFile(target))) throw new Error(`Run node scripts/build-site.mjs: ${file} is stale`);
  } else await copyFile(source, target);
}
// Preserve the app styles; only make font URLs relative for static hosting.
const css = (await readFile(path.join(root, 'web/style.css'), 'utf8')).replaceAll("url('/fonts/", "url('../fonts/");
const cssTarget = path.join(root, 'site/assets/runtime/style.css');
if (check) {
  if (await readFile(cssTarget, 'utf8') !== css) throw new Error('Landing app styles are stale');
} else await writeFile(cssTarget, css);
await mkdir(path.join(root, 'site/assets/fonts'), { recursive: true });
for (const font of ['mono.woff2', 'JetBrainsMono-500-latin.woff2', 'JetBrainsMono-700-latin.woff2', 'OFL-JetBrainsMono.txt']) {
  const source = path.join(root, 'web/fonts', font), target = path.join(root, 'site/assets/fonts', font);
  if (check) {
    if (!(await readFile(source)).equals(await readFile(target))) throw new Error(`Landing font is stale: ${font}`);
  } else await copyFile(source, target);
}
const icon = path.join(root, 'site/assets/favicon.svg');
if (check) {
  if (!(await readFile(path.join(root, 'web/favicon.svg'))).equals(await readFile(icon))) throw new Error('Landing favicon is stale');
} else await copyFile(path.join(root, 'web/favicon.svg'), icon);
console.log(check ? 'Landing uses the exact app renderer, hierarchy, themes and favicon.' : 'Landing runtime refreshed from the app.');
