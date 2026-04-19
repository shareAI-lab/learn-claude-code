import { MACRO } from '@constants/macros'
import type { Command } from '@commands'
import { RELEASE_NOTES } from '@constants/releaseNotes'

const releaseNotes: Command = {
  description: 'Show release notes for the current or specified version',
  isEnabled: false,
  isHidden: false,
  name: 'release-notes',
  userFacingName() {
    return 'release-notes'
  },
  type: 'local',
  async call(args) {
    const currentVersion = MACRO.VERSION

    const requestedVersion = args ? args.trim() : currentVersion

    const notes = RELEASE_NOTES[requestedVersion]

    if (!notes || notes.length === 0) {
      return `No release notes available for version ${requestedVersion}.`
    }

    const header = `Release notes for version ${requestedVersion}:`
    const formattedNotes = notes.map(note => `• ${note}`).join('\n')

    return `${header}\n\n${formattedNotes}`
  },
}

export default releaseNotes
