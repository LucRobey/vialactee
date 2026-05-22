# Current Objectives

## Completed ✅
- [x] Copy core algorithm to BeatTracking_Evaluation_Test.ipynb
- [x] Implement Phase Flywheel logic
- [x] Implement mir_eval metric calculation
- [x] Benchmark 12-song dataset and export `full_benchmark_results.pkl`
- [x] Build automated failure window plotting (visualizing phase, LTM class, and circular distance)
- [x] Analyze True Positives, False Positives, and Failure Modes

## Next Steps: Algorithm Refinement 🚀
- [x] **Tune Groove Distance Penalty:** Reduce the strict change threshold from `0.30` to `~0.25` to prevent the tracker from becoming "stubborn" and getting stuck on wrong metrical levels in complex electronic tracks (e.g., *Nobody Rules the Streets*).
- [x] **Filterbank Isolation:** Reduce Custom Flux sensitivity to mid-range melodic transients (guitars/vocals) to lower False Positives. Tune `FakeListener` to isolate low-end (Kick) and high-end (Snare/Hi-hat) more aggressively (e.g., *Money For Nothing*).
- [ ] **Downbeat Weighting:** Add a heuristic to strongly prefer phase alignment with low-frequency transients, solving the phase-inversion problem where the tracker perfectly matches BPM but locks onto the upbeat (e.g., *Stayin' Alive*).
- [ ] **Hardware Migration:** Once the algorithm is tuned and the benchmark scores improve, port the `FastTemplateBank` and `Groove Distance Penalty` logic into the production C++/Python environment for the Raspberry Pi.
