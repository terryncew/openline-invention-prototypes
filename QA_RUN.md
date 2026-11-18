# Independent execution notes, 2026-11-17

- Original source archive recovered from owner's connected Drive: `OPENLINE_REALITY_GROUNDED_FRONTIER_INVENTION_001_PACKAGE.zip`.
- Argon report screened seven families A–G and selected A; finalist C distinct, D held.
- Inspected original code: Argon's C comparator `evaluate_finalist2_shmc_sts3215()` directly assigns outcomes for four scenario strings, so reported 39/40 is a constructed benchmark target, not a bus-level simulation.
- Original package contained 19 ZIP entries and references an unbundled `work_013` runtime for its standalone execution. This new package is separately written, dependency-free and not claimed as a full reproduction of the Argon engine.
- New source executes no physical I/O and does not claim hardware measurement or receipt custody.
- Authored and ran `python -m unittest discover -s tests -v` and `python -O -m unittest discover -s tests -v`: 27/27 PASS in each mode.
- Ran `python run_portfolio.py` and `python -O run_portfolio.py`: 1,000/1,000 defined input safety invariants, 1,000/1,000 defined servo route safety invariants. These are generated cases, not independent hardware evaluation.
- The tremor model shows 6/37 frequency bins improved, 31/37 worse. Uncalibrated and not person-specific.
- Used Matplotlib to generate all figures from the generated data; rendered PDF previews for inspection; used Pandoc + XeLaTeX for PDFs.
- Prior-art comparison includes existing low-cost mouth-mouse/sip-and-puff devices and standard SO-101 Feetech serial motor bus designs.
- External product, clinical, safety, manufacturing, durability, pricing, licensing and DOI acceptance all remain UNPROVEN or NOT RUN.
