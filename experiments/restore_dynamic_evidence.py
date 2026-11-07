"""Restore archived frozen dynamic results into the ignored local artifact folder."""
from pathlib import Path
import shutil


def main():
    source=Path('docs/evidence/dynamic-policy-20261107/studies');dest=Path('artifacts/dynamic-policy-20261107')
    if not source.exists():raise FileNotFoundError('archived dynamic evidence missing')
    dest.mkdir(parents=True,exist_ok=True)
    for p in source.rglob('*'):
        if p.is_file():
            target=dest/p.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and target.read_bytes()!=p.read_bytes():raise FileExistsError('Refusing to overwrite changed local evidence: '+str(target))
            if not target.exists():shutil.copy2(p,target)
    print('Archived frozen results restored. No paths generated or policies reselected.')

if __name__=='__main__':main()
