"""Explicit staging download. Never overwrites pinned data or grants a licence.

Example: python scripts/fetch_raw_drop.py --url VERIFIED_CSV_URL --output /tmp/drop.csv
Inspect the file and source terms, then deliberately update the manifest and hash.
"""
import argparse,csv,io,hashlib
from pathlib import Path
from urllib.request import urlopen,Request


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',required=True);p.add_argument('--output',required=True)
    args=p.parse_args()
    if not args.url.startswith('https://'):p.error('HTTPS source required')
    out=Path(args.output)
    if out.exists():p.error('staging output already exists; choose a new path')
    with urlopen(Request(args.url,headers={'User-Agent':'capstone-data-staging/1'}),timeout=30) as response:
        content=response.read(20_000_001)
    if len(content)>20_000_000:raise ValueError('download exceeded 20MB staging limit')
    text=content.decode('utf-8-sig');rows=list(csv.reader(io.StringIO(text)))
    if len(rows)<2 or len(rows[0])<2 or '<html' in text.lower():raise ValueError('not a nonempty multi-column CSV')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(content)
    print(out,hashlib.sha256(content).hexdigest())
    print('Staged only. Review licence/data before any manifest update or publication.')

if __name__=='__main__':main()
