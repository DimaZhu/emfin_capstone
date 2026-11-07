from emfin_v2.issuer_import import ishares_nav_total_return
import pytest


def workbook(tmp_path,amount='1'):
    p=tmp_path/'issuer.xls'
    def sheet(name,rows):return '<ss:Worksheet ss:Name="'+name+'"><ss:Table>'+''.join('<ss:Row>'+''.join('<ss:Cell><ss:Data ss:Type="String">'+x+'</ss:Data></ss:Cell>' for x in r)+'</ss:Row>' for r in rows)+'</ss:Table></ss:Worksheet>'
    p.write_text('<ss:Workbook xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'+sheet('Disclaimers',[['A & B personal use only']])+sheet('Historical',[['As Of','NAV per Share','Ex-Dividends'],['Jan 03, 2020','99','1'],['Jan 02, 2020','100','--']])+sheet('Distributions',[['Ex-Date','Total Distribution'],['Jan 03, 2020',amount]])+'</ss:Workbook>')
    return p


def test_ex_date_nav_reinvestment_is_not_price_only(tmp_path):
    f,m=ishares_nav_total_return(workbook(tmp_path));assert f.total_return_index.iloc[-1]==pytest.approx(100.);assert m['distribution_count']==1


def test_ledger_disagreement_fails_not_silently_ignores_income(tmp_path):
    with pytest.raises(ValueError,match='ledger'):ishares_nav_total_return(workbook(tmp_path,'2'))
