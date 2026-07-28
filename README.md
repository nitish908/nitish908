# Trading Agent

An automated trading agent for crypto and stocks. It generates buy/sell
signals from technical indicators, sizes and gates every trade through an
explicit risk-management layer, and tracks accurate, fee-inclusive profit
margins using FIFO cost-basis accounting.

## ⚠️ Read this before doing anything else

- **This is not financial advice.** Nothing here is a recommendation to buy
  or sell any asset.
- **Past performance does not guarantee future results.** A strategy that
  backtests well can still lose money in live markets.
- **Start with `backtest`, then paper trading. Do not go straight to `--mode
  live`.** The default configuration (`mode: paper`) never touches a real
  account.
- **Live trading places real orders with real money.** Reaching live mode
  requires two independent, deliberate opt-ins (see [Live trading
  safeguards](#live-trading-safeguards)) specifically so it can't happen by
  accident.
- **Use API keys scoped to trading only.** Disable withdrawal/transfer
  permissions on every exchange/broker API key you create for this agent.
- You are solely responsible for any funds you choose to trade with this
  software.

## What it does

- **Strategies** (`src/trading_agent/strategies/`): rule-based technical
  indicators — moving-average crossover, RSI mean-reversion, MACD crossover —
  each producing a BUY/SELL/HOLD signal plus a stop-loss/take-profit.
- **Risk management** (`src/trading_agent/risk/`): every signal is sized and
  gated before it can become an order:
  - Minimum risk:reward ratio (rejects trades with a poor payoff profile).
  - Position sizing from the stop-loss distance: `quantity = (equity *
    risk_pct_per_trade) / stop_distance`.
  - Max number of concurrent open positions.
  - Max exposure % of equity per symbol.
  - A daily-drawdown kill switch that halts new entries for the rest of the
    UTC day once losses cross a configured threshold.
- **Accurate profit margins** (`src/trading_agent/portfolio/`): a FIFO
  cost-basis ledger using `Decimal` (never `float`) for every money
  calculation, netting out fees on both entry and exit, reporting per-trade
  and aggregate net profit margin, realized/unrealized P&L, and win rate.
- **Backtesting** (`src/trading_agent/backtest/`): runs a strategy + risk
  manager + portfolio over historical OHLCV data with zero network calls,
  producing a performance report (return, win rate, max drawdown, net
  margin, a Sharpe-like ratio).
- **Adapters** (`src/trading_agent/adapters/`): a common interface
  implemented for crypto (Binance via `ccxt`, with testnet/sandbox support),
  stocks (Alpaca, with native paper trading), and a fully offline
  `SimulatedAdapter` used when no API keys are configured.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
# Edit .env and add your own API keys if/when you want to use a real
# sandbox or live account. Leave it empty to run entirely offline.
```

## Usage

### Backtest (no API keys needed)

```bash
python -m trading_agent.cli backtest \
  --data data/fixtures/sample_ohlcv.csv \
  --strategy ma_crossover \
  --config config/config.yaml
```

Prints total return, win rate, max drawdown, and net profit margin computed
against the bundled synthetic OHLCV fixture. Point `--data` at your own
historical CSV (columns: `timestamp, open, high, low, close, volume`) to
backtest a real market. Available `--strategy` values: `ma_crossover`,
`rsi_mean_reversion`, `macd`.

### Paper trading

```bash
python -m trading_agent.cli run --mode paper --market crypto
```

With no API keys in `.env`, this automatically uses the offline
`SimulatedAdapter` fed by the bundled fixture data (override with
`--sim-data path/to.csv`), so it runs with zero network access. Add Binance
testnet or Alpaca paper keys to `.env` (and set `sandbox`/`paper: true` in
`config/config.yaml`, the defaults) to paper-trade against a real sandbox
account instead.

### Live trading

Live trading is **off by default** and gated behind two independent
switches — see below.

```bash
python -m trading_agent.cli run --mode live --market crypto --live-confirm
```

## Configuration

All settings live in `config/config.yaml`; secrets live in `.env` (see
`.env.example`). Key sections:

```yaml
mode: paper                # paper | live
markets:
  crypto: { symbol: BTC/USDT, timeframe: 1h, sandbox: true }
  stocks: { symbol: AAPL, timeframe: 1Hour, paper: true }
strategy: { name: ma_crossover, params: { fast_period: 10, slow_period: 50 } }
risk:
  risk_pct_per_trade: 0.01           # 1% of equity risked per trade
  min_risk_reward_ratio: 1.5
  max_open_positions: 5
  max_exposure_pct_per_symbol: 0.25
  max_daily_drawdown_pct: 0.05
fees: { taker_fee_pct: 0.001 }
live: { confirm_live_trading: false }
```

## Live trading safeguards

Reaching a real broker/exchange adapter in live mode requires **both**:

1. `live.confirm_live_trading: true` in `config/config.yaml`, and
2. the `--live-confirm` flag on the `run` command.

Either one alone is not enough — this is intentional, to make accidental
real-money trading structurally difficult. When live mode does start, the
agent prints a repeated warning banner before doing anything else.

## Running tests

```bash
pytest -q
```

53 tests cover indicator math, strategy signal generation, risk-manager
position sizing/kill-switch logic, FIFO P&L/margin accounting, adapter
translation (mocked — no real network calls), execution retry/logging, the
agent loop, and a full end-to-end backtest.

## Project layout

```
config/config.yaml            # default configuration
data/fixtures/sample_ohlcv.csv  # synthetic OHLCV data for backtest/tests
src/trading_agent/
  indicators/     sma, ema, rsi, macd, bollinger_bands
  strategies/     Strategy interface + MA crossover / RSI / MACD strategies
  risk/           RiskManager: sizing, risk:reward gate, exposure cap, kill switch
  portfolio/      FIFO cost-basis ledger, Decimal-based P&L and profit margins
  adapters/       ExchangeAdapter interface + CCXT/Binance, Alpaca, Simulated
  execution/      OrderExecutor (retries) + TradeLogger (SQLite/CSV)
  backtest/       BacktestEngine + PerformanceReport
  agent/          AgentLoop (poll -> signal -> risk -> execute -> log)
  cli.py          `run` and `backtest` commands
tests/            pytest suite (53 tests, all offline)
```
