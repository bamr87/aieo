import fs from 'node:fs';

const app = fs.readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
const requiredRoutes = [
  '/workspace',
  '/topics',
  '/research',
  '/drafts',
  '/rewrites',
  '/published',
  '/landing-pages',
  '/performance',
  '/agents',
];

for (const route of requiredRoutes) {
  if (!app.includes(`path="${route}"`)) {
    throw new Error(`Missing route: ${route}`);
  }
}

console.log('Frontend smoke check passed.');
