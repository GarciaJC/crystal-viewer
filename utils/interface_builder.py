"""Interface generation utilities using pymatgen's CoherentInterfaceBuilder."""

from pymatgen.analysis.elasticity.strain import Deformation
from pymatgen.analysis.interfaces.coherent_interfaces import CoherentInterfaceBuilder
from pymatgen.analysis.interfaces.substrate_analyzer import SubstrateAnalyzer
from pymatgen.analysis.interfaces.zsl import ZSLGenerator
from pymatgen.core.structure import Structure
from pymatgen.core.surface import SlabGenerator


def analyze_substrates(
    substrate: Structure,
    film: Structure,
    film_max_miller: int = 1,
    substrate_max_miller: int = 1,
    max_area: float = 400,
) -> list[dict]:
    """Screen all Miller index combinations and return matches sorted by strain.

    Returns a list of dicts with keys: film_miller, substrate_miller,
    von_mises_strain, match_area.
    """
    sa = SubstrateAnalyzer(
        film_max_miller=film_max_miller,
        substrate_max_miller=substrate_max_miller,
        max_area=max_area,
    )
    matches = list(sa.calculate(film, substrate, lowest=True))
    results = []
    for m in matches:
        results.append({
            "film_miller": m.film_miller,
            "substrate_miller": m.substrate_miller,
            "von_mises_strain": m.von_mises_strain,
            "match_area": m.match_area,
        })
    results.sort(key=lambda r: r["von_mises_strain"])
    return results


def compute_interface_strain(match, film_structure: Structure, film_miller: tuple) -> float:
    """Compute the Von Mises strain for a single ZSL match.

    Uses the match transformation matrix to derive the Green-Lagrange strain
    tensor, then returns the scalar Von Mises strain.
    """
    deformation = Deformation(match.match_transformation)
    strain = deformation.green_lagrange_strain
    return float(strain.von_mises_strain)


def compute_interface_energies(
    interface_dicts: list[dict],
    device: str = "cpu",
    progress_callback=None,
) -> list[float]:
    """Compute MACE potential energies for a list of interface structures.

    Each entry in *interface_dicts* must have a ``"structure"`` key containing
    a pymatgen Structure.  Returns a list of energies in eV (same order).
    """
    from mace.calculators import mace_mp
    from pymatgen.io.ase import AseAtomsAdaptor

    calc = mace_mp(model="medium", dispersion=False, default_dtype="float32", device=device)
    adaptor = AseAtomsAdaptor()
    energies = []
    total = len(interface_dicts)
    for i, entry in enumerate(interface_dicts):
        atoms = adaptor.get_atoms(entry["structure"])
        atoms.calc = calc
        energies.append(float(atoms.get_potential_energy()))
        if progress_callback:
            progress_callback(i + 1, total)
    return energies


def get_terminations(
    substrate: Structure,
    film: Structure,
    substrate_miller: tuple,
    film_miller: tuple,
    max_area: float = 800,
) -> tuple:
    """Return (CoherentInterfaceBuilder, list_of_terminations).

    The CIB is returned so it can be reused for interface generation
    without rebuilding.
    """
    zsl = ZSLGenerator(max_area=max_area)
    cib = CoherentInterfaceBuilder(
        film_structure=film,
        substrate_structure=substrate,
        film_miller=film_miller,
        substrate_miller=substrate_miller,
        zslgen=zsl,
    )
    return cib, cib.terminations


def count_zsl_matches(cib: CoherentInterfaceBuilder) -> int:
    """Return the number of ZSL matches already computed by the builder."""
    return len(cib.zsl_matches)


def build_interfaces(
    cib: CoherentInterfaceBuilder,
    termination: tuple,
    film_thickness: int = 18,
    substrate_thickness: int = 12,
    num_interfaces: int | None = 10,
    progress_callback=None,
    film_structure: Structure | None = None,
    film_miller: tuple | None = None,
) -> list[dict]:
    """Generate up to *num_interfaces* coherent interfaces.

    If *num_interfaces* is None, generate all available interfaces.
    *progress_callback*, if provided, is called with (current, total) after
    each interface is built.

    Returns a list of dicts with keys: "structure" (Structure),
    "match_area" (float), and "von_mises_strain" (float).
    """
    iterator = cib.get_interfaces(
        termination=termination,
        film_thickness=film_thickness,
        substrate_thickness=substrate_thickness,
    )
    total = count_zsl_matches(cib)
    zsl_matches = cib.zsl_matches
    results = []
    for i, iface in enumerate(iterator):
        area = zsl_matches[i].match_area if i < len(zsl_matches) else 0.0
        strain = 0.0
        if film_structure is not None and film_miller is not None and i < len(zsl_matches):
            try:
                strain = compute_interface_strain(zsl_matches[i], film_structure, film_miller)
            except Exception:
                strain = 0.0
        results.append({"structure": iface, "match_area": area, "von_mises_strain": strain})
        if progress_callback:
            progress_callback(len(results), total)
        if num_interfaces is not None and len(results) >= num_interfaces:
            break
    return results
