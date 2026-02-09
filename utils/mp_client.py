"""Materials Project API wrapper for fetching crystal structures."""

from mp_api.client import MPRester


def fetch_structure(api_key: str, mp_id: str) -> dict:
    """Fetch a crystal structure and its metadata from Materials Project.

    Args:
        api_key: Materials Project API key.
        mp_id: Material ID (e.g. "mp-149").

    Returns:
        Dict with keys: structure_dict, formula, spacegroup, mp_id, nsites,
        energy_above_hull.

    Raises:
        ValueError: If the material ID is not found or the API key is invalid.
        ConnectionError: If there is a network issue.
    """
    mp_id = mp_id.strip()
    if not mp_id:
        raise ValueError("Material ID cannot be empty.")

    try:
        with MPRester(api_key) as mpr:
            structure = mpr.get_structure_by_material_id(mp_id)

            docs = mpr.materials.summary.search(
                material_ids=[mp_id],
                fields=[
                    "material_id",
                    "formula_pretty",
                    "symmetry",
                    "energy_above_hull",
                    "nsites",
                ],
            )
            if not docs:
                raise ValueError(
                    f"No summary data found for {mp_id}. "
                    "Check that the ID is correct."
                )

            doc = docs[0]
            spacegroup = ""
            crystal_system = ""
            if hasattr(doc, "symmetry") and doc.symmetry:
                spacegroup = getattr(doc.symmetry, "symbol", str(doc.symmetry))
                crystal_system = getattr(doc.symmetry, "crystal_system", "")
                if crystal_system:
                    crystal_system = str(crystal_system)

            return {
                "structure_dict": structure.as_dict(),
                "formula": doc.formula_pretty,
                "spacegroup": spacegroup,
                "crystal_system": crystal_system,
                "mp_id": str(doc.material_id),
                "nsites": doc.nsites,
                "energy_above_hull": doc.energy_above_hull,
            }

    except ValueError:
        raise
    except Exception as exc:
        msg = str(exc)
        if "API_KEY" in msg.upper() or "401" in msg or "UNAUTHORIZED" in msg.upper():
            raise ValueError(
                "Invalid API key. Get one at https://next-gen.materialsproject.org/api"
            ) from exc
        if "404" in msg or "not found" in msg.lower():
            raise ValueError(f"Material ID '{mp_id}' not found.") from exc
        raise ConnectionError(
            f"Error contacting Materials Project: {msg}"
        ) from exc


def search_by_formula(api_key: str, formula: str) -> list[dict]:
    """Search Materials Project by chemical formula.

    Args:
        api_key: Materials Project API key.
        formula: Chemical formula (e.g. "Si", "Fe2O3").

    Returns:
        List of dicts sorted by energy_above_hull, each with keys:
        material_id, formula_pretty, energy_above_hull, nsites.

    Raises:
        ValueError: If no results are found or the API key is invalid.
        ConnectionError: If there is a network issue.
    """
    formula = formula.strip()
    if not formula:
        raise ValueError("Formula cannot be empty.")

    try:
        with MPRester(api_key) as mpr:
            docs = mpr.materials.summary.search(
                formula=formula,
                fields=[
                    "material_id",
                    "formula_pretty",
                    "energy_above_hull",
                    "nsites",
                ],
            )

        if not docs:
            raise ValueError(f"No materials found for formula '{formula}'.")

        results = []
        for doc in docs:
            results.append(
                {
                    "material_id": str(doc.material_id),
                    "formula_pretty": doc.formula_pretty,
                    "energy_above_hull": doc.energy_above_hull,
                    "nsites": doc.nsites,
                }
            )

        results.sort(key=lambda x: x["energy_above_hull"] or 0.0)
        return results

    except ValueError:
        raise
    except Exception as exc:
        msg = str(exc)
        if "API_KEY" in msg.upper() or "401" in msg or "UNAUTHORIZED" in msg.upper():
            raise ValueError(
                "Invalid API key. Get one at https://next-gen.materialsproject.org/api"
            ) from exc
        raise ConnectionError(
            f"Error contacting Materials Project: {msg}"
        ) from exc
