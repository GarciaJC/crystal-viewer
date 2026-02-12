# Crystal Interface Generator

A Streamlit web application for looking up crystal structures from the [Materials Project](https://next-gen.materialsproject.org) database, visualizing them in interactive 3D, and generating coherent interfaces between two materials. Screen surface orientations for the best lattice matches, tune Miller indices and layer thicknesses, and download structure files in POSCAR and CIF formats.

## Features

### Structure Lookup & Visualization
- **Side-by-side 3D visualization** of two crystal structures using py3Dmol
- **Search by MP ID or formula** with results sorted by thermodynamic stability
- **Multiple rendering styles** — Ball & Stick, Space-filling, and Stick
- **Supercell toggle** — switch between 1x1x1 and 2x2x2 views
- **Atom labels** — overlay element symbols on atoms
- **Property cards** — space group, crystal system, sites, energy above hull, volume, and density
- **Comparison table** — side-by-side lattice parameters and metadata when both structures are loaded
- **File export** — download individual POSCAR/CIF files or a ZIP bundle

### Substrate Analysis
- **Surface match screening** — automatically screen all Miller index combinations using pymatgen's `SubstrateAnalyzer` to find the lowest-strain substrate/film pairings
- **Sortable results table** — view film/substrate Miller indices, Von Mises strain, and match area for every combination
- **Auto-populate parameters** — select a match from the dropdown to fill in Miller indices for the interface builder

### Interface Generation
- **Coherent interface builder** — generate interfaces using pymatgen's `CoherentInterfaceBuilder` with configurable Miller indices, ZSL area, and layer thicknesses
- **ZSL match count** — see how many interfaces are available before generating
- **Flexible generation** — choose a specific number of interfaces or generate all with a single checkbox
- **Progress bar** — real-time progress tracking during interface generation
- **Descriptive filenames** — generated POSCAR files include material formulas, Miller indices, and interface area (e.g. `Al_SiC_100-100_area24_000.vasp`)
- **Interface visualization** — browse generated interfaces in an interactive 3D viewer with sites, volume, and interface area metrics

## Installation

```bash
git clone https://github.com/GarciaJC/crystal-viewer.git
cd crystal-viewer
pip install -r requirements.txt
streamlit run app.py
```

The app will open at [http://localhost:8501](http://localhost:8501).

## Getting a Materials Project API Key

1. Create a free account at [next-gen.materialsproject.org](https://next-gen.materialsproject.org).
2. Go to **Dashboard > API** or visit [materialsproject.org/api](https://next-gen.materialsproject.org/api) directly.
3. Click **Generate API Key** and copy it.
4. Paste the key into the sidebar of the app. The key is only used for the current session and is never stored.

## Usage

1. **Enter your API key** in the sidebar.
2. **Choose a search mode** — *MP ID* to look up a material directly (e.g. `mp-149` for Si), or *Formula* to search by chemical formula (e.g. `Fe2O3`).
3. **Load structures** in the left and right columns using the *Look Up* button.
4. **Adjust the 3D viewer** — change the representation style, enable a 2x2x2 supercell, or toggle atom labels.
5. **Download files** — use the POSCAR/CIF buttons under each structure, or the *Download All as ZIP* button in the comparison section.
6. **Find best surfaces** — once both structures are loaded, click **Analyze Substrate Matches** to screen Miller index combinations. The results table shows Von Mises strain and match area for each pairing. Select a match to auto-populate the Miller indices below.
7. **Generate interfaces** — in the Interface Builder section:
   - Adjust substrate/film thickness and max ZSL area.
   - Click **Find Terminations**, select one from the dropdown.
   - See how many ZSL matches are available, then choose how many to generate or check **Generate all**.
   - Click **Generate Interfaces** — a progress bar tracks the build.
   - Pick any generated interface from the dropdown to visualize and download it.

## Tech Stack

| Component | Library |
|---|---|
| Web framework | [Streamlit](https://streamlit.io) |
| 3D visualization | [py3Dmol](https://github.com/3dmol/3Dmol.js) + [stmol](https://github.com/napoles-uach/stmol) |
| Data source | [Materials Project API](https://next-gen.materialsproject.org/api) via [mp-api](https://github.com/materialsproject/api) |
| Structure handling | [pymatgen](https://pymatgen.org) |
| Surface screening | [pymatgen SubstrateAnalyzer](https://pymatgen.org) |
| Interface generation | [pymatgen CoherentInterfaceBuilder](https://pymatgen.org) |

## Deployment

### Streamlit Community Cloud

1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with your GitHub account.
3. Click **New app** and select this repository, branch `main`, and file `app.py`.
4. Click **Deploy**. The app will be live at a public URL within a few minutes.

Users will enter their own Materials Project API key in the sidebar at runtime, so no secrets configuration is needed on the server.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
