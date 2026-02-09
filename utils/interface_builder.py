"""Interface generation utilities using pymatgen's CoherentInterfaceBuilder."""

from pymatgen.analysis.interfaces.coherent_interfaces import CoherentInterfaceBuilder
from pymatgen.analysis.interfaces.zsl import ZSLGenerator
from pymatgen.core.structure import Structure


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
