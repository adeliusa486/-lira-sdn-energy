# Phase 1 — Literature Review & Reference Verification

**Goal:** Map the field, prove the gap, and build a bibliography where every entry has been checked against a source.
**Module:** `tools/verify_refs.py`  **Inputs:** `references_candidate.bib`, `LITERATURE_REVIEW.md`

## Steps
1. Read the seed papers listed in `LITERATURE_REVIEW.md` (sections A–H).
2. Search forward and backward from the seeds (Google Scholar "cited by", Semantic Scholar API) for 2021–2026 work on: ML/DRL for energy-aware SDN, ML replacing ILP for green TE, sleep-mode lifetime, network update consistency, online learning with switching costs, and concept drift in network traffic.
3. **Find the direct competitor(s):** the "snapshot ML classifier mapping TM → precomputed configuration" framework that the abstract argues against. Get the exact paper(s), venue, and reported numbers. These set baseline B4. If such a paper is the author's own earlier work, cite it and frame this paper as the follow-up.
4. Add each new paper to `references_candidate.bib` with DOI or URL.
5. Run `python tools/verify_refs.py references_candidate.bib`. It checks:
   - the DOI resolves on Crossref, and the title/year/first author match (fuzzy ratio ≥ 0.9);
   - arXiv IDs exist and the titles match;
   - entries with URL only: the URL returns HTTP 200.
6. Fix or delete every entry marked `MISMATCH` or `NOT_FOUND`. Never cite an entry you have not opened and read at least the abstract of.
7. Fill in the gap matrix (Section I of `LITERATURE_REVIEW.md`).

## Outputs
- `references_verified.bib` (only PASS entries), `results/ref_verification.csv`
- Completed gap matrix

## Exit gate
- ≥ 35 verified references, of which ≥ 15 are from 2021–2026
- Direct competitor(s) identified with their reported numbers
- 0 unverified entries in `references_verified.bib`
