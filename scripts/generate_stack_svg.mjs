#!/usr/bin/env node
/** Build the profile stack artwork from locally installed CC0 simple-icons paths. */
import * as simpleIcons from 'simple-icons';
import { mkdir, writeFile } from 'node:fs/promises';

const groups = [
  { label: 'Backend', names: ['Python', 'FastAPI', 'PostgreSQL', 'Go'] },
  { label: 'Frontend', names: ['React', 'TypeScript', 'Vite', 'Tailwind CSS'] },
  { label: 'Tools', names: ['Docker', 'GitHub Actions'] },
  { label: 'Data / ML', names: ['scikit-learn', 'XGBoost'] },
  { label: 'Also', names: ['Rust', 'Java'] },
];
const iconKeys = {
  Python: 'siPython', FastAPI: 'siFastapi', PostgreSQL: 'siPostgresql', Go: 'siGo',
  React: 'siReact', TypeScript: 'siTypescript', Vite: 'siVite',
  'Tailwind CSS': 'siTailwindcss', Docker: 'siDocker', 'GitHub Actions': 'siGithubactions',
  'scikit-learn': 'siScikitlearn', XGBoost: 'siXgboost', Rust: 'siRust', Java: 'siJava',
};
const themes = {
  dark: {
    panel: '#10192b', grid: '#31435d', chip: '#192a40', border: '#486079',
    text: '#f4f7fb', muted: '#a7bbca', teal: '#76e4df', pink: '#ed97c7',
  },
  light: {
    panel: '#ecf5f7', grid: '#b7d0da', chip: '#ffffff', border: '#afc7d2',
    text: '#142638', muted: '#496476', teal: '#087e81', pink: '#aa477b',
  },
};

const escape = (value) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const pct = (seconds) => `${(seconds / 13 * 100).toFixed(3)}%`;

function icon(name, x, y, tint) {
  const entry = simpleIcons[iconKeys[name]];
  if (entry?.path) {
    return `<svg x="${x}" y="${y}" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><path fill="${tint}" d="${entry.path}"/></svg>`;
  }
  // Deliberate fallback: no alternate brand may replace a missing icon.
  const initials = name === 'Java' ? 'Ja' : name.slice(0, 2).toUpperCase();
  return `<circle cx="${x + 12}" cy="${y + 12}" r="12" fill="${tint}" opacity=".18"/>` +
    `<text class="monogram" x="${x + 12}" y="${y + 17}" text-anchor="middle" fill="${tint}" font-size="14" font-weight="700">${escape(initials)}</text>`;
}

function build(theme) {
  const c = themes[theme];
  const css = [
    'svg{font-family:system-ui,-apple-system,"Segoe UI",sans-serif}',
    '@keyframes float-a{50%{transform:translateY(-3px)}}',
    '@keyframes float-b{50%{transform:translateY(3px)}}',
    '@keyframes pulse{50%{opacity:.25}}',
    '@keyframes sweep{0%,7%{opacity:0;transform:translateX(-180px)}12%{opacity:.32}34%,100%{opacity:0;transform:translateX(1000px)}}',
    '.float-a{animation:float-a 4.8s ease-in-out infinite}',
    '.float-b{animation:float-b 5.4s ease-in-out -2.2s infinite}',
    '.dot{animation:pulse 3.6s ease-in-out infinite}',
    '.sweep{opacity:0;animation:sweep 13s ease-in-out infinite}',
    '.sweep-1{animation-delay:.55s}.sweep-2{animation-delay:1.1s}.sweep-3{animation-delay:1.65s}.sweep-4{animation-delay:2.2s}',
    '@media (max-width:500px){.chip-name{font-size:32px}.group-label{font-size:24px}.monogram{font-size:20px}}',
  ];
  const rows = [];
  let item = 0;
  for (const [rowIndex, group] of groups.entries()) {
    const y = 24 + rowIndex * 60;
    const row = [];
    row.push(`<circle class="dot" cx="55" cy="${y + 23}" r="4" fill="${c.teal}"/>`);
    row.push(`<text class="group-label" x="70" y="${y + 30}" fill="${c.muted}" font-size="16" font-weight="600">${group.label}</text>`);
    row.push(`<g clip-path="url(#row-${rowIndex})"><path class="sweep sweep-${rowIndex}" d="M220 ${y + 2}h42l60 42h-42z" fill="url(#shine)"/></g>`);
    let x = 228;
    for (const [column, name] of group.names.entries()) {
      const width = 72 + name.length * 14;
      const start = rowIndex * .52 + column * .12;
      const end = start + .48;
      css.push(`@keyframes reveal-${item}{0%,${pct(start)}{opacity:0;transform:translateX(-16px)}${pct(end)},82%{opacity:1;transform:translateX(0)}94%,100%{opacity:0;transform:translateX(0)}}`);
      css.push(`.chip-${item}{animation:reveal-${item} 13s ease-in-out infinite}`);
      const tint = item % 3 === 2 ? c.pink : c.teal;
      row.push(`<g class="chip chip-${item}"><g class="${item % 2 ? 'float-b' : 'float-a'}">` +
        `<rect x="${x}" y="${y}" width="${width}" height="46" rx="23" fill="${c.chip}" stroke="${c.border}" stroke-width="1.5"/>` +
        icon(name, x + 14, y + 11, tint) +
        `<text class="chip-name" x="${x + 52}" y="${y + 31}" fill="${c.text}" font-size="16" font-weight="600">${escape(name)}</text></g></g>`);
      x += width + 12;
      item += 1;
    }
    if (x > 1178) throw new Error(`Row ${group.label} exceeds the canvas`);
    rows.push(`<g data-group="${escape(group.label)}">${row.join('')}</g>`);
  }
  css.push('@media (prefers-reduced-motion:reduce){.chip,.float-a,.float-b,.sweep,.dot{animation:none!important}.chip{opacity:1!important;transform:none!important}.sweep{opacity:0!important}}');
  const defs = groups.map((_, i) => `<clipPath id="row-${i}"><rect x="220" y="${24 + i * 60}" width="950" height="46"/></clipPath>`).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 340" role="img" aria-labelledby="title desc">\n` +
    `<title id="title">Stack</title><desc id="desc">${groups.map(group => `${group.label}: ${group.names.join(', ')}.`).join(' ')}</desc>\n` +
    `<style>${css.join('')}</style>\n<defs><pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="${c.grid}" stroke-opacity=".25"/></pattern>` +
    `<linearGradient id="shine"><stop stop-color="${c.teal}" stop-opacity="0"/><stop offset=".5" stop-color="${c.teal}" stop-opacity=".36"/><stop offset="1" stop-color="${c.teal}" stop-opacity="0"/></linearGradient>${defs}</defs>\n` +
    `<rect width="1200" height="340" rx="22" fill="${c.panel}"/><rect width="1200" height="340" rx="22" fill="url(#grid)"/>\n` +
    `${rows.join('\n')}\n</svg>\n`;
}

await mkdir(new URL('../assets/', import.meta.url), { recursive: true });
for (const theme of Object.keys(themes)) {
  const output = build(theme);
  if (Buffer.byteLength(output) >= 150_000) throw new Error(`${theme} SVG exceeds 150 KB`);
  await writeFile(new URL(`../assets/stack-${theme}.svg`, import.meta.url), output);
}
