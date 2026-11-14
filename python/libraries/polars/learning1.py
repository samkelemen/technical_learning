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

# 3.3 get percent of messages with last event flag
flags_col = "flags"
num_messages_with_last_event_flag = lf.filter(pl.col(flags_col) & 0x80 != 0).select(pl.len()).collect().item()
num_messages = lf.select(pl.len()).collect().item()

percent_messages_with_last_event_flag = num_messages_with_last_event_flag / num_messages * 100
print(f"{percent_messages_with_last_event_flag=}%")

# 3.4 do the same with mbo data
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
flags_col = "flags"
num_messages_with_last_event_flag = lf.filter(pl.col(flags_col) & 0x80 != 0).select(pl.len()).collect().item()
num_messages = lf.select(pl.len()).collect().item()

percent_messages_with_last_event_flag = num_messages_with_last_event_flag / num_messages * 100
print(f"{percent_messages_with_last_event_flag=}%")


# %%
