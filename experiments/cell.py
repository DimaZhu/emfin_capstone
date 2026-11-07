"""One isolated bounded grid cell. Internal entry point."""
import argparse,json
from pathlib import Path
from experiments.grid import run_cell
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--job',required=True);a=p.parse_args()
    job=json.loads(Path(a.job).read_text());result=run_cell(job)
    (Path(a.job).parent/'cell_result.json').write_text(json.dumps(result)+'\n')
