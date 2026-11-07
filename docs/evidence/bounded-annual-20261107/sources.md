# Method sources,7November2026
All fetched/read. The cap and moment proof are own specification/derivation;
none of these sources is claimed to prescribe cap9 or validate this model.

1. User-supplied Meucci(2005), Risk and Asset Allocation. Printed103-105,123-125,
233-234. Primary textbook: invariance, horizon projection, conditional context.
No book pages redistributed.
2. RiskMetrics1996, JPMorgan/Reuters. Primary technical manual viaMSCI:
https://www.msci.com/documents/10199/5915b101-4206-4ba0-aee2-3449d5c7e95a
EWMA methodological context only. Weekly.94 is inherited project choice, not
an attribution of a daily recommendation to weekly data. Second observed copy:
https://elischolar.library.yale.edu/cgi/viewcontent.cgi?article=1546&context=ypfs-documents
3. Gneiting/Raftery2007, JASA. Primary journal paper: exact proper CRPS and
empirical-support comparison, negative orientation lowerbetter.
https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf
4. Patton2011, Journal of Econometrics. Primary journal paper: QLIKE robust
ranking under conditionally unbiased noisy variance proxies; unknown means
limit interpretation of squared residuals in this study.
https://public.econ.duke.edu/~ap172/Patton_vol_proxies_JoE_2011.pdf
5. Gneiting/Balabdaoui/Raftery2007, JRSSB. Primary journal paper: calibration,
sharpness and PIT limits; pooled rates do not certify joint dynamics.
https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jrssb.pdf
6. Official arch forecast docs. Software documentation: conditional-variance
forecast timing and simulation; no code copied or arch dependency added.
https://arch.readthedocs.io/en/stable/univariate/forecasting.html
7. Pritsker/FederalReserve2001. Central-bank working paper: historical/FHS
limitations and multivariate dependence under changing volatility.
https://www.federalreserve.gov/Pubs/feds/2001/200127/200127pap.pdf

Additional sources supporting the separate improvement-priority advice:
http://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf
Rockafellar/Uryasev, scenario CVaR convex/LP formulations. Already implemented
CVaR constraints are not falsely described as missing.
https://optimization-online.org/wp-content/uploads/2002/01/434.pdf
Shapiro, multistage inference/conditional sampling/nonanticipativity limits.
https://link.springer.com/article/10.1007/s10107-017-1172-1
Esfahani/Kuhn, Wasserstein reformulations/assumptions and practical radius
calibration. No transplantation of iid bounds onto our dependent path model.
