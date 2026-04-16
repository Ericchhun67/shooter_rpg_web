from __future__ import annotations

import shutil
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    web_dir = project_root / "build" / "web"
    dist_dir = project_root / "dist"

    if not web_dir.is_dir():
        raise SystemExit("Missing build/web output. Run `python -m pygbag --build --html .` first.")

    html_files = sorted(web_dir.glob("*.html"))
    if not html_files:
        raise SystemExit("No HTML launcher found in build/web.")

    dist_dir.mkdir(parents=True, exist_ok=True)
    for existing in dist_dir.iterdir():
        if existing.is_dir():
            shutil.rmtree(existing)
        else:
            existing.unlink()

    launcher = html_files[0]
    for source in web_dir.iterdir():
        target = dist_dir / source.name
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

    if launcher.name != "index.html":
        shutil.copy2(launcher, dist_dir / "index.html")

    # Mirror the launcher for direct error-page refreshes on static hosting.
    shutil.copy2(launcher, dist_dir / "404.html")

    print(f"Prepared GitHub Pages output in {dist_dir}")


if __name__ == "__main__":
    main()
