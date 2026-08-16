/**
 * Finds the .webm Playwright just recorded and encodes it to an MP4 that plays
 * anywhere — WhatsApp, Slack, PowerPoint, an iPhone.
 *
 * Playwright writes VP8 .webm, which Windows Media Player, QuickTime and most
 * messaging apps will not open. H.264 in an MP4 container will.
 */

import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const RESULTS = path.join(here, '..', 'test-results');
const OUT_DIR = path.resolve(here, '..', '..', '..', 'video');

function findNewestWebm(dir) {
  if (!existsSync(dir)) return null;
  let best = null;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      const nested = findNewestWebm(full);
      if (nested && (!best || nested.mtime > best.mtime)) best = nested;
    } else if (entry.name.endsWith('.webm')) {
      const { mtimeMs } = statSync(full);
      if (!best || mtimeMs > best.mtime) best = { file: full, mtime: mtimeMs };
    }
  }
  return best;
}

const found = findNewestWebm(RESULTS);
if (!found) {
  console.error('No recording found. Run: npx playwright test --project=demo');
  process.exit(1);
}

mkdirSync(OUT_DIR, { recursive: true });
const mp4 = path.join(OUT_DIR, 'pramonit-product-tour.mp4');

console.log(`encoding ${path.relative(process.cwd(), found.file)}`);

execFileSync(
  'ffmpeg',
  [
    '-y',
    '-i', found.file,
    '-c:v', 'libx264',
    '-preset', 'slow',
    '-crf', '20',
    // yuv420p + even dimensions: without both, QuickTime and most phones show
    // a black screen instead of the video.
    '-pix_fmt', 'yuv420p',
    '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=30',
    '-movflags', '+faststart',
    '-an',
    mp4,
  ],
  { stdio: ['ignore', 'ignore', 'inherit'] },
);

const size = (statSync(mp4).size / 1024 / 1024).toFixed(1);
console.log(`\n  ✓ ${mp4}  (${size} MB)\n`);
