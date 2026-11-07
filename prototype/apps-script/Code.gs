/** Prepared only. No deployment or sharing is performed by these files. */
function doGet() {
  const template = HtmlService.createTemplateFromFile('Index');
  template.data = JSON.stringify(readSyntheticGrid_()).replace(/</g,'\\u003c');
  template.lookup = HtmlService.createHtmlOutputFromFile('Lookup').getContent();
  return template.evaluate().setTitle('Ballast | precomputed synthetic prototype');
}
function readSyntheticGrid_() {
  // Configure this non-secret ID only after the owner approves a Sheet mirror.
  const id = PropertiesService.getScriptProperties().getProperty('GRID_SHEET_ID');
  if (!id) throw new Error('GRID_SHEET_ID is not configured. No dataset was shared.');
  const sheet = SpreadsheetApp.openById(id).getSheetByName('synthetic_grid');
  if (!sheet) throw new Error('Expected synthetic_grid tab');
  const cells = sheet.getDataRange().getValues();
  if (cells.length < 2 || cells[0][0] !== 'dataset') throw new Error('Invalid dataset header');
  const dataset = JSON.parse(String(cells[1][0]));
  if (dataset.source !== 'synthetic' || !Array.isArray(dataset.rows)) throw new Error('Private or unknown grid rejected');
  // For larger grids use chunked rows, not one cell containing the whole grid.
  dataset.rows = cells.slice(2).filter(r=>r[0]).map(r=>JSON.parse(String(r[0])));
  if (dataset.rows.some(r=>r.source!=='synthetic')) throw new Error('Mixed-source grid rejected');
  return dataset;
}
