import { build } from 'esbuild';
import { readFile, writeFile } from 'node:fs/promises';
await build({entryPoints:['src/reporting/ui/dashboard.ts'],bundle:true,minify:true,format:'iife',
  target:'es2022',outfile:'src/reporting/ui/dashboard.js',legalComments:'eof'});
// Dependency code-generation templates contain indented blank lines. Keep the
// checked-in artifact free of trailing whitespace without stripping legal notices.
const output='src/reporting/ui/dashboard.js';
await writeFile(output,(await readFile(output,'utf8')).replace(/^[\t ]+$/gm,''));
