# Notice and attribution

EMFin V2, version 2.1.0, is Tijs de Boer's V2 project. New V2 work is attributed
to Tijs de Boer. This attribution does not reassign rights in inherited material
or imply that he personally authored every underlying utility.

Inherited capstone material and its rights remain with the original authors.
Original files, their author metadata and a commit/hash provenance record are
preserved under legacy/. Active derived modules are identified in
legacy/ATTRIBUTION.md. Git history and the fork relationship are unchanged.
V2 is not represented as a wholly clean-room codebase.

Active derived utilities include data_types.py and toolbox cache.py,
normal_market.py, price.py, returns.py and scenario_market.py, with configuration
also descended from the original tree. Original main commit and per-file hashes
are recorded in legacy/original-provenance.json in the source checkout. The
standalone wheel does not include the legacy notebook or original source archive.

No open-source licence is granted to mixed or inherited code by this notice.
The licence for new V2 work is to be decided before any separate public release.
Existing rights and any applicable original terms remain unaffected. A version
tag or local wheel is not permission to redistribute data or inherited code.

## Data and third-party work

The bundled manifests are authoritative records of the collected sources,
access dates, file hashes and known terms/limits:

- emfin_v2/resources/data/snapshot/manifest.json: Yahoo/yfinance adjusted ETF
  closes and the CBOE 10Y Treasury yield index. Market-data rights are separate
  from the software. Verify redistribution rights before publication.
- emfin_v2/resources/data/raw/manifest.json: ICE BofA OAS via FRED (ICE
  redistribution terms need review), US Treasury DGS3MO via FRED (government
  data, cite source), and BIS UAE RPPI via FRED (REIDIN national source,
  BIS permitted-use terms and source attribution; data are stale and national,
  not an Abu Dhabi index). See the manifest's exact source URLs and terms.

NumPy, pandas, SciPy, CVXPY and their transitive dependencies retain their own
licences. The BSD entropy-pooling package is only a development reference, not
an installed V2 runtime dependency. No GPL fortitudo.tech dependency is used.
Public method references are listed in the model documentation and source.
Synthetic liabilities, views and RE scenarios are not supplied client evidence.
