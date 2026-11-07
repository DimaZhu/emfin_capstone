"""Validate and install a local private sheet export. Never commits it.

JSON: {tabs:[{range:'AD_Apt_Monthly!...',values:[[...],...]}]} or a
CSV download of the AD_Apt_Monthly tab (including the top explanation rows).
"""
from pathlib import Path
import argparse,csv,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from emfin_v2.abu_dhabi import load_observed


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True)
    p.add_argument('--output',default=str(Path.home()/'.config/emfin-v2/abu_dhabi_sheet.json'))
    args=p.parse_args();source=Path(args.input);out=Path(args.output)
    if source.suffix.lower()=='.csv':
        rows=[]
        with source.open(newline='',encoding='utf-8-sig') as f:
            for row in csv.reader(f):
                parsed=[]
                for value in row:
                    try:parsed.append(float(value) if value.strip() else '')
                    except ValueError:parsed.append(value)
                rows.append(parsed)
        text=json.dumps(dict(tabs=[dict(range='AD_Apt_Monthly!CSV',values=rows)]),indent=2)+'\n'
    else:text=source.read_text()
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        check=Path(tmp)/'check.json';check.write_text(text)
        info=load_observed(str(check))
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(text);out.chmod(0o600)
    print('Private import saved:',out)
    print(info['first_month'],info['last_month'],info['observations'],'observed levels')
    print('Excluded proxy/backcast/forecast rows. No data published or committed.')

if __name__=='__main__':main()
