# PaperPlane Autofill — Chrome Extension

A standalone Chrome (Manifest V3) extension that fills job-application forms from your
profile, uses an LLM (Gemini by default) for open-ended questions, learns your answers over
time, and lets you chat with an assistant that has context about you.

It is **standalone** — it does not need the paperplane Python backend running. It reuses the
same *logic* (field mapping, the yes-man answer prompts, answer validation, the `Applicant`
profile schema), ported to TypeScript.

## Quick start

```bash
cd extension
npm install
npm run dev          # or: npm run build   (outputs to dist/)
```

Then in Chrome:

1. Go to `chrome://extensions`, enable **Developer mode**.
2. **Load unpacked** → select `extension/dist`.
3. Click the toolbar icon → **Open side panel**.
4. **Settings** → paste your Gemini API key ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)).
5. **Profile** → **Import profile.json…** (pick `../data/profile.json`) and **Upload PDF** for your resume.
   - Tip: `npm run seed` prints your `data/profile.json` ready to paste.

## How it works

- **Local-first resolution.** Most fields (name, email, address, links, yes/no, dropdowns) are
  resolved by ported rules with **no** API call. Only open-ended free-text and genuinely
  ambiguous dropdowns hit the LLM, batched into **one** request per page.
- **Learning.** When you accept/edit a generated answer it's remembered per-question and reused
  on any future site — no LLM call.
- **Review step.** Auto-detected forms show an in-page badge; one click fills simple fields and
  shows review chips for AI/essay/sensitive fields (salary, visa, sponsorship are always
  reviewed, never silently filled).
- **Pluggable LLM.** Gemini today; a local **Ollama** engine is a drop-in (Settings → Provider).

## Layout

```
src/
  background/   service worker + message handlers (LLM calls, resume bytes)
  content/      detector + filler + Shadow-DOM review overlay (runs on pages)
  panel/        React side panel: Chat, Profile, Learned, Settings
  popup/        React toolbar popup
  lib/          ported logic: types, storage, profile, fieldMapper, llm,
                validator, learning, detect, fill, messaging
```

## Privacy

Everything lives in your browser (`chrome.storage.local` + IndexedDB for the resume). The only
network calls are to your chosen LLM provider (Gemini, or a local Ollama). Switch to Ollama for
fully-local, zero-cost inference.
