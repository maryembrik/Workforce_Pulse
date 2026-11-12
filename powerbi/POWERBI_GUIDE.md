# Workforce Pulse — Power BI Build Guide (Phase 7)

Goal: a 3-page management dashboard, **Workforce Overview → Attrition Drivers → Retention Scenario Simulator**,
saved as `powerbi/Workforce_Pulse.pbix`. Estimated time: 3–4 hours.

Everything you need is in `powerbi/`:

| File | Use |
|---|---|
| `data/fact_employees.csv` | Main table: 1 row per employee (1,470), attributes + model score |
| `data/scenario_sensitivity.csv` | Model sensitivity scores per scenario (2,459 rows) |
| `data/feature_importance.csv` | Global SHAP importance (42 features) with business labels |
| `data/dim_risk_band.csv` | Risk band definitions, sort order, colors |
| `data/model_metrics.csv` | Model card numbers |
| `dax_query_1_core_measures.dax` | **Recommended:** all KPI / driver / model measures in one paste (DAX query view) |
| `dax_query_2_simulator_measures.dax` | Satisfaction + simulator measures in one paste (after Step 7.1) |
| `measures.dax` | Same measures as single blocks, for *New measure* one at a time (reference) |
| `workforce_pulse_theme.json` | Color / font theme. **Not** a data file: never load it with Get data |

> Regenerate the data at any time with `python -m src.export_powerbi`.

**French UI notes (Power BI en français)**
- *Fichier → Options et paramètres → Options → Global → Paramètres régionaux* → tick **"Utiliser les séparateurs DAX standard"**
  (or keep the default and accept that `,` becomes `;` in DAX). The `.dax` files use standard separators (`,`).
- Menu names: Modeling = *Modélisation*, New parameter = *Nouveau paramètre*, DAX query view = *Vue de requête DAX*,
  Run = *Exécuter*, View → Themes = *Affichage → Thèmes*.

---

## Step 1 — Load data
0. Start a **new, blank report** (*Fichier → Nouveau*). Do not build inside another project's .pbix.
1. Open Power BI Desktop → **Get data → Text/CSV**. Load the five CSVs from `powerbi/data/`.
   Use **Transform Data** (not Load) for `fact_employees` so you can check types first.
2. **View → Themes → Browse for themes** (*Affichage → Thèmes → Rechercher des thèmes*) → select `workforce_pulse_theme.json`.
   If a table called `workforce_pulse_theme` appeared in the Data pane, delete it: the theme is applied, not loaded.

## Step 2 — Power Query (Transform Data)
**2.1 Data types** (`fact_employees`):
- Whole number: EmployeeNumber, JobLevel, Education, all `Years*`, satisfaction columns, AttritionFlag, OvertimeFlag,
  PredictedClass, `*Sort` columns, MonthlyIncome, DistanceFromHome, NumCompaniesWorked, TrainingTimesLastYear,
  StockOptionLevel, PercentSalaryHike, PerformanceRating, TotalWorkingYears, LowSatisfactionCount.
- Decimal number: SalaryRatioToLevel, JobLevelMedianIncome, SatisfactionIndex, RoleShareOfTenure, PredictedProbability.
- Text: everything else.

**2.2 Check for errors:** select all columns → *View → Column quality*. Expect 0 % errors and 0 % empty.

**2.3 Rename the query** if needed so table names are exactly: `fact_employees`, `scenario_sensitivity`,
`feature_importance`, `dim_risk_band`, `model_metrics` (the DAX depends on these names).

**2.4 Create `satisfaction_long`** (unpivot, needed for the satisfaction chart on page 2):
1. Right-click `fact_employees` → **Reference**. Rename it `satisfaction_long`.
2. Keep only: EmployeeNumber, AttritionFlag, JobSatisfaction, EnvironmentSatisfaction, RelationshipSatisfaction,
   WorkLifeBalance, JobInvolvement.
3. Select the five satisfaction columns → **Transform → Unpivot Columns**. Rename `Attribute` → `Dimension`, `Value` → `Level`.
4. **Add Column → Conditional Column** `LevelLabel`:
   if Dimension = "WorkLifeBalance": 1 Bad · 2 Good · 3 Better · 4 Best; otherwise 1 Low · 2 Medium · 3 High · 4 Very High.
   (Simplest: two nested conditional columns, or `Add Column → Custom Column` with an `if … then … else` expression.)
5. Expected result: 1,470 × 5 = **7,350 rows**.

**Close & Apply.**

## Step 3 — Data model (Model view)
| From (many) | To (one) | Cardinality | Cross-filter |
|---|---|---|---|
| `scenario_sensitivity[EmployeeNumber]` | `fact_employees[EmployeeNumber]` | Many-to-one | Single (fact → scenario) |
| `satisfaction_long[EmployeeNumber]` | `fact_employees[EmployeeNumber]` | Many-to-one | Single |
| `fact_employees[RiskBand]` | `dim_risk_band[RiskBand]` | Many-to-one | Single |

`feature_importance` and `model_metrics` stay **unrelated**: they describe the model, not employees, so they shouldn't
react to employee slicers.

**Sort-by-column** (Data view → select column → *Column tools → Sort by column*):
TenureBand → TenureBandSort · IncomeBand → IncomeBandSort · AgeBand → AgeBandSort · RiskBand → RiskBandSort
(both in fact and dim_risk_band).

**Hide** technical columns from report view: all `*Sort` columns, `Split`, `OvertimeFlag`, `AttritionFlag`.

## Step 4 — Measures
**Fast way (DAX query view, one paste):**
1. Left bar → **DAX query view** (*Vue de requête DAX*) → new query tab.
2. Open `dax_query_1_core_measures.dax`, copy the **whole file**, paste it, click **Run** (*Exécuter*).
   A one-row result appears: 1470 | 237 | 0.161 | 0.305 | 0.104 | 567 | 0.789 | 0.330 | 241.7.
3. Click **Update model with changes** (*Mettre à jour le modèle avec les modifications*), above the query.
   The measures are now in `fact_employees`.
4. Set formats (select measure → *Measure tools / Outils de mesure*): rates as %, counts as whole numbers.
5. Optional: Model view → select measures → Properties → Display folder `1 KPIs`, `2 Drivers`, `3 Model`.

> Do **not** paste `measures.dax` into the DAX query view: it is a list of separate measures, not a query, so every
> line turns red. Use it only with *New measure*, one block at a time.

**Validation**: the query result above, or drop each measure on a card with no filters and compare.

| Measure | Expected |
|---|---|
| Workforce Size | 1,470 |
| Attrition Count | 237 |
| Attrition Rate | 16.1 % |
| Retention Rate | 83.9 % |
| Avg Tenure (Years) | 7.0 |
| Avg Monthly Income | 6,503 |
| Overtime Prevalence | 28.3 % |
| Attrition Rate Overtime / No Overtime | 30.5 % / 10.4 % |
| Overtime Risk Ratio | 2.9x |
| Flagged Employees | 567 |
| Recall of Flags / Precision of Flags | 78.9 % / 33.0 % |
| Model Expected Leavers | 241.7 |

If a number differs, check data types (Step 2.1) before touching the DAX.

---

## Step 5 — Page 1: Workforce Overview
*Question answered: How big is the workforce, how many leave, and where?*

Canvas 1280 × 720. Layout (top to bottom):

| Zone | Visual | Fields |
|---|---|---|
| Title bar | Text box | "Workforce Overview" + subtitle "IBM HR sample (fictional) · historical snapshot" |
| Slicers (top right) | 3 dropdown slicers | Department · JobRole · TenureBand |
| KPI row | 6 cards | Workforce Size · Attrition Count · Attrition Rate · Retention Rate · Avg Tenure (Years) · Avg Monthly Income |
| Left middle | Clustered bar | Y: Department · X: Attrition Rate · Tooltip: Workforce Size, Attrition Count, Share of All Leavers |
| Right middle | Bar chart | Y: JobRole · X: Attrition Rate (sort desc) · Data label: Rate Label · Conditional color: Attrition Rate vs Overall (pp) (diverging, 0 = neutral) |
| Bottom left | Column chart | X: TenureBand · Y: Attrition Rate · line/secondary: Workforce Size (line & clustered column) |
| Bottom middle | Donut | Legend: Department · Values: Workforce Size |
| Bottom right | Column chart | X: IncomeBand · Y: Attrition Rate · Tooltip: Avg Monthly Income |

Tips:
- Add a **constant line** at the overall rate (Analytics pane → Constant line = 0.161) on the rate charts.
- Turn on tooltips with n everywhere. A rate without its group size misleads (HR dept: 19 % but only 63 people).
- Gender and age composition, if shown, go here **only** as workforce composition (e.g. a small Gender donut). Never
  put protected attributes on the model or simulator pages.

## Step 6 — Page 2: Attrition Drivers
*Question answered: Which patterns deserve investigation?*

| Zone | Visual | Fields |
|---|---|---|
| Top left | 2 cards + clustered column | Cards: Attrition Rate Overtime, Overtime Risk Ratio. Column: X OverTime, Y Attrition Rate, small multiples: Department |
| Top right | Line chart (or matrix with heat colors) | `satisfaction_long`: X Level, Y Sat Attrition Rate, Legend Dimension. Tooltip: Sat Employees |
| Middle left | Column | X: LowSatisfactionCount · Y: Attrition Rate · Tooltip: Workforce Size (shows the "dissatisfaction adds up" pattern) |
| Middle right | Clustered bar | Y: SalaryPosition · X: Attrition Rate |
| Bottom left | Line + column | X: YearsAtCompany (filter visual to ≤ 20) · Line: Attrition Rate · Column: Workforce Size |
| Bottom right | Bar | `feature_importance`: Y FeatureLabel · X Feature Importance · Legend: Effect · Filter: Rank ≤ 12 · Title: "What the model relies on (SHAP)" |

**Tooltip page** (*Page → New page → Page information: Allow use as tooltip*, size Tooltip):
cards for Workforce Size, Attrition Count, Attrition Rate, Small Group Flag. Assign it to the bar/column visuals
(Format → General → Tooltips → Type: Report page).

Add a text box under the SHAP chart:
> "Importance = how much the model uses a factor. It does not prove that changing the factor changes behaviour."

## Step 7 — Page 3: Retention Scenario Simulator
*Question answered: What could management explore, and how sensitive is the picture to assumptions?*

**7.1 What-if parameters** (Modeling → New parameter → Numeric range), with "Add slicer to this page" ticked:

| Name | Min | Max | Increment | Default |
|---|---|---|---|---|
| Overtime Reduction | 0 | 100 | 5 | 0 |
| Satisfaction Improvement | 0 | 100 | 5 | 0 |
| Pay Alignment | 0 | 100 | 5 | 0 |

Use these names **exactly** (no `%`). Each creates a table with a column of the same name. The DAX reads that column
with `SELECTEDVALUE`, so it does not depend on the auto-measure name ("… Value" in English, "… Valeur" in French).

**7.1b Simulator measures:** make sure `satisfaction_long` exists (Step 2.4), then in DAX query view paste the whole
`dax_query_2_simulator_measures.dax` → **Run**. The row (sliders forced to 100 %) must read
153.4 | 162.4 | 211.3 | −72.7 | −18.6 | −4.7 | 7350. Then **Update model with changes**.

**7.2 Layout: two clearly separated layers.** Use two rectangles with headers.

**Left panel: "A. Descriptive scenario (historical rates)"**
| Visual | Fields |
|---|---|
| Card | Attrition Count (label "Leavers today") |
| Card | Scenario A Leavers - Combined (label "Illustrative leavers") |
| Card | Scenario A Change (pp) |
| Clustered bar | 3 measures: Scenario A Leavers - Overtime / - Satisfaction / - Pay, with a constant line at Attrition Count |
| Text | "Assumes employees moved out of a group take on the current attrition rate of the comparison group. Combined total ignores overlap and overstates the effect." |

**Right panel: "B. Model sensitivity (how the model's score responds)"**
| Visual | Fields |
|---|---|
| Card | Model Sensitivity - Combined (label "Change in model-expected leavers") |
| Waterfall | Category: create a small Enter-Data table `SensitivityLever` with values Overtime / Satisfaction / Pay, plus a measure `Lever Value = SWITCH(SELECTEDVALUE(SensitivityLever[Lever]), "Overtime", [Model Sensitivity - Overtime], "Satisfaction", [Model Sensitivity - Satisfaction], "Pay", [Model Sensitivity - Pay])` |
| Card | Employees Affected - Overtime |

**Bottom strip: current risk distribution (aggregated, no individual names)**
| Visual | Fields |
|---|---|
| Stacked bar | Y: Department · X: Workforce Size · Legend: RiskBand (colors from dim_risk_band: High #C0392B, Elevated #E67E22, Low #7F8C8D) |
| Table | dim_risk_band[RiskBand], Rule, Workforce Size, Attrition Rate (retrospective actual), Avg Predicted Risk |
| Card (wide) | Simulator Disclaimer |

**Validation at 100 %, no filters:**

| Measure | Expected |
|---|---|
| Scenario A Leavers - Overtime | 153.4 |
| Scenario A Leavers - Satisfaction | 162.4 |
| Scenario A Leavers - Pay | 211.3 |
| Model Sensitivity - Overtime | −72.7 |
| Model Sensitivity - Satisfaction | −18.6 |
| Model Sensitivity - Pay | −4.7 |

At 0 % every scenario equals today (237) and every sensitivity is 0.

**How to explain the two layers in an interview**
- Layer A says: "*If* overtime employees left at the rate non-overtime employees currently do, we would see ~153
  leavers instead of 237." This is an arithmetic illustration resting on an assumption.
- Layer B says: "The model's expected-leaver count falls by ~73 if overtime is switched off in its inputs." This
  tells us how much the model relies on overtime, **not** how many people would stay.
- Both agree that overtime is the lever with the largest *association* and pay alignment the smallest. Whether it is
  *causal* would need a pilot (e.g. an overtime cap in one site vs a comparison site).

## Step 8 — Responsible design checklist
- [ ] No page shows an employee-level list ranked by risk. Scores appear only aggregated.
- [ ] Protected attributes (Gender, AgeBand, MaritalStatus) appear only as composition on page 1, if at all.
- [ ] Every rate visual shows n (tooltip or label).
- [ ] The simulator page carries the disclaimer card.
- [ ] Footer on every page: "Fictional IBM HR sample · portfolio simulation · not a real HR system".

## Step 9 — Finish
1. **Navigation:** Insert → Buttons → Navigator → Page navigator (top of each page).
2. **Bookmarks** (optional): "Simulator reset" bookmark with all parameters at 0.
3. **Performance check:** View → Performance analyzer → refresh visuals. Everything should run well under 1 s on 1,470 rows.
4. **Screenshots:** export each page (File → Export → PDF, or Win + Shift + S) to `powerbi/screenshots/`:
   `01_overview.png`, `02_drivers.png`, `03_simulator.png`. The README links these names.
5. Save as `powerbi/Workforce_Pulse.pbix`.
