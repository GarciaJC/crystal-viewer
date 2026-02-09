# Crystal Structure Comparator

A Streamlit web application for looking up, visualizing, and comparing crystal structures from the [Materials Project](https://next-gen.materialsproject.org) database. Enter two material IDs (or search by chemical formula), view them side-by-side in interactive 3D viewers, inspect key crystallographic properties, and download structure files in POSCAR and CIF formats.

![Screenshot](screenshot.png)

## Features

- **Side-by-side 3D visualization** of two crystal structures using py3Dmol
- **Search by MP ID or formula** with results sorted by thermodynamic stability
- **Multiple rendering styles** — Ball & Stick, Space-filling, and Stick
- **Supercell toggle** — switch between 1x1x1 and 2x2x2 views
- **Atom labels** — overlay element symbols on atoms
- **Property cards** — space group, crystal system, sites, energy above hull, volume, and density
- **Comparison table** — side-by-side lattice parameters and metadata when both structures are loaded
- **File export** — download individual POSCAR/CIF files or a ZIP bundle with all files

## Installation

```bash
git clone https://github.com/<your-username>/crystal-viewer.git
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

## Tech Stack

| Component | Library |
|---|---|
| Web framework | [Streamlit](https://streamlit.io) |
| 3D visualization | [py3Dmol](https://github.com/3dmol/3Dmol.js) + [stmol](https://github.com/napoles-uach/stmol) |
| Data source | [Materials Project API](https://next-gen.materialsproject.org/api) via [mp-api](https://github.com/materialsproject/api) |
| Structure handling | [pymatgen](https://pymatgen.org) |

## Deployment

### Streamlit Community Cloud

1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with your GitHub account.
3. Click **New app** and select this repository, branch `main`, and file `app.py`.
4. Click **Deploy**. The app will be live at a public URL within a few minutes.

Users will enter their own Materials Project API key in the sidebar at runtime, so no secrets configuration is needed on the server.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
