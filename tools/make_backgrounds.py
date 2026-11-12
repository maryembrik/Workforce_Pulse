"""Generate 1280x720 Power BI page backgrounds for the three Workforce Pulse pages.

For each page two PNGs are written to powerbi/backgrounds/:
  *_bg.png      the canvas background to load in Power BI (panels, titles, notes; empty slots)
  *_layout.png  the same image with dashed boxes naming the visual that goes in each slot (reference only)

Run:  python tools/make_backgrounds.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parents[1] / "powerbi" / "backgrounds"
W, H = 1280, 720
PAGE_BG = "#F4F6F9"
PANEL = "#FFFFFF"
BORDER = "#E5E7EB"
NAVY = "#1F3A5F"
TEXT = "#1F2937"
MUTED = "#6B7280"
SLOT = "#2E86AB"
FONT = "Segoe UI"
FONT_B = "Segoe UI Semibold"
PX = 72 / 100  # matplotlib points per pixel at dpi=100

FOOTER = "Fictional IBM HR sample  ·  portfolio simulation  ·  not a real HR system"


class Page:
    def __init__(self, title, subtitle, layout):
        self.layout = layout
        self.fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(H, 0)
        self.ax.axis("off")
        self.ax.add_patch(Rectangle((0, 0), W, H, color=PAGE_BG, zorder=0))
        # title band
        self.ax.add_patch(Rectangle((0, 0), W, 72, color=PANEL, zorder=1))
        self.ax.add_patch(Rectangle((0, 71), W, 1, color=BORDER, zorder=1))
        self.ax.add_patch(Rectangle((0, 0), 8, 72, color=NAVY, zorder=2))
        self.text(28, 30, title, 22, FONT_B, TEXT)
        self.text(28, 54, subtitle, 12, FONT, MUTED)
        self.text(24, 708, FOOTER, 10, FONT, MUTED)
        self.text(1256, 708, "Workforce Pulse", 10, FONT_B, NAVY, ha="right")
        self.slot(880, 20, 376, 34, "Page navigator (Insérer > Boutons > Navigateur)")

    def text(self, x, y, s, size_px, font, color, ha="left", wrap_w=None):
        if wrap_w:
            s = wrap(s, size_px, wrap_w)
        self.ax.text(x, y, s, fontsize=size_px * PX, fontfamily=font, color=color,
                     ha=ha, va="center", zorder=5, linespacing=1.35)

    def panel(self, x, y, w, h, title=None, sub=None):
        self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=8",
                                         facecolor=PANEL, edgecolor=BORDER, linewidth=1, zorder=2))
        if title:
            self.text(x + 14, y + 20, title, 14, FONT_B, TEXT)
        if sub:
            self.text(x + 14, y + 38, sub, 11, FONT, MUTED)

    def header_panel(self, x, y, w, h, title, sub, accent):
        """Panel with a coloured top strip (used for the two simulator layers)."""
        self.panel(x, y, w, h)
        self.ax.add_patch(Rectangle((x + 1, y + 1), w - 2, 4, color=accent, zorder=3))
        self.text(x + 14, y + 24, title, 15, FONT_B, TEXT)
        self.text(x + 14, y + 43, sub, 11, FONT, MUTED)

    def slot(self, x, y, w, h, label):
        if not self.layout:
            return
        self.ax.add_patch(Rectangle((x, y), w, h, fill=False, edgecolor=SLOT, linewidth=1.2,
                                    linestyle=(0, (5, 3)), zorder=6))
        self.ax.text(x + w / 2, y + h / 2, wrap(label, 11, w - 12), fontsize=11 * PX, fontfamily=FONT,
                     color=SLOT, ha="center", va="center", zorder=7, linespacing=1.3)

    def save(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        suffix = "layout" if self.layout else "bg"
        self.fig.savefig(OUT / f"{name}_{suffix}.png", dpi=100)
        plt.close(self.fig)


def wrap(s, size_px, width_px):
    """Greedy word wrap using an average glyph width of 0.52 * font size."""
    max_chars = max(8, int(width_px / (size_px * 0.52)))
    lines, cur = [], ""
    for word in s.split():
        if len(cur) + len(word) + 1 > max_chars and cur:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    lines.append(cur)
    return "\n".join(lines)


def filter_strip(p, y=84):
    p.panel(24, y, 1232, 44)
    p.text(40, y + 22, "Filters", 12, FONT_B, MUTED)
    for i, name in enumerate(["Department", "JobRole", "TenureBand"]):
        p.slot(110 + i * 250, y + 6, 236, 32, f"Slicer (dropdown): {name}")


def overview(layout):
    p = Page("Workforce overview", "How big is the workforce, how many leave, and where?", layout)
    filter_strip(p)
    kpis = ["Workforce Size", "Attrition Count", "Attrition Rate", "Retention Rate",
            "Avg Tenure (Years)", "Avg Monthly Income"]
    cw = (1232 - 5 * 12) / 6
    for i, k in enumerate(kpis):
        x = 24 + i * (cw + 12)
        p.panel(x, 140, cw, 84)
        p.slot(x + 6, 146, cw - 12, 72, f"Card: {k}")
    p.panel(24, 236, 610, 230, "Attrition rate by department", "Hover for headcount and share of all leavers")
    p.slot(34, 286, 590, 170, "Clustered bar: Department × Attrition Rate (+ constant line 0.161)")
    p.panel(646, 236, 610, 230, "Attrition rate by job role", "Sorted high to low; label shows rate and n")
    p.slot(656, 286, 590, 170, "Bar: JobRole × Attrition Rate, data label Rate Label")
    w3 = (1232 - 24) / 3
    titles = [("Attrition by tenure", "Rate (columns) and headcount (line)",
               "Line & clustered column: TenureBand × Attrition Rate / Workforce Size"),
              ("Workforce by department", "Headcount share",
               "Donut: Department × Workforce Size"),
              ("Attrition by income band", "Hover for average monthly income",
               "Column: IncomeBand × Attrition Rate")]
    for i, (t, s, v) in enumerate(titles):
        x = 24 + i * (w3 + 12)
        p.panel(x, 478, w3, 212, t, s)
        p.slot(x + 10, 528, w3 - 20, 152, v)
    p.save("01_overview")


def drivers(layout):
    p = Page("Attrition drivers", "Which patterns deserve investigation? (associations, not causes)", layout)
    filter_strip(p)
    rows = [140, 323, 506]
    rh = 172
    p.panel(24, rows[0], 610, rh, "Overtime and attrition", "Attrition rate with and without overtime, by department")
    p.slot(34, rows[0] + 50, 150, 54, "Card: Attrition Rate Overtime")
    p.slot(34, rows[0] + 110, 150, 54, "Card: Overtime Risk Ratio")
    p.slot(194, rows[0] + 50, 430, 114, "Clustered column: OverTime × Attrition Rate, small multiples Department")
    p.panel(646, rows[0], 610, rh, "Attrition by satisfaction level", "Each line is one survey dimension (1 = lowest)")
    p.slot(656, rows[0] + 50, 590, 114, "Line: satisfaction_long Level × Sat Attrition Rate, legend Dimension")
    p.panel(24, rows[1], 610, rh, "Dissatisfaction adds up", "Number of survey dimensions rated at the lowest level")
    p.slot(34, rows[1] + 50, 590, 114, "Column: LowSatisfactionCount × Attrition Rate")
    p.panel(646, rows[1], 610, rh, "Pay relative to job-level peers", "Monthly income vs. the median of the same job level")
    p.slot(656, rows[1] + 50, 590, 114, "Clustered bar: SalaryPosition × Attrition Rate")
    p.panel(24, rows[2], 610, 184, "Attrition over tenure", "Rate (line) and headcount (columns), first 20 years")
    p.slot(34, rows[2] + 50, 590, 126, "Line & clustered column: YearsAtCompany × Attrition Rate / Workforce Size")
    p.panel(646, rows[2], 610, 184, "What the model relies on (SHAP)", "Top 12 factors by mean absolute SHAP value")
    p.slot(656, rows[2] + 50, 590, 100, "Bar: feature_importance FeatureLabel × Feature Importance, legend Effect")
    p.text(660, rows[2] + 166, "Importance = how much the model uses a factor. It does not prove that changing "
           "the factor changes behaviour.", 11, FONT, MUTED)
    p.save("02_drivers")


def simulator(layout):
    p = Page("Retention scenario simulator",
             "What could management explore, and how sensitive is the picture to assumptions?", layout)
    sw = (1232 - 24) / 3
    for i, name in enumerate(["Overtime Reduction", "Satisfaction Improvement", "Pay Alignment"]):
        x = 24 + i * (sw + 12)
        p.panel(x, 84, sw, 60)
        p.slot(x + 6, 90, sw - 12, 48, f"What-if slider: {name} (0–100 %)")
    # Layer A
    p.header_panel(24, 156, 610, 318, "A. Descriptive scenario (historical rates)",
                   "Illustrative leavers if groups took on the comparison group's current rate", "#2E86AB")
    cw = (590 - 16) / 3
    for i, k in enumerate(["Attrition Count ('Leavers today')", "Scenario A Leavers - Combined",
                           "Scenario A Change (pp)"]):
        p.slot(34 + i * (cw + 8), 214, cw, 64, f"Card: {k}")
    p.slot(34, 288, 590, 134, "Clustered bar: Scenario A Leavers - Overtime / - Satisfaction / - Pay, constant line 237")
    p.text(38, 446, "Assumes employees moved out of a group take on the current attrition rate of the comparison "
           "group. The combined total ignores overlap and overstates the effect.", 11, FONT, MUTED, wrap_w=580)
    # Layer B
    p.header_panel(646, 156, 610, 318, "B. Model sensitivity (how the model's score responds)",
                   "Change in the model's expected-leaver count", "#27AE60")
    cw = (590 - 8) / 2
    for i, k in enumerate(["Model Sensitivity - Combined", "Employees Affected - Overtime"]):
        p.slot(656 + i * (cw + 8), 214, cw, 64, f"Card: {k}")
    p.slot(656, 288, 590, 134, "Waterfall: SensitivityLever[Lever] × Lever Value")
    p.text(660, 446, "Shows how much the model relies on each lever. It is not a count of employees retained "
           "and not a causal estimate.", 11, FONT, MUTED, wrap_w=580)
    # Risk strip
    p.panel(24, 486, 610, 166, "Current risk distribution by department", "Aggregated model scores, no individuals shown")
    p.slot(34, 534, 590, 110, "Stacked bar: Department × Workforce Size, legend RiskBand")
    p.panel(646, 486, 610, 166, "Risk bands", "Band rule, headcount, actual attrition, average score")
    p.slot(656, 534, 590, 110, "Table: RiskBand, Rule, Workforce Size, Attrition Rate, Avg Predicted Risk")
    # disclaimer
    p.ax.add_patch(FancyBboxPatch((24, 662), 1232, 30, boxstyle="round,pad=0,rounding_size=6",
                                  facecolor="#FDF2E9", edgecolor="#F5CBA7", linewidth=1, zorder=2))
    p.text(40, 677, "Illustrative only. Layer A applies historical group rates under an explicit assumption. "
           "Layer B shows how the model's score responds. Neither is a causal estimate or a count of "
           "employees retained.", 11, FONT, "#8A4B12")
    p.save("03_simulator")


if __name__ == "__main__":
    for layout in (False, True):
        overview(layout)
        drivers(layout)
        simulator(layout)
    print("written to", OUT)
