import json
import sqlite3
import logging
import hashlib
import pandas as pd


class PlantDataBase:
    def __init__(self, db_name: str) -> None:
        self.db_name = db_name

    def create_tables(self):

        conn: sqlite3.Connection = sqlite3.connect(self.db_name)
        cursor: sqlite3.Cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Metadata (
                series_id TEXT PRIMARY KEY,
                msr TEXT NOT NULL,
                msr_attribute TEXT NOT NULL,
                object_id TEXT NOT NULL,
                object_type TEXT,
                cfg TEXT,
                device TEXT,
                number TEXT,
                object_description TEXT,
                object_name TEXT,
                unit TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                raster_size INTEGER NOT NULL,
                raster_unit TEXT NOT NULL,
                scale INTEGER NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Data (
                data_id INTEGER PRIMARY KEY AUTOINCREMENT,
                series_id TEXT NOT NULL,
                date DATETIME,
                mean REAL,
                status TEXT,
                FOREIGN KEY(series_id) REFERENCES Metadata(series_id)
            )
        ''')

        conn.commit()
        conn.close()

    def query_measurements(
            self, msr: str, msr_attribute: str, start_date: str, end_date: str, raster_size: int = 15,
            raster_unit: str = "min"):

        conn: sqlite3.Connection = sqlite3.connect(self.db_name)
        cursor: sqlite3.Cursor = conn.cursor()

        series_id = self.get_hash(msr, msr_attribute, start_date, end_date, raster_size, raster_unit)
        cursor.execute("SELECT * FROM Data WHERE series_id=?", (series_id,))
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=[x[0] for x in cursor.description])

        cursor.execute("SELECT * FROM Metadata WHERE series_id=?", (series_id,))
        rows = cursor.fetchall()
        df_meta = pd.DataFrame(rows, columns=[x[0] for x in cursor.description])

        conn.close()

        return df, df_meta

    def query_all_metadata(self) -> pd.DataFrame:

        conn: sqlite3.Connection = sqlite3.connect(self.db_name)
        cursor: sqlite3.Cursor = conn.cursor()

        cursor.execute("SELECT * FROM Metadata")
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=[x[0] for x in cursor.description])

        conn.close()

        return df

    def delete_measurements(self, series_id: str):

        conn: sqlite3.Connection = sqlite3.connect(self.db_name)
        cursor: sqlite3.Cursor = conn.cursor()

        cursor.execute("DELETE FROM Data WHERE series_id=?", (series_id,))
        cursor.execute("DELETE FROM Metadata WHERE series_id=?", (series_id,))

        conn.commit()
        conn.close()

    def query_data(self, series_id: str, start_date=None, end_date=None) -> pd.DataFrame:

        conn: sqlite3.Connection = sqlite3.connect(self.db_name)
        cursor: sqlite3.Cursor = conn.cursor()

        query = f"SELECT * FROM Data WHERE series_id = '{series_id}'"
        if start_date:
            query += f" AND date >= '{start_date}'"
        if end_date:
            query += f" AND date <= '{end_date}'"

        cursor.execute(query)
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=[x[0] for x in cursor.description])

        conn.close()

        return df

    def query_multiple(self, series_ids: list):
        meta_all = self.query_all_metadata()

        for i, series_id in enumerate(series_ids):
            df_series = self.query_data(series_id)
            df_series['date'] = pd.to_datetime(df_series['date'], format='%Y-%m-%d %H:%M:%S')
            df_series.rename(columns={'mean': f'm_{i}'}, inplace=True)
            if i == 0:
                df = df_series[['date', f'm_{i}']]
                meta = meta_all[meta_all['series_id'] == series_id].copy()
                meta['name'] = f'm_{i}'
            else:
                df = pd.merge(df, df_series[['date', f'm_{i}']], on='date', how='outer')
                meta_row = meta_all[meta_all['series_id'] == series_id].copy()
                meta_row['name'] = f'm_{i}'
                meta = pd.concat([meta, meta_row])

        return df, meta

    def execute_query(self, query: str) -> pd.DataFrame:
        conn: sqlite3.Connection = sqlite3.connect(self.db_name)
        cursor: sqlite3.Cursor = conn.cursor()

        cursor.execute(query)
        rows = cursor.fetchall()
        df = pd.DataFrame(rows, columns=[x[0] for x in cursor.description])

        conn.close()

        return df

    def get_hash(
            self, msr: str, msr_attribute: str, start_date: str, end_date: str, raster_size: int,
            raster_unit: str):

        series_name = f"{msr}_{msr_attribute}_{start_date}_{end_date}_{raster_size}_{raster_unit}"
        series_id = hashlib.sha256(series_name.encode()).hexdigest()
        return series_id

    def drop_tables(self):

        conn: sqlite3.Connection = sqlite3.connect(self.db_name)
        cursor: sqlite3.Cursor = conn.cursor()

        cursor.execute("DROP TABLE Data")
        cursor.execute("DROP TABLE Metadata")

        conn.commit()
        conn.close()


if __name__ == '__main__':
    logger: logging.Logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.WARNING)
    logger.info('Started')

    db = PlantDataBase('db/test.db')
    db.create_tables()
    meta_all = db.query_all_metadata()
    df = db.query_data(meta_all['series_id'][0], '2023-01-01', '2023-12-31')
    df, df_meta = db.query_measurements('10BGA.80.01', 'ISTWERT', '2016-01-01', '2024-01-01')
    print(len(df), len(df_meta))
