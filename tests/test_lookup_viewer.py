import json,shutil,subprocess
from pathlib import Path
import pytest
from prototype.build_viewer import build
ROOT=Path(__file__).resolve().parents[1]


def test_pure_lookup_exact_nearest_range_and_private_rejection():
    if not shutil.which('node'):pytest.skip('node unavailable for JS reference check')
    code=r'''
const assert=require('assert');const f=require(process.argv[1]);
const data={source:'synthetic',axes:{profile:['A','B'],x:[0,.5,1]},rows:[{source:'synthetic',point:{profile:'A',x:.5},status:'complete'}]};
assert.equal(f.lookupGrid({profile:'A',x:.49},data).row.status,'complete');
assert.equal(f.snapPoint({profile:'A',x:.49},data.axes).point.x,.5);
assert.throws(()=>f.lookupGrid({profile:'A',x:2},data),/Outside/);
assert.throws(()=>f.lookupGrid({profile:'C',x:0},data),/Unsupported/);
assert.throws(()=>f.lookupGrid({profile:'A',x:0},{...data,source:'private'}),/synthetic/);
assert.equal(f.lookupGrid({profile:'A',x:0},data).status,'not precomputed');
'''
    subprocess.run(['node','-e',code,str(ROOT/'prototype/apps-script/Lookup.js')],check=True)


def test_builder_rejects_private_and_nonprototype_sources(tmp_path):
    folder=tmp_path/'source';folder.mkdir()
    (folder/'manifest.json').write_text(json.dumps(dict(spec=dict(axes={'x':[0]},tier='research'),expected_count=1)))
    (folder/'summary.json').write_text('[]')
    with pytest.raises(ValueError):build(folder,tmp_path/'out')
    (folder/'manifest.json').write_text(json.dumps(dict(spec=dict(axes={'x':[0]},tier='prototype',engine={},real_estate={}),expected_count=1)))
    (folder/'summary.json').write_text(json.dumps([{'source':'private'}]))
    with pytest.raises(ValueError):build(folder,tmp_path/'out')
