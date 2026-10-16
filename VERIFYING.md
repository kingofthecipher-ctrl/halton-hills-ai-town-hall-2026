# Verification and reproduction

## Inspect without running software

Compare the original screenshots with transcripts, then the original prompt and raw reviews with the six final columns. Read the correction log and the four narration edits. The source record intentionally includes model disagreement and superseded/error records.

## Recalculate

Run python3 verify.py from the repository root. No model API, API key, network connection or third-party Python package is required. It checks raw Markdown score tables, the recorded repairs, integer levels, weights, totals, CSV exports, original screenshot hashes, episode mappings, provenance hashes and all published file checksums.

Add --video /path/to/ai-town-hall-full-episode.mp4 to compare the release asset's SHA-256 and byte size. That identifies the exact checked export. It does not independently validate every spoken claim or subjective score.

## Recorded checks on the released video

production/verification.json records the final source-side checks: 98 scenes, 42 reviews, 252 weighted entries, narration/render-input fingerprints, all encoded AAC packets in source order, full decode, subtitles, fourteen chapters, audio levels and actual encoded open/blink states for six robot characters. Source-side recorded checks are distinct from what the standalone verifier reruns. Verification images are supplied for inspection. No successful OCR check is claimed.

## Reconstruct the presentation

The published episode JSON contains the saved script, source review references, edits, voices and scores. It does not ask models to regrade anything.

1. Work from the repository root. Use separate Python environments for audio and rendering, with the observed versions in production/requirements-audio.txt and production/requirements-render.txt.
2. The audio script requires the English spaCy model en_core_web_sm 3.8.0 and downloads or uses the pinned public Kokoro revision. A local model snapshot can be supplied with the KOKORO_SNAPSHOT environment variable. It contains model weights that are not bundled in this repo.
3. Run python production/make-audio.py, then python production/render.py --preview. Inspect the generated frames before running python production/render.py.
4. The released layout uses macOS Avenir Next at /System/Library/Fonts/Avenir Next.ttc and FFmpeg on PATH. The font is not bundled. Another font or platform may change wrapping and layout. Local absolute user paths were replaced for this public export.

The exported scripts preserve the production logic with repository-relative paths and pinned model lookup. Their syntax and rendering previews were checked on the original macOS host. A clean installation and full rebuild on another computer are not claimed to have been tested. Model, library, font, encoder and platform differences can change audio or bytes. The released MP4 and its checksum are the canonical artifact.

## What checks cannot establish

Hashes protect consistency with the published snapshot, not historical intent, preregistration or model-provider authenticity. Passing calculations cannot prove unbiased grading. Re-running a stochastic or changed model can produce different assessments. See FAIRNESS.md and data/model-provenance.json.
