# Branch archive (9 Nov 2026 integration)

On 9 Nov 2026 the active side branches were merged into `engine-v2` and the
fully contained ones deleted. Their SHAs are listed below. A separate unreviewed
branch was later removed at the owner's request; its full SHA is recorded for
recovery. Nothing was force-pushed or rewritten.

To restore one:

```bash
git fetch origin
git branch <name> <full-sha>
git push origin <name>
```

## Deleted 9 Nov 2026 (fully contained in `engine-v2`)

| Branch | Final SHA | Contents |
|--------|-----------|----------|
| fix-log-cara-solver-tolerance-20261108 | b89ed3d03e6af70c0241ab8ddd979ec79fca1701 | CI test-tolerance fix |
| paper-prep-20261108 | 09bec4fdce7661fc84c4cc6318494c5bcd1f3b63 | Backtest + radius study + paper docs |
| paper-offline-chained-20261109 | 2d28c1489faa45059e0e52fe06e5d453b41cc488 | Offline chained study + referee notes |
| paper-chained-20261109 | 9b08a41141043e4581b75eedf6450c8785eb40e2 | Chained-wealth code (dispatch-only) + design fixes |
| finalize-20261108 | 7a499d0e4dea7dfaff79bbdccdcc72d590522c19 | Finalization line, already merged |
| cleanup-legacy-deps-20261108 | ba99006df6fdf9e6b78e980c98516f0c207483b2 | Legacy dependency cleanup |
| engine-horizon-t25-20261108 | 83dc597bd19ed2679afc974e7731c88acf7c4d75 | Horizon 25y experiments |
| engine-horizon-t25-s09-20261108 | 00beba6beb4e728547637f70f18fc7b4e81fbb06 | Horizon 25y, seed 9 |
| engine-round2-20261108 | 506751c9f8526d8c48b6c15a769bae3fad95b813 | Round-2 engine studies |
| engine-sensitivity-20261108 | a21ad9cc5b1dde87e7d98ab30bfe34fbc93df054 | Sensitivity runs |
| feature/bounded-annual-volatility | 687a99cf910eae62f5e4cf6291cd49aa45272a26 | Bounded annual volatility |
| feature/dynamic-execution-policy | 087e7038aae1dd33fefc349374763e23bff56652 | Dynamic execution policy |
| feature/prespecified-conditional-adequacy | 2944475d36b9958028c1e74dac912c419cbfea9c | Conditional adequacy |
| open-points-fixes-20261108 | a570bca9868401f11de7074851aebcd6f4e8a757 | Open-points fixes |
| owner-defaults-10y-cml40 | 6c196c644ba7ed322504627d4b8bacd87e27e820 | Owner defaults: 10y, 40% drawdown cap |
| refactor-shared-accounting-20261108 | e5c908708d73fa1da0e8b818e3022aa14d693e72 | Shared accounting refactor |
| report-visual-fixes-20261108 | 442483577a3512764360ed34319e81578bb8682e | Report visuals |
| report-visual-fixes-series-20261108 | 77da6e3a1b2e83a6cdca5914f0a37cadd6974993 | Report visuals, series |
| research-uncertainty-inflation-fees-20261108 | 61aa6417b419e45f6355311aa4f22923a3ed3ecd | UIF studies |
| scenario-mean-reversion-20261108 | c31ebc0c757480cbbfee8feb69bf450f001e7b4a | Mean-reversion scenario |
| tbill-asset | fde68ecd6ee91cd765237a8f60c55a83be57dfe8 | T-bill asset |
| tips-model-10y | 1206801513391ce9e58e035dee58d78ba1680ed5 | TIPS model, 10y |

## Dropped 9 Nov 2026 at owner's request (not merged)

| Branch | Final SHA | Contents |
|--------|-----------|----------|
| TijsdeBoer-patch-1 | a420c8845592ddf630277da59a795a66da1be347 | Unreviewed web-uploaded `real_estate` toolbox draft; dropped at the owner's request, not merged. |

## Kept

| Branch | SHA | Why |
|--------|-----|-----|
| engine-v2 | moving | The default branch and integration line. |
| main | e80e6c33a57d43d22fc93a72940267b9a1142d24 | Historical root from the original fork; kept for provenance. |

Tags v2.0 and v2.1 are unchanged.
