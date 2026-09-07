import { defineConfig } from '@playwright/test';
export default defineConfig({testDir:'tests',testMatch:'dashboard.spec.js',timeout:30000,workers:1,
  outputDir:'/private/tmp/canvas-dashboard-test-results',reporter:'list',
  use:{baseURL:'http://127.0.0.1:8765',viewport:{width:1440,height:1080},headless:true,
    launchOptions:process.env.CANVAS_TEST_BROWSER_PATH ? {executablePath:process.env.CANVAS_TEST_BROWSER_PATH}:{}},
  webServer:{command:'node scripts/build-dashboard.mjs && node scripts/build-test-host.mjs && .venv/bin/python tests/dashboard_server.py',
    url:'http://127.0.0.1:8765',reuseExistingServer:false,timeout:30000}});
