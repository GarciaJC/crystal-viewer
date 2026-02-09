"""Crystal Structure Comparator — Streamlit application."""

import streamlit as st
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from stmol import showmol

from utils.mp_client import fetch_structure, search_by_formula
from utils.renderer import STYLES, render_structure
from utils.exporters import to_poscar, to_cif, to_zip


def _fmt_ehull(val, fmt=".3f"):
    """Format energy_above_hull, handling None."""
    if val is None:
        return "N/A"
    return f"{val:{fmt}}"


def _get_crystal_system(data: dict, struct: Structure) -> str:
    """Get crystal system from fetched data, falling back to SpacegroupAnalyzer."""
    cs = data.get("crystal_system", "")
    if cs:
        return cs
    try:
        sga = SpacegroupAnalyzer(struct)
        return sga.get_crystal_system()
    except Exception:
        return "N/A"


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Crystal Structure Comparator",
    page_icon="\U0001f52c",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS for info cards
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Info card container */
    div[data-testid="stMetric"] {
        background-color: #f8f9fb;
        border: 1px solid #e1e4e8;
        border-radius: 8px;
        padding: 12px 16px;
    }
    div[data-testid="stMetric"] label {
        color: #586069;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.25rem;
        font-weight: 600;
    }

    /* Header styling */
    .app-header {
        text-align: center;
        padding: 0.5rem 0 1rem 0;
    }
    .app-header h1 {
        margin-bottom: 0.25rem;
    }
    .app-header p {
        color: #586069;
        font-size: 1.05rem;
        margin-top: 0;
    }

    /* Comparison table */
    div[data-testid="stTable"] table {
        border-collapse: collapse;
        width: 100%;
    }
    div[data-testid="stTable"] th {
        background-color: #f0f2f6;
        font-weight: 600;
    }
    div[data-testid="stTable"] td, div[data-testid="stTable"] th {
        padding: 8px 12px;
        border: 1px solid #e1e4e8;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session-state defaults
# ---------------------------------------------------------------------------
for side in ("left", "right"):
    st.session_state.setdefault(f"{side}_data", None)
    st.session_state.setdefault(f"{side}_search", None)
    st.session_state.setdefault(f"{side}_style", "Ball & Stick")
    st.session_state.setdefault(f"{side}_supercell", False)
    st.session_state.setdefault(f"{side}_labels", False)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input(
        "Materials Project API Key",
        type="password",
        help="Required to fetch crystal structures.",
    )
    search_mode = st.radio(
        "Search mode",
        options=["MP ID", "Formula"],
        horizontal=True,
    )
    with st.expander("How to get an API key"):
        st.markdown(
            """
1. Go to [**Materials Project**](https://next-gen.materialsproject.org)
   and create a free account (or sign in).
2. Navigate to **Dashboard** \u2192 **API** settings, or go directly to
   [materialsproject.org/api](https://next-gen.materialsproject.org/api).
3. Click **Generate API Key** and copy it.
4. Paste the key in the field above. It is never stored outside this session.
"""
        )
    with st.expander("Help"):
        st.markdown(
            """
**MP ID mode** \u2014 enter a Materials Project ID directly (e.g. `mp-149`
for Si, `mp-5020` for GaAs).

**Formula mode** \u2014 type a chemical formula (e.g. `Fe2O3`). The app
searches for matching entries sorted by thermodynamic stability
(energy above hull). Pick one from the dropdown, then click *Look Up*.

**Visualization controls** appear below each 3D viewer once a
structure is loaded. You can switch representation style, toggle a
2\u00d72\u00d72 supercell, and show/hide atom labels.

**Downloads** \u2014 POSCAR and CIF buttons export the conventional cell.
When both structures are loaded a ZIP download with all files appears
in the comparison section.
"""
        )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="app-header">
        <h1>\U0001f52c Crystal Structure Comparator</h1>
        <p>
            Look up two crystal structures from the
            <a href="https://next-gen.materialsproject.org" target="_blank">Materials Project</a>
            database, visualize them side-by-side in interactive 3D,
            and download structure files.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Guard: require API key
if not api_key:
    st.info("Enter your Materials Project API key in the sidebar to get started.")
    st.stop()

# ---------------------------------------------------------------------------
# Helper: build a column UI for one structure slot
# ---------------------------------------------------------------------------

def _structure_column(side: str):
    """Render the UI for one side ('left' or 'right')."""
    label = "Structure A" if side == "left" else "Structure B"
    st.subheader(label)

    # --- Input -----------------------------------------------------------
    if search_mode == "MP ID":
        mp_id = st.text_input(
            "Material ID",
            placeholder="e.g. mp-149",
            key=f"{side}_mpid_input",
        )
        lookup = st.button("Look Up", key=f"{side}_lookup", use_container_width=True)

        if lookup and mp_id:
            try:
                with st.spinner("Fetching structure\u2026"):
                    data = fetch_structure(api_key, mp_id)
                st.session_state[f"{side}_data"] = data
            except (ValueError, ConnectionError) as exc:
                st.error(str(exc))

    else:  # Formula mode
        formula = st.text_input(
            "Formula",
            placeholder="e.g. Fe2O3",
            key=f"{side}_formula_input",
        )
        search_btn = st.button("Search", key=f"{side}_search_btn", use_container_width=True)

        if search_btn and formula:
            try:
                with st.spinner("Searching\u2026"):
                    results = search_by_formula(api_key, formula)
                st.session_state[f"{side}_search"] = results
            except (ValueError, ConnectionError) as exc:
                st.error(str(exc))

        results = st.session_state[f"{side}_search"]
        if results:
            options = [
                (
                    f"{r['material_id']}  {r['formula_pretty']}  "
                    f"(E_hull={r['energy_above_hull']:.3f} eV, {r['nsites']} sites)"
                )
                if r["energy_above_hull"] is not None
                else (
                    f"{r['material_id']}  {r['formula_pretty']}  "
                    f"(E_hull=N/A, {r['nsites']} sites)"
                )
                for r in results
            ]
            choice = st.selectbox(
                "Select a material", options, key=f"{side}_formula_select"
            )
            chosen_idx = options.index(choice)
            chosen_id = results[chosen_idx]["material_id"]
            fetch_btn = st.button("Look Up", key=f"{side}_fetch_btn", use_container_width=True)

            if fetch_btn:
                try:
                    with st.spinner("Fetching structure\u2026"):
                        data = fetch_structure(api_key, chosen_id)
                    st.session_state[f"{side}_data"] = data
                except (ValueError, ConnectionError) as exc:
                    st.error(str(exc))

    # --- Display loaded structure ----------------------------------------
    data = st.session_state[f"{side}_data"]
    if data is None:
        return

    struct = Structure.from_dict(data["structure_dict"])
    lattice = struct.lattice
    crystal_sys = _get_crystal_system(data, struct)

    st.divider()

    # Info card
    st.markdown(f"### {data['formula']}  \u2014  `{data['mp_id']}`")

    c1, c2, c3 = st.columns(3)
    c1.metric("Spacegroup", data["spacegroup"])
    c2.metric("Crystal System", crystal_sys.title() if crystal_sys else "N/A")
    c3.metric("Sites", data["nsites"])

    c4, c5, c6 = st.columns(3)
    c4.metric("E above hull", f"{_fmt_ehull(data['energy_above_hull'])} eV")
    c5.metric("Volume", f"{lattice.volume:.2f} \u00c5\u00b3")
    c6.metric("Density", f"{struct.density:.3f} g/cm\u00b3")

    st.caption(
        f"a = {lattice.a:.4f}  \u00c5 \u00a0\u00a0 "
        f"b = {lattice.b:.4f}  \u00c5 \u00a0\u00a0 "
        f"c = {lattice.c:.4f}  \u00c5 \u00a0\u00a0\u00a0\u00a0 "
        f"\u03b1 = {lattice.alpha:.2f}\u00b0 \u00a0\u00a0 "
        f"\u03b2 = {lattice.beta:.2f}\u00b0 \u00a0\u00a0 "
        f"\u03b3 = {lattice.gamma:.2f}\u00b0"
    )

    # Download buttons
    dl1, dl2 = st.columns(2)
    dl1.download_button(
        "\u2b07 Download POSCAR",
        data=to_poscar(struct),
        file_name=f"{data['mp_id']}.vasp",
        mime="text/plain",
        key=f"{side}_dl_poscar",
        use_container_width=True,
    )
    dl2.download_button(
        "\u2b07 Download CIF",
        data=to_cif(struct),
        file_name=f"{data['mp_id']}.cif",
        mime="text/plain",
        key=f"{side}_dl_cif",
        use_container_width=True,
    )

    # Viewer controls
    vc1, vc2, vc3 = st.columns(3)
    style_name = vc1.selectbox(
        "Representation",
        list(STYLES.keys()),
        key=f"{side}_style",
    )
    supercell_on = vc2.checkbox(
        "2\u00d72\u00d72 supercell",
        key=f"{side}_supercell",
    )
    show_labels = vc3.checkbox(
        "Atom labels",
        key=f"{side}_labels",
    )
    sc = (2, 2, 2) if supercell_on else (1, 1, 1)

    # 3D viewer
    view = render_structure(
        struct,
        style_name=style_name,
        supercell=sc,
        show_labels=show_labels,
    )
    showmol(view, height=450, width=500)


# ---------------------------------------------------------------------------
# Main layout: two columns
# ---------------------------------------------------------------------------
col_left, col_right = st.columns(2)
with col_left:
    _structure_column("left")
with col_right:
    _structure_column("right")

# ---------------------------------------------------------------------------
# Comparison section (shown when both structures are loaded)
# ---------------------------------------------------------------------------
left_data = st.session_state["left_data"]
right_data = st.session_state["right_data"]

if left_data and right_data:
    st.divider()
    st.subheader("Comparison")

    struct_l = Structure.from_dict(left_data["structure_dict"])
    struct_r = Structure.from_dict(right_data["structure_dict"])
    cs_l = _get_crystal_system(left_data, struct_l)
    cs_r = _get_crystal_system(right_data, struct_r)

    rows = {
        "Property": [
            "Formula",
            "MP ID",
            "Space Group",
            "Crystal System",
            "Sites",
            "E above hull (eV)",
            "a (\u00c5)",
            "b (\u00c5)",
            "c (\u00c5)",
            "\u03b1 (\u00b0)",
            "\u03b2 (\u00b0)",
            "\u03b3 (\u00b0)",
            "Volume (\u00c5\u00b3)",
        ],
        f"{left_data['formula']} ({left_data['mp_id']})": [
            left_data["formula"],
            left_data["mp_id"],
            left_data["spacegroup"],
            cs_l.title() if cs_l else "N/A",
            left_data["nsites"],
            _fmt_ehull(left_data["energy_above_hull"], ".4f"),
            f"{struct_l.lattice.a:.4f}",
            f"{struct_l.lattice.b:.4f}",
            f"{struct_l.lattice.c:.4f}",
            f"{struct_l.lattice.alpha:.2f}",
            f"{struct_l.lattice.beta:.2f}",
            f"{struct_l.lattice.gamma:.2f}",
            f"{struct_l.lattice.volume:.2f}",
        ],
        f"{right_data['formula']} ({right_data['mp_id']})": [
            right_data["formula"],
            right_data["mp_id"],
            right_data["spacegroup"],
            cs_r.title() if cs_r else "N/A",
            right_data["nsites"],
            _fmt_ehull(right_data["energy_above_hull"], ".4f"),
            f"{struct_r.lattice.a:.4f}",
            f"{struct_r.lattice.b:.4f}",
            f"{struct_r.lattice.c:.4f}",
            f"{struct_r.lattice.alpha:.2f}",
            f"{struct_r.lattice.beta:.2f}",
            f"{struct_r.lattice.gamma:.2f}",
            f"{struct_r.lattice.volume:.2f}",
        ],
    }
    st.table(rows)

    # ZIP download with all files
    structures = {
        f"{left_data['mp_id']}_{left_data['formula']}": struct_l,
        f"{right_data['mp_id']}_{right_data['formula']}": struct_r,
    }
    zip_bytes = to_zip(structures)
    st.download_button(
        "\U0001f4e6 Download All as ZIP",
        data=zip_bytes,
        file_name="crystal_structures.zip",
        mime="application/zip",
        use_container_width=True,
    )
