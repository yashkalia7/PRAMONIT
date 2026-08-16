/**
 * Narration overlay for the recorded product tour.
 *
 * Playwright records the raw page, which on its own is a silent, context-free
 * screen recording — you see clicks but never learn why. These helpers inject a
 * caption bar, a step counter and a spotlight ring so the finished video
 * explains itself without a voiceover.
 *
 * Everything is injected at record time and never ships in the app bundle.
 */

import type { Locator, Page } from '@playwright/test';

const OVERLAY_ID = '__pramonit_narration__';

/** Re-injects on every call, so it survives full page navigations. */
async function render(
  page: Page,
  payload: { step?: string; title: string; body?: string },
) {
  await page.evaluate(
    ({ id, step, title, body }) => {
      let root = document.getElementById(id);
      if (!root) {
        root = document.createElement('div');
        root.id = id;
        root.style.cssText = [
          'position:fixed',
          'left:0',
          'right:0',
          'bottom:0',
          'z-index:2147483647',
          'padding:18px 28px 20px',
          'background:linear-gradient(to top, rgba(4,7,5,0.97) 55%, rgba(4,7,5,0))',
          'font-family:Inter,Segoe UI,system-ui,sans-serif',
          'pointer-events:none',
          'display:flex',
          'align-items:flex-end',
          'gap:18px',
        ].join(';');
        document.body.appendChild(root);
      }

      root.innerHTML = `
        <div style="
          min-width:52px;height:52px;border-radius:14px;background:#C7F53F;
          color:#08120A;font-weight:800;font-size:20px;display:flex;
          align-items:center;justify-content:center;flex:0 0 auto;">
          ${step ?? '●'}
        </div>
        <div style="flex:1">
          <div style="color:#C7F53F;font-size:20px;font-weight:800;letter-spacing:-0.2px">
            ${title}
          </div>
          ${
            body
              ? `<div style="color:#DCE7E1;font-size:15px;line-height:1.45;margin-top:4px;max-width:1050px">${body}</div>`
              : ''
          }
        </div>`;
    },
    { id: OVERLAY_ID, step: payload.step, title: payload.title, body: payload.body },
  );
}

let stepNumber = 0;

/** Show a caption and hold it long enough to read. */
export async function say(
  page: Page,
  title: string,
  body?: string,
  holdMs = 2600,
): Promise<void> {
  stepNumber += 1;
  await render(page, { step: String(stepNumber), title, body });
  await page.waitForTimeout(holdMs);
}

/** Caption without advancing the step counter — for follow-on detail. */
export async function aside(
  page: Page,
  title: string,
  body?: string,
  holdMs = 2400,
): Promise<void> {
  await render(page, { step: '↳', title, body });
  await page.waitForTimeout(holdMs);
}

/** Full-screen card, used to open and close the tour. */
export async function card(
  page: Page,
  heading: string,
  sub: string,
  lines: string[] = [],
  holdMs = 3800,
): Promise<void> {
  await page.evaluate(
    ({ heading, sub, lines }) => {
      const existing = document.getElementById('__pramonit_card__');
      existing?.remove();
      const el = document.createElement('div');
      el.id = '__pramonit_card__';
      el.style.cssText = [
        'position:fixed',
        'inset:0',
        'z-index:2147483647',
        'background:#050806',
        'display:flex',
        'flex-direction:column',
        'align-items:center',
        'justify-content:center',
        'gap:14px',
        'font-family:Inter,Segoe UI,system-ui,sans-serif',
      ].join(';');
      el.innerHTML = `
        <div style="font-size:64px">⚽</div>
        <div style="color:#F2F7F4;font-size:46px;font-weight:800;letter-spacing:-1px">${heading}</div>
        <div style="color:#C7F53F;font-size:19px;font-weight:700;letter-spacing:2px">${sub.toUpperCase()}</div>
        ${
          lines.length
            ? `<div style="margin-top:22px;display:flex;flex-direction:column;gap:9px;align-items:center">
                 ${lines
                   .map(
                     (l) =>
                       `<div style="color:#93A99E;font-size:16px;line-height:1.5">${l}</div>`,
                   )
                   .join('')}
               </div>`
            : ''
        }`;
      document.body.appendChild(el);
    },
    { heading, sub, lines },
  );
  await page.waitForTimeout(holdMs);
  await page.evaluate(() => document.getElementById('__pramonit_card__')?.remove());
}

/** Draw a pulsing ring around an element just before interacting with it. */
export async function spotlight(page: Page, target: Locator, holdMs = 900): Promise<void> {
  const box = await target.boundingBox();
  if (!box) return;
  await page.evaluate(
    ({ box }) => {
      const existing = document.getElementById('__pramonit_ring__');
      existing?.remove();
      const ring = document.createElement('div');
      ring.id = '__pramonit_ring__';
      ring.style.cssText = [
        'position:fixed',
        `left:${box.x - 8}px`,
        `top:${box.y - 8}px`,
        `width:${box.width + 16}px`,
        `height:${box.height + 16}px`,
        'border:3px solid #C7F53F',
        'border-radius:14px',
        'box-shadow:0 0 0 6px rgba(199,245,63,0.18)',
        'z-index:2147483646',
        'pointer-events:none',
        'transition:opacity .3s',
      ].join(';');
      document.body.appendChild(ring);
    },
    { box },
  );
  await page.waitForTimeout(holdMs);
}

export async function clearSpotlight(page: Page): Promise<void> {
  await page.evaluate(() => document.getElementById('__pramonit_ring__')?.remove());
}

/** Spotlight, then click. The pairing every step of the tour uses. */
export async function point(page: Page, target: Locator, holdMs = 850): Promise<void> {
  await spotlight(page, target, holdMs);
  await clearSpotlight(page);
  await target.click();
}

export function resetSteps(): void {
  stepNumber = 0;
}
