/**
 * Cloudflare Worker + Durable Object that drives the Python trading agent's
 * `/step` endpoint on a fixed interval, using the `@cloudflare/containers`
 * SDK's `Container` class (a Durable Object subclass) as the orchestrator.
 *
 * Why a Durable Object at all: the Python container is a *stateless* HTTP
 * step function (see src/trading_agent/server.py) -- it takes the previous
 * run's serialized Portfolio/RiskManager state and returns the updated
 * state, but does not persist anything itself. Something has to own that
 * state and the polling schedule across container sleep/restart cycles;
 * that's this Durable Object, using its own transactional storage
 * (`this.ctx.storage`), which survives independently of the container.
 *
 * This has been type-checked (`npm run -s tsc --noEmit`, see cloudflare/worker/)
 * against the real `@cloudflare/containers` type declarations, which
 * confirmed the shape of `defaultPort`, `sleepAfter`, `envVars` (a plain
 * `Record<string,string>` property, not a getter -- hence setting it in the
 * constructor below), `containerFetch()`, `onStart()`, and `schedule()`.
 * Cloudflare's docs site blocked automated fetches when this was written
 * (403s), so this was NOT deployed or run against a real Cloudflare account
 * in this session -- only compiled. Before trusting it with real funds,
 * verify at runtime (`wrangler dev` / a real deploy):
 *   - That `schedule()` calls don't stack duplicate pending callbacks if
 *     `onStart()` fires again on a container restart (not just the very
 *     first cold start) -- watch `wrangler tail` for doubled-up polls.
 *   - That secrets set via `wrangler secret put` actually appear on `env`
 *     inside this Durable Object's constructor as assumed below.
 */

import { Container, getContainer } from "@cloudflare/containers";
import type { DurableObject } from "cloudflare:workers";

interface Env {
  TRADING_AGENT_CONTAINER: DurableObjectNamespace<TradingAgentContainer>;
  TRADING_AGENT_MARKET?: string;
  BINANCE_API_KEY?: string;
  BINANCE_API_SECRET?: string;
  ALPACA_API_KEY?: string;
  ALPACA_API_SECRET?: string;
}

// Keep in sync with `execution.poll_interval_seconds` in config/config.yaml.
const POLL_INTERVAL_SECONDS = 60;
const STATE_STORAGE_KEY = "agent_state";

interface StepResponse {
  state: unknown;
  signal: string;
  reason: string;
  equity: string;
  order: { order_id: string; side: string; quantity: string; fill_price: string } | null;
}

export class TradingAgentContainer extends Container<Env> {
  defaultPort = 8080;
  // Keep the container warm well past the poll interval so the alarm-driven
  // step loop doesn't pay a cold-start penalty on every single poll.
  sleepAfter = "30m";

  constructor(ctx: DurableObject["ctx"], env: Env) {
    super(ctx, env);
    // `envVars` is a plain instance property on the base Container class
    // (not a getter), so it must be assigned here, after `super()` has set
    // `this.env` from the Worker's bindings/secrets.
    this.envVars = {
      TRADING_AGENT_MARKET: env.TRADING_AGENT_MARKET ?? "crypto",
      BINANCE_API_KEY: env.BINANCE_API_KEY ?? "",
      BINANCE_API_SECRET: env.BINANCE_API_SECRET ?? "",
      ALPACA_API_KEY: env.ALPACA_API_KEY ?? "",
      ALPACA_API_SECRET: env.ALPACA_API_SECRET ?? "",
    };
  }

  override onStart(): void {
    console.log("[trading-agent] container started, scheduling poll loop");
    this.schedule(1, "poll");
  }

  async poll(): Promise<void> {
    const priorState = (await this.ctx.storage.get<unknown>(STATE_STORAGE_KEY)) ?? null;

    try {
      const response = await this.containerFetch("/step", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: priorState }),
      });

      if (response.ok) {
        const body = (await response.json()) as StepResponse;
        await this.ctx.storage.put(STATE_STORAGE_KEY, body.state);
        console.log(
          `[trading-agent] ${body.signal}: ${body.reason} (equity=${body.equity})`,
        );
      } else {
        console.error(`[trading-agent] step failed: HTTP ${response.status}`);
      }
    } catch (err) {
      // Network/container error -- log and reschedule anyway so a
      // transient failure doesn't permanently stop the poll loop.
      console.error("[trading-agent] step threw:", err);
    }

    await this.schedule(POLL_INTERVAL_SECONDS, "poll");
  }

  // Manual pass-through for hitting e.g. /health directly during setup.
  override async fetch(request: Request): Promise<Response> {
    return this.containerFetch(request);
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // Singleton container -- this agent runs exactly one instance, trading
    // one configured symbol, not one container per inbound request.
    const container = getContainer(env.TRADING_AGENT_CONTAINER);
    return container.fetch(request);
  },
};
