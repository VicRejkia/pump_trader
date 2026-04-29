CREATE SEQUENCE IF NOT EXISTS completed_trades_trade_id_seq;

CREATE TABLE IF NOT EXISTS public.completed_trades
(
    trade_id integer NOT NULL DEFAULT nextval('completed_trades_trade_id_seq'::regclass),
    token_address character varying(44) COLLATE pg_catalog."default" NOT NULL,
    side character varying(4) COLLATE pg_catalog."default" NOT NULL,
    amount_in_sol numeric NOT NULL,
    amount_out_tokens numeric NOT NULL,
    fill_price numeric NOT NULL,
    market_cap_at_trade numeric,
    tx_fee_sol numeric,
    tip_sol numeric DEFAULT 0,
    slippage_percent numeric,
    trade_context jsonb,
    created_at timestamp with time zone DEFAULT now(),
    social_velocity double precision,
    volatility_at_entry double precision,
    rugcheck_score_at_entry integer,
    market_regime text COLLATE pg_catalog."default",
    crossed_cooldown_boundary boolean,
    sell_fraction double precision,
    rebuy boolean DEFAULT false,
    CONSTRAINT completed_trades_pkey PRIMARY KEY (trade_id),
    CONSTRAINT completed_trades_side_check CHECK (side::text = ANY (ARRAY['buy'::character varying, 'sell'::character varying]::text[]))
)