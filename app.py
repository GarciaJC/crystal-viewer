"""Crystal Interface Generator — Streamlit application."""

import numpy as np
import streamlit as st
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from stmol import showmol

from utils.mp_client import fetch_structure, search_by_formula
from utils.renderer import STYLES, render_structure
from utils.exporters import to_poscar, to_cif, to_zip
from utils.interface_builder import analyze_substrates, get_terminations, build_interfaces, count_zsl_matches


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
    page_title="Crystal Interface Generator",
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

# Interface builder state
st.session_state.setdefault("ib_terminations", None)
st.session_state.setdefault("ib_cib", None)
st.session_state.setdefault("ib_generated", False)
st.session_state.setdefault("sa_matches", None)

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

**Interface Builder** \u2014 once both structures are loaded, scroll down
to set Miller indices, layer thicknesses, and ZSL parameters. Click
*Find Terminations*, pick one, then *Generate Interfaces*. Select any
generated interface from the dropdown to visualize and download it.
"""
        )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="app-header">
        <h1>\U0001f52c Crystal Interface Generator</h1>
        <p>
            Look up two crystal structures from the
            <a href="https://next-gen.materialsproject.org" target="_blank">Materials Project</a>
            database, visualize them in interactive 3D,
            and generate coherent interfaces between them.
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

# ---------------------------------------------------------------------------
# Interface Builder section (requires both structures loaded)
# ---------------------------------------------------------------------------
if left_data and right_data:
    from pathlib import Path

    st.divider()
    st.subheader("Interface Builder")
    st.markdown(
        "Generate coherent interfaces between the two loaded structures "
        "using pymatgen's `CoherentInterfaceBuilder`."
    )

    struct_sub = Structure.from_dict(left_data["structure_dict"])
    struct_film = Structure.from_dict(right_data["structure_dict"])

    # --- Substrate Analysis --------------------------------------------------
    st.markdown("#### Find Best Surface Matches")
    st.markdown(
        "Screen Miller index combinations to find the lowest-strain "
        "substrate/film pairings using pymatgen's `SubstrateAnalyzer`."
    )

    sa_c1, sa_c2, sa_c3 = st.columns(3)
    sa_film_max = sa_c1.number_input(
        "Film max Miller index", value=1, min_value=1, max_value=3, step=1, key="sa_film_max"
    )
    sa_sub_max = sa_c2.number_input(
        "Substrate max Miller index", value=1, min_value=1, max_value=3, step=1, key="sa_sub_max"
    )
    sa_max_area = sa_c3.number_input(
        "Max area (ZSL)", value=400.0, min_value=10.0, step=50.0, key="sa_max_area"
    )

    if st.button("Analyze Substrate Matches", use_container_width=True, key="sa_btn"):
        try:
            with st.spinner("Screening Miller index combinations..."):
                matches = analyze_substrates(
                    struct_sub, struct_film,
                    film_max_miller=sa_film_max,
                    substrate_max_miller=sa_sub_max,
                    max_area=sa_max_area,
                )
            if not matches:
                st.warning("No matches found. Try increasing max Miller index or max area.")
            else:
                st.session_state["sa_matches"] = matches
        except Exception as exc:
            st.error(f"Error analyzing substrates: {exc}")

    sa_matches = st.session_state["sa_matches"]
    if sa_matches:
        import pandas as pd

        df = pd.DataFrame([
            {
                "Film (hkl)": str(m["film_miller"]),
                "Substrate (hkl)": str(m["substrate_miller"]),
                "Von Mises Strain": f"{m['von_mises_strain']:.6f}",
                "Match Area (\u00c5\u00b2)": f"{m['match_area']:.1f}",
            }
            for m in sa_matches
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

        match_labels = [
            f"Film {m['film_miller']}  |  Sub {m['substrate_miller']}  |  "
            f"strain {m['von_mises_strain']:.6f}  |  area {m['match_area']:.1f}"
            for m in sa_matches
        ]

        def _on_match_selected():
            idx = match_labels.index(st.session_state["sa_match_select"])
            m = sa_matches[idx]
            sh, sk, sl = m["substrate_miller"]
            fh, fk, fl = m["film_miller"]
            st.session_state["sub_h"] = sh
            st.session_state["sub_k"] = sk
            st.session_state["sub_l"] = sl
            st.session_state["film_h"] = fh
            st.session_state["film_k"] = fk
            st.session_state["film_l"] = fl

        st.selectbox(
            "Use a match to populate Miller indices below",
            match_labels,
            key="sa_match_select",
            on_change=_on_match_selected,
        )

    st.divider()

    # --- Interface parameters ------------------------------------------------
    st.markdown("#### Parameters")

    p1, p2 = st.columns(2)

    with p1:
        st.markdown(f"**Substrate:** {left_data['formula']} ({left_data['mp_id']})")
        mc1, mc2, mc3 = st.columns(3)
        sub_h = mc1.number_input("h", value=1, step=1, key="sub_h")
        sub_k = mc2.number_input("k", value=0, step=1, key="sub_k")
        sub_l = mc3.number_input("l", value=0, step=1, key="sub_l")
        substrate_thickness = st.number_input(
            "Substrate thickness (layers)", value=12, min_value=1, step=1, key="sub_thick"
        )

    with p2:
        st.markdown(f"**Film:** {right_data['formula']} ({right_data['mp_id']})")
        mc4, mc5, mc6 = st.columns(3)
        film_h = mc4.number_input("h", value=1, step=1, key="film_h")
        film_k = mc5.number_input("k", value=0, step=1, key="film_k")
        film_l = mc6.number_input("l", value=0, step=1, key="film_l")
        film_thickness = st.number_input(
            "Film thickness (layers)", value=18, min_value=1, step=1, key="film_thick"
        )

    max_area = st.number_input("Max area (ZSL)", value=800.0, min_value=10.0, step=50.0, key="max_area")

    substrate_miller = (int(sub_h), int(sub_k), int(sub_l))
    film_miller = (int(film_h), int(film_k), int(film_l))

    # --- Step 1: Find terminations -------------------------------------------
    if st.button("Find Terminations", use_container_width=True, key="find_term_btn"):
        try:
            with st.spinner("Finding terminations..."):
                cib, terminations = get_terminations(
                    struct_sub, struct_film, substrate_miller, film_miller, max_area
                )
            if not terminations:
                st.error("No terminations found for the given Miller indices.")
            else:
                st.session_state["ib_cib"] = cib
                st.session_state["ib_terminations"] = terminations
                st.session_state["ib_generated"] = False
        except Exception as exc:
            st.error(f"Error finding terminations: {exc}")

    # --- Step 2: Select termination and generate -----------------------------
    terminations = st.session_state["ib_terminations"]
    if terminations:
        cib = st.session_state["ib_cib"]
        total_matches = count_zsl_matches(cib)

        term_labels = [
            f"[{i}] Film: {t[0]}, Substrate: {t[1]}"
            for i, t in enumerate(terminations)
        ]
        selected_label = st.selectbox("Select termination", term_labels, key="term_select")
        selected_idx = term_labels.index(selected_label)
        selected_termination = terminations[selected_idx]

        st.info(f"**{total_matches}** ZSL matches available for this configuration.")

        gen_c1, gen_c2 = st.columns([3, 1])
        num_interfaces = gen_c1.number_input(
            "Number of interfaces to generate",
            value=min(10, total_matches),
            min_value=1,
            max_value=total_matches,
            step=1,
            key="num_ifaces",
        )
        generate_all = gen_c2.checkbox("Generate all", key="gen_all")

        if generate_all:
            num_to_generate = None  # signals "all" to build_interfaces
            label = f"all {total_matches}"
        else:
            num_to_generate = num_interfaces
            label = str(num_interfaces)

        if st.button(
            f"Generate Interfaces ({label})",
            use_container_width=True,
            type="primary",
            key="gen_iface_btn",
        ):
            try:
                progress_bar = st.progress(0, text="Generating interfaces...")

                def _update_progress(current, total):
                    frac = current / total if total else 1.0
                    progress_bar.progress(frac, text=f"Building interface {current}/{total}...")

                interfaces = build_interfaces(
                    cib,
                    selected_termination,
                    film_thickness=film_thickness,
                    substrate_thickness=substrate_thickness,
                    num_interfaces=num_to_generate,
                    progress_callback=_update_progress,
                )
                progress_bar.empty()

                if not interfaces:
                    st.error("No interfaces were generated.")
                else:
                    # Save to generated_interfaces/ folder
                    out_dir = Path("generated_interfaces")
                    out_dir.mkdir(parents=True, exist_ok=True)

                    sub_formula = left_data["formula"]
                    film_formula = right_data["formula"]
                    sub_m = "".join(str(m) for m in substrate_miller)
                    film_m = "".join(str(m) for m in film_miller)

                    for i, entry in enumerate(interfaces):
                        area_int = round(entry["match_area"])
                        fname = f"{sub_formula}_{film_formula}_{sub_m}-{film_m}_area{area_int}_{i:03d}.vasp"
                        entry["structure"].to(str(out_dir / fname), fmt="poscar")

                    st.session_state["ib_generated"] = True
                    st.success(f"Generated {len(interfaces)} interfaces and saved to `generated_interfaces/`.")
            except Exception as exc:
                st.error(f"Error generating interfaces: {exc}")

    # --- Step 3: Visualize generated interfaces ------------------------------
    iface_dir = Path("generated_interfaces")
    if iface_dir.exists():
        vasp_files = sorted(iface_dir.glob("*.vasp"))
        if vasp_files:
            st.divider()
            st.markdown("#### Generated Interfaces")

            selected_file = st.selectbox(
                "Select an interface to visualize",
                vasp_files,
                format_func=lambda f: f.name,
                key="iface_file_select",
            )

            if selected_file:
                iface_struct = Structure.from_file(str(selected_file))

                # Info
                lattice = iface_struct.lattice
                # Cross-section area: |a x b| (area of the ab plane)
                area = np.linalg.norm(np.cross(lattice.matrix[0], lattice.matrix[1]))

                ic1, ic2, ic3 = st.columns(3)
                ic1.metric("Sites", iface_struct.num_sites)
                ic2.metric("Volume", f"{lattice.volume:.2f} \u00c5\u00b3")
                ic3.metric("Interface Area", f"{area:.2f} \u00c5\u00b2")

                # Viewer controls
                vc1, vc2, vc3 = st.columns(3)
                iface_style = vc1.selectbox(
                    "Representation",
                    list(STYLES.keys()),
                    key="iface_style",
                )
                iface_supercell = vc2.checkbox(
                    "2\u00d72\u00d72 supercell",
                    key="iface_supercell",
                )
                iface_labels = vc3.checkbox(
                    "Atom labels",
                    key="iface_labels",
                )

                sc = (2, 2, 2) if iface_supercell else (1, 1, 1)
                view = render_structure(
                    iface_struct,
                    style_name=iface_style,
                    supercell=sc,
                    show_labels=iface_labels,
                )
                showmol(view, height=450, width=700)

                # Download button for selected interface
                st.download_button(
                    "\u2b07 Download selected interface POSCAR",
                    data=to_poscar(iface_struct),
                    file_name=selected_file.name,
                    mime="text/plain",
                    key="dl_iface_poscar",
                    use_container_width=True,
                )
