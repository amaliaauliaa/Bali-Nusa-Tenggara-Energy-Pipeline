import pandas as pd

CLIP_RULES = {
    "shortwave_radiation": (0, None),
    "direct_radiation": (0, None),
    "diffuse_radiation": (0, None),
    "cloud_cover": (0, 100),
}


def transform(data, locations):
    frames = []
    for item, loc in zip(data, locations):
        df_loc = pd.DataFrame(item["hourly"])
        df_loc["location"] = loc["location"]
        df_loc["island"] = loc["island"]
        df_loc["province"] = loc["province"]
        df_loc["elevation_m"] = item["elevation"]
        frames.append(df_loc)

    df = pd.concat(frames, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"])
    return df


def clean(df):
    changes = {"duplicates_removed": 0, "clipped": {}, "interpolated": {}}

    rows_before = len(df)
    df = df.drop_duplicates(subset=["location", "time"]).copy()
    changes["duplicates_removed"] = rows_before - len(df)

    for col, (low, high) in CLIP_RULES.items():
        outside = pd.Series(False, index=df.index)
        if low is not None:
            outside |= df[col] < low
        if high is not None:
            outside |= df[col] > high

        changes["clipped"][col] = int(outside.sum())
        df[col] = df[col].clip(lower=low, upper=high)

    num_cols = df.select_dtypes("number").columns.drop("elevation_m")
    df = df.sort_values(["location", "time"])

    nulls_before = df[num_cols].isna().sum()
    df[num_cols] = df.groupby("location")[num_cols].transform(
        lambda s: s.interpolate(limit_direction="both")
    )
    nulls_after = df[num_cols].isna().sum()

    changes["interpolated"] = {col: int(nulls_before[col] - nulls_after[col]) for col in num_cols}

    return df.reset_index(drop=True), changes