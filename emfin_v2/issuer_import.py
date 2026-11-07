"""Local importer for the issuer's downloaded Excel XML fund workbook.

No requests or third-party retrieval code. Keep the source and generated
series private wherever source terms require it. Reinvestment is at ex-date
NAV, before investor taxes or trading frictions, and is not market execution.
"""
import re,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import pandas as pd


def ishares_nav_total_return(path):
    text=Path(path).read_text(encoding='utf-8-sig')
    # Some issuer legal headings contain bare ampersands in an otherwise XML file.
    text=re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)','&amp;',text)
    ns={'s':'urn:schemas-microsoft-com:office:spreadsheet'};root=ET.fromstring(text);sheets={}
    for sheet in root.findall('s:Worksheet',ns):
        rows=[]
        for row in sheet.findall('.//s:Row',ns):
            values=[]
            for cell in row.findall('s:Cell',ns):
                explicit=cell.attrib.get('{'+ns['s']+'}Index')
                if explicit:values.extend(['']*max(0,int(explicit)-1-len(values)))
                data=cell.find('s:Data',ns);values.append('' if data is None else ''.join(data.itertext()))
            rows.append(values)
        sheets[sheet.attrib['{'+ns['s']+'}Name']]=rows
    if not all(k in sheets for k in ('Historical','Distributions','Disclaimers')):raise ValueError('issuer historical/distribution/disclaimer sheets required')
    def table(name,label):
        rows=sheets[name];at=next((i for i,r in enumerate(rows) if label in r),None)
        if at is None:raise ValueError('issuer sheet header missing')
        keys=rows[at];return [dict(zip(keys,r)) for r in rows[at+1:] if any(r)]
    history=table('Historical','As Of');ledger=table('Distributions','Ex-Date')
    rows=[]
    for r in history:
        rows.append((pd.to_datetime(r['As Of'],format='%b %d, %Y'),float(r['NAV per Share'].replace(',','')),0. if r['Ex-Dividends'] in ('','--','-') else float(r['Ex-Dividends'].replace(',',''))))
    f=pd.DataFrame(rows,columns=['date','nav','distribution']).set_index('date').sort_index()
    if f.index.duplicated().any() or (f.nav<=0).any() or (f.distribution<0).any() or not np.isfinite(f.to_numpy()).all():raise ValueError('invalid issuer daily observations')
    expected={}
    for r in ledger:
        date=pd.to_datetime(r['Ex-Date'],format='%b %d, %Y');expected[date]=expected.get(date,0)+float(r['Total Distribution'].replace(',',''))
    actual=f.loc[f.distribution>0,'distribution'].to_dict()
    if set(expected)!=set(actual) or any(abs(expected[k]-actual[k])>1e-7 for k in actual):raise ValueError('issuer distribution ledger disagrees with ex-dividend observations')
    gross=(f.nav+f.distribution)/f.nav.shift(1)
    if (gross.dropna()<.5).any() or (gross.dropna()>1.5).any():raise ValueError('possible split/corporate action; independent adjustment check required')
    f['total_return_index']=100*gross.fillna(1).cumprod()
    return f,dict(first=str(f.index[0].date()),last=str(f.index[-1].date()),observations=len(f),distribution_count=len(actual),reinvestment='Cash distributions reinvested at ex-date NAV; before taxes/frictions. NAV and ledger matched at1e-7.',source_notices_retained=True)
