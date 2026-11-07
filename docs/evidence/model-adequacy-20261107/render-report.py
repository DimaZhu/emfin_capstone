from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
root=Path('/home/sandbox/repo');e=root/'artifacts/model-adequacy-20261107';s=json.loads((e/'summary.json').read_text());allrows=[r for r in s['rows'] if r['asset']=='ALL'];names={'iid_mix':'iid mixture','ewma_mix':'EWMA mixture','garch_mix':'GARCH variance + mixture','ewma_fhs':'EWMA empirical FHS'};assets={'us_equity':'VTI','em_equity':'VWO','gold':'GLD','treasury':'IEF','__fx_usd_per_sgd':'SGD/USD'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'text.color':'#251f21','axes.labelcolor':'#251f21','xtick.color':'#585254','ytick.color':'#585254'})
fig,ax=plt.subplots(figsize=(8,3.0));base=allrows[0]['normalized_crps'];values=[100*(base-r['normalized_crps'])/base for r in allrows];ax.barh([names[r['method']] for r in allrows],values,color=['#bfb9bb','#8d8588','#73a89a','#8d8588']);ax.invert_yaxis();ax.set_xlim(0,2.3);ax.set_xlabel('Reduction in normalized CRPS vs iid baseline (%)');ax.grid(axis='x',color='#eae9ea');ax.set_axisbelow(True)
for i,v in enumerate(values):ax.text(v+.04,i,f'{v:.2f}%',va='center')
fig.tight_layout();fig.savefig('/downloads/model-adequacy/score-improvement.png',dpi=190);plt.close(fig)
fig,ax=plt.subplots(figsize=(8,3.25));y=np.arange(5)
for offset,method,color,label in [(-.16,'iid_mix','#8d8588','iid baseline'),(.16,'garch_mix','#73a89a','Locked GARCH candidate')]:
 rows=[r for r in s['rows'] if r['method']==method and r['asset']!='ALL'];v=[r['squared_standardized_lag1'] for r in rows];ax.barh(y+offset,v,height=.3,color=color,label=label)
 for yy,x in zip(y+offset,v):ax.text(x+.008 if x>=0 else x-.008,yy,f'{x:.3f}',va='center',ha='left' if x>=0 else 'right',fontsize=9)
ax.set_yticks(y,[assets[r['asset']] for r in rows]);ax.invert_yaxis();ax.set_xlim(-.10,.46);ax.axvline(0,color='#585254',linewidth=.7);ax.set_xlabel('Lag-one correlation of squared standardized returns');ax.legend(fontsize=8,loc='lower right');ax.grid(axis='x',color='#eae9ea');ax.set_axisbelow(True);fig.tight_layout();fig.savefig('/downloads/model-adequacy/residual-clustering.png',dpi=190);plt.close(fig)
font=Path('/skills/platform/files/assets/fonts');pdfmetrics.registerFont(TTFont('Melange',str(font/'melange-grotesk-350.ttf')));pdfmetrics.registerFont(TTFont('Aime',str(font/'Aime-Light.ttf')))
ink=colors.HexColor('#251f21');muted=colors.HexColor('#585254');teal=colors.HexColor('#73a89a');red=colors.HexColor('#ed313e');rule=colors.HexColor('#eae9ea')
styles={k:ParagraphStyle(k,fontName='Aime' if k in ['title','h1'] else 'Melange',fontSize=z,leading=l,textColor=ink,spaceAfter=a,keepWithNext=k in ['title','h1','h2']) for k,z,l,a in [('title',26,30,14),('h1',20,24,11),('h2',12,17,6),('body',10.2,15,10),('small',8,11,8)]};styles['small'].textColor=muted
story=[]
def p(text,style='body'):story.append(Paragraph(text,styles[style]))
def title(label):p(label,'h1')
def table(rows,widths):
 t=Table([[Paragraph(str(c),styles['small']) for c in row] for row in rows],colWidths=widths,hAlign='LEFT',repeatRows=1)
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f4efec')),('LINEBELOW',(0,0),(-1,0),.8,teal),('LINEBELOW',(0,1),(-1,-1),.3,rule),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story.append(t);story.append(Spacer(1,9))
def image(name,height):story.append(Image('/downloads/model-adequacy/'+name,width=475,height=height))
p('Ballast / private research / 7 November 2026','small');p('Changing volatility helps.<br/>That is not an annual safety claim.','title')
p('The validation-selected conditional-variance model reduced one-week forecast error by 1.82% against the iid-mixture baseline on 2019-2025. It also removed much of the residual volatility clustering. No production model, allocation or funding rule was changed.')
image('score-improvement.png',178)
p('Primary score: exact marginal CRPS, normalized by a frozen per-asset initial-history scale. Lower is better. This is forecast quality, not investment return or a portfolio-performance gain.','small')
title('A useful result with a hard promotion blocker')
p('The selected model is GARCH(1,1) conditional variance with the same development-selected finite Gaussian-mixture innovations. One-week forecasts have finite exponential moments. But unbounded Gaussian variance feedback can produce <b>infinite price moments over three weeks</b>. A better weekly score is therefore not enough to use this candidate in the annual engine.')
p('We derived the moment-domain counterexample independently and kept the candidate in research only. No hidden volatility cap, truncation, new path generator or automatic replacement was added. The existing iid finite-mixture default and empirical EWMA-FHS competitor are unchanged.')
p('332 tests pass. Exact score formulas, variance timing, unit scaling, future-data exclusion and incomplete-study failure handling have independent tests. Raw forecasts, optimizer starts, source/data hashes and the locked selection accompany this report.','small')
story.append(PageBreak());title('Past-only, but not genuinely blind')
p('Initial fit and scoring scales use common weekly history through 2006. Parameters and the shared shrunk mean refit once at each year start using only earlier observations. During the year, variance updates only after the realized return is scored. Cash is deterministic; quarterly property is not fabricated into a weekly series.')
table([['Stage','Dates','Allowed use'],['Development','2007-2013','Descriptive checks, including 2008. 2007 unavailable.'],['Validation','2014-2018','Choose among three conditional candidates using equal-asset normalized CRPS.'],['Final comparison','2019-2025','Score the saved choice; show all models without reselecting.']],[92,94,289])
p('These historical periods had already been viewed during earlier development. The new protocol was committed before this study, but it is a retrospective design, not independent blind preregistration. Later annual refits can use earlier outcomes already observed in the final period; the model class is never reselected.')
p('The conditional candidates were EWMA mixture, Gaussian-QML GARCH variance plus fixed mixture, and empirical EWMA-FHS. Both EWMA models use decay 0.94 and the same variance states. All four models share past-only mean estimates, with FX log drift set to zero. This is a marginal study; it does not validate joint dependence or EP stress.','body')
title('The locked comparison')
table([['Method','CRPS','QLIKE','1% exceptions','5% exceptions']]+[[names[r['method']],f"{r['normalized_crps']:.6f}",f"{r['qlike']:.6f}",str(r['exception1']),str(r['exception5'])] for r in allrows],[149,72,72,89,93])
p('365 weekly dates x five correlated assets = 1,825 asset-week forecasts, not 1,825 independent time observations. Exceptions are pooled counts; they are not a calibration test. QLIKE uses noisy squared mean-forecast residuals rather than observable true conditional variance. Identical EWMA QLIKE is expected because their variance forecasts match.','small')
p('Validation CRPS: GARCH 0.573587, EWMA mixture 0.574018, FHS 0.574723. The small differences do not settle model choice. The locked candidate beat iid in all seven final calendar years and all five asset-average point scores, not every alternative in every year.')
p('Paired normalized CRPS difference, GARCH minus iid: -0.012301. Exploratory 20-week circular-block 95% percentile interval: [-0.019437, -0.005627]. Prespecified 10/40-week intervals also stay below zero. These descriptive intervals are not selection-adjusted or economic coverage guarantees.','body')
story.append(PageBreak());title('Clustering falls. Tail calibration is still open.')
image('residual-clustering.png',193)
p('Final 2019-2025 one-step standardized residuals. The axis is zoomed; the possible correlation range is -1 to 1. Low lag-one squared correlation does not prove independence, full distribution calibration or correct multivariate tails.','small')
chosen=[r for r in s['rows'] if r['method']=='garch_mix' and r['asset']!='ALL']
table([['Asset','5% exceptions /365','1% exceptions /365']]+[[assets[r['asset']],str(r['exception5']),str(r['exception1'])] for r in chosen],[133,171,171])
p('Ideal-model expected counts per asset would be 18.25 at 5% and 3.65 at 1%. Actual small, dependent counts are not full-funding probabilities. The iid pooled 5%-exception rate of 3.89% hides VTI/VWO/GLD/IEF/FX counts of 14/7/10/31/9. A convenient pooled rate is not calibration.')
title('Crisis slices do not get a pass')
p('In the descriptive 2008 development slice, 5% pooled exception rates were 21.54% iid, 13.85% GARCH, 10.77% EWMA mixture and 8.85% FHS. GARCH improved on iid but still missed its nominal frequency badly. This was not new unseen crisis evidence.')
p('In 2020, iid/GARCH 5% rates were 7.69%/8.46%; in 2022 they were 9.62%/6.92%. A lower general forecast score does not improve every tail statistic. PIT histograms and exception-transition/run counts stay in the evidence without an unadjusted parade of p-values.')
story.append(PageBreak());title('Failures, scope and next steps')
p('2007 had only 94 past common weeks, below the fixed 104-week GARCH requirement. The first development run aborted. The runner was improved to retain unavailable years and withhold incomplete comparative summaries, not shorten the minimum or omit failures. Development 2008-2013 then completed; 2007 stays unavailable.')
p('All 25 validation and 35 final asset-year GARCH fits succeeded, including all three fixed starts each. All 30 available development fits succeeded. Internal SLSQP bound-step clipping warnings remain visible. No final out-of-range parameter was accepted. The final score/selection artifacts remain preserved at their original clean 4be65c0 implementation basis.')
p('Measured compute: pilot 0.14s, validation 0.57s, final 0.79s, available development 0.66s. A later full test run took 15.29s. No grid, long batch, spend, public hosting, contact or new dependency was needed.','small')
p('The next scientific step needs a conditional annual model with a defensible moment domain, then joint listed/FX/property dependence and multihorizon/executable-policy validation. Do not promote the one-week candidate automatically. Cash carry, property vintages/publication, settlement costs, radius calibration and the optimizer/ledger gap remain open.')
p('A 20% tail-shortfall allowance still is not a paid-in-full promise. None of this forecast evidence changes the original funding policy or proves an annual probability of making every payment.')
title('Source and reproduction notes')
sources=[('Meucci (2005), user-supplied Risk and Asset Allocation. Printed pp.103-105,123-125,233-234; corresponding PDF pp.125-127,145-147,254-255. No pages redistributed.',None),('Gneiting &amp; Raftery (2007): proper scoring rules and CRPS.','https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf'),('Patton (2011): QLIKE and noisy variance proxies.','https://public.econ.duke.edu/~ap172/Patton_vol_proxies_JoE_2011.pdf'),('Bollerslev (1986): GARCH recursion and stationarity. The price-moment counterexample is our own derivation.','https://public.econ.duke.edu/%7Eboller/Published_Papers/joe_86.pdf'),('Gneiting, Balabdaoui &amp; Raftery (2007): calibration, sharpness and PIT limitations.','https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jrssb.pdf'),('Official arch forecast documentation: forecast timing and analytical/simulation distinction. No package dependency added.','https://arch.readthedocs.io/en/stable/univariate/forecasting.html'),('Federal Reserve: historical-simulation cautions.','https://www.federalreserve.gov/Pubs/feds/2001/200127/200127pap.pdf')]
for text,url in sources:p(text+(' <link href="'+url+'" color="#35776a">Source</link>.' if url else ''),'small')
p('Full protocol, formulas, limits, per-forecast data, fit attempts and selection lock accompany the private evidence. The earlier annual portfolio report and default remain unchanged.','small')
def footer(c,doc):
 c.saveState();c.setStrokeColor(rule);c.line(52,43,543,43);c.setFont('Melange',8);c.setFillColor(muted);c.drawString(52,30,'Ballast / private research / no recommendation');c.drawRightString(543,30,str(doc.page));c.restoreState()
SimpleDocTemplate('/downloads/ballast-model-adequacy-20261107.pdf',pagesize=A4,rightMargin=52,leftMargin=52,topMargin=47,bottomMargin=58,title='Ballast: conditional-volatility comparison',author='Tijs de Boer').build(story,onFirstPage=footer,onLaterPages=footer)
print('/downloads/ballast-model-adequacy-20261107.pdf')
