"""Ejecuta el notebook con este Python y un kernel temporal local, sin instalación global."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

import nbformat
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parent


def execute(output):
    runtime = HERE.parent / ".runtime"
    runtime.mkdir(exist_ok=True)
    notebook = nbformat.read(HERE / "algoritmos.ipynb", as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    # El directorio generado está dentro de .runtime; la biblioteca lo limpia al salir.
    with tempfile.TemporaryDirectory(prefix="ml-kernel-", dir=runtime) as temporary:
        root = Path(temporary).resolve()
        if root.parent != runtime.resolve():
            raise RuntimeError("El kernel temporal debe quedar dentro del runtime del proyecto")
        spec = root / "kernels" / "aiops-ml-local"
        spec.mkdir(parents=True)
        (spec / "kernel.json").write_text(json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "AIOps ML local", "language": "python"}), encoding="utf-8")
        changes = {"JUPYTER_PATH": str(root), "JUPYTER_RUNTIME_DIR": str(root / "runtime"),
                   "IPYTHONDIR": str(root / "ipython"), "MPLCONFIGDIR": str(runtime / "ml-matplotlib")}
        previous = {name: os.environ.get(name) for name in changes}
        os.environ.update(changes)
        try:
            NotebookClient(notebook, timeout=120, kernel_name="aiops-ml-local", allow_errors=False,
                           resources={"metadata": {"path": str(HERE)}}).execute()
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
    nbformat.validate(notebook)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, output)
    count = sum(c.cell_type == "code" for c in notebook.cells)
    print(f"PASS: {count} celdas de código ejecutadas; notebook guardado en {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE.parent / ".runtime" / "algoritmos-ejecutado.ipynb")
    execute(parser.parse_args().output)
