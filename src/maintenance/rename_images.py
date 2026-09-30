import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MAINTENANCE_DIR = Path(__file__).resolve().parent


def main():
    for script in (
        "standardize_catalog_identity.py",
        "map_source_images.py",
    ):
        subprocess.run(
            [sys.executable, str(MAINTENANCE_DIR / script), "--apply"],
            cwd=REPO_ROOT,
            check=True,
        )


if __name__ == "__main__":
    main()
