// Per-field resolution pipeline (runs in the worker). Order:
//   1. learned answer  2. direct/fuzzy mapping  3. heuristics  4. LLM
// then an always-review keyword gate. The `llm` and `learned` deps are optional
// so Phase 2 works with mapping/heuristics alone (no API key).

import type {
  DetectedField,
  JobContext,
  Profile,
  ResolvedField,
  Settings,
  FieldOption,
} from '../lib/types'
import {
  resolveBasic,
  getBooleanAnswer,
  getDropdownValue,
  matchOption,
  normalizeLabel,
} from '../lib/fieldMapper'
import { RESUME_SENTINEL } from '../lib/fill'
import { assessAnswer } from '../lib/validator'

export interface LlmResolver {
  /** Free-text answer for an essay/open question. */
  answer(question: string, job: JobContext): Promise<string | null>
  /** Batch of essay/open questions -> answers in the same order. */
  answerBatch(questions: string[], job: JobContext): Promise<(string | null)[]>
  /** Pick one option from a list. */
  selectOption(options: FieldOption[], label: string, job: JobContext): Promise<string | null>
}

export interface LearnedLookup {
  find(normalizedQuestion: string): Promise<string | null>
}

export interface ResolveDeps {
  profile: Profile
  settings: Settings
  llm?: LlmResolver
  learned?: LearnedLookup
}

const CONF = { learned: 0.95, mapping: 0.9, heuristic: 0.75, llm: 0.6, none: 0 }

function matchesReviewKeyword(label: string, keywords: string[]): string | null {
  const l = label.toLowerCase()
  for (const k of keywords) if (k && l.includes(k.toLowerCase())) return k
  return null
}

function boolToText(v: boolean): string {
  return v ? 'Yes' : 'No'
}

function isEssayField(f: DetectedField): boolean {
  return f.type === 'textarea' || (f.type === 'text' && f.label.length > 40)
}

function none(id: string): ResolvedField {
  return { id, value: '', source: 'none', confidence: 0, needsReview: false }
}

/** Resolve one field WITHOUT the LLM (steps 1–3). Returns null value/source 'none'
 *  if nothing local matched, so the caller can batch it to the LLM. */
async function resolveLocal(
  f: DetectedField,
  deps: ResolveDeps,
): Promise<ResolvedField> {
  const { profile, learned } = deps

  // 1. learned answer (by normalized label)
  if (learned) {
    const hit = await learned.find(normalizeLabel(f.label))
    if (hit) return { id: f.id, value: hit, source: 'learned', confidence: CONF.learned, needsReview: false, question: f.label, isEssay: isEssayField(f) }
  }

  switch (f.type) {
    case 'text':
    case 'email':
    case 'tel':
    case 'url':
    case 'number': {
      const v = resolveBasic(f.label, profile)
      if (v !== null && typeof v !== 'boolean' && v !== '') {
        return { id: f.id, value: v, source: 'mapping', confidence: CONF.mapping, needsReview: false }
      }
      if (typeof v === 'boolean') {
        return { id: f.id, value: boolToText(v), source: 'mapping', confidence: CONF.mapping, needsReview: false }
      }
      return none(f.id)
    }

    case 'textarea': {
      const v = resolveBasic(f.label, profile)
      if (typeof v === 'string' && v) {
        return { id: f.id, value: v, source: 'mapping', confidence: CONF.mapping, needsReview: false }
      }
      return none(f.id) // essay → LLM step
    }

    case 'select':
    case 'radio': {
      const opts = f.options ?? []
      const match = getDropdownValue(opts, f.label, profile)
      if (match) {
        return { id: f.id, value: match.label, source: 'heuristic', confidence: CONF.heuristic, needsReview: false }
      }
      return none(f.id)
    }

    case 'checkbox': {
      const opts = f.options ?? []
      if (opts.length <= 1) {
        const b = getBooleanAnswer(f.label, profile)
        if (b !== null) {
          return { id: f.id, value: b ? 'true' : 'false', source: 'heuristic', confidence: CONF.heuristic, needsReview: false }
        }
        // Yes-man: tick required / consent / certification boxes (needed to submit),
        // but never auto-tick optional opt-ins (marketing, etc.).
        const consent = /agree|consent|certif|terms|privacy|acknowledge|authorize|gdpr|accurate|true and complete/i
        if (f.required || consent.test(f.label)) {
          return { id: f.id, value: 'true', source: 'heuristic', confidence: CONF.heuristic, needsReview: false }
        }
        return none(f.id)
      }
      const match = getDropdownValue(opts, f.label, profile)
      if (match) {
        return { id: f.id, value: match.label, source: 'heuristic', confidence: CONF.heuristic, needsReview: false }
      }
      return none(f.id)
    }

    case 'combobox': {
      // Custom single-select (location, school, degree…). Try label mapping first.
      const v = resolveBasic(f.label, profile)
      if (typeof v === 'string' && v) {
        return { id: f.id, value: v, source: 'mapping', confidence: CONF.mapping, needsReview: false }
      }
      if (typeof v === 'boolean') {
        return { id: f.id, value: boolToText(v), source: 'mapping', confidence: CONF.mapping, needsReview: false }
      }
      return none(f.id) // LLM step handles it if options are known
    }

    case 'file': {
      if (/resume|cv|curriculum/i.test(f.label) || /resume|cv/i.test(f.name ?? '')) {
        return { id: f.id, value: RESUME_SENTINEL, source: 'mapping', confidence: CONF.mapping, needsReview: false }
      }
      return none(f.id)
    }

    default:
      return none(f.id)
  }
}

/** Full resolve for all fields, batching LLM-bound essays into a single request. */
export async function resolveFields(
  fields: DetectedField[],
  job: JobContext,
  deps: ResolveDeps,
): Promise<ResolvedField[]> {
  const { settings, llm } = deps

  // Step 1–3 locally.
  const resolved = await Promise.all(fields.map((f) => resolveLocal(f, deps)))
  const byId = new Map(resolved.map((r) => [r.id, r]))
  const fieldById = new Map(fields.map((f) => [f.id, f]))

  // Step 4: LLM for anything still unresolved.
  if (llm) {
    const unresolved = resolved.filter((r) => r.source === 'none')

    // 4a. Essays / open text -> batch. Only genuinely open-ended fields go to the
    // LLM; short unmapped inputs are left blank rather than hallucinated.
    const essayFields = unresolved
      .map((r) => fieldById.get(r.id)!)
      .filter((f) => isEssayField(f))
    if (essayFields.length > 0) {
      const answers = await llm.answerBatch(essayFields.map((f) => f.label), job)
      essayFields.forEach((f, i) => {
        const a = answers[i]
        if (a) {
          byId.set(f.id, {
            id: f.id,
            value: a,
            source: 'llm',
            confidence: CONF.llm,
            needsReview: true, // generated answers are always reviewed
            reviewReason: assessAnswer(a, f.label) ?? undefined,
            isEssay: f.type === 'textarea',
            question: f.label,
          })
        }
      })
    }

    // 4b. Option pickers (select/radio + multi-checkbox groups) -> per field.
    // Single checkboxes are handled locally so the LLM can't tick stray opt-ins.
    const optionFields = unresolved.map((r) => fieldById.get(r.id)!).filter((f) => {
      const n = f.options?.length ?? 0
      if (f.type === 'select' || f.type === 'radio') return n > 0
      if (f.type === 'checkbox') return n > 1
      return false
    })
    await Promise.all(
      optionFields.map(async (f) => {
        const choice = await llm.selectOption(f.options!, f.label, job)
        if (choice) {
          const match = matchOption(f.options!, choice)
          if (match) {
            byId.set(f.id, {
              id: f.id,
              value: match.label,
              source: 'llm',
              confidence: CONF.llm,
              needsReview: false,
            })
          }
        }
      }),
    )
  }

  // Always-review keyword gate (applies regardless of source).
  const out: ResolvedField[] = []
  for (const f of fields) {
    const r = byId.get(f.id)!
    const kw = matchesReviewKeyword(f.label, settings.alwaysReviewKeywords)
    if (kw && r.source !== 'none') {
      out.push({ ...r, needsReview: true, reviewReason: r.reviewReason ?? `Sensitive topic: ${kw}`, question: r.question ?? f.label })
    } else {
      out.push(r)
    }
  }
  return out
}
