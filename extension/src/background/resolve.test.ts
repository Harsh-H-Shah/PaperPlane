import { describe, it, expect } from 'vitest'
import { resolveFields } from './resolve'
import { emptyProfile, defaultSettings } from '../lib/storage'
import type { DetectedField, JobContext } from '../lib/types'

const job: JobContext = { title: 'Engineer', company: 'Acme', url: 'https://acme.test' }

function resolve(fields: DetectedField[]) {
  return resolveFields(fields, job, { profile: emptyProfile(), settings: defaultSettings() })
}

describe('resolveFields — options without an LLM', () => {
  it('picks Yes for a willingness radio', async () => {
    const [r] = await resolve([
      {
        id: 'a',
        label: 'Are you willing to relocate?',
        type: 'radio',
        options: [
          { label: 'Yes', value: 'yes' },
          { label: 'No', value: 'no' },
        ],
      },
    ])
    expect(r.value).toBe('Yes')
    expect(r.source).toBe('heuristic')
  })

  it('matches a country dropdown', async () => {
    const [r] = await resolve([
      {
        id: 'b',
        label: 'Country',
        type: 'select',
        options: [
          { label: 'Canada', value: 'CA' },
          { label: 'United States', value: 'US' },
        ],
      },
    ])
    expect(r.value).toBe('United States')
  })

  it('ticks a required consent checkbox', async () => {
    const [r] = await resolve([
      {
        id: 'c',
        label: 'I certify the information provided is true and complete',
        type: 'checkbox',
        required: true,
        options: [{ label: 'I certify…', value: 'true' }],
      },
    ])
    expect(r.value).toBe('true')
  })

  it('does NOT auto-tick an optional marketing checkbox', async () => {
    const [r] = await resolve([
      {
        id: 'd',
        label: 'Subscribe me to the newsletter',
        type: 'checkbox',
        required: false,
        options: [{ label: 'Subscribe', value: 'true' }],
      },
    ])
    expect(r.source).toBe('none')
  })

  it('routes salary questions to review', async () => {
    const [r] = await resolve([{ id: 'e', label: 'Desired salary', type: 'text' }])
    // no LLM, so no value, but the review gate only flags resolved fields; salary text is unmapped
    expect(r.source).toBe('none')
  })
})
