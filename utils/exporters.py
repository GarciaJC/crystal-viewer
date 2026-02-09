"""Export crystal structures to POSCAR, CIF, and ZIP formats."""

import io
import zipfile

from pymatgen.core import Structure
from pymatgen.io.vasp import Poscar


def to_poscar(structure: Structure) -> str:
    """Convert a pymatgen Structure to a POSCAR string."""
    return Poscar(structure).get_str()


def to_cif(structure: Structure) -> str:
    """Convert a pymatgen Structure to a CIF string."""
    return structure.to(fmt="cif")


def to_zip(structures: dict[str, Structure]) -> bytes:
    """Create a ZIP archive containing POSCAR and CIF files for each structure.

    Args:
        structures: Mapping of label (e.g. "mp-149_Si") to Structure objects.

    Returns:
        Bytes of the ZIP file.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for label, struct in structures.items():
            zf.writestr(f"{label}.vasp", to_poscar(struct))
            zf.writestr(f"{label}.cif", to_cif(struct))
    return buf.getvalue()
