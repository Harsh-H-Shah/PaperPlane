import { defineManifest } from '@crxjs/vite-plugin'
import pkg from './package.json'

export default defineManifest({
  manifest_version: 3,
  name: 'PaperPlane Autofill',
  version: pkg.version,
  description: pkg.description,
  icons: {
    16: 'icons/icon16.png',
    32: 'icons/icon32.png',
    48: 'icons/icon48.png',
    128: 'icons/icon128.png',
  },
  action: {
    default_title: 'PaperPlane Autofill',
    default_popup: 'src/popup/index.html',
    default_icon: {
      16: 'icons/icon16.png',
      32: 'icons/icon32.png',
      48: 'icons/icon48.png',
      128: 'icons/icon128.png',
    },
  },
  background: {
    service_worker: 'src/background/service-worker.ts',
    type: 'module',
  },
  side_panel: {
    default_path: 'src/panel/index.html',
  },
  content_scripts: [
    {
      matches: ['<all_urls>'],
      js: ['src/content/detector.ts'],
      run_at: 'document_idle',
      // Many ATS forms (Greenhouse/Lever/Ashby embeds) live in an iframe on the
      // company's careers page, so we must run in sub-frames too.
      all_frames: true,
    },
  ],
  permissions: ['storage', 'activeTab', 'scripting', 'sidePanel', 'tabs'],
  host_permissions: ['<all_urls>', 'https://generativelanguage.googleapis.com/*'],
})
