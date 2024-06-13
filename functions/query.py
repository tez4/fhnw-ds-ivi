import pandas as pd


def query_and_prepare_data(db, meta_all, msr, start_date, end_date):
    meta_row = meta_all[meta_all['msr'] == msr]
    if meta_row.empty:
        raise ValueError(f"Measurement {msr} not found in metadata")
    elif meta_row.shape[0] > 1:
        raise ValueError(f"Measurement {msr} has multiple entries in metadata")

    series_id = meta_row.iloc[0, 0]

    df = db.query_data(series_id, start_date, end_date)
    df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d %H:%M:%S')

    return meta_row, df


def query_multiple_msr(db, meta_all, msr_list):
    for i, msr in enumerate(msr_list):
        meta_row, df_single = query_and_prepare_data(db, meta_all, msr, '2023-01-01', '2023-02-31')
        if i == 0:
            df_single.rename(columns={'mean': msr}, inplace=True)
            df = df_single[['date', msr]]
            meta = meta_row
        else:
            df_single.rename(columns={'mean': msr}, inplace=True)
            df = pd.merge(df, df_single[['date', msr]], on='date', how='outer')
            meta = pd.concat([meta, meta_row])

    return df, meta
