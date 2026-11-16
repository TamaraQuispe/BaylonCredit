"""Delegate academic V4 CLI arguments to the unchanged frozen runner."""

import runpy
import sys
from pathlib import Path


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    code = Path(__file__).absolute().parent / 'codigo'
    sys.path.insert(0, str(code))
    runner = code / 'scripts/academic_credit_aligned_v4.py'
    sys.argv[0] = str(runner)
    runpy.run_path(str(runner), run_name='__main__')
