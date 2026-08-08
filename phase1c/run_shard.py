import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from run_phase1c import ALL_REGIMES, _worker


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--regime', required=True, choices=ALL_REGIMES)
    ap.add_argument('--seeds', type=int, required=True)
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    tasks = [(args.regime, i) for i in range(args.seeds)]
    if args.jobs > 1:
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            rows = list(ex.map(_worker, tasks, chunksize=max(1, len(tasks) // (args.jobs * 8))))
    else:
        rows = [_worker(t) for t in tasks]
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False)
    print(json.dumps({'regime': args.regime, 'n': len(rows)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
