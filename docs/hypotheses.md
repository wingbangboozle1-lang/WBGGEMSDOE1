# Four Ranked Blind-Fault Hypotheses — GEMSDOE Focus-9

> Preregistered in `registry/wbg3_preregistration.json` (SHA e891cd7c…). Validated on spatially-blocked whole-component holdout (buffer, visible-only recomputation, pixel-exact catalogue mask, pooled triangular-kernel DTI α=0.2 β=0.8 300 m). Leakage canary: each feature alone AUC >0.90 = leakage suspect. Budget: 3 experiments / 2 h. No slot spent.

## Rank #1 — SPI-PMR-WCS-1 (EXECUTED) — Crustal SPI × Monogenic Phase × Wing-Crack

- **Exact layers:** Official 19-band `rtp`(14), `tmi`(16), `iso_grav_anom`(13), `det_elev`(12), `elev`(11), `geod_shearstr`(7), `geod_dilaterate`(8) + OpenEI GDR 1391 thermal wells (DOI:10.15121/1881483, fault-distance columns stripped) + fold-visible mask. Zero LiDAR/DEM.
- **Transform:** `k_SPI = ‖∇ atan2(∂zF, ‖∇hF‖)‖` over upward-continued RTP/gravity; 2D FFT Riesz monogenic phase congruency; Pollard-Segall wing-crack lobes at ±32° from visible tips.
- **Why it catches catalogue-missing faults:** Intrabasinal blind faults under 10–250 m of Lahontan/playa alluvium lack scarps, but Tertiary volcanic vs basin-fill contacts give sharp k_SPI maxima directly above, while degraded <1 m splays retain phase alignment.
- **Mimic:** Lake Lahontan wave-cut benches, basalt sill edges, railroad embankments.
- **Diff vs repo:** Not Hessian commutator (WBG-C1), not fixed tip (TIP1), not magnetic trough (MVGZ), not LiDAR/DEM (H1/S2), not random KDE (WBG-2).
- **Measured vs expected:** HOLDOUT-DTI 0.11818 vs 0.09078 ctrl (+30.2%, 4/4 folds won, CI [+0.014,+0.042], n=60,988). Highest expected and measured gain. Cost medium-high. Source: free official 19-band + GDR 1391 — obtainable.

## Rank #2 — PPDR-1 — FFT Poisson Pseudogravity Magnetite-Destruction Residual

- **Layers:** Official `rtp`(14), `iso_grav_anom`(13), `cond_surf`(17) + USGS GeoDAWN K,Th,U,TC (DOI:10.5066/P93LGLVQ, https://doi.org/10.5066/P93LGLVQ).
- **Transform:** Poisson pseudogravity `g_pseudo = F⁻¹[F(RTP)/max(‖k‖,k0)]` → gravity-gradient minus pseudogravity-gradient residual gated by K/Th.
- **Why catalogue-missing:** Hydrothermal brines destroy magnetite → magnetic gradient collapses but density contrast persists → PPDR high with K/Th metasomatism.
- **Mimic:** Felsic calderas, evaporite playas.
- **Diff vs repo:** SPI is local wavenumber; PPDR is integral residual — complementary; peer ratio-only not Poisson.
- **Measured vs expected:** +12.0% in Arm 2 (0.1017 vs 0.09078). Cost medium. Source free official GeoDAWN — obtainable.

## Rank #3 — AFBD-1 — Flexural Basement Curvature & MT Conductance Anisotropy (Deferred)

- **Layers:** Official-only `depth_to_base_surf`(15), `cond_10_to_20_km`(2), `cond_2_to_5_km`(4), `cond_surf`(17), `geod_shearstr`(7), `geod_dilaterate`(8).
- **Transform:** Biharmonic flexural hinge ∇⁴z_b at master rollovers × strike-projected MT conductance pipe.
- **Why catalogue-missing:** Deep master faults flex basement and channel MT conductance vertically with no scarp.
- **Mimic:** Compaction hinges over paleo-valleys.
- **Diff vs repo:** No prior lane used flexure × MT; differs from SPI. Cost low-medium. No new data needed. Expected gain moderate, untested.

## Rank #4 — InSAR-1 — NASA ASF OPERA Sentinel-1 DInSAR Velocity-Gradient Discontinuity (Gated)

- **Layers & free official source:** NASA/JPL OPERA Sentinel-1 L3 Displacement (https://asf.alaska.edu/datasets/daac/opera/) resampled to 100 m, LOS velocity-gradient discontinuity.
- **Why catalogue-missing:** Creeping <1 mm/yr intrabasinal faults offset LOS velocity across playas with zero scarp, invisible to 1 km GPS.
- **Mimic:** Pumping subsidence bowls.
- **Diff vs repo:** No prior lane used orbital radar. Cost high. Expected gain highest on playa faults, untested. Gate: asf.alaska.edu blocked in sandbox — verify via official OPERA page before viable.

---

Ranking: expected DTI gain vs cost. #1 top because strongest measured gain (+30.2% 4/4 wins) and targets exact blind-fault failure mode with already-pinned free data, most distinct from prior lanes.
