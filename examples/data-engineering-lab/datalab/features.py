"""Project 2: point-in-time features, chronological split and hashed datasets."""
import csv
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from .pipeline import canonical_time


def export_features(database, output, split_at, window=3):
    """Predict current throughput from strictly earlier measurements of that cell.

    Features never read the current target or later observations. Test rows may
    use earlier test-period measurements: this models sequential one-step-ahead
    prediction after each preceding measurement becomes available, not a fixed
    multi-step forecast. The pipeline does not train a model or claim accuracy.
    """
    if not isinstance(window, int) or window < 1:
        raise ValueError('window must be a positive integer')
    split_at = canonical_time(split_at)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as conn:
        data = conn.execute('SELECT cell_id,timestamp,throughput_mbps,latency_ms FROM observations ORDER BY timestamp,cell_id').fetchall()
        lineage = dict(conn.execute('SELECT key,value FROM lineage'))
    history, partitions = {}, {'train': [], 'test': []}
    for cell_id, timestamp, throughput, latency in data:
        past = history.setdefault(cell_id, [])
        if len(past) >= window:
            previous = past[-window:]
            row = [cell_id, timestamp, past[-1][0],
                   sum(r[0] for r in previous)/window, sum(r[1] for r in previous)/window,
                   throughput]
            partitions['train' if timestamp < split_at else 'test'].append(row)
        past.append((throughput, latency))
    if not all(partitions.values()):
        raise ValueError('split/window must produce nonempty train and test datasets')
    fields = ['cell_id','timestamp','throughput_lag_1','throughput_mean_past','latency_mean_past','target_throughput_mbps']
    files = {}
    for name, rows in partitions.items():
        path = output/(name+'.csv')
        with path.open('w',encoding='utf-8',newline='') as stream:
            writer=csv.writer(stream, lineterminator='\n')
            writer.writerow(fields)
            writer.writerows(rows)
        files[name] = {'rows':len(rows),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest = {'version':'1','split_at':split_at,'window':window,'features':fields[2:-1],
                'target':fields[-1], 'source_lineage':{k:json.loads(v) for k,v in lineage.items()},
                'evaluation':'sequential_one_step_ahead','files':files}
    encoded=json.dumps(manifest,sort_keys=True,ensure_ascii=False).encode()
    manifest['dataset_version']=hashlib.sha256(encoded).hexdigest()
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding='utf-8')
    return manifest
