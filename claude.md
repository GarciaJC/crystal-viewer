# Crystal Interface Generator

## Project Overview
A Streamlit web app that lets users look up two crystal structures from the
Materials Project database, visualize them in interactive 3D viewers, screen
surface orientations for lattice compatibility, and generate coherent
interfaces between them. Structures can be downloaded as POSCAR and CIF
files, and generated interfaces are saved as POSCAR files.

## Tech Stack
- **Framework**: Streamlit
- **3D Visualization**: py3Dmol + stmol (for embedding in Streamlit)
- **Data Source**: Materials Project API via `mp-api` (MPRester)
- **Structure Handling**: pymatgen (Structure objects, CIF/POSCAR conversion)
- **Surface Screening**: pymatgen SubstrateAnalyzer (Von Mises strain ranking)
- **Interface Generation**: pymatgen CoherentInterfaceBuilder + ZSLGenerator
- **Python**: 3.10+

## Key Design Decisions
- The MP API key is entered by the user in the sidebar at runtime (never hardcoded)
- Structures are cached in `st.session_state` to avoid redundant API calls
- Use py3Dmol's `addUnitCell()` to show the unit cell box
- Use Jmol color scheme for atom colors
- Side-by-side layout using `st.columns(2)`
- SubstrateAnalyzer screens Miller index pairs before interface generation
- `cib.zsl_matches` is used to count available interfaces (already computed
  when the CoherentInterfaceBuilder is created — no extra cost)
- Miller index widgets use `session_state.setdefault()` for defaults and
  `on_change` callbacks to update values (avoids Streamlit warnings about
  both `value=` and session state being set)
- Generated POSCAR filenames include per-interface match area:
  `Al_SiC_100-100_area24_000.vasp`
- `build_interfaces()` returns dicts with both `structure` and `match_area`
  so the area can be embedded in filenames

## File Structure
crystal-viewer/
├── claude.md              # This file
├── app.py                 # Main Streamlit app
├── make_interfaces.py     # CLI interface generator (standalone)
├── requirements.txt       # Python dependencies
├── utils/
│   ├── __init__.py
│   ├── mp_client.py       # Materials Project API wrapper
│   ├── renderer.py        # 3D visualization functions
│   ├── exporters.py       # POSCAR/CIF export helpers
│   └── interface_builder.py  # Substrate analysis + coherent interface generation
├── generated_interfaces/  # Output folder for generated POSCAR files (gitignored)
├── .streamlit/
│   └── config.toml        # Streamlit theme config
└── README.md              # User-facing documentation

## App Workflow
1. User enters MP API key in sidebar
2. Load two structures (by MP ID or formula search)
3. View side-by-side 3D visualizations and comparison table
4. **Substrate Analysis** — screen Miller index combinations, view strain
   table, select best match to auto-populate parameters
5. **Interface Builder** — set thicknesses/area, find terminations, see ZSL
   match count, generate interfaces (with progress bar), visualize results

## Important Notes
- pymatgen Structure objects are NOT directly serializable by Streamlit cache.
  Store them as dicts via `structure.as_dict()` and reconstruct with
  `Structure.from_dict()`.
- `stmol.showmol()` renders py3Dmol views as HTML iframes in Streamlit.
- For CIF export: `structure.to(fmt="cif")`
- For POSCAR export: `Poscar(structure).get_str()`
- `view.addUnitCell()` in py3Dmol works when the model is loaded from CIF format.
- The app should handle errors gracefully (invalid MP IDs, network issues, etc.)
- `SubstrateAnalyzer.calculate()` with `lowest=True` returns one match per
  Miller pair (fastest screening). Without it, returns all matches.
- `CoherentInterfaceBuilder.get_interfaces()` is a generator — each yielded
  structure corresponds to a ZSL match in `cib.zsl_matches` (same order).
