"""Publication-quality figure styling — the default for every report tool.

Design decisions (see skills/tools/plotting_conventions.md for the rationale):
- Okabe-Ito colorblind-safe palette in a fixed, CVD-validated order
  (adjacent-pair Delta E checked computationally, not by eye).
- Journal geometry: 3.5 in single-column / 7.2 in double-column widths,
  300 dpi raster, TrueType (fonttype 42) embedded in PDF/PS so text stays
  editable in vector editors.
- Inward ticks on all four spines with minor ticks, the physics-journal look.
- Recessive grid, frameless legends, constrained layout.

Usage:
    from helio_agent.style import apply_style, figsize
    apply_style()                      # once, before any figure
    fig, ax = plt.subplots(figsize=figsize("column"))
Seaborn (statistical plots) inherits the same look via seaborn_theme().
"""

from __future__ import annotations

# Okabe-Ito (Wong 2011, Nature Methods) reordered so adjacent pairs stay
# separable under deuteranopia/tritanopia (validated: worst adjacent pair
# Delta E 9.6 deutan / 8.5 tritan; all lightness+chroma checks pass).
# Fixed order — never cycle or reassign colors when series counts change.
PALETTE = [
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#009E73",  # bluish green
    "#E69F00",  # orange
    "#CC79A7",  # reddish purple
    "#56B4E9",  # sky blue
    "#000000",  # black (7th series / emphasis)
]

EVENT_COLOR = "#D55E00"     # vertical event markers (vermillion, not red)
NEUTRAL = "#666666"          # secondary annotations
SEQUENTIAL_CMAP = "viridis"  # magnitude data (perceptually uniform)
DIVERGING_CMAP = "RdBu_r"    # signed data (e.g. Bz): neutral at zero

# Figure widths in inches (heights chosen per aspect)
_WIDTHS = {"column": 3.5, "page": 7.2, "slide": 10.0}

RC = {
    # --- fonts: sans-serif, sized for print at column width ---
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 9.0,
    "axes.titlesize": 10.5,
    "axes.labelsize": 10.0,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8.5,
    "figure.titlesize": 11.0,
    "mathtext.default": "regular",
    # --- axes and ticks: boxed, inward, with minors ---
    "axes.linewidth": 1.0,
    "axes.edgecolor": "black",
    "axes.prop_cycle": __import__("cycler").cycler(color=PALETTE),
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.top": True,
    "ytick.right": True,
    "xtick.minor.visible": True,
    "ytick.minor.visible": True,
    "xtick.major.size": 4.5,
    "ytick.major.size": 4.5,
    "xtick.minor.size": 2.5,
    "ytick.minor.size": 2.5,
    "xtick.major.width": 1.0,
    "ytick.major.width": 1.0,
    # --- marks ---
    "lines.linewidth": 1.5,
    "lines.markersize": 5.0,
    "lines.markeredgewidth": 1.0,
    # --- recessive grid ---
    "axes.grid": True,
    "grid.color": "#b0b0b0",
    "grid.alpha": 0.25,
    "grid.linewidth": 0.6,
    # --- legend: frameless ---
    "legend.frameon": False,
    "legend.handlelength": 1.6,
    "legend.borderaxespad": 0.4,
    # --- layout and output ---
    "figure.constrained_layout.use": True,
    "figure.dpi": 130,          # on-screen
    "savefig.dpi": 300,         # print-quality raster
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
    "pdf.fonttype": 42,         # embed TrueType: editable text in Illustrator
    "ps.fonttype": 42,
    "svg.fonttype": "none",
}


def apply_style() -> None:
    """Apply the publication style globally (Agg backend, all rcParams)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update(RC)


def figsize(width: str | float = "page", aspect: float = 0.5) -> tuple[float, float]:
    """(width, height) inches. width: 'column' (3.5), 'page' (7.2),
    'slide' (10), or a number; aspect = height/width."""
    w = _WIDTHS.get(width, width) if isinstance(width, str) else float(width)
    if isinstance(w, str):
        raise ValueError(f"unknown width {width!r}; use {list(_WIDTHS)} or inches")
    return (w, w * aspect)


def seaborn_theme() -> None:
    """Make seaborn statistical plots inherit the same publication look."""
    import seaborn as sns
    apply_style()
    sns.set_theme(context="paper", style="ticks", palette=PALETTE, rc=RC)


def style_event_lines(ax, times, labels=None) -> None:
    """Standard event markers: vermillion dashed verticals + small top labels."""
    import pandas as pd
    for i, t in enumerate(times or []):
        ts = pd.Timestamp(t)
        ax.axvline(ts, color=EVENT_COLOR, ls="--", lw=0.9, alpha=0.85, zorder=1)
        if labels and i < len(labels):
            ax.annotate(labels[i], xy=(ts, 1.0), xycoords=("data", "axes fraction"),
                        rotation=90, va="top", ha="right", fontsize=7,
                        color=EVENT_COLOR)
