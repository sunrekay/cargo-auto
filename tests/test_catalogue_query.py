"""The shipped SQLite catalogue must support detail and gallery queries."""
import sqlite3
import unittest
from pathlib import Path
from backend import queries


class CatalogueDetailTest(unittest.TestCase):
    def test_detail_and_gallery_use_shipped_schema(self):
        catalogue = Path(__file__).resolve().parents[1] / 'data/cargo-auto.db'
        with sqlite3.connect(f'file:{catalogue}?mode=ro', uri=True) as conn:
            listing_id = conn.execute('select listing_id from cars limit 1').fetchone()[0]
            params = {'id': listing_id}
            self.assertIsNotNone(conn.execute(queries.GET_CAR, params).fetchone())
            self.assertTrue(conn.execute(queries.GET_PHOTOS, params).fetchall())
            self.assertTrue(conn.execute(queries.GET_SPECS, params).fetchall())
