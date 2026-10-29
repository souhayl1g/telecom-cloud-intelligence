import argparse
import json
from pathlib import Path
from .pipeline import ingest, monitor
from .features import export_features

parser=argparse.ArgumentParser(description='Reproducible synthetic telecom data lab')
commands=parser.add_subparsers(dest='command',required=True)
demo=commands.add_parser('demo')
demo.add_argument('--out',type=Path,default=Path('artifacts'))
demo.add_argument('--data',type=Path,default=Path(__file__).resolve().parent.parent/'data')
args=parser.parse_args()
args.out.mkdir(parents=True,exist_ok=True)
database=args.out/'telecom.sqlite'
load=ingest(args.data/'kpis.csv',args.data/'cells.json',database)
health=monitor(database,'2026-10-29T00:00:00Z',max_rejection_rate=0.2)
manifest=export_features(database,args.out/'features','2026-10-27T00:00:00Z',window=2)
report={'load':load,'health':health,'dataset_version':manifest['dataset_version']}
(args.out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
