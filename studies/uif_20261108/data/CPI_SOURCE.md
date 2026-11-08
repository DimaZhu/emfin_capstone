# CPI data provenance

- Series: BLS CUUR0000SA0 (CPI-U, all items, US city average, not seasonally adjusted), monthly.
- Pulled via the BLS public API (no key), 8 Nov 2026, three decade windows 1996-2025.
- 359 monthly observations, Jan 1996 - Dec 2025; Oct 2025 missing at source (dropped).
- sha256 of cpiu_nsa_bls_1996_2025.csv: f0f33649f5f8caa8e3cbfa245857de1a6e488772d0bad2c33be31e16a537ddfc
- FRED (CPIAUCSL) was unavailable (site maintenance) at fetch time; BLS is the primary source.
- Fit used in study3_inflation.py: monthly log-change mean 0.00207, sd 0.00357 (2.52%/yr mean).
