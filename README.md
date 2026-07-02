# ECO STOR Bollingstedt BESS Independent Audit (103.5 MW)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21135862.svg)](https://doi.org/10.5281/zenodo.21135862)

Independent verification of dynamic grid operations and regime shift claims for the ECO STOR Bollingstedt battery storage system (BESS), conducted under the **VolMax P10 Verification Protocol**.

---

## ⚠️ Limitations First

Before reviewing the audit findings, it is critical to understand the boundaries and limitations of this verification:

1. **Lack of Internal Battery State Data (SOC/RTE):** The public dashboard data exports do not contain State of Charge (SOC) or internal charge/discharge energy series. Consequently, physical limits relating to battery health degradation, State of Charge, and Round-Trip Efficiency (RTE) **could not be verified**.
2. **No Grid-Side High-Resolution Telemetry:** Contractual physical limit boundaries at the grid connection point (e.g., reactive power compensation, sub-second active power ramp rates for FCR) could not be checked. Verification is limited to the BESS operator's self-reported 15-minute resolution values.
3. **Trace Rename & Schema Drift:** March 2026 data had a schema drift where PV and Wind column names were renamed to `trace_3` and `trace_1` between March 24 and March 31. This was resolved programmatically, but introduces minor mapping assumptions.
4. **Data Completeness Gaps:**
   * **March 2026:** Contains a resolved gap of 459 intervals for PV and Wind power data.
   * **June 2026:** Truncated by the final 8 intervals (2 hours) at the end of the month due to the export window limitations.
5. **Data Ownership and Licensing:** The raw data remains the proprietary property of the operator (ECO STOR GmbH). No explicit public license for the raw dashboard exports is provided.

---

## 📊 Core Audit Findings

* **Final Report Hash (SHA-256):** `fbe0ff2ceeba9ce893778418d0304418649c4949d39615e497a256f5f91202b0`
* **ES-01 (Physical Limits):** Out of 37,912 active samples, **180 deviations** were detected (0.4748% violation rate).
  * **Taxonomic Resolution:** **151** are sub-MW night-time auxiliary load fluctuations ($\le 1.0$ MW), and **11** are pre-regime discharge exceedances occurring in June 2025.
  * **Two-Part Verdict:** **Verified with Limitations**. During the FCA regime period (July 2025 onwards), there are **zero** operational limit violations (only sub-MW noise). Multi-megawatt exceedances occur exclusively in the pre-regime period (June 2025), consistent with the suppression of limit violations following the introduction of the FCA regime.
* **ES-02 (Regime Shift):**
  * **Allowed Discharge Power Limit Activity CUSUM** detects the transition almost in-day on **July 5, 2025** ($d = 1.063$), coinciding with the claimed July 1 regime shift.
  * **Dispatch Volume CUSUM** detects a delayed transition on **August 3, 2025** ($d = 0.644$).
* **ES-03 (Netzdienlichkeit):** The BESS exhibits a strong and statistically significant negative correlation with PV output ($r = -0.3005$), peaking at **-0.460** in May 2026. Correlation with wind is negligible ($r = -0.0512$, $p > 0.05$ during autumn/winter).

---

## 🛠️ Repository Structure

* `schema_validation.py`: Structural checks, SHA-256 calculation, completeness, and DST offsets.
* `verify_claims.py`: Stitches data, runs physics gates, calculates correlations, detects CUSUM changepoints, classifies taxonomy, and dynamically generates the markdown report.
* `reproduce.py`: Unified entry point to run validation and verification.
* `ecostor_audit_report.md`: Dynamically generated, publication-ready audit report.
* `results/`: Contains generated plots (`plot1_double_cusum.png`, `plot2_correlations_trend.png`, `plot3_deviations_hourly.png`) and metrics JSONs.

---

## 🚀 Reproduction Instructions

Ensure you have Python 3 and the required dependencies installed (see `requirements.txt`):

```bash
pip install -r requirements.txt
python3 reproduce.py
```

This single command will run the Level 1 schema validation, run Level 2/3 claims verifications, output the figures to `results/`, and regenerate the markdown report.
