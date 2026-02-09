from typing import Annotated
from datetime import datetime
from dateutil.relativedelta import relativedelta
import yfinance as yf
import os
from .stockstats_utils import StockstatsUtils


def get_live_price(
    symbol: Annotated[str, "ticker symbol of the company"],
) -> dict:
    """
    Get live/real-time stock price using fast_info (fastest method).
    Returns the most current price available from Yahoo Finance.
    Note: Some exchanges may have 15-20 minute delay.
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        fast_info = ticker.fast_info

        return {
            "symbol": symbol.upper(),
            "last_price": fast_info.last_price,
            "previous_close": fast_info.previous_close,
            "open": fast_info.open,
            "day_high": fast_info.day_high,
            "day_low": fast_info.day_low,
            "market_cap": fast_info.market_cap,
            "retrieved_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    except Exception as e:
        return {"error": f"Failed to get live price for {symbol}: {str(e)}"}


def get_latest_price_intraday(
    symbol: Annotated[str, "ticker symbol of the company"],
) -> dict:
    """
    Get the latest price using 1-minute intraday data (most reliable method).
    Returns the most recent close price from today's trading.
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        # Fetch 1-minute interval data for today
        data = ticker.history(period="1d", interval="1m")

        if data.empty:
            # Market might be closed, fall back to fast_info
            return get_live_price(symbol)

        latest = data.iloc[-1]
        return {
            "symbol": symbol.upper(),
            "latest_price": round(latest['Close'], 2),
            "latest_high": round(latest['High'], 2),
            "latest_low": round(latest['Low'], 2),
            "latest_volume": int(latest['Volume']),
            "timestamp": str(data.index[-1]),
            "retrieved_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    except Exception as e:
        # Fall back to fast_info method
        return get_live_price(symbol)


def get_YFin_data_online(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
):

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    today = datetime.now().date()

    # Create ticker object
    ticker = yf.Ticker(symbol.upper())

    # Check if we need live/current day data
    is_requesting_today = end_dt.date() >= today

    if is_requesting_today:
        # Use intraday data for current day to get latest prices
        # First get historical daily data for the range before today
        if start_dt.date() < today:
            historical_data = ticker.history(start=start_date, end=str(today))
        else:
            historical_data = None

        # Get today's intraday data (1-minute intervals)
        try:
            intraday_data = ticker.history(period="1d", interval="1m")
            if not intraday_data.empty:
                # Aggregate intraday data to get today's OHLCV
                today_ohlcv = {
                    'Open': intraday_data['Open'].iloc[0],
                    'High': intraday_data['High'].max(),
                    'Low': intraday_data['Low'].min(),
                    'Close': intraday_data['Close'].iloc[-1],
                    'Volume': intraday_data['Volume'].sum(),
                }

                # Create a DataFrame for today
                import pandas as pd
                today_df = pd.DataFrame([today_ohlcv], index=[pd.Timestamp(today)])
                today_df.index.name = 'Date'

                # Combine historical and today's data
                if historical_data is not None and not historical_data.empty:
                    # Remove timezone info from historical data
                    if historical_data.index.tz is not None:
                        historical_data.index = historical_data.index.tz_localize(None)
                    data = pd.concat([historical_data, today_df])
                else:
                    data = today_df
            else:
                # Fall back to regular history if intraday fails
                data = ticker.history(start=start_date, end=end_date)
        except Exception as e:
            print(f"Intraday fetch failed, falling back to daily: {e}")
            data = ticker.history(start=start_date, end=end_date)
    else:
        # Historical data only, use regular method
        data = ticker.history(start=start_date, end=end_date)

    # Check if data is empty
    if data.empty:
        return (
            f"No data found for symbol '{symbol}' between {start_date} and {end_date}"
        )

    # Remove timezone info from index for cleaner output
    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)

    # Round numerical values to 2 decimal places for cleaner display
    numeric_columns = ["Open", "High", "Low", "Close", "Adj Close"]
    for col in numeric_columns:
        if col in data.columns:
            data[col] = data[col].round(2)

    # Convert DataFrame to CSV string
    csv_string = data.to_csv()

    # Add header information
    header = f"# Stock data for {symbol.upper()} from {start_date} to {end_date}\n"
    header += f"# Total records: {len(data)}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    if is_requesting_today:
        header += f"# NOTE: Includes live/intraday data for today\n"
    header += "\n"

    return header + csv_string

def get_stock_stats_indicators_window(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[
        str, "The current trading date you are trading on, YYYY-mm-dd"
    ],
    look_back_days: Annotated[int, "how many days to look back"],
) -> str:

    best_ind_params = {
        # Moving Averages
        "close_50_sma": (
            "50 SMA: A medium-term trend indicator. "
            "Usage: Identify trend direction and serve as dynamic support/resistance. "
            "Tips: It lags price; combine with faster indicators for timely signals."
        ),
        "close_200_sma": (
            "200 SMA: A long-term trend benchmark. "
            "Usage: Confirm overall market trend and identify golden/death cross setups. "
            "Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries."
        ),
        "close_10_ema": (
            "10 EMA: A responsive short-term average. "
            "Usage: Capture quick shifts in momentum and potential entry points. "
            "Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals."
        ),
        # MACD Related
        "macd": (
            "MACD: Computes momentum via differences of EMAs. "
            "Usage: Look for crossovers and divergence as signals of trend changes. "
            "Tips: Confirm with other indicators in low-volatility or sideways markets."
        ),
        "macds": (
            "MACD Signal: An EMA smoothing of the MACD line. "
            "Usage: Use crossovers with the MACD line to trigger trades. "
            "Tips: Should be part of a broader strategy to avoid false positives."
        ),
        "macdh": (
            "MACD Histogram: Shows the gap between the MACD line and its signal. "
            "Usage: Visualize momentum strength and spot divergence early. "
            "Tips: Can be volatile; complement with additional filters in fast-moving markets."
        ),
        # Momentum Indicators
        "rsi": (
            "RSI: Measures momentum to flag overbought/oversold conditions. "
            "Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. "
            "Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis."
        ),
        # Volatility Indicators
        "boll": (
            "Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. "
            "Usage: Acts as a dynamic benchmark for price movement. "
            "Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals."
        ),
        "boll_ub": (
            "Bollinger Upper Band: Typically 2 standard deviations above the middle line. "
            "Usage: Signals potential overbought conditions and breakout zones. "
            "Tips: Confirm signals with other tools; prices may ride the band in strong trends."
        ),
        "boll_lb": (
            "Bollinger Lower Band: Typically 2 standard deviations below the middle line. "
            "Usage: Indicates potential oversold conditions. "
            "Tips: Use additional analysis to avoid false reversal signals."
        ),
        "atr": (
            "ATR: Averages true range to measure volatility. "
            "Usage: Set stop-loss levels and adjust position sizes based on current market volatility. "
            "Tips: It's a reactive measure, so use it as part of a broader risk management strategy."
        ),
        # Volume-Based Indicators
        "vwma": (
            "VWMA: A moving average weighted by volume. "
            "Usage: Confirm trends by integrating price action with volume data. "
            "Tips: Watch for skewed results from volume spikes; use in combination with other volume analyses."
        ),
        "mfi": (
            "MFI: The Money Flow Index is a momentum indicator that uses both price and volume to measure buying and selling pressure. "
            "Usage: Identify overbought (>80) or oversold (<20) conditions and confirm the strength of trends or reversals. "
            "Tips: Use alongside RSI or MACD to confirm signals; divergence between price and MFI can indicate potential reversals."
        ),
    }

    # Handle comma-separated indicators (LLM may pass multiple at once)
    indicators_to_process = [ind.strip() for ind in indicator.split(",")]

    # Validate all indicators first
    invalid_indicators = [ind for ind in indicators_to_process if ind not in best_ind_params]
    if invalid_indicators:
        raise ValueError(
            f"Indicator {','.join(invalid_indicators)} is not supported. Please choose from: {list(best_ind_params.keys())}"
        )

    # Process each indicator and collect results
    all_results = []

    for single_indicator in indicators_to_process:
        end_date = curr_date
        curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
        before = curr_date_dt - relativedelta(days=look_back_days)

        # Optimized: Get stock data once and calculate indicators for all dates
        try:
            indicator_data = _get_stock_stats_bulk(symbol, single_indicator, curr_date)

            # Generate the date range we need
            current_dt = curr_date_dt
            date_values = []

            while current_dt >= before:
                date_str = current_dt.strftime('%Y-%m-%d')

                # Look up the indicator value for this date
                if date_str in indicator_data:
                    indicator_value = indicator_data[date_str]
                else:
                    indicator_value = "N/A: Not a trading day (weekend or holiday)"

                date_values.append((date_str, indicator_value))
                current_dt = current_dt - relativedelta(days=1)

            # Build the result string
            ind_string = ""
            for date_str, value in date_values:
                ind_string += f"{date_str}: {value}\n"

        except Exception as e:
            print(f"Error getting bulk stockstats data: {e}")
            # Fallback to original implementation if bulk method fails
            ind_string = ""
            curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
            while curr_date_dt >= before:
                indicator_value = get_stockstats_indicator(
                    symbol, single_indicator, curr_date_dt.strftime("%Y-%m-%d")
                )
                ind_string += f"{curr_date_dt.strftime('%Y-%m-%d')}: {indicator_value}\n"
                curr_date_dt = curr_date_dt - relativedelta(days=1)

        result_str = (
            f"## {single_indicator} values from {before.strftime('%Y-%m-%d')} to {end_date}:\n\n"
            + ind_string
            + "\n\n"
            + best_ind_params.get(single_indicator, "No description available.")
        )

        all_results.append(result_str)

    # Return all indicator results combined
    return "\n\n---\n\n".join(all_results)


def _get_stock_stats_bulk(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to calculate"],
    curr_date: Annotated[str, "current date for reference"]
) -> dict:
    """
    Optimized bulk calculation of stock stats indicators.
    Fetches data once and calculates indicator for all available dates.
    Returns dict mapping date strings to indicator values.
    """
    from .config import get_config
    import pandas as pd
    from stockstats import wrap
    import os
    
    config = get_config()
    online = config["data_vendors"]["technical_indicators"] != "local"
    
    if not online:
        # Local data path
        try:
            data = pd.read_csv(
                os.path.join(
                    config.get("data_cache_dir", "data"),
                    f"{symbol}-YFin-data-2015-01-01-2025-03-25.csv",
                )
            )
            df = wrap(data)
        except FileNotFoundError:
            raise Exception("Stockstats fail: Yahoo Finance data not fetched yet!")
    else:
        # Online data fetching with caching
        today_date = pd.Timestamp.today()
        curr_date_dt = pd.to_datetime(curr_date)

        end_date = today_date
        start_date = today_date - pd.DateOffset(years=15)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        os.makedirs(config["data_cache_dir"], exist_ok=True)

        data_file = os.path.join(
            config["data_cache_dir"],
            f"{symbol}-YFin-data-{start_date_str}-{end_date_str}.csv",
        )

        # Check if requesting current day data - always fetch fresh
        is_current_day = curr_date_dt.date() >= today_date.date()

        # Check if cache file exists and is fresh enough
        use_cache = False
        if os.path.exists(data_file) and not is_current_day:
            # For historical data, use cache
            use_cache = True
        elif os.path.exists(data_file) and is_current_day:
            # For current day, check if cache is from today and recent (within 30 minutes)
            import time
            file_mtime = os.path.getmtime(data_file)
            cache_age_minutes = (time.time() - file_mtime) / 60
            if cache_age_minutes < 30:
                use_cache = True
                print(f"Using recent cache for {symbol} (age: {cache_age_minutes:.1f} minutes)")
            else:
                print(f"Cache for {symbol} is stale ({cache_age_minutes:.1f} minutes old), fetching fresh data")

        if use_cache:
            data = pd.read_csv(data_file)
            data["Date"] = pd.to_datetime(data["Date"])
        else:
            # Fetch fresh data from yfinance
            data = yf.download(
                symbol,
                start=start_date_str,
                end=end_date_str,
                multi_level_index=False,
                progress=False,
                auto_adjust=True,
            )
            data = data.reset_index()

            # For current day, also try to get intraday data to include today's price
            if is_current_day:
                try:
                    ticker = yf.Ticker(symbol)
                    intraday = ticker.history(period="1d", interval="1m")
                    if not intraday.empty:
                        # Aggregate today's intraday data
                        today_ohlcv = {
                            'Date': pd.Timestamp(today_date.date()),
                            'Open': intraday['Open'].iloc[0],
                            'High': intraday['High'].max(),
                            'Low': intraday['Low'].min(),
                            'Close': intraday['Close'].iloc[-1],
                            'Volume': intraday['Volume'].sum(),
                        }
                        # Check if today is already in data
                        today_str = today_date.strftime("%Y-%m-%d")
                        if 'Date' in data.columns:
                            data['Date'] = pd.to_datetime(data['Date'])
                            if not any(data['Date'].dt.strftime("%Y-%m-%d") == today_str):
                                today_df = pd.DataFrame([today_ohlcv])
                                data = pd.concat([data, today_df], ignore_index=True)
                                print(f"Added live intraday data for {symbol} on {today_str}")
                except Exception as e:
                    print(f"Could not fetch intraday data for {symbol}: {e}")

            data.to_csv(data_file, index=False)
        
        df = wrap(data)
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    
    # Calculate the indicator for all rows at once
    df[indicator]  # This triggers stockstats to calculate the indicator
    
    # Create a dictionary mapping date strings to indicator values
    result_dict = {}
    for _, row in df.iterrows():
        date_str = row["Date"]
        indicator_value = row[indicator]
        
        # Handle NaN/None values
        if pd.isna(indicator_value):
            result_dict[date_str] = "N/A"
        else:
            result_dict[date_str] = str(indicator_value)
    
    return result_dict


def get_stockstats_indicator(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[
        str, "The current trading date you are trading on, YYYY-mm-dd"
    ],
) -> str:

    curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    curr_date = curr_date_dt.strftime("%Y-%m-%d")

    try:
        indicator_value = StockstatsUtils.get_stock_stats(
            symbol,
            indicator,
            curr_date,
        )
    except Exception as e:
        print(
            f"Error getting stockstats indicator data for indicator {indicator} on {curr_date}: {e}"
        )
        return ""

    return str(indicator_value)


def get_fundamentals(
    ticker: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "current date (not used for yfinance)"] = None
) -> str:
    """
    Get comprehensive fundamental data from yfinance including PE ratio, market cap, and other key metrics.
    Uses ticker.info which provides the most up-to-date fundamental data.
    """
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        info = ticker_obj.info

        if not info or len(info) == 0:
            return f"No fundamental data found for symbol '{ticker}'"

        # Format the data into a comprehensive report
        report_lines = []
        report_lines.append(f"# Fundamental Data for {ticker.upper()}")
        report_lines.append(f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        # Detect if this is an ETF, mutual fund, or similar instrument
        quote_type = info.get('quoteType', 'EQUITY')
        long_name = info.get('longName', '') or ''
        short_name = info.get('shortName', '') or ''
        name_combined = (long_name + ' ' + short_name).upper()

        is_etf_or_fund = (
            quote_type in ['ETF', 'MUTUALFUND'] or
            'ETF' in name_combined or
            'BEES' in name_combined or  # Indian ETFs often have BEES suffix
            'FUND' in name_combined or
            'INDEX' in name_combined
        )

        if is_etf_or_fund:
            report_lines.append("## ⚠️ Note: This appears to be an ETF/Fund")
            report_lines.append("ETFs and funds track underlying assets and typically don't have")
            report_lines.append("traditional fundamental metrics like PE ratio, revenue, or earnings.")
            report_lines.append("The following shows available market data.")
            report_lines.append("")

        # Company/Fund Profile
        report_lines.append("## Profile")
        report_lines.append(f"Name: {info.get('shortName', 'N/A')}")
        report_lines.append(f"Long Name: {info.get('longName', 'N/A')}")
        report_lines.append(f"Quote Type: {quote_type}")
        if not is_etf_or_fund:
            report_lines.append(f"Sector: {info.get('sector', 'N/A')}")
            report_lines.append(f"Industry: {info.get('industry', 'N/A')}")
            report_lines.append(f"Country: {info.get('country', 'N/A')}")
            report_lines.append(f"Website: {info.get('website', 'N/A')}")
            report_lines.append(f"Full-Time Employees: {info.get('fullTimeEmployees', 'N/A')}")
        else:
            # ETF-specific fields
            report_lines.append(f"Category: {info.get('category', 'N/A')}")
            report_lines.append(f"Fund Family: {info.get('fundFamily', 'N/A')}")
            total_assets = info.get('totalAssets')
            if total_assets:
                report_lines.append(f"Total Assets (AUM): {total_assets:,.0f}")
            else:
                report_lines.append(f"Total Assets (AUM): N/A")
            report_lines.append(f"NAV Price: {info.get('navPrice', 'N/A')}")
            report_lines.append(f"Expense Ratio: {info.get('annualReportExpenseRatio', info.get('expenseRatio', 'N/A'))}")
        report_lines.append("")

        # Market Data (available for all instruments)
        report_lines.append("## Market Data")
        report_lines.append(f"Current Price: {info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))}")
        report_lines.append(f"Previous Close: {info.get('previousClose', info.get('regularMarketPreviousClose', 'N/A'))}")
        report_lines.append(f"Open: {info.get('open', info.get('regularMarketOpen', 'N/A'))}")
        report_lines.append(f"Day High: {info.get('dayHigh', info.get('regularMarketDayHigh', 'N/A'))}")
        report_lines.append(f"Day Low: {info.get('dayLow', info.get('regularMarketDayLow', 'N/A'))}")
        report_lines.append(f"52 Week High: {info.get('fiftyTwoWeekHigh', 'N/A')}")
        report_lines.append(f"52 Week Low: {info.get('fiftyTwoWeekLow', 'N/A')}")
        report_lines.append(f"50 Day Average: {info.get('fiftyDayAverage', 'N/A')}")
        report_lines.append(f"200 Day Average: {info.get('twoHundredDayAverage', 'N/A')}")
        report_lines.append(f"Volume: {info.get('volume', info.get('regularMarketVolume', 'N/A'))}")
        report_lines.append(f"Average Volume: {info.get('averageVolume', 'N/A')}")
        report_lines.append(f"Average Volume (10 days): {info.get('averageVolume10days', 'N/A')}")

        # 52-week performance
        week_change = info.get('fiftyTwoWeekChangePercent')
        if week_change is not None:
            report_lines.append(f"52 Week Change: {week_change*100:.2f}%")
        report_lines.append("")

        # ETF-specific performance metrics
        if is_etf_or_fund:
            report_lines.append("## Fund Performance")
            ytd = info.get('ytdReturn')
            if ytd is not None:
                report_lines.append(f"YTD Return: {ytd*100:.2f}%")
            else:
                report_lines.append(f"YTD Return: N/A")

            three_yr = info.get('threeYearAverageReturn')
            if three_yr is not None:
                report_lines.append(f"3-Year Average Return: {three_yr*100:.2f}%")
            else:
                report_lines.append(f"3-Year Average Return: N/A")

            five_yr = info.get('fiveYearAverageReturn')
            if five_yr is not None:
                report_lines.append(f"5-Year Average Return: {five_yr*100:.2f}%")
            else:
                report_lines.append(f"5-Year Average Return: N/A")

            div_yield = info.get('yield') or info.get('trailingAnnualDividendYield')
            if div_yield is not None and div_yield != 0:
                report_lines.append(f"Dividend Yield: {div_yield*100:.2f}%")
            else:
                report_lines.append(f"Dividend Yield: N/A (or 0%)")
            report_lines.append("")

            report_lines.append("## Risk Metrics")
            report_lines.append(f"Beta (3Y): {info.get('beta3Year', info.get('beta', 'N/A'))}")
            report_lines.append("")

            # Skip traditional fundamental sections for ETFs
            return "\n".join(report_lines)

        # ==========================================
        # STOCKS ONLY - Traditional Fundamentals
        # ==========================================

        # Market Cap and Valuation
        report_lines.append("## Valuation Metrics")
        market_cap = info.get('marketCap', 'N/A')
        if market_cap != 'N/A' and market_cap is not None:
            if market_cap >= 1e12:
                market_cap_str = f"${market_cap/1e12:.2f}T"
            elif market_cap >= 1e9:
                market_cap_str = f"${market_cap/1e9:.2f}B"
            elif market_cap >= 1e6:
                market_cap_str = f"${market_cap/1e6:.2f}M"
            else:
                market_cap_str = f"${market_cap:,.0f}"
            report_lines.append(f"Market Cap: {market_cap_str} ({market_cap:,.0f})")
        else:
            report_lines.append(f"Market Cap: N/A")

        enterprise_value = info.get('enterpriseValue', 'N/A')
        if enterprise_value != 'N/A' and enterprise_value is not None:
            if enterprise_value >= 1e12:
                ev_str = f"${enterprise_value/1e12:.2f}T"
            elif enterprise_value >= 1e9:
                ev_str = f"${enterprise_value/1e9:.2f}B"
            elif enterprise_value >= 1e6:
                ev_str = f"${enterprise_value/1e6:.2f}M"
            else:
                ev_str = f"${enterprise_value:,.0f}"
            report_lines.append(f"Enterprise Value: {ev_str} ({enterprise_value:,.0f})")
        else:
            report_lines.append(f"Enterprise Value: N/A")

        report_lines.append(f"Trailing PE Ratio: {info.get('trailingPE', 'N/A')}")
        report_lines.append(f"Forward PE Ratio: {info.get('forwardPE', 'N/A')}")
        report_lines.append(f"PEG Ratio: {info.get('pegRatio', 'N/A')}")
        report_lines.append(f"Price to Book (P/B): {info.get('priceToBook', 'N/A')}")
        report_lines.append(f"Price to Sales (P/S) TTM: {info.get('priceToSalesTrailing12Months', 'N/A')}")
        report_lines.append(f"Enterprise to Revenue: {info.get('enterpriseToRevenue', 'N/A')}")
        report_lines.append(f"Enterprise to EBITDA: {info.get('enterpriseToEbitda', 'N/A')}")
        report_lines.append("")

        # Financial Performance
        report_lines.append("## Financial Performance")
        revenue = info.get('totalRevenue', 'N/A')
        if revenue != 'N/A' and revenue is not None:
            report_lines.append(f"Total Revenue: ${revenue:,.0f}")
        else:
            report_lines.append(f"Total Revenue: N/A")

        report_lines.append(f"Revenue Per Share: {info.get('revenuePerShare', 'N/A')}")
        report_lines.append(f"Revenue Growth (YoY): {info.get('revenueGrowth', 'N/A')}")

        gross_profit = info.get('grossProfits', 'N/A')
        if gross_profit != 'N/A' and gross_profit is not None:
            report_lines.append(f"Gross Profits: ${gross_profit:,.0f}")
        else:
            report_lines.append(f"Gross Profits: N/A")

        ebitda = info.get('ebitda', 'N/A')
        if ebitda != 'N/A' and ebitda is not None:
            report_lines.append(f"EBITDA: ${ebitda:,.0f}")
        else:
            report_lines.append(f"EBITDA: N/A")

        net_income = info.get('netIncomeToCommon', 'N/A')
        if net_income != 'N/A' and net_income is not None:
            report_lines.append(f"Net Income: ${net_income:,.0f}")
        else:
            report_lines.append(f"Net Income: N/A")

        report_lines.append(f"Earnings Growth (YoY): {info.get('earningsGrowth', 'N/A')}")
        report_lines.append("")

        # Earnings Per Share
        report_lines.append("## Earnings Per Share (EPS)")
        report_lines.append(f"Trailing EPS: {info.get('trailingEps', 'N/A')}")
        report_lines.append(f"Forward EPS: {info.get('forwardEps', 'N/A')}")
        report_lines.append("")

        # Profitability Margins
        report_lines.append("## Profitability Margins")
        profit_margin = info.get('profitMargins', 'N/A')
        if profit_margin != 'N/A' and profit_margin is not None:
            report_lines.append(f"Profit Margin: {profit_margin*100:.2f}%")
        else:
            report_lines.append(f"Profit Margin: N/A")

        gross_margin = info.get('grossMargins', 'N/A')
        if gross_margin != 'N/A' and gross_margin is not None:
            report_lines.append(f"Gross Margin: {gross_margin*100:.2f}%")
        else:
            report_lines.append(f"Gross Margin: N/A")

        operating_margin = info.get('operatingMargins', 'N/A')
        if operating_margin != 'N/A' and operating_margin is not None:
            report_lines.append(f"Operating Margin: {operating_margin*100:.2f}%")
        else:
            report_lines.append(f"Operating Margin: N/A")

        ebitda_margin = info.get('ebitdaMargins', 'N/A')
        if ebitda_margin != 'N/A' and ebitda_margin is not None:
            report_lines.append(f"EBITDA Margin: {ebitda_margin*100:.2f}%")
        else:
            report_lines.append(f"EBITDA Margin: N/A")
        report_lines.append("")

        # Returns
        report_lines.append("## Returns")
        roe = info.get('returnOnEquity', 'N/A')
        if roe != 'N/A' and roe is not None:
            report_lines.append(f"Return on Equity (ROE): {roe*100:.2f}%")
        else:
            report_lines.append(f"Return on Equity (ROE): N/A")

        roa = info.get('returnOnAssets', 'N/A')
        if roa != 'N/A' and roa is not None:
            report_lines.append(f"Return on Assets (ROA): {roa*100:.2f}%")
        else:
            report_lines.append(f"Return on Assets (ROA): N/A")
        report_lines.append("")

        # Dividend Information
        report_lines.append("## Dividend Information")
        report_lines.append(f"Dividend Rate: {info.get('dividendRate', 'N/A')}")
        dividend_yield = info.get('dividendYield', 'N/A')
        if dividend_yield != 'N/A' and dividend_yield is not None:
            report_lines.append(f"Dividend Yield: {dividend_yield*100:.2f}%")
        else:
            report_lines.append(f"Dividend Yield: N/A")
        report_lines.append(f"Payout Ratio: {info.get('payoutRatio', 'N/A')}")
        report_lines.append(f"Ex-Dividend Date: {info.get('exDividendDate', 'N/A')}")
        report_lines.append("")

        # Balance Sheet Metrics
        report_lines.append("## Balance Sheet Metrics")
        total_cash = info.get('totalCash', 'N/A')
        if total_cash != 'N/A' and total_cash is not None:
            report_lines.append(f"Total Cash: ${total_cash:,.0f}")
        else:
            report_lines.append(f"Total Cash: N/A")

        report_lines.append(f"Total Cash Per Share: {info.get('totalCashPerShare', 'N/A')}")

        total_debt = info.get('totalDebt', 'N/A')
        if total_debt != 'N/A' and total_debt is not None:
            report_lines.append(f"Total Debt: ${total_debt:,.0f}")
        else:
            report_lines.append(f"Total Debt: N/A")

        report_lines.append(f"Debt to Equity: {info.get('debtToEquity', 'N/A')}")
        report_lines.append(f"Current Ratio: {info.get('currentRatio', 'N/A')}")
        report_lines.append(f"Quick Ratio: {info.get('quickRatio', 'N/A')}")
        report_lines.append(f"Book Value Per Share: {info.get('bookValue', 'N/A')}")
        report_lines.append("")

        # Cash Flow Metrics
        report_lines.append("## Cash Flow Metrics")
        free_cashflow = info.get('freeCashflow', 'N/A')
        if free_cashflow != 'N/A' and free_cashflow is not None:
            report_lines.append(f"Free Cash Flow: ${free_cashflow:,.0f}")
        else:
            report_lines.append(f"Free Cash Flow: N/A")

        operating_cashflow = info.get('operatingCashflow', 'N/A')
        if operating_cashflow != 'N/A' and operating_cashflow is not None:
            report_lines.append(f"Operating Cash Flow: ${operating_cashflow:,.0f}")
        else:
            report_lines.append(f"Operating Cash Flow: N/A")
        report_lines.append("")

        # Analyst Targets
        report_lines.append("## Analyst Targets")
        report_lines.append(f"Target Mean Price: {info.get('targetMeanPrice', 'N/A')}")
        report_lines.append(f"Target High Price: {info.get('targetHighPrice', 'N/A')}")
        report_lines.append(f"Target Low Price: {info.get('targetLowPrice', 'N/A')}")
        report_lines.append(f"Target Median Price: {info.get('targetMedianPrice', 'N/A')}")
        report_lines.append(f"Recommendation: {info.get('recommendationKey', 'N/A')}")
        report_lines.append(f"Number of Analyst Opinions: {info.get('numberOfAnalystOpinions', 'N/A')}")
        report_lines.append("")

        # Beta and Risk
        report_lines.append("## Risk Metrics")
        report_lines.append(f"Beta: {info.get('beta', 'N/A')}")
        report_lines.append(f"Audit Risk: {info.get('auditRisk', 'N/A')}")
        report_lines.append(f"Board Risk: {info.get('boardRisk', 'N/A')}")
        report_lines.append(f"Overall Risk: {info.get('overallRisk', 'N/A')}")

        return "\n".join(report_lines)

    except Exception as e:
        return f"Error retrieving fundamentals for {ticker}: {str(e)}"


def get_balance_sheet(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date (not used for yfinance)"] = None
):
    """Get balance sheet data from yfinance."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        
        if freq.lower() == "quarterly":
            data = ticker_obj.quarterly_balance_sheet
        else:
            data = ticker_obj.balance_sheet
            
        if data.empty:
            return f"No balance sheet data found for symbol '{ticker}'"
            
        # Convert to CSV string for consistency with other functions
        csv_string = data.to_csv()
        
        # Add header information
        header = f"# Balance Sheet data for {ticker.upper()} ({freq})\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string
        
    except Exception as e:
        return f"Error retrieving balance sheet for {ticker}: {str(e)}"


def get_cashflow(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date (not used for yfinance)"] = None
):
    """Get cash flow data from yfinance."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        
        if freq.lower() == "quarterly":
            data = ticker_obj.quarterly_cashflow
        else:
            data = ticker_obj.cashflow
            
        if data.empty:
            return f"No cash flow data found for symbol '{ticker}'"
            
        # Convert to CSV string for consistency with other functions
        csv_string = data.to_csv()
        
        # Add header information
        header = f"# Cash Flow data for {ticker.upper()} ({freq})\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string
        
    except Exception as e:
        return f"Error retrieving cash flow for {ticker}: {str(e)}"


def get_income_statement(
    ticker: Annotated[str, "ticker symbol of the company"],
    freq: Annotated[str, "frequency of data: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date (not used for yfinance)"] = None
):
    """Get income statement data from yfinance."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        
        if freq.lower() == "quarterly":
            data = ticker_obj.quarterly_income_stmt
        else:
            data = ticker_obj.income_stmt
            
        if data.empty:
            return f"No income statement data found for symbol '{ticker}'"
            
        # Convert to CSV string for consistency with other functions
        csv_string = data.to_csv()
        
        # Add header information
        header = f"# Income Statement data for {ticker.upper()} ({freq})\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string
        
    except Exception as e:
        return f"Error retrieving income statement for {ticker}: {str(e)}"


def get_insider_transactions(
    ticker: Annotated[str, "ticker symbol of the company"]
):
    """Get insider transactions data from yfinance."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        data = ticker_obj.insider_transactions
        
        if data is None or data.empty:
            return f"No insider transactions data found for symbol '{ticker}'"
            
        # Convert to CSV string for consistency with other functions
        csv_string = data.to_csv()
        
        # Add header information
        header = f"# Insider Transactions data for {ticker.upper()}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string
        
    except Exception as e:
        return f"Error retrieving insider transactions for {ticker}: {str(e)}"