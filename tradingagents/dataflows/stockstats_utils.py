import pandas as pd
import yfinance as yf
from stockstats import wrap
from typing import Annotated
import os
from .config import get_config, DATA_DIR


class StockstatsUtils:
    @staticmethod
    def get_stock_stats(
        symbol: Annotated[str, "ticker symbol for the company"],
        indicator: Annotated[
            str, "quantitative indicators based off of the stock data for the company"
        ],
        curr_date: Annotated[
            str, "curr date for retrieving stock price data, YYYY-mm-dd"
        ],
    ):
        # Get config and set up data directory path
        config = get_config()
        online = config["data_vendors"]["technical_indicators"] != "local"

        df = None
        data = None

        if not online:
            try:
                data = pd.read_csv(
                    os.path.join(
                        DATA_DIR,
                        f"{symbol}-YFin-data-2015-01-01-2025-03-25.csv",
                    )
                )
                df = wrap(data)
            except FileNotFoundError:
                raise Exception("Stockstats fail: Yahoo Finance data not fetched yet!")
        else:
            # Get today's date as YYYY-mm-dd to add to cache
            today_date = pd.Timestamp.today()
            curr_date_parsed = pd.to_datetime(curr_date)

            end_date = today_date
            start_date = today_date - pd.DateOffset(years=15)
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")

            # Get config and ensure cache directory exists
            os.makedirs(config["data_cache_dir"], exist_ok=True)

            data_file = os.path.join(
                config["data_cache_dir"],
                f"{symbol}-YFin-data-{start_date_str}-{end_date_str}.csv",
            )

            # Check if requesting current day data - need fresh data
            is_current_day = curr_date_parsed.date() >= today_date.date()

            # Check if cache file exists and is fresh enough
            use_cache = False
            if os.path.exists(data_file) and not is_current_day:
                # For historical data, use cache
                use_cache = True
            elif os.path.exists(data_file) and is_current_day:
                # For current day, check if cache is recent (within 30 minutes)
                import time
                file_mtime = os.path.getmtime(data_file)
                cache_age_minutes = (time.time() - file_mtime) / 60
                if cache_age_minutes < 30:
                    use_cache = True

            if use_cache:
                data = pd.read_csv(data_file)
                data["Date"] = pd.to_datetime(data["Date"])
            else:
                # Fetch fresh data
                data = yf.download(
                    symbol,
                    start=start_date_str,
                    end=end_date_str,
                    multi_level_index=False,
                    progress=False,
                    auto_adjust=True,
                )
                data = data.reset_index()

                # For current day, also try to get intraday data
                if is_current_day:
                    try:
                        ticker = yf.Ticker(symbol)
                        intraday = ticker.history(period="1d", interval="1m")
                        if not intraday.empty:
                            today_ohlcv = {
                                'Date': pd.Timestamp(today_date.date()),
                                'Open': intraday['Open'].iloc[0],
                                'High': intraday['High'].max(),
                                'Low': intraday['Low'].min(),
                                'Close': intraday['Close'].iloc[-1],
                                'Volume': intraday['Volume'].sum(),
                            }
                            today_str = today_date.strftime("%Y-%m-%d")
                            if 'Date' in data.columns:
                                data['Date'] = pd.to_datetime(data['Date'])
                                if not any(data['Date'].dt.strftime("%Y-%m-%d") == today_str):
                                    today_df = pd.DataFrame([today_ohlcv])
                                    data = pd.concat([data, today_df], ignore_index=True)
                    except Exception as e:
                        print(f"Could not fetch intraday data for {symbol}: {e}")

                data.to_csv(data_file, index=False)

            df = wrap(data)
            df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
            curr_date = curr_date_parsed.strftime("%Y-%m-%d")

        df[indicator]  # trigger stockstats to calculate the indicator
        matching_rows = df[df["Date"].str.startswith(curr_date)]

        if not matching_rows.empty:
            indicator_value = matching_rows[indicator].values[0]
            return indicator_value
        else:
            return "N/A: Not a trading day (weekend or holiday)"
