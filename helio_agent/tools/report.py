"""Report: publication-style figures and PDF reports.

Conventions (see skills/tools/plotting_conventions.md): UTC time axes,
labels carry dataset IDs and units, event markers as dashed vertical lines.
"""

from __future__ import annotations

from helio_agent.registry import tool
from helio_agent.workspace import output_path


def _load_csv(file: str):
    import pandas as pd
    return pd.read_csv(file, index_col="time", parse_dates=True)


def _setup_mpl():
    from helio_agent.style import apply_style
    apply_style()
    import matplotlib.pyplot as plt
    return plt


@tool(family="report")
def plot_timeseries(file: str, columns: list[str] | None = None,
                    title: str = "", log_y: bool = False,
                    event_times: list[str] | None = None,
                    event_labels: list[str] | None = None,
                    series_labels: list[str] | None = None,
                    y_label: str = "",
                    out_name: str = "timeseries.png") -> dict:
    """Single-panel time-series plot of one or more columns from a workspace CSV.

    series_labels: legend names for the plotted columns, in the same order
    (e.g. ["Monthly SSN", "13-month smoothed"]) — finished figures should
    never show raw column names. y_label: axis label with units.
    """
    from helio_agent.style import figsize, style_event_lines
    plt = _setup_mpl()
    df = _load_csv(file)
    cols = columns or list(df.columns)[:6]
    if series_labels and len(series_labels) != len(cols):
        return {"status": "error",
                "error": f"series_labels has {len(series_labels)} entries "
                         f"for {len(cols)} columns"}
    fig, ax = plt.subplots(figsize=figsize("page", 0.42))
    for i, c in enumerate(cols):
        ax.plot(df.index, df[c], lw=1.2,
                label=series_labels[i] if series_labels else c)
    if log_y:
        ax.set_yscale("log")
    style_event_lines(ax, event_times, event_labels)
    ax.set_xlabel("Time (UTC)")
    if y_label:
        ax.set_ylabel(y_label)
    ax.set_title(title or file.rsplit("/", 1)[-1])
    if len(cols) > 1:
        ax.legend(loc="best")
    fig.autofmt_xdate()
    fpath = output_path(out_name)
    fig.savefig(fpath, bbox_inches="tight")
    plt.close(fig)
    return {"file": str(fpath), "artifacts": [str(fpath)]}


@tool(family="report")
def plot_stack(files_columns: list[dict], title: str = "",
               event_times: list[str] | None = None,
               out_name: str = "stackplot.png") -> dict:
    """Multi-panel stacked time-series plot (the standard space-physics figure).

    files_columns: list of {"file": path, "column": name, "label": ylabel,
    "log": bool} — one panel per entry, shared time axis.
    """
    from helio_agent.style import PALETTE, figsize, style_event_lines
    plt = _setup_mpl()
    n = len(files_columns)
    w, _ = figsize("page")
    fig, axes = plt.subplots(n, 1, figsize=(w, 1.35 * n + 0.5), sharex=True)
    if n == 1:
        axes = [axes]
    for i, (ax, spec) in enumerate(zip(axes, files_columns)):
        df = _load_csv(spec["file"])
        col = spec["column"]
        ax.plot(df.index, df[col], lw=1.1, color=PALETTE[i % len(PALETTE)])
        ax.set_ylabel(spec.get("label", col))
        if spec.get("log"):
            ax.set_yscale("log")
        style_event_lines(ax, event_times)
    axes[0].set_title(title)
    axes[-1].set_xlabel("Time (UTC)")
    fig.autofmt_xdate()
    fig.align_ylabels(axes)
    fpath = output_path(out_name)
    fig.savefig(fpath, bbox_inches="tight")
    plt.close(fig)
    return {"file": str(fpath), "n_panels": n, "artifacts": [str(fpath)]}


@tool(family="report")
def plot_solar_map(fits_file: str, out_name: str = "solar_map.png",
                   clip_percent: float = 99.5) -> dict:
    """Render a solar FITS file (AIA/HMI/LASCO/...) with the proper colormap."""
    import numpy as np
    import sunpy.map
    plt = _setup_mpl()
    m = sunpy.map.Map(fits_file)
    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(projection=m)
    vmax = np.nanpercentile(m.data, clip_percent)
    m.plot(axes=ax, clip_interval=None, vmin=0, vmax=vmax)
    fpath = output_path(out_name)
    fig.savefig(fpath, bbox_inches="tight")
    plt.close(fig)
    return {"file": str(fpath), "instrument": m.instrument,
            "date": str(m.date), "artifacts": [str(fpath)]}


@tool(family="report")
def plot_orbits(file: str, plane: str = "xy", units: str = "Re",
                title: str = "", out_name: str = "orbits.png") -> dict:
    """Plot spacecraft trajectories from an ephemeris CSV (fetch_spacecraft_ephemeris).

    plane: 'xy', 'xz', or 'yz' (GSE/GSM axes). units: 'Re' (Earth radii) or 'km'.
    Earth drawn at origin when units='Re'.
    """
    from helio_agent.style import PALETTE
    plt = _setup_mpl()
    df = _load_csv(file)
    scale = 6371.0 if units == "Re" else 1.0
    sats = sorted({c.rsplit("_", 2)[0] for c in df.columns})
    a1, a2 = plane[0], plane[1]
    fig, ax = plt.subplots(figsize=(5, 5))
    for i, sat in enumerate(sats):
        x = df[f"{sat}_{a1}_km"] / scale
        y = df[f"{sat}_{a2}_km"] / scale
        color = PALETTE[i % len(PALETTE)]
        ax.plot(x, y, lw=1.3, label=sat, color=color)
        ax.plot(x.iloc[-1], y.iloc[-1], "o", ms=5, mfc="white",
                mec=color, mew=1.2)
    if units == "Re":
        from matplotlib.patches import Circle
        ax.add_patch(Circle((0, 0), 1.0, color="#0072B2", alpha=0.7, zorder=3))
    ax.set_xlabel(f"{a1.upper()} ({units})")
    ax.set_ylabel(f"{a2.upper()} ({units})")
    ax.set_title(title or f"Trajectories ({plane.upper()} plane)")
    ax.set_aspect("equal")
    ax.legend()
    fpath = output_path(out_name)
    fig.savefig(fpath, bbox_inches="tight")
    plt.close(fig)
    return {"file": str(fpath), "spacecraft": sats, "artifacts": [str(fpath)]}


@tool(family="report")
def write_pdf_report(title: str, sections: list[dict],
                     out_name: str = "report.pdf") -> dict:
    """Assemble a PDF report from text sections and figure files.

    sections: list of {"heading": str, "text": str, "image": optional path}.
    Every numeric claim in the text must trace to an audit-logged tool result.
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 9, title)
    pdf.ln(2)
    for sec in sections:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, sec.get("heading", ""))
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "", 10)
        text = sec.get("text", "").encode("latin-1", "replace").decode("latin-1")
        if text:
            pdf.multi_cell(0, 5, text)
        img = sec.get("image")
        if img:
            pdf.ln(2)
            pdf.set_x(pdf.l_margin)
            pdf.image(img, x=pdf.l_margin, w=pdf.epw)
        pdf.ln(4)
    fpath = output_path(out_name)
    pdf.output(str(fpath))
    return {"file": str(fpath), "n_sections": len(sections), "artifacts": [str(fpath)]}


@tool(family="report")
def plot_distribution(file: str, columns: list[str], kind: str = "violin",
                      title: str = "", y_label: str = "", log_y: bool = False,
                      out_name: str = "distribution.png") -> dict:
    """Statistical distribution plot (seaborn): 'violin', 'box', or 'hist'.

    Compares the distributions of one or more numeric columns from a
    workspace CSV — e.g. solar wind speed by interval, or Bz in storm vs
    quiet times (merge_series first to get the columns side by side).
    """
    from helio_agent.style import figsize, seaborn_theme
    seaborn_theme()
    import matplotlib.pyplot as plt
    import seaborn as sns

    df = _load_csv(file)[columns]
    long = df.melt(var_name="series", value_name="value").dropna()
    fig, ax = plt.subplots(figsize=figsize("column", 0.85))
    if kind == "violin":
        sns.violinplot(data=long, x="series", y="value", hue="series",
                       inner="quart", cut=0, linewidth=1.0, legend=False, ax=ax)
    elif kind == "box":
        sns.boxplot(data=long, x="series", y="value", hue="series",
                    width=0.5, linewidth=1.0, fliersize=2.5, legend=False, ax=ax)
    elif kind == "hist":
        sns.histplot(data=long, x="value", hue="series", element="step",
                     stat="density", common_norm=False, ax=ax)
    else:
        return {"status": "error", "error": "kind must be violin, box, or hist"}
    if log_y and kind != "hist":
        ax.set_yscale("log")
    ax.set_title(title)
    ax.set_xlabel("")
    if y_label:
        (ax.set_xlabel if kind == "hist" else ax.set_ylabel)(y_label)
    sns.despine(fig=fig) if kind == "hist" else None
    fpath = output_path(out_name)
    fig.savefig(fpath)
    plt.close(fig)
    return {"file": str(fpath), "kind": kind,
            "n_points": int(len(long)), "artifacts": [str(fpath)]}


@tool(family="report")
def plot_scatter(file: str, x_column: str, y_column: str, fit: bool = False,
                 title: str = "", x_label: str = "", y_label: str = "",
                 log_x: bool = False, log_y: bool = False,
                 out_name: str = "scatter.png") -> dict:
    """Scatter plot of two columns with optional linear fit + 95% CI band
    (seaborn regplot). Open markers, publication style.

    Typical use: solar wind speed vs |B|, Kp vs Bz, flare peak flux vs
    duration. Reports Pearson r alongside the figure.
    """
    import numpy as np
    from helio_agent.style import PALETTE, figsize, seaborn_theme
    seaborn_theme()
    import matplotlib.pyplot as plt
    import seaborn as sns

    df = _load_csv(file)[[x_column, y_column]].dropna()
    if df.empty:
        return {"status": "error", "error": "no overlapping valid data"}
    fig, ax = plt.subplots(figsize=figsize("column", 0.85))
    sns.regplot(data=df, x=x_column, y=y_column, fit_reg=fit, ax=ax,
                scatter_kws={"s": 14, "facecolors": "none",
                             "edgecolors": PALETTE[0], "linewidths": 0.8},
                line_kws={"color": PALETTE[1], "lw": 1.5})
    if log_x:
        ax.set_xscale("log")
    if log_y:
        ax.set_yscale("log")
    ax.set_xlabel(x_label or x_column)
    ax.set_ylabel(y_label or y_column)
    ax.set_title(title)
    r = float(np.corrcoef(df[x_column], df[y_column])[0, 1])
    fpath = output_path(out_name)
    fig.savefig(fpath)
    plt.close(fig)
    return {"file": str(fpath), "n_points": len(df),
            "pearson_r": round(r, 4), "artifacts": [str(fpath)]}
