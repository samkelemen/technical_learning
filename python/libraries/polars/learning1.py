# %% [markdown]
# #learning1.py

# %% [markdown]
# ### load mbo data
#
# %%
from datetime import datetime

import epios_core as ec
import market_calendars.futures as fcals

calendar = fcals.get_market_calendar(fcals.CmeProductGroup.INTEREST_RATES)
lf = ec.get_data(
    data_type=ec.MarketDataType.MBP10,
    start_datetime_utc=datetime(2026, 10, 14),
    end_datetime_utc=datetime(2026, 10, 18),
    data_provider=ec.DataProvider.DATABENTO,
    market_calendar=calendar,
    symbols=[
        "ZBZ6",
    ],
    trading_session=ec.TradingSession.REGULAR_SESSION,
)

# %% [markdown]
# ### 1. lazyframe attributes
# these attributes give performance warnings when you use them
# %%

# 1.1 public attributes of lazyframe
print(f"{lf.columns=}")
print(f"{lf.dtypes=}")
print(f"{lf.schema=}")
print(f"{lf.width=}")

# %% [markdown]
# ### 2. equivalent, more performant methods
#
# %%
import polars as pl
import polars.selectors as cs

# 2.1 get the count of non-null and null values per column
print(f"{lf.count().collect()=}")
print(f"{lf.null_count().collect()=}")

# 2.2 get number of rows
len: int = lf.select(pl.len()).collect().item()
print(f"{len=}")

# 2.3 get whether each column has nulls
has_nulls = lf.select(pl.all().has_nulls()).collect().row(0)

# %% [markdown]
# ### 3. mbp10 data anlysis practice
#
# %%

# 3.1 see if there are any price values that are the max sentinal
max_sentinal = pl.Int64.max()
has_max_sentinal_values: bool = (
    lf.select(cs.starts_with("ask_px") | cs.starts_with("bid_px"))
    .select((cs.all() == max_sentinal).sum())
    .unpivot(variable_name="column", value_name="num_max_sentinals")
    .filter(pl.col("num_max_sentinals") != 0)
).select(pl.len()).collect().item() > 0

# 3.2 see how many messages there are per hour and plot it with altair
event_hour_col = "event_hour"
ts_event_col = "ts_event"
num_messages_col = "num_messages"
df_messages_per_hour = (
    lf.with_columns(
        pl.col(ts_event_col).dt.truncate("1h").alias(event_hour_col),
    )
    .group_by(event_hour_col)
    .agg(pl.len().alias(num_messages_col))
).collect()

chart_messages_per_hour = df_messages_per_hour.plot.line(x=event_hour_col, y=num_messages_col)
chart_messages_per_hour.save("messages_per_hour.png", scale_factor=2)

# 3.2 see how many events there are per hour
day_hour_col = "day_hour"
flags_col = "flags"
ts_event_col = "ts_event"
num_events_col = "num events"

df_events_per_hour = (
    lf.filter(pl.col(flags_col) & 0x80 != 0)
    .with_columns(
        pl.col(ts_event_col).dt.truncate("1h").alias(day_hour_col),
    )
    .group_by(day_hour_col)
    .agg(pl.len().alias(num_events_col))
    .collect()
)

chart_events_per_hour = df_events_per_hour.plot.line(x=day_hour_col, y=num_events_col)
chart_events_per_hour.save("events_per_hour.png", scale_factor=2)


# %% [markdown]
# 4. do the same with mbo data
#
# %%
from datetime import datetime

import epios_core as ec
import market_calendars.futures as fcals
import polars as pl
import polars.selectors as cs

calendar = fcals.get_market_calendar(fcals.CmeProductGroup.INTEREST_RATES)
lf = ec.get_data(
    data_type=ec.MarketDataType.MBO,
    start_datetime_utc=datetime(2026, 10, 14),
    end_datetime_utc=datetime(2026, 10, 18),
    data_provider=ec.DataProvider.DATABENTO,
    market_calendar=calendar,
    symbols=[
        "ZBZ6",
    ],
    trading_session=ec.TradingSession.REGULAR_SESSION,
)

# 3.3 get percent of messages with last event flag
flags_col = "flags"
num_messages_with_last_event_flag = lf.filter(pl.col(flags_col) & 0x80 != 0).select(pl.len()).collect().item()
num_messages = lf.select(pl.len()).collect().item()

percent_messages_with_last_event_flag = num_messages_with_last_event_flag / num_messages * 100
print(f"{percent_messages_with_last_event_flag=}%")

# 4.2 figure out the max number of messages in a row without last message in event flag
is_sorted = lf.select(pl.col("ts_event").is_sorted()).collect().item()

# rle() panics on multi-chunk input in polars 2.1.0 (chunks.len() == 1 assertion),
# so compute each row's distance from the most recent F_LAST row instead
is_last = (pl.col(flags_col) & 0x80) != 0

runs = (
    lf.filter((pl.col(flags_col) & 0x20) == 0)  # drop snapshot records
    .with_row_index("idx")
    .with_columns(
        (
            pl.col("idx").cast(pl.Int64)
            - pl.when(is_last).then(pl.col("idx").cast(pl.Int64)).forward_fill().fill_null(-1)
        ).alias("run")
    )
)

max_seq = runs.filter(~is_last).select(pl.col("run").max()).collect().item()
print(f"{is_sorted=} {max_seq=}")

# 4.3 inspect the longest run: one ts_event/sequence => genuine single event,
# ts_event spread over time => artifact (missing F_LAST at a boundary, or bad row order)
end_idx = runs.filter(~is_last).select(pl.col("idx").get(pl.col("run").arg_max())).collect().item()

longest_seq = runs.filter(pl.col("idx").is_between(end_idx - max_seq, end_idx + 1)).collect()
print(longest_seq.select("ts_recv", "ts_event", "sequence", "action", "side", "price", "size", "flags"))
print(longest_seq.select(pl.col("ts_event", "ts_recv", "sequence").n_unique()))
print(longest_seq["action"].value_counts())


# %%
# 4.4 price path after the longest event (the sweep), in 1-minute buckets
from datetime import datetime, timedelta

import epios_core as ec
import market_calendars.futures as fcals
import polars as pl

# ts_event of the 1341-lot sweep found in 4.3 (exact: 19:38:04.111057327; python datetime is µs only)
event_ts = datetime(2026, 10, 15, 19, 38, 4, 111057)
TICK = 1 / 32  # ZB tick size

# only load the day of the sweep
calendar = fcals.get_market_calendar(fcals.CmeProductGroup.INTEREST_RATES)
lf = ec.get_data(
    data_type=ec.MarketDataType.MBO,
    start_datetime_utc=datetime(2026, 10, 15),
    end_datetime_utc=datetime(2026, 10, 16),
    data_provider=ec.DataProvider.DATABENTO,
    market_calendar=calendar,
    symbols=["ZBZ6"],
    trading_session=ec.TradingSession.REGULAR_SESSION,
)

trades = (
    lf.filter(
        pl.col("action") == "T",
        pl.col("ts_event").is_between(event_ts - timedelta(minutes=5), event_ts + timedelta(minutes=60)),
    )
    .select("ts_event", "price", "size", "side")
    .collect()
)

ref_price = trades.filter(pl.col("ts_event") < event_ts)["price"][-1]  # last trade before the sweep
print(f"{event_ts=} {ref_price=}")

price_path = trades.group_by_dynamic("ts_event", every="1m").agg(
    pl.col("price").last().alias("last_price"),
    ((pl.col("price").last() - ref_price) / TICK).alias("ticks_vs_ref"),
    pl.col("size").sum().alias("volume"),
    pl.col("size").filter(pl.col("side") == "B").sum().alias("buy_aggr_vol"),
    pl.col("size").filter(pl.col("side") == "A").sum().alias("sell_aggr_vol"),
)
print(price_path)

chart_price_path = price_path.plot.line(x="ts_event", y="ticks_vs_ref")
chart_price_path.save("price_path_after_sweep.png", scale_factor=2)


# %%
# 4.5 average contracts traded per 5-second bucket on 10/15
# buckets with no trades count as 0; a bucket is "in session" if any MBO message arrived in it,
# so session gaps / maintenance breaks with no data don't drag the average down
from datetime import datetime

import epios_core as ec
import market_calendars.futures as fcals
import polars as pl

calendar = fcals.get_market_calendar(fcals.CmeProductGroup.INTEREST_RATES)
lf = ec.get_data(
    data_type=ec.MarketDataType.MBO,
    start_datetime_utc=datetime(2026, 10, 15),
    end_datetime_utc=datetime(2026, 10, 16),
    data_provider=ec.DataProvider.DATABENTO,
    market_calendar=calendar,
    symbols=["ZBZ6"],
    trading_session=ec.TradingSession.REGULAR_SESSION,
)

volume_5s = (
    lf.select(
        pl.col("ts_event").dt.truncate("5s").alias("bucket"),
        pl.when(pl.col("action") == "T").then(pl.col("size")).otherwise(0).alias("traded"),
    )
    .group_by("bucket")
    .agg(pl.col("traded").sum().alias("volume"))
    .sort("bucket")
    .collect()
)

avg_volume_5s = volume_5s["volume"].mean()
print(f"{volume_5s.height=} buckets, {volume_5s['volume'].sum()=} contracts, {avg_volume_5s=:.2f}")
print(volume_5s["volume"].describe())

volume_5s_tails = volume_5s.select(
    pl.col("volume").quantile(0.90).alias("p90"),
    pl.col("volume").quantile(0.99).alias("p99"),
    pl.col("volume").quantile(0.999).alias("p99.9"),
    pl.col("volume").max().alias("max"),
)
print(volume_5s_tails)
