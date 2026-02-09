"""3D visualization of crystal structures using py3Dmol."""

import py3Dmol
from pymatgen.core import Structure


# Visualization style presets
STYLES = {
    "Ball & Stick": {
        "sphere": {"scale": 0.3, "colorscheme": "Jmol"},
        "stick": {"radius": 0.15, "colorscheme": "Jmol"},
    },
    "Space-filling": {
        "sphere": {"scale": 0.8, "colorscheme": "Jmol"},
    },
    "Stick": {
        "stick": {"radius": 0.2, "colorscheme": "Jmol"},
    },
}


def _make_supercell(structure: Structure, size: tuple[int, int, int]) -> Structure:
    """Create a supercell of the given structure."""
    if size == (1, 1, 1):
        return structure
    return structure * size


def render_structure(
    structure: Structure,
    style_name: str = "Ball & Stick",
    supercell: tuple[int, int, int] = (1, 1, 1),
    show_labels: bool = False,
    width: int = 500,
    height: int = 450,
) -> py3Dmol.view:
    """Render a pymatgen Structure as an interactive 3D viewer.

    Args:
        structure: A pymatgen Structure object.
        style_name: One of "Ball & Stick", "Space-filling", "Stick".
        supercell: Supercell dimensions as (a, b, c).
        show_labels: Whether to show element symbol labels on atoms.
        width: Viewer width in pixels.
        height: Viewer height in pixels.

    Returns:
        A py3Dmol.view object ready for display.
    """
    display_structure = _make_supercell(structure, supercell)
    cif_str = display_structure.to(fmt="cif")

    view = py3Dmol.view(width=width, height=height)
    view.addModel(cif_str, "cif")

    atom_style = STYLES.get(style_name, STYLES["Ball & Stick"])
    view.setStyle({}, atom_style)

    if show_labels:
        view.addPropertyLabels(
            "elem",
            {},
            {
                "fontColor": "black",
                "font": "sans-serif",
                "fontSize": 12,
                "showBackground": True,
                "backgroundOpacity": 0.7,
                "backgroundColor": "white",
                "alignment": "center",
            },
        )

    view.addUnitCell()
    view.setBackgroundColor("white")
    view.zoomTo()

    return view
