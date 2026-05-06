import { rmSync, readdirSync, existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { build, context } from 'esbuild';
import { sassPlugin } from 'esbuild-sass-plugin';
import yaml from 'js-yaml';

// Enable watch mode when the script is started with `--watch` flag.
const watch = process.argv.includes('--watch');
// Current node env (defaults to 'production')
const env = JSON.stringify(process.env.NODE_ENV ?? 'production');
// Define output folder
const outdir = path.resolve('../static');
const modulesdir = path.resolve('./src/modules');
const metafile = path.resolve('../meta.yaml');

// Shared esbuild options
const shared = {
  bundle: true,
  platform: 'browser',
  mainFields: ['browser', 'module', 'main'],
  format: 'iife',
  sourcemap: true,
  define: {
    'process.env.NODE_ENV': env,
  },
  loader: {
    '.md': 'text',
  },
  plugins: [
    sassPlugin({
      filter: /\.scss$/,
      type: 'style',
      loadPaths: ['node_modules'],
    }),
  ],
};

// ── Per-socket builds for the "add" module ──────────────────────────────
// The list of sockets is derived from meta.yaml: any plug whose `href`
// starts with `/static/add/` contributes its (socket, href) pair. For each
// such plug we emit a separate bundle at the path declared in `href`, with
// `__SOCKET_ID__` baked in. This keeps meta.yaml as the single source of
// truth — adding a new add-* plug is picked up automatically, and a typo
// in `href` now breaks the build loudly instead of silently at runtime.
const meta = yaml.load(readFileSync(metafile, 'utf8'));
const addPlugs = (meta.plugs ?? []).filter(
  (p) => typeof p.href === 'string' && p.href.startsWith('/static/add/'),
);

async function buildAddModules() {
  const entry = path.join(modulesdir, 'add', 'index.tsx');
  if (!existsSync(entry)) return;

  for (const plug of addPlugs) {
    const outfile = path.join(outdir, plug.href.replace(/^\/static\//, ''));
    await build({
      ...shared,
      entryPoints: [entry],
      outfile,
      define: {
        ...shared.define,
        '__SOCKET_ID__': JSON.stringify(plug.socket),
      },
    });
  }
}

// ── Regular modules (everything except "add") ───────────────────────────
const entryPoints = readdirSync(modulesdir, { withFileTypes: true })
  .filter((dirent) => dirent.isDirectory() && dirent.name !== 'add')
  .map((dirent) => path.join(modulesdir, dirent.name, 'index.tsx'))
  .filter((filePath) => existsSync(filePath));

// Cleanup previous revision of bundles
rmSync(outdir, { recursive: true, force: true });

const ctx = await context({
  ...shared,
  entryPoints,
  outbase: modulesdir,
  entryNames: '[dir]',
  outdir,
});

// In watch mode keep the context alive. Otherwise run a single rebuild and dispose the context immediately.
if (watch) {
  await ctx.watch();
  await buildAddModules();
  console.log('watching...');
} else {
  await ctx.rebuild();
  await ctx.dispose();
  await buildAddModules();
}
