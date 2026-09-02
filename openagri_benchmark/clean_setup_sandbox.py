#!/usr/bin/env python
import os
import sys
import shutil
import subprocess

from openagri_benchmark.conf import BOOTSTRAP_DIR, BOOTSTRAP_CONFIGS_DIR

def run():
    subpath = sys.argv[1]
    src = os.path.join(BOOTSTRAP_CONFIGS_DIR, subpath)
    dst = BOOTSTRAP_DIR

    print(f"Resetting bootstrap sandbox...")
    subprocess.check_call(["git", "reset", "--hard"], cwd=dst)
    subprocess.check_call(["git", "clean", "-fdx"], cwd=dst)

    print(f"Copying configs from {src} to {dst}...")
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
        print(f"  {s} -> {d}")

    print("Done.")

if __name__ == '__main__':
    run()
