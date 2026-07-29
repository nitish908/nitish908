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
- **Stateless deployment** (`src/trading_agent/server.py`): the same
  poll-signal-risk-execute pipeline exposed as a single `POST /step` HTTP
  call that takes/returns serialized Portfolio+RiskManager state, for
  platforms that can't run a long-lived process (see [Deploying to
  Cloudflare Containers](#deploying-to-cloudflare-containers)).

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

60 tests cover indicator math, strategy signal generation, risk-manager
position sizing/kill-switch logic, FIFO P&L/margin accounting, adapter
translation (mocked — no real network calls), execution retry/logging, the
agent loop, and a full end-to-end backtest -- including a test that proves
serializing Portfolio/RiskManager to JSON and rebuilding them from scratch
between *every single poll* produces identical results to running
continuously in memory (the guarantee the Cloudflare deployment below
depends on).

## Deploying to Cloudflare Containers

The `run` command above is a long-lived process; Cloudflare's container
platform is consumption-based and can sleep a container between requests.
So instead of deploying `run` as-is, this repo ships a **stateless**
variant: `src/trading_agent/server.py` exposes a single `POST /step` that
does one poll (fetch → signal → risk → execute) and returns the *updated*
Portfolio/RiskManager state as JSON. A small Cloudflare Worker + Durable
Object (`cloudflare/worker/src/index.ts`) owns the polling schedule and
persists that state in the Durable Object's own storage between calls —
so open positions, cost-basis history, and the daily kill switch all
survive the container going to sleep and waking back up.

```
Dockerfile                      # packages the app to run trading_agent.server
wrangler.toml                   # container + Durable Object + Worker config
cloudflare/worker/
  src/index.ts                  # Container subclass: schedule()'s /step every N seconds
  package.json / tsconfig.json
```

**⚠️ Verification status:** this was built and type-checked in a sandboxed
session where Cloudflare's docs site returned 403s to automated fetches, and
Docker Hub image pulls were blocked by the sandbox's own egress policy — so
it could not be built into an image or deployed to a real Cloudflare account
here. What *was* verified in this session:
- The full pytest suite, including the state-serialization round-trip proof.
- `src/trading_agent/server.py` running directly and answering `GET
  /health` / `POST /step` correctly.
- `cloudflare/worker/src/index.ts` type-checks cleanly against the real
  `@cloudflare/containers` type declarations (`npx tsc --noEmit`).
- `wrangler deploy --dry-run` parses `wrangler.toml` without errors (it
  actually caught and helped fix a deprecated config field: `[[containers]]`
  fields must be flattened at the top level, not nested under
  `[containers.configuration]`, in the currently installed wrangler version).

What was **not** verified (confirm yourself before trusting this with real
funds): whether `this.schedule()` re-fires cleanly across container
restarts without stacking duplicate polls, and whether secrets set via
`wrangler secret put` actually reach the container the way `envVars` in
`index.ts` assumes. Watch `wrangler tail` after deploying to check for
doubled-up `/step` calls before pointing this at anything real.

### Deploy steps

```bash
cd cloudflare/worker
npm install

npx wrangler login                       # one-time, opens a browser

# Secrets (never commit these; leave unset to run on the offline SimulatedAdapter)
npx wrangler secret put BINANCE_API_KEY --config ../../wrangler.toml
npx wrangler secret put BINANCE_API_SECRET --config ../../wrangler.toml
# ...and/or ALPACA_API_KEY / ALPACA_API_SECRET for stocks

npx wrangler deploy --config ../../wrangler.toml
```

Start in paper mode (`config/config.yaml` already defaults to it) and watch
`npx wrangler tail --config ../../wrangler.toml` for the first several polls
before ever flipping to live mode.

## Project layout

```
Dockerfile                      # container image for src/trading_agent/server.py
wrangler.toml                   # Cloudflare Containers/Worker deployment config
cloudflare/worker/               # Worker + Durable Object driving the container
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
  agent/          step.py (execute_step, shared) + loop.py (AgentLoop, continuous)
  factory.py      shared adapter/risk-config construction (used by cli.py and server.py)
  server.py       stateless POST /step HTTP wrapper, for container/serverless deployment
  cli.py          `run` and `backtest` commands
tests/            pytest suite (60 tests, all offline)
```
