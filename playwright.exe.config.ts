import { defineConfig } from '@playwright/test';

process.env.VF_EMBALAGEM_API = 'http://127.0.0.1:3021';
export default defineConfig({
  testDir:'./e2e', testMatch:'embalagem.spec.ts', workers:1, retries:0,
  use:{baseURL:'http://127.0.0.1:3021',browserName:'chromium',viewport:{width:1366,height:900},trace:'off',screenshot:'off'},
  webServer:{command:'node e2e/servidor-exe.cjs',url:'http://127.0.0.1:3021/health',reuseExistingServer:false,timeout:90000},
});
