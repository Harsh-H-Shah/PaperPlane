// Worker-side message handlers.
//   Phase 2: PING, GET_RESUME, RESOLVE_FIELDS (mapping/heuristics), LEARN_ANSWER.
//   Phase 3 adds the LLM to RESOLVE_FIELDS + REGENERATE; Phase 4 adds CHAT.

import type { Message, MsgResponse } from '../lib/messaging'
import { store, resumeStore } from '../lib/storage'
import { arrayBufferToBase64 } from '../lib/base64'
import { resolveFields, type ResolveDeps } from './resolve'
import { findLearned, learnAnswer } from '../lib/learning'
import { makeLlmResolver, chat } from './llm-resolver'

async function buildDeps(): Promise<ResolveDeps> {
  const [profile, settings] = await Promise.all([store.getProfile(), store.getSettings()])
  const llm = makeLlmResolver(settings, profile)
  return {
    profile,
    settings,
    llm: llm ?? undefined,
    learned: { find: findLearned },
  }
}

export async function handleWorkerMessage(
  msg: Message,
  _sender: chrome.runtime.MessageSender,
): Promise<MsgResponse> {
  switch (msg.type) {
    case 'PING':
      return { ok: true, count: 0 }

    case 'GET_RESUME': {
      const r = await resumeStore.load()
      if (!r) return { ok: false, error: 'No resume stored' }
      return { ok: true, base64: arrayBufferToBase64(r.bytes), name: r.name, mimeType: r.mimeType }
    }

    case 'RESOLVE_FIELDS': {
      const deps = await buildDeps()
      const resolved = await resolveFields(msg.fields, msg.job, deps)
      return { ok: true, resolved }
    }

    case 'REGENERATE': {
      const deps = await buildDeps()
      // Resolve just this one field, forcing a fresh LLM answer (ignore learned cache).
      const resolved = await resolveFields([msg.field], msg.job, {
        ...deps,
        learned: undefined,
      })
      return { ok: true, resolved: resolved[0] }
    }

    case 'LEARN_ANSWER':
      await learnAnswer(msg.question, msg.answer)
      return { ok: true, count: 0 }

    case 'CHAT': {
      const [profile, settings] = await Promise.all([store.getProfile(), store.getSettings()])
      const reply = await chat(msg.messages, profile, settings, msg.job)
      return { ok: true, reply: reply ?? '' }
    }

    default:
      return { ok: false, error: `Unknown message: ${(msg as { type?: string }).type}` }
  }
}
