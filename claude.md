# Crystal Structure Comparator

## Project Overview
A Streamlit web app that lets users look up two crystal structures from the
Materials Project database, visualize them side-by-side in interactive 3D
viewers, and download the structures as POSCAR and CIF files.

## Tech Stack
- **Framework**: Streamlit
- **3D Visualization**: py3Dmol + stmol (for embedding in Streamlit)
- **Data Source**: Materials Project API via `mp-api` (MPRester)
- **Structure Handling**: pymatgen (Structure objects, CIF/POSCAR conversion)
- **Python**: 3.10+

## Key Design Decisions
- The MP API key is entered by the user in the sidebar at runtime (never hardcoded)
- Structures are cached in `st.session_state` to avoid redundant API calls
- Use py3Dmol's `addUnitCell()` to show the unit cell box
- Use Jmol color scheme for atom colors
- Side-by-side layout using `st.columns(2)`

## File Structure
crystal-viewer/
├── CLAUDE.md              # This file
├── app.py                 # Main Streamlit app
├── make_interfaces.py     # CLI interface generator (standalone)
├── requirements.txt       # Python dependencies
├── utils/
│   ├── __init__.py
│   ├── mp_client.py       # Materials Project API wrapper
│   ├── renderer.py        # 3D visualization functions
│   ├── exporters.py       # POSCAR/CIF export helpers
│   └── interface_builder.py  # Coherent interface generation
├── generated_interfaces/  # Output folder for generated POSCAR files (gitignored)
├── .streamlit/
│   └── config.toml        # Streamlit theme config
└── README.md              # User-facing documentation

## Important Notes
- pymatgen Structure objects are NOT directly serializable by Streamlit cache.
  Store them as dicts via `structure.as_dict()` and reconstruct with
  `Structure.from_dict()`.
- `stmol.showmol()` renders py3Dmol views as HTML iframes in Streamlit.
- For CIF export: `structure.to(fmt="cif")`
- For POSCAR export: `Poscar(structure).get_str()`
- `view.addUnitCell()` in py3Dmol works when the model is loaded from CIF format.
- The app should handle errors gracefully (invalid MP IDs, network issues, etc.)
