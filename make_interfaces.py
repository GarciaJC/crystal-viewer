#!/usr/bin/env python3
"""
Interface Generator

A script to generate coherent interfaces between two materials using Pymatgen.
Can load structures from local CIF files or download from the Materials Project.

Author: Juan C. Garcia (2025)
"""

import argparse
import os
import pickle
import sys
from pathlib import Path

from pymatgen.analysis.interfaces.coherent_interfaces import CoherentInterfaceBuilder
from pymatgen.analysis.interfaces.zsl import ZSLGenerator
from pymatgen.core.structure import Structure


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate coherent interfaces between two materials.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Local file options
    parser.add_argument(
        "--substrate-file",
        type=str,
        default=None,
        help="Path to substrate structure file (CIF, POSCAR, etc.)",
    )
    parser.add_argument(
        "--film-file",
        type=str,
        default=None,
        help="Path to film structure file (CIF, POSCAR, etc.)",
    )

    # Materials Project options (optional, requires mp-api)
    parser.add_argument(
        "--substrate-id",
        type=str,
        default="mp-134",
        help="Materials Project ID for substrate (default: mp-134 for Al). Used if --substrate-file not provided.",
    )
    parser.add_argument(
        "--film-id",
        type=str,
        default="mp-8062",
        help="Materials Project ID for film (default: mp-8062 for SiC). Used if --film-file not provided.",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Materials Project API key (or set MP_API_KEY environment variable)",
    )

    # Interface builder options
    parser.add_argument(
        "--substrate-miller",
        type=int,
        nargs=3,
        default=[1, 0, 0],
        help="Miller indices for substrate surface",
    )
    parser.add_argument(
        "--film-miller",
        type=int,
        nargs=3,
        default=[1, 0, 0],
        help="Miller indices for film surface",
    )
    parser.add_argument(
        "--max-area",
        type=float,
        default=800,
        help="Maximum area for ZSL generator",
    )
    parser.add_argument(
        "--film-thickness",
        type=int,
        default=18,
        help="Film thickness in layers",
    )
    parser.add_argument(
        "--substrate-thickness",
        type=int,
        default=12,
        help="Substrate thickness in layers",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Output directory for generated files",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of interfaces to generate per batch",
    )
    return parser.parse_args()


def load_structure_from_file(filepath: str) -> Structure:
    """Load a structure from a local file."""
    print(f"  Loading from {filepath}...", end=" ", flush=True)
    structure = Structure.from_file(filepath)
    print(f"Done! ({structure.composition.reduced_formula})")
    return structure


def download_structure_from_mp(mp_id: str, api_key: str = None) -> Structure:
    """Download a structure from the Materials Project."""
    try:
        from mp_api.client import MPRester
    except ImportError as e:
        print(f"\nError: Failed to import mp-api: {e}")
        print("\nThis may be due to package version incompatibility with Python 3.10.")
        print("Try installing compatible versions:")
        print('  pip install "emmet-core<0.70" "mp-api<0.42"')
        print("\nOr provide local structure files with --substrate-file and --film-file")
        sys.exit(1)

    print(f"  Downloading {mp_id} from Materials Project...", end=" ", flush=True)
    with MPRester(api_key) as mpr:
        structure = mpr.get_structure_by_material_id(mp_id)
    print(f"Done! ({structure.composition.reduced_formula})")
    return structure


def get_structure(file_path: str = None, mp_id: str = None, api_key: str = None, name: str = "structure") -> Structure:
    """Get a structure from either a local file or Materials Project."""
    if file_path:
        if not Path(file_path).exists():
            print(f"\nError: {name} file not found: {file_path}")
            sys.exit(1)
        return load_structure_from_file(file_path)
    elif mp_id:
        return download_structure_from_mp(mp_id, api_key)
    else:
        print(f"\nError: No {name} provided. Use --{name}-file or --{name}-id")
        sys.exit(1)


def select_termination(terminations: list) -> tuple:
    """Display terminations and let user select one."""
    print("\nAvailable terminations:")
    print("-" * 50)
    for i, term in enumerate(terminations):
        print(f"  [{i}] Film: {term[0]}, Substrate: {term[1]}")
    print("-" * 50)

    while True:
        try:
            choice = input(f"\nSelect termination (0-{len(terminations)-1}): ").strip()
            idx = int(choice)
            if 0 <= idx < len(terminations):
                return terminations[idx]
            print(f"Please enter a number between 0 and {len(terminations)-1}")
        except ValueError:
            print("Please enter a valid number")


def print_progress_bar(current: int, total: int = None, bar_length: int = 40):
    """Print a progress bar to the console."""
    if total:
        percent = current / total
        filled = int(bar_length * percent)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"\r  Progress: [{bar}] {current}/{total} ({percent*100:.1f}%)", end="", flush=True)
    else:
        # Unknown total - show spinner-like progress
        spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        print(f"\r  Generating interfaces... {spinner[current % 10]} {current} generated", end="", flush=True)


def generate_interfaces_batch(interface_iterator, batch_size: int, current_count: int = 0):
    """Generate a batch of interfaces from the iterator."""
    interfaces = []
    for i, interface in enumerate(interface_iterator):
        interfaces.append(interface)
        print_progress_bar(current_count + i + 1)
        if len(interfaces) >= batch_size:
            break
    print()  # New line after progress bar
    return interfaces


def main():
    args = parse_arguments()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir.absolute()}")

    # Step 1: Load structures
    print("\n" + "=" * 60)
    print("Step 1: Loading structures")
    print("=" * 60)

    # Get API key if needed for MP downloads
    api_key = args.api_key or os.environ.get("MP_API_KEY")
    use_mp = not args.substrate_file or not args.film_file

    if use_mp and not api_key:
        print("\nWarning: No API key provided for Materials Project download.")
        print("Set MP_API_KEY environment variable or use --api-key argument.")
        print("Alternatively, provide local files with --substrate-file and --film-file")

    substrate = get_structure(
        file_path=args.substrate_file,
        mp_id=args.substrate_id,
        api_key=api_key,
        name="substrate"
    )
    film = get_structure(
        file_path=args.film_file,
        mp_id=args.film_id,
        api_key=api_key,
        name="film"
    )

    substrate_label = args.substrate_file or args.substrate_id
    film_label = args.film_file or args.film_id

    print(f"\n  Substrate: {substrate.composition.reduced_formula} ({substrate_label})")
    print(f"  Film: {film.composition.reduced_formula} ({film_label})")

    # Step 2: Set up ZSL Generator
    print("\n" + "=" * 60)
    print("Step 2: Setting up ZSL Generator")
    print("=" * 60)
    print(f"  Max area: {args.max_area}")

    zsl = ZSLGenerator(max_area=args.max_area)

    # Step 3: Create Coherent Interface Builder
    print("\n" + "=" * 60)
    print("Step 3: Creating Coherent Interface Builder")
    print("=" * 60)

    substrate_miller = tuple(args.substrate_miller)
    film_miller = tuple(args.film_miller)

    print(f"  Substrate Miller indices: {substrate_miller}")
    print(f"  Film Miller indices: {film_miller}")

    cib = CoherentInterfaceBuilder(
        film_structure=film,
        substrate_structure=substrate,
        film_miller=film_miller,
        substrate_miller=substrate_miller,
        zslgen=zsl,
    )

    # Step 4: Show terminations and let user select
    print("\n" + "=" * 60)
    print("Step 4: Select interface termination")
    print("=" * 60)

    if not cib.terminations:
        print("Error: No terminations found for the given Miller indices!")
        sys.exit(1)

    selected_termination = select_termination(cib.terminations)
    print(f"\nSelected: Film={selected_termination[0]}, Substrate={selected_termination[1]}")

    # Step 5: Generate interfaces in batches
    print("\n" + "=" * 60)
    print("Step 5: Generating interfaces")
    print("=" * 60)
    print(f"  Film thickness: {args.film_thickness} layers")
    print(f"  Substrate thickness: {args.substrate_thickness} layers")
    print(f"  Batch size: {args.batch_size}")
    print()

    # Get the iterator
    interface_iterator = cib.get_interfaces(
        termination=selected_termination,
        film_thickness=args.film_thickness,
        substrate_thickness=args.substrate_thickness,
    )

    all_interfaces = []
    batch_num = 1

    # Generate first batch
    print(f"Generating batch {batch_num} (interfaces 1-{args.batch_size})...")
    batch = generate_interfaces_batch(interface_iterator, args.batch_size, len(all_interfaces))
    all_interfaces.extend(batch)

    if len(batch) < args.batch_size:
        print(f"  All interfaces generated! Total: {len(all_interfaces)}")
    else:
        # Ask user if they want more batches
        while True:
            print(f"\n  Generated {len(all_interfaces)} interfaces so far.")
            response = input("  Generate more interfaces? (y/n): ").strip().lower()

            if response in ["n", "no"]:
                print("  Stopping interface generation.")
                break
            elif response in ["y", "yes"]:
                batch_num += 1
                start = len(all_interfaces) + 1
                end = start + args.batch_size - 1
                print(f"\nGenerating batch {batch_num} (interfaces {start}-{end})...")
                batch = generate_interfaces_batch(interface_iterator, args.batch_size, len(all_interfaces))

                if not batch:
                    print("  No more interfaces available. Generation complete!")
                    break

                all_interfaces.extend(batch)

                if len(batch) < args.batch_size:
                    print(f"  All interfaces generated! Total: {len(all_interfaces)}")
                    break
            else:
                print("  Please enter 'y' or 'n'")

    print(f"\n  Total interfaces generated: {len(all_interfaces)}")

    # Step 6: Pickle the interfaces
    print("\n" + "=" * 60)
    print("Step 6: Saving interfaces to pickle file")
    print("=" * 60)

    pickle_path = output_dir / "interfaces.pkl"
    with open(pickle_path, "wb") as f:
        pickle.dump(all_interfaces, f)
    print(f"  Saved {len(all_interfaces)} interfaces to: {pickle_path}")

    # Step 7: Save first 10 interfaces as VASP POSCAR files
    print("\n" + "=" * 60)
    print("Step 7: Saving first 10 interfaces as VASP POSCAR files")
    print("=" * 60)

    vasp_dir = output_dir / "vasp_files"
    vasp_dir.mkdir(parents=True, exist_ok=True)

    sub_formula = substrate.composition.reduced_formula
    film_formula = film.composition.reduced_formula
    sub_miller_str = "".join(str(m) for m in substrate_miller)
    film_miller_str = "".join(str(m) for m in film_miller)

    num_to_save = min(10, len(all_interfaces))
    for i in range(num_to_save):
        filename = f"{sub_formula}_{film_formula}_{sub_miller_str}-{film_miller_str}_interface_{i:03d}.vasp"
        filepath = vasp_dir / filename
        all_interfaces[i].to(str(filepath), fmt="poscar")
        print(f"  Saved: {filepath}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Substrate: {substrate.composition.reduced_formula} {substrate_miller} ({substrate_label})")
    print(f"  Film: {film.composition.reduced_formula} {film_miller} ({film_label})")
    print(f"  Termination: {selected_termination}")
    print(f"  Total interfaces: {len(all_interfaces)}")
    print(f"  Pickle file: {pickle_path}")
    print(f"  VASP files: {vasp_dir} ({num_to_save} files)")
    print("\nDone!")


if __name__ == "__main__":
    main()
