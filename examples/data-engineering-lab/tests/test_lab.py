import csv
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from datalab.pipeline import ingest, monitor
from datalab.features import export_features

DATA=Path(__file__).resolve().parent.parent/'data'

class LabTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.db=self.root/'db.sqlite'
        self.load=ingest(DATA/'kpis.csv',DATA/'cells.json',self.db)

    def test_quarantine_and_sql_aggregation(self):
        self.assertEqual((self.load['accepted_rows'],self.load['rejected_rows']),(12,2))
        with closing(sqlite3.connect(self.db)) as conn, conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM daily_region_kpis').fetchone()[0],12)
            reasons=[r[0] for r in conn.execute('SELECT reason FROM quarantine')]
        self.assertIn('unknown cell_id',reasons)
        self.assertIn('duplicate cell/time key',reasons)

    def test_rerun_is_idempotent(self):
        self.assertEqual(ingest(DATA/'kpis.csv',DATA/'cells.json',self.db),self.load)
        with closing(sqlite3.connect(self.db)) as conn, conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM observations').fetchone()[0],12)

    def test_structural_failure_preserves_prior_snapshot(self):
        bad=self.root/'bad.csv';bad.write_text('wrong\nfield\n')
        with self.assertRaises(ValueError):
            ingest(bad,DATA/'cells.json',self.db)
        with closing(sqlite3.connect(self.db)) as conn, conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM observations').fetchone()[0],12)

    def test_nonfinite_and_negative_values_rejected(self):
        bad=self.root/'bad.csv'
        bad.write_text('cell_id,timestamp,throughput_mbps,latency_ms\nTN001,2026-10-28T00:00:00Z,NaN,1\nTN002,2026-10-28T00:00:00Z,1,-1\n')
        result=ingest(bad,DATA/'cells.json',self.db)
        self.assertEqual(result['rejected_rows'],2)
        self.assertFalse(monitor(self.db,'2026-10-29T00:00:00Z')['healthy'])

    def test_monitor_flags_stale_and_quality_thresholds(self):
        self.assertTrue(monitor(self.db,'2026-10-29T00:00:00Z',max_rejection_rate=0.2)['healthy'])
        self.assertFalse(monitor(self.db,'2026-11-10T00:00:00Z',max_rejection_rate=0.2)['checks']['fresh'])
        self.assertFalse(monitor(self.db,'2026-10-29T00:00:00Z')['checks']['quality'])

    def test_feature_values_split_and_deterministic_version(self):
        out=self.root/'features'
        manifest=export_features(self.db,out,'2026-10-27T00:00:00Z',window=2)
        with (out/'train.csv').open(newline='') as stream:
            train=list(csv.DictReader(stream))
        self.assertEqual(float(train[0]['throughput_lag_1']),42)
        self.assertEqual(float(train[0]['throughput_mean_past']),41)
        self.assertEqual(float(train[0]['target_throughput_mbps']),44)
        self.assertTrue(all(r['timestamp']<manifest['split_at'] for r in train))
        self.assertEqual(manifest['dataset_version'],export_features(self.db,out,'2026-10-27T00:00:00Z',window=2)['dataset_version'])

    def test_future_changes_do_not_leak_into_past_features(self):
        a=self.root/'a';b=self.root/'b'
        export_features(self.db,a,'2026-10-27T00:00:00Z',window=2)
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("UPDATE observations SET throughput_mbps=999 WHERE timestamp>='2026-10-27'")
        export_features(self.db,b,'2026-10-27T00:00:00Z',window=2)
        self.assertEqual((a/'train.csv').read_bytes(),(b/'train.csv').read_bytes())

    def test_invalid_split_does_not_produce_datasets(self):
        with self.assertRaises(ValueError):
            export_features(self.db,self.root/'invalid','2020-01-01T00:00:00Z')
        self.assertFalse((self.root/'invalid/train.csv').exists())

if __name__=='__main__':
    unittest.main()
