import pandas as pd

RADIATION_COLS = ["shortwave_radiation", "direct_radiation", "diffuse_radiation"]


def transform(data, locations):
    frames = []
    for item, loc in zip(data, locations):
        df_loc = pd.DataFrame(item["hourly"])
        df_loc["lokasi"] = loc["lokasi"]
        df_loc["pulau"] = loc["pulau"]
        df_loc["provinsi"] = loc["provinsi"]
        df_loc["elevasi_m"] = item["elevation"]
        frames.append(df_loc)

    df = pd.concat(frames, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"])
    return df


def clean(df):
    df = df.drop_duplicates(subset=["lokasi", "time"]).copy()

    df[RADIATION_COLS] = df[RADIATION_COLS].clip(lower=0)   
    df["cloud_cover"] = df["cloud_cover"].clip(0, 100)     

    num_cols = df.select_dtypes("number").columns.drop("elevasi_m")
    df = df.sort_values(["lokasi", "time"])
    df[num_cols] = df.groupby("lokasi")[num_cols].transform(
        lambda s: s.interpolate(limit_direction="both")
    )
    return df.reset_index(drop=True)