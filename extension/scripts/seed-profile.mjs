// One-off helper: read ../data/profile.json (the backend's profile) and print an
// import blob you can paste into the extension's Profile tab. This never leaves
// your machine.
//
//   node scripts/seed-profile.mjs            # prints the JSON
//   node scripts/seed-profile.mjs --copy     # (mac) copies to clipboard
//
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { spawn } from 'node:child_process'

const here = dirname(fileURLToPath(import.meta.url))
const profilePath = resolve(here, '..', '..', 'data', 'profile.json')

try {
  const raw = await readFile(profilePath, 'utf8')
  // Validate it parses; print pretty so it's paste-ready.
  const pretty = JSON.stringify(JSON.parse(raw), null, 2)

  if (process.argv.includes('--copy') && process.platform === 'darwin') {
    const pbcopy = spawn('pbcopy')
    pbcopy.stdin.write(pretty)
    pbcopy.stdin.end()
    console.error('✓ Profile copied to clipboard. Paste it into Profile → Import raw JSON.')
  } else {
    console.log(pretty)
    console.error(
      `\n✓ Read ${profilePath}. Copy the JSON above and paste into the extension's Profile tab (Advanced → edit raw JSON), or use the "Import profile.json…" button to pick the file directly.`,
    )
  }
} catch (err) {
  console.error(`✗ Could not read ${profilePath}: ${err.message}`)
  console.error('  Make sure data/profile.json exists in the repo root.')
  process.exit(1)
}
