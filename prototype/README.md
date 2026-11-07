# Local synthetic lookup prototype

Nothing here deploys, uploads, creates a Google Sheet or changes access.
The owner must separately confirm deployment and intended audience.

## Build and inspect locally

```bash
python -m prototype.build_viewer --grid artifacts/grid729-prototype-final --output artifacts/lookup-viewer
# Open artifacts/lookup-viewer/index.html in a browser.
```

The builder accepts only the explicitly labelled prototype tier, forces synthetic
source checks and rejects private calibration. It exports HTML, compact JSON,
a single-column Sheet-import CSV and the prepared Apps Script source. The JSON
has allocations, KPIs, funding verdicts and provenance, not private raw prices.
An incomplete grid is usable for inspection: matched pending/error cells say
unavailable; the viewer never substitutes a nearby completed portfolio.

Numerical inputs snap independently to the nearest configured level, with
normalized numeric distance and requested/matched values visible. Categorical
inputs must match exactly. Out-of-range requests are rejected, not extrapolated.
Verdicts are never interpolated. A stored funding pass is conditional on the
coarse scenario model, not general risk approval or a new solve.

## Prepared Apps Script route, not performed

After owner confirmation of sharing and audience:

1. Import `synthetic-grid-sheet.csv` into a tab named `synthetic_grid` in an
   approved Google Sheet. Column A contains a header, metadata JSON, then one
   compact JSON object per grid cell. Do not paste the entire grid into one cell.
2. In an Apps Script project, add `Code.gs`, `Index.html`, and an HTML file named
   `Lookup.html` whose contents are the source `Lookup.js` (without script tags).
   `doGet` includes that pure lookup logic inside the page's script element.
3. Set script property `GRID_SHEET_ID` to the approved Sheet's ID. This is an
   identifier, not a secret. No credentials are stored in these source files.
4. Inspect access choices before deploying. Executing as owner versus viewer
   changes which account reads the Sheet. A public web app would disclose all
   embedded synthetic rows, even if the Sheet is private. Do not use hidden
   controls as access control, and never point this app at a private-data Sheet.
5. Deploy only after the owner approves audience and URL. Test as a member of
   that audience. Keep the coarse-data label and incomplete-cell behavior.

The prepared script reads the dataset once per page load and uses client-side
lookup. It does not run Python/CVXPY. For exact new solves, use a separately
secured Python backend; that is a different deployment, cost and authorization.
Current Google runtime/HTML guidance:
https://developers.google.com/apps-script/guides/html
https://developers.google.com/apps-script/guides/v8-runtime
https://developers.google.com/apps-script/guides/services/quotas

A synthetic source label does not erase inherited-code or market-data rights.
Settle licensing before a public release, even without the private Abu Dhabi data.
