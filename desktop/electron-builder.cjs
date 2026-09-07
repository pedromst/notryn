const path = require('node:path');

const root = path.resolve(__dirname, '..');
const sidecar = process.env.NOTRYN_SIDECAR_DIR;
if (!sidecar) throw new Error('NOTRYN_SIDECAR_DIR is required.');

module.exports = {
  appId: 'com.notryn.app',
  productName: 'Notryn',
  copyright: 'Copyright 2026 Notryn contributors',
  directories: { output: process.env.NOTRYN_ELECTRON_OUTPUT || path.join(root, '.build', 'electron') },
  files: ['desktop/main.cjs'],
  extraResources: [{ from: sidecar, to: 'notryn' }],
  npmRebuild: false,
  asar: true,
  publish: null,
  mac: {
    category: 'public.app-category.productivity',
    icon: path.join(root, '.build', 'macos', 'Notryn.icns'),
    identity: null,
    hardenedRuntime: false,
    target: [{ target: 'dir', arch: ['x64'] }],
  },
  linux: {
    category: 'Office',
    icon: path.join(root, 'web', 'favicon.svg'),
    target: [{ target: 'AppImage', arch: ['x64'] }],
    artifactName: 'Notryn-${version}-linux-x86_64.AppImage',
  },
};
