"""Interface generation utilities using pymatgen's CoherentInterfaceBuilder."""

from pymatgen.analysis.interfaces.coherent_interfaces import CoherentInterfaceBuilder
from pymatgen.analysis.interfaces.substrate_analyzer import SubstrateAnalyzer
from pymatgen.analysis.interfaces.zsl import ZSLGenerator
from pymatgen.core.structure import Structure


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


def build_interfaces(
    cib: CoherentInterfaceBuilder,
    termination: tuple,
    film_thickness: int = 18,
    substrate_thickness: int = 12,
    num_interfaces: int = 10,
) -> list:
    """Generate up to *num_interfaces* coherent interfaces.

    Returns a list of pymatgen Structure objects.
    """
    iterator = cib.get_interfaces(
        termination=termination,
        film_thickness=film_thickness,
        substrate_thickness=substrate_thickness,
    )
    interfaces = []
    for iface in iterator:
        interfaces.append(iface)
        if len(interfaces) >= num_interfaces:
            break
    return interfaces
