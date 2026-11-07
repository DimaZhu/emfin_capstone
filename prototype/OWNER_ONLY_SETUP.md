# Owner-only setup: Ballast synthetic prototype

The Sheet has been created in tijsdeboer@gmail.com, with only its owner granted access:
https://docs.google.com/spreadsheets/d/1NjluLr3Az1blvah01W2raW6s3tayV1gWShqMyLgguFg/edit?authuser=tijsdeboer%40gmail.com

No Apps Script project or deployment has been created. The browser is signed out of Google. These files let you finish without giving anyone your password. Do not change Sheet or app access to anyone else unless you choose to do so yourself.

1. Open the Sheet while signed into tijsdeboer@gmail.com. Use Extensions > Apps Script. A new bound project opens. Name it `Ballast synthetic lookup`.
2. Replace the starter Code.gs with the supplied Code.gs.
3. Click + beside Files > HTML. Name the first file `Index` and replace its contents with supplied Index.html.
4. Add another HTML file named `Lookup`. Paste the contents of Lookup.js into it, with no added script tags.
5. Open Project Settings (gear). Under Script properties choose Add script property. Enter `GRID_SHEET_ID` as property and `1NjluLr3Az1blvah01W2raW6s3tayV1gWShqMyLgguFg` as value. Save.
6. Click Deploy > New deployment. Open the type selector (gear) and choose Web app. Description: `Synthetic coarse prototype - owner only`. Set Execute as to `Me (tijsdeboer@gmail.com)` and Who has access to `Only myself`. If this exact restriction is not available, stop rather than choose a broader audience.
7. Click Deploy. If prompted, authorize this project to read its Sheet. Check the account is tijsdeboer@gmail.com. This source reads the configured Sheet and serves its synthetic rows; it sends no email, changes no sharing and runs no Python optimizer. Do not authorize unfamiliar added scopes or a different project.
8. Copy the returned Web app URL. Open it in your signed-in browser. Check the synthetic/coarse label, total coverage, a completed lookup, and out-of-range rejection. A stored funding pass is not a safety guarantee.
9. Open the URL in an incognito/signed-out window. It must not reveal the grid. Check Deploy > Manage deployments still says Only myself. Close the test window.

The CSV, local HTML and JSON are snapshots, not a running service. The Sheet drives the app. Later Sheet updates appear on the next page load; source changes require a new deployment version. The app offers stored lookup only, not new portfolio optimization. Some combinations may have no feasible proposal even after their computation completes.

Never point GRID_SHEET_ID at a private Abu Dhabi/client-data Sheet. Synthetic labels do not settle inherited-code or market-data licensing. Resolve those rights before public release. You control any later sharing yourself.
