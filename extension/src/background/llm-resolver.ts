// Composes an LLMProvider + prompts into the LlmResolver the resolution pipeline
// needs (answer / answerBatch / selectOption), plus a chat() helper for the panel.

import type { Profile, Settings, JobContext, FieldOption } from '../lib/types'
import { getProvider } from '../lib/llm'
import {
  essayPrompt,
  batchPrompt,
  selectPrompt,
  buildContext,
  chatSystemPrompt,
} from '../lib/prompts'
import type { LlmResolver } from './resolve'
import type { ChatMessage } from '../lib/messaging'

export function makeLlmResolver(settings: Settings, profile: Profile): LlmResolver | null {
  const provider = getProvider(settings)
  if (!provider) return null

  const tone = settings.essayTone
  const maxLen = settings.essayMaxLength
  const strat = settings.answerStrategy

  async function answer(question: string, job: JobContext): Promise<string | null> {
    const ctx = buildContext(profile, question)
    return provider!.generate(essayPrompt(question, job, ctx, strat, tone, maxLen), {
      maxTokens: Math.ceil(maxLen / 3),
      temperature: 0.7,
    })
  }

  async function answerBatch(questions: string[], job: JobContext): Promise<(string | null)[]> {
    if (questions.length === 0) return []
    if (questions.length === 1) return [await answer(questions[0], job)]

    const ctx = buildContext(profile, questions.join(' '))
    const raw = await provider!.generate(batchPrompt(questions, job, ctx, strat, tone, maxLen), {
      maxTokens: Math.min(questions.length * Math.ceil(maxLen / 3), 2048),
      temperature: 0.7,
    })
    const parsed = tryParseArray(raw, questions.length)
    if (parsed) return parsed
    // Fall back to individual calls if the batch response wasn't parseable.
    return Promise.all(questions.map((q) => answer(q, job)))
  }

  async function selectOption(
    options: FieldOption[],
    label: string,
    job: JobContext,
  ): Promise<string | null> {
    const ctx = buildContext(profile, label)
    const out = await provider!.generate(selectPrompt(options, label, job, ctx, strat), {
      maxTokens: 40,
      temperature: 0.1,
    })
    if (!out || /^none$/i.test(out.trim())) return null
    return out.trim()
  }

  return { answer, answerBatch, selectOption }
}

/** Parse an LLM "return a JSON array" response robustly; returns null if it can't. */
function tryParseArray(raw: string | null, expected: number): string[] | null {
  if (!raw) return null
  let text = raw.trim()
  // strip markdown code fences
  text = text.replace(/^```(?:json)?/i, '').replace(/```$/, '').trim()
  // grab the outermost [ ... ]
  const start = text.indexOf('[')
  const end = text.lastIndexOf(']')
  if (start !== -1 && end > start) text = text.slice(start, end + 1)
  try {
    const arr = JSON.parse(text)
    if (Array.isArray(arr) && arr.every((x) => typeof x === 'string')) {
      // pad/trim to expected length
      const out = arr.slice(0, expected)
      while (out.length < expected) out.push('')
      return out
    }
  } catch {
    /* not parseable */
  }
  return null
}

/** Chat completion for the side panel (Phase 4 handler calls this). */
export async function chat(
  messages: ChatMessage[],
  profile: Profile,
  settings: Settings,
  job?: JobContext,
): Promise<string | null> {
  const provider = getProvider(settings)
  if (!provider) throw new Error('No LLM configured — add your Gemini key in Settings.')

  const system = chatSystemPrompt(profile)
  const jobLine = job?.title ? `\n\n(The user is currently viewing: ${job.title} at ${job.company}.)` : ''
  const transcript = messages
    .map((m) => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`)
    .join('\n')
  const prompt = `${transcript}${jobLine}\n\nAssistant:`
  return provider.generate(prompt, { system, maxTokens: 800, temperature: 0.7 })
}
