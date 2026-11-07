/* Pure lookup logic, used unchanged in local and Apps Script viewers. */
function snapPoint(request, axes) {
  const point = {}, deltas = {};
  let distance2 = 0;
  for (const key of Object.keys(axes)) {
    const values = axes[key];
    if (!Array.isArray(values) || !values.length) throw Error('Invalid grid axis: ' + key);
    if (typeof values[0] === 'number') {
      const value = Number(request[key]);
      const low = Math.min(...values), high = Math.max(...values);
      if (!Number.isFinite(value) || value < low || value > high) throw Error('Outside precomputed range: ' + key);
      point[key] = values.reduce((best, x) => Math.abs(x-value)<Math.abs(best-value)?x:best, values[0]);
      deltas[key] = value-point[key];
      distance2 += (deltas[key]/(high-low || 1))**2;
    } else {
      if (!values.includes(request[key])) throw Error('Unsupported category: ' + key);
      point[key] = request[key]; deltas[key] = 0;
    }
  }
  return {point, deltas, distance: Math.sqrt(distance2)};
}
function lookupGrid(request, dataset) {
  if (dataset.source !== 'synthetic' || !dataset.axes || !Array.isArray(dataset.rows)) throw Error('Only a validated synthetic dataset is supported');
  const match = snapPoint(request, dataset.axes);
  const row = dataset.rows.find(r => Object.keys(dataset.axes).every(k=>r.point[k]===match.point[k]));
  if (!row) return {...match,row:null,status:'not precomputed'};
  if (row.source !== 'synthetic') throw Error('Private or unknown source rejected');
  return {...match,row,status:row.status};
}
if (typeof module !== 'undefined') module.exports={snapPoint,lookupGrid};
