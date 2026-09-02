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
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 130, "axes.grid": True,
                         "grid.alpha": 0.3, "font.size": 9})
    return plt


@tool(family="report")
def plot_timeseries(file: str, columns: list[str] | None = None,
                    title: str = "", log_y: bool = False,
                    event_times: list[str] | None = None,
                    event_labels: list[str] | None = None,
                    out_name: str = "timeseries.png") -> dict:
    """Single-panel time-series plot of one or more columns from a workspace CSV."""
    plt = _setup_mpl()
    df = _load_csv(file)
    cols = columns or list(df.columns)[:6]
    fig, ax = plt.subplots(figsize=(10, 4))
    for c in cols:
        ax.plot(df.index, df[c], lw=0.8, label=c)
    if log_y:
        ax.set_yscale("log")
    for i, t in enumerate(event_times or []):
        import pandas as pd
        ax.axvline(pd.Timestamp(t), color="crimson", ls="--", lw=0.8)
        if event_labels and i < len(event_labels):
            ax.annotate(event_labels[i], xy=(pd.Timestamp(t), ax.get_ylim()[1]),
                        rotation=90, va="top", fontsize=7, color="crimson")
    ax.set_xlabel("Time (UTC)")
    ax.set_title(title or file.rsplit("/", 1)[-1])
    ax.legend(loc="best", fontsize=7)
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
    import pandas as pd
    plt = _setup_mpl()
    n = len(files_columns)
    fig, axes = plt.subplots(n, 1, figsize=(10, 1.9 * n), sharex=True)
    if n == 1:
        axes = [axes]
    for ax, spec in zip(axes, files_columns):
        df = _load_csv(spec["file"])
        col = spec["column"]
        ax.plot(df.index, df[col], lw=0.8, color="steelblue")
        ax.set_ylabel(spec.get("label", col), fontsize=8)
        if spec.get("log"):
            ax.set_yscale("log")
        for t in event_times or []:
            ax.axvline(pd.Timestamp(t), color="crimson", ls="--", lw=0.8)
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
    plt = _setup_mpl()
    df = _load_csv(file)
    scale = 6371.0 if units == "Re" else 1.0
    sats = sorted({c.rsplit("_", 2)[0] for c in df.columns})
    a1, a2 = plane[0], plane[1]
    fig, ax = plt.subplots(figsize=(6, 6))
    for sat in sats:
        x = df[f"{sat}_{a1}_km"] / scale
        y = df[f"{sat}_{a2}_km"] / scale
        ax.plot(x, y, lw=1.0, label=sat)
        ax.plot(x.iloc[-1], y.iloc[-1], "o", ms=4)
    if units == "Re":
        from matplotlib.patches import Circle
        ax.add_patch(Circle((0, 0), 1.0, color="navy", alpha=0.6))
    ax.set_xlabel(f"{a1.upper()} ({units})")
    ax.set_ylabel(f"{a2.upper()} ({units})")
    ax.set_title(title or f"Trajectories ({plane.upper()} plane)")
    ax.set_aspect("equal")
    ax.legend(fontsize=7)
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
