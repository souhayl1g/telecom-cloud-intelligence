"""Gantt chart aligned with ESPRIT PFE milestones — English."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from datetime import datetime, timedelta
import matplotlib.dates as mdates

start_date = datetime(2026, 2, 10)
end_date = datetime(2026, 8, 3)
today = datetime(2026, 4, 3)

milestones = [
    ("PFE Launch",           datetime(2026, 2, 2)),
    ("Journal de Bord",      datetime(2026, 2, 16)),
    ("Bilan V1",             datetime(2026, 3, 16)),
    ("Restitution 1",        datetime(2026, 4, 6)),
    ("Mid-Internship Visit", datetime(2026, 5, 4)),
    ("Bilan V2",             datetime(2026, 5, 18)),
    ("Report V1",            datetime(2026, 6, 22)),
    ("Restitution 2",        datetime(2026, 6, 29)),
    ("Bilan V3",             datetime(2026, 7, 27)),
    ("Report V2",            datetime(2026, 8, 3)),
]

phases = [
    ("Ph.1 Design & Architecture",   datetime(2026,2,10),  datetime(2026,2,22),  "#4F46E5", True),
    ("Ph.2 Infrastructure & Lake",   datetime(2026,2,23),  datetime(2026,3,3),   "#7C3AED", True),
    ("Ph.3 ML Models & AI",          datetime(2026,3,4),   datetime(2026,3,5),   "#8B5CF6", True),
    ("Ph.4 Dashboard & Viz",         datetime(2026,3,5),   datetime(2026,3,11),  "#2563EB", True),
    ("Ph.5 Auth, Security & CI/CD",  datetime(2026,3,12),  datetime(2026,4,1),   "#0891B2", True),
    ("Ph.6 Advanced UX & DWH",       datetime(2026,4,1),   datetime(2026,4,4),   "#059669", True),
    ("Ph.7 HCS Licensing",           datetime(2026,4,6),   datetime(2026,5,4),   "#CA8A04", False),
    ("Ph.8 Advanced Features",       datetime(2026,5,5),   datetime(2026,6,1),   "#D97706", False),
    ("Ph.9 TT Integration & Tests",  datetime(2026,6,1),   datetime(2026,6,22),  "#EA580C", False),
    ("Ph.10 Report & Defense",       datetime(2026,6,22),  datetime(2026,8,3),   "#DC2626", False),
]

fig, ax = plt.subplots(figsize=(22, 10))
fig.patch.set_facecolor("#FAFBFC")
ax.set_facecolor("#FAFBFC")

n = len(phases)
bar_h = 0.45

# Milestone lines
for ml_label, ml_date in milestones:
    x = mdates.date2num(ml_date)
    ax.axvline(x=x, color="#CBD5E1", linewidth=0.8, linestyle=":", zorder=1)
    ax.text(x, n + 0.15, ml_label, ha="center", va="bottom",
            fontsize=6.5, color="#64748B", rotation=35, fontweight="500")

# Bars
for i, (label, ps, pe, color, done) in enumerate(phases):
    y = n - 1 - i
    left = mdates.date2num(ps)
    right = mdates.date2num(pe)
    w = right - left
    alpha = 0.9 if done else 0.4
    hatch = "" if done else "///"
    bar = FancyBboxPatch(
        (left, y - bar_h / 2), w, bar_h,
        boxstyle="round,pad=0.3",
        facecolor=color, edgecolor="white", linewidth=1.5,
        alpha=alpha, zorder=3, hatch=hatch,
    )
    ax.add_patch(bar)
    days = (pe - ps).days
    weeks = round(days / 7)
    dur = f"{weeks}w" if weeks >= 1 else f"{days}d"
    if w > 5:
        ax.text(left + w / 2, y, dur, ha="center", va="center",
                fontsize=8, fontweight="bold", color="white", zorder=4)
    if done:
        ax.text(right + 0.8, y, "\u2713", ha="left", va="center",
                fontsize=10, color="#16A34A", fontweight="bold", zorder=4)
    elif ps <= today <= pe:
        ax.text(right + 0.8, y, "\u25B6", ha="left", va="center",
                fontsize=8, color="#CA8A04", fontweight="bold", zorder=4)

# Today
td = mdates.date2num(today)
ax.axvline(x=td, color="#EF4444", linewidth=2, linestyle="--", zorder=5, alpha=0.8)
ax.text(td + 0.5, n - 0.3, f"Today\n{today.strftime('%d/%m/%Y')}",
        fontsize=8, color="#EF4444", fontweight="bold", va="top", zorder=6)

# Axes
ax.xaxis_date()
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0, interval=2))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
ax.xaxis.set_minor_locator(mdates.WeekdayLocator(byweekday=0))
ax.set_xlim(mdates.date2num(datetime(2026, 1, 28)), mdates.date2num(datetime(2026, 8, 10)))
plt.setp(ax.get_xticklabels(), fontsize=7.5, color="#64748B")
ax.set_ylim(-0.7, n + 1.2)
ax.set_yticks(range(n - 1, -1, -1))
ax.set_yticklabels([p[0] for p in phases], fontsize=9, fontweight="600", color="#1E293B")
ax.grid(axis="x", which="minor", color="#F1F5F9", linewidth=0.3, zorder=0)
ax.grid(axis="x", which="major", color="#E2E8F0", linewidth=0.5, zorder=0)

# Month header
ax2 = ax.twiny()
ax2.set_xlim(ax.get_xlim())
ax2.xaxis_date()
ax2.xaxis.set_major_locator(mdates.MonthLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%B %Y"))
plt.setp(ax2.get_xticklabels(), fontsize=9, fontweight="600", color="#475569")
ax2.tick_params(length=0)

fig.suptitle("Gantt Chart — NexOps AI (Telecom Cloud Intelligence Platform)",
             fontsize=14, fontweight="bold", color="#0F172A", y=0.98)
ax.set_title("PFE Internship — Huawei Tunisia (Cloud IT) — Souhayl Guenichi — 10/02/2026 to 03/08/2026",
             fontsize=10, color="#475569", pad=8)

legend = [
    mpatches.Patch(facecolor="#4F46E5", alpha=0.9, label="Completed"),
    mpatches.Patch(facecolor="#94A3B8", alpha=0.4, hatch="///", label="Planned"),
    mpatches.Patch(facecolor="none", edgecolor="#EF4444", linestyle="--", linewidth=1.5, label="Today"),
    mpatches.Patch(facecolor="none", edgecolor="#CBD5E1", linestyle=":", linewidth=0.8, label="ESPRIT Milestones"),
]
ax.legend(handles=legend, loc="lower right", fontsize=8,
          frameon=True, facecolor="white", edgecolor="#E2E8F0")

for s in ["top", "right", "left"]:
    ax.spines[s].set_visible(False)
    ax2.spines[s].set_visible(False)
ax.spines["bottom"].set_color("#CBD5E1")
ax.tick_params(left=False)

plt.tight_layout()
plt.savefig("/home/souhayl/projects/telecom-cloud-intelligence/report/gantt_pfe.png", dpi=200, bbox_inches="tight")
plt.savefig("/home/souhayl/projects/telecom-cloud-intelligence/report/gantt_pfe.pdf", bbox_inches="tight")
print("Done")
