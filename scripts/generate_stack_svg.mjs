#!/usr/bin/env node
/** Build the profile stack artwork from locally installed CC0 simple-icons paths. */
import * as simpleIcons from 'simple-icons';
import { mkdir, writeFile } from 'node:fs/promises';

const groups = [
  { label: 'Backend', names: ['Python', 'FastAPI', 'Go', 'Rust', 'Java', 'PostgreSQL'] },
  { label: 'Frontend', names: ['React', 'TypeScript', 'Vite', 'Tailwind CSS'] },
  { label: 'Data / ML', names: ['scikit-learn', 'XGBoost'] },
  { label: 'Tools', names: ['Git', 'GitHub Actions', 'Docker', 'Docker Compose', 'Linux'] },
];
const iconKeys = {
  Python: 'siPython', FastAPI: 'siFastapi', PostgreSQL: 'siPostgresql', Go: 'siGo',
  React: 'siReact', TypeScript: 'siTypescript', Vite: 'siVite',
  'Tailwind CSS': 'siTailwindcss', Docker: 'siDocker', 'GitHub Actions': 'siGithubactions',
  'scikit-learn': 'siScikitlearn', XGBoost: 'siXgboost', Rust: 'siRust', Java: 'siJava',
  Git: 'siGit', 'Docker Compose': 'siDockercompose', Linux: 'siLinux',
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
    return `<svg x="${x}" y="${y}" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><path fill="${tint}" d="${entry.path}"/></svg>`;
  }
  // Deliberate fallback: no alternate brand may replace a missing icon.
  const initials = name === 'Java' ? 'Ja' : name === 'XGBoost' ? 'XG' : name === 'Docker Compose' ? 'DC' : name.slice(0, 2);
  return `<circle cx="${x + 8}" cy="${y + 8}" r="8" fill="${tint}" opacity=".18"/>` +
    `<text class="monogram" x="${x + 8}" y="${y + 11}" text-anchor="middle" fill="${tint}" font-size="9" font-weight="700">${escape(initials)}</text>`;
}

function build(theme) {
  const c = themes[theme];
  const css = [
    'svg{font-family:system-ui,-apple-system,"Segoe UI",sans-serif}',
    '@keyframes float-a{50%{transform:translateY(-1.5px)}}',
    '@keyframes float-b{50%{transform:translateY(1.5px)}}',
    '@keyframes glow{0%,14%{opacity:0;stroke-dashoffset:112}18%,75%{opacity:.8}82%,100%{opacity:0;stroke-dashoffset:0}}',
    '@keyframes sweep{0%,28%{opacity:0;transform:translateX(-220px)}34%{opacity:.32}60%,100%{opacity:0;transform:translateX(850px)}}',
    '.float-a{animation:float-a 4.8s ease-in-out infinite}',
    '.float-b{animation:float-b 5.4s ease-in-out -2.2s infinite}',
    '.sweep{opacity:0;animation:sweep 13s ease-in-out infinite}',
    '.glow{opacity:0;animation:glow 13s linear infinite}',
    '@media (max-width:500px){.chip-name{font-size:19px}.group-label{font-size:19px}.monogram{font-size:11px}}',
  ];
  const cards = [];
  let item = 0;
  const positions = [
    { x: 12, y: 12, width: 360, height: 137 },
    { x: 384, y: 12, width: 364, height: 125 },
    { x: 12, y: 161, width: 360, height: 85 },
    { x: 384, y: 143, width: 364, height: 145 },
  ];
  for (const [cardIndex, group] of groups.entries()) {
    const box = positions[cardIndex];
    const start = cardIndex * .3;
    css.push(`@keyframes card-${cardIndex}{0%,${pct(start)}{opacity:0;transform:translateY(7px)}${pct(start + .45)},86%{opacity:1;transform:translateY(0)}96%,100%{opacity:0;transform:translateY(0)}}`);
    css.push(`.card-${cardIndex}{animation:card-${cardIndex} 13s ease-in-out infinite}`);
    css.push(`.glow-${cardIndex}{animation-delay:${(cardIndex * .42).toFixed(2)}s}`);
    const left = box.x + 13;
    const right = box.x + box.width - 13;
    let x = left;
    let y = box.y + 35;
    const chips = [];
    for (const [column, name] of group.names.entries()) {
      const width = 36 + name.length * 10.5;
      if (x + width > right) { x = left; y += 36; }
      if (y + 28 > box.y + box.height - 9) throw new Error(`${group.label} chips overflow card`);
      const entrance = start + .32 + column * .06;
      css.push(`@keyframes chip-${item}{0%,${pct(entrance)}{opacity:0;transform:translateY(4px) scale(.96)}${pct(entrance + .3)},86%{opacity:1;transform:translateY(0) scale(1)}96%,100%{opacity:0;transform:translateY(0) scale(1)}}`);
      css.push(`.chip-${item}{animation:chip-${item} 13s ease-in-out infinite}`);
      const tint = item % 3 === 2 ? c.pink : c.teal;
      chips.push(`<g class="chip chip-${item}"><g class="${item % 2 ? 'float-b' : 'float-a'}">` +
        `<rect x="${x}" y="${y}" width="${width}" height="28" rx="14" fill="${c.chip}" stroke="${c.border}" stroke-width="1"/>` +
        icon(name, x + 8, y + 6, tint) +
        `<text class="chip-name" x="${x + 30}" y="${y + 19.5}" fill="${c.text}" font-size="15" font-weight="600">${escape(name)}</text></g></g>`);
      x += width + 8;
      item += 1;
    }
    cards.push(`<g class="card card-${cardIndex}" data-group="${escape(group.label)}">` +
      `<rect x="${box.x}" y="${box.y}" width="${box.width}" height="${box.height}" rx="17" fill="${c.chip}" stroke="${c.border}"/>` +
      `<rect class="glow glow-${cardIndex}" x="${box.x + 1}" y="${box.y + 1}" width="${box.width - 2}" height="${box.height - 2}" rx="16" fill="none" stroke="${c.teal}" stroke-width="2" pathLength="100" stroke-dasharray="12 88"/>` +
      `<text class="group-label" x="${box.x + 14}" y="${box.y + 24}" fill="${c.muted}" font-size="15" font-weight="700" letter-spacing="1">${escape(group.label.toUpperCase())}</text>` + chips.join('') + '</g>');
  }
  if (item > 24) throw new Error('More than 24 chips');
  css.push('@media (prefers-reduced-motion:reduce){.card,.chip,.float-a,.float-b,.glow,.sweep{animation:none!important}.card,.chip{opacity:1!important;transform:none!important}.glow,.sweep{opacity:0!important}}');
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 300" role="img" aria-labelledby="title desc">\n` +
    `<title id="title">Stack</title><desc id="desc">${groups.map(group => `${group.label}: ${group.names.join(', ')}.`).join(' ')}</desc>\n` +
    `<style>${css.join('')}</style>\n<defs><pattern id="grid" width="25" height="25" patternUnits="userSpaceOnUse"><path d="M25 0H0V25" fill="none" stroke="${c.grid}" stroke-opacity=".22"/></pattern>` +
    `<linearGradient id="shine"><stop stop-color="${c.teal}" stop-opacity="0"/><stop offset=".5" stop-color="${c.teal}" stop-opacity=".36"/><stop offset="1" stop-color="${c.teal}" stop-opacity="0"/></linearGradient><clipPath id="panel"><rect width="760" height="300" rx="20"/></clipPath></defs>\n` +
    `<rect width="760" height="300" rx="20" fill="${c.panel}"/><rect width="760" height="300" rx="20" fill="url(#grid)"/>\n` +
    `${cards.join('\n')}\n<g clip-path="url(#panel)"><path class="sweep" d="M0 0h70l145 300h-70z" fill="url(#shine)"/></g>\n</svg>\n`;
}

await mkdir(new URL('../assets/', import.meta.url), { recursive: true });
for (const theme of Object.keys(themes)) {
  const output = build(theme);
  if (Buffer.byteLength(output) >= 150_000) throw new Error(`${theme} SVG exceeds 150 KB`);
  await writeFile(new URL(`../assets/stack-${theme}.svg`, import.meta.url), output);
}
