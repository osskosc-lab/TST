import argparse
import csv
import json
from pathlib import Path

import numpy as np

from run_phase1c import make_report, summarize


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--indir', default='phase1c/shards')
    ap.add_argument('--permutations', type=int, default=10000)
    ap.add_argument('--outdir', default='phase1c/results/confirmatory')
    args = ap.parse_args()

    rows = []
    for p in sorted(Path(args.indir).rglob('*.json')):
        with p.open(encoding='utf-8') as f:
            rows.extend(json.load(f))
    if not rows:
        raise RuntimeError('No shard rows found')

    summary, null = summarize(rows, args.permutations)
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / 'summary.json').open('w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with (out / 'REPORT.md').open('w', encoding='utf-8') as f:
        f.write(make_report(summary))
    cols = list(rows[0].keys())
    with (out / 'runs.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(rows)
    np.savetxt(out / 'cramers_v_null.csv', null, delimiter=',')
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
