"""Convert unconverted source PDFs -> markdown using marker, loading models once.

Mirrors marker.scripts.convert_single but loops over many files in one process so
the (expensive) model load happens a single time. Output layout matches the existing
`converted/` tree: one folder per PDF containing <stem>.md, <stem>_meta.json and images.
"""

import os
import sys
import time
import traceback

os.environ.setdefault("TORCH_DEVICE", "cuda")
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"

from marker.config.parser import ConfigParser
from marker.models import create_model_dict
from marker.output import output_exists, save_output

ROOT = r"C:\workspace\thesis"

# (source dir, converted target dir). PDFs are taken non-recursively from each source dir.
JOBS = [
    (os.path.join(ROOT, "sources", "academic"), os.path.join(ROOT, "converted", "academic")),
    (os.path.join(ROOT, "sources", "nonacademic"), os.path.join(ROOT, "converted", "nonacademic")),
    (
        os.path.join(ROOT, "sources", "academic", "Theoretical framework"),
        os.path.join(ROOT, "converted", "theoretical framework"),
    ),
]

# Already converted under a DIFFERENT folder name (PDF since renamed) -> skip explicitly,
# since the stem-based output_exists check cannot see them.
SKIP_BASENAMES = {
    "Abou Elgeit - 2025 - Generative AI as a Disruptive Innovation.pdf",  # -> Elgeit - 2025 - ...
    "Hasan et al - 2025 - Transforming the Digital Landscape.pdf",         # -> EmanPublisher_14_5967...
    "Lamplugh - 2024 - The AI marketing playbook.pdf",                     # -> 10.1515_9781501520037
}


def collect():
    todo = []
    for src_dir, out_dir in JOBS:
        if not os.path.isdir(src_dir):
            continue
        for name in sorted(os.listdir(src_dir)):
            if not name.lower().endswith(".pdf"):
                continue
            fpath = os.path.join(src_dir, name)
            if not os.path.isfile(fpath):
                continue
            if name in SKIP_BASENAMES:
                continue
            cfg = ConfigParser({"output_dir": out_dir, "output_format": "markdown"})
            out_folder = cfg.get_output_folder(fpath)
            base = cfg.get_base_filename(fpath)
            if output_exists(out_folder, base):
                continue
            todo.append((fpath, out_dir))
    return todo


def main():
    todo = collect()
    print(f"[plan] {len(todo)} PDF(s) to convert", flush=True)
    for fpath, out_dir in todo:
        print(f"  - {os.path.basename(fpath)}", flush=True)
    if not todo:
        print("[done] nothing to convert", flush=True)
        return

    print("[load] loading marker models...", flush=True)
    models = create_model_dict()

    ok, failed = [], []
    for i, (fpath, out_dir) in enumerate(todo, 1):
        name = os.path.basename(fpath)
        t0 = time.time()
        print(f"[{i}/{len(todo)}] converting: {name}", flush=True)
        try:
            cfg = ConfigParser({"output_dir": out_dir, "output_format": "markdown"})
            converter_cls = cfg.get_converter_cls()
            converter = converter_cls(
                config=cfg.generate_config_dict(),
                artifact_dict=models,
                processor_list=cfg.get_processors(),
                renderer=cfg.get_renderer(),
                llm_service=cfg.get_llm_service(),
            )
            rendered = converter(fpath)
            out_folder = cfg.get_output_folder(fpath)
            save_output(rendered, out_folder, cfg.get_base_filename(fpath))
            print(f"      ok ({time.time() - t0:.0f}s) -> {out_folder}", flush=True)
            ok.append(name)
        except Exception as e:  # keep going on failure
            print(f"      FAILED: {e}", flush=True)
            traceback.print_exc()
            failed.append(name)

    print(f"\n[summary] converted {len(ok)}, failed {len(failed)}", flush=True)
    if failed:
        print("[summary] failures:", flush=True)
        for n in failed:
            print(f"  - {n}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
