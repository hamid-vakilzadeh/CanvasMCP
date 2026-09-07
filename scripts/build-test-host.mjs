import { build } from 'esbuild';
await build({entryPoints:['tests/dashboard_host.ts'],bundle:true,format:'esm',target:'es2022',outfile:'/private/tmp/canvas-test-host.js'});
