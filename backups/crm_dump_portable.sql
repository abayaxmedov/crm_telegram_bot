--
-- PostgreSQL database dump
--


-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id integer NOT NULL,
    actor_id integer,
    action character varying(120) NOT NULL,
    entity_type character varying(120),
    entity_id character varying(120),
    details text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: ball_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ball_transactions (
    id integer NOT NULL,
    kind character varying(11) NOT NULL,
    status character varying(8) DEFAULT 'pending'::character varying NOT NULL,
    amount integer NOT NULL,
    from_user_id integer,
    to_user_id integer,
    to_doctor_id integer,
    sale_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    decided_at timestamp with time zone
);


--
-- Name: ball_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ball_transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ball_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ball_transactions_id_seq OWNED BY public.ball_transactions.id;


--
-- Name: contracts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contracts (
    id integer NOT NULL,
    pharmacy_id integer NOT NULL,
    number character varying(120) NOT NULL,
    signed_date character varying(32),
    status character varying(9) DEFAULT 'active'::character varying NOT NULL,
    requested_by_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    file_id character varying(255)
);


--
-- Name: contracts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contracts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contracts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contracts_id_seq OWNED BY public.contracts.id;


--
-- Name: daily_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.daily_reports (
    id integer NOT NULL,
    author_id integer NOT NULL,
    target_type character varying(32) NOT NULL,
    target_name character varying(255),
    text text,
    voice_file_id character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: daily_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.daily_reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: daily_reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.daily_reports_id_seq OWNED BY public.daily_reports.id;


--
-- Name: doctors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.doctors (
    id integer NOT NULL,
    full_name character varying(255) NOT NULL,
    phone_number character varying(64),
    location_text character varying(500),
    latitude numeric(10,7),
    longitude numeric(10,7),
    class_category character varying(120),
    manager_id integer,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    bonus_balance numeric(14,2) DEFAULT 0,
    region_id integer,
    approval_status character varying(20) DEFAULT 'approved'::character varying,
    created_by_id integer,
    ball_balance integer DEFAULT 0,
    user_id integer
);


--
-- Name: doctors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.doctors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: doctors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.doctors_id_seq OWNED BY public.doctors.id;


--
-- Name: drug_materials; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.drug_materials (
    id integer NOT NULL,
    title character varying(255) NOT NULL,
    file_id character varying(255) NOT NULL,
    file_name character varying(255),
    uploaded_by_id integer,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: drug_materials_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.drug_materials_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: drug_materials_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.drug_materials_id_seq OWNED BY public.drug_materials.id;


--
-- Name: drugs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.drugs (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    stock integer DEFAULT 0 NOT NULL,
    doctor_bonus_per_pack numeric(12,2) DEFAULT '0'::numeric NOT NULL,
    kpi_plan_qty integer DEFAULT 0 NOT NULL,
    kpi_period_months integer DEFAULT 1 NOT NULL,
    kpi_bonus_full numeric(12,2) DEFAULT '0'::numeric NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    price numeric(14,2) DEFAULT 0,
    ball integer DEFAULT 0
);


--
-- Name: drugs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.drugs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: drugs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.drugs_id_seq OWNED BY public.drugs.id;


--
-- Name: finance_operations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.finance_operations (
    id integer NOT NULL,
    operation_type character varying(7) NOT NULL,
    amount numeric(14,2) NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    created_by_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: finance_operations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.finance_operations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: finance_operations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.finance_operations_id_seq OWNED BY public.finance_operations.id;


--
-- Name: pharmacies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pharmacies (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    phone_number character varying(64),
    location_text character varying(500),
    latitude numeric(10,7),
    longitude numeric(10,7),
    responsible_person character varying(255),
    manager_id integer,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    inn character varying(32),
    filial character varying(120),
    region_id integer,
    approval_status character varying(20) DEFAULT 'approved'::character varying
);


--
-- Name: pharmacies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pharmacies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pharmacies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pharmacies_id_seq OWNED BY public.pharmacies.id;


--
-- Name: regions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.regions (
    id integer NOT NULL,
    name character varying(120) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: regions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.regions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: regions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.regions_id_seq OWNED BY public.regions.id;


--
-- Name: rep_payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rep_payments (
    id integer NOT NULL,
    rep_id integer NOT NULL,
    doctor_id integer,
    kind character varying(6) NOT NULL,
    amount numeric(14,2) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: rep_payments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rep_payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rep_payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rep_payments_id_seq OWNED BY public.rep_payments.id;


--
-- Name: requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.requests (
    id integer NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    status character varying(11) DEFAULT 'new'::character varying NOT NULL,
    created_by_id integer NOT NULL,
    assigned_to_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.requests_id_seq OWNED BY public.requests.id;


--
-- Name: salaries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.salaries (
    id integer NOT NULL,
    user_id integer NOT NULL,
    month character varying(32) NOT NULL,
    base_salary numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    bonus numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    penalty numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    total_amount numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    status character varying(32) DEFAULT 'unpaid'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: salaries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.salaries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: salaries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.salaries_id_seq OWNED BY public.salaries.id;


--
-- Name: sale_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sale_items (
    id integer NOT NULL,
    sale_id integer NOT NULL,
    drug_id integer NOT NULL,
    drug_name character varying(255) NOT NULL,
    quantity integer NOT NULL,
    bonus numeric(12,2) DEFAULT '0'::numeric NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    price numeric(14,2) DEFAULT 0,
    ball integer DEFAULT 0
);


--
-- Name: sale_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sale_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sale_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sale_items_id_seq OWNED BY public.sale_items.id;


--
-- Name: sales; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sales (
    id integer NOT NULL,
    rep_id integer NOT NULL,
    pharmacy_id integer,
    doctor_id integer,
    total_bonus numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    total_price numeric(14,2) DEFAULT 0,
    total_ball integer DEFAULT 0
);


--
-- Name: sales_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sales_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sales_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sales_id_seq OWNED BY public.sales.id;


--
-- Name: scheduled_deletions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scheduled_deletions (
    id integer NOT NULL,
    chat_id bigint NOT NULL,
    message_id bigint NOT NULL,
    delete_at timestamp with time zone NOT NULL,
    ball_tx_id integer
);


--
-- Name: scheduled_deletions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scheduled_deletions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scheduled_deletions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.scheduled_deletions_id_seq OWNED BY public.scheduled_deletions.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    telegram_id bigint,
    username character varying(255),
    full_name character varying(255) NOT NULL,
    role character varying(9) NOT NULL,
    phone_number character varying(64),
    is_active boolean DEFAULT true NOT NULL,
    invite_token character varying(128),
    invite_used boolean DEFAULT false NOT NULL,
    invited_by_id integer,
    activated_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    language character varying(16),
    region_city character varying(120),
    region_rayon character varying(120),
    balance numeric(14,2) DEFAULT 0,
    region_id integer,
    ball_balance integer DEFAULT 0
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: visit_diaries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.visit_diaries (
    id integer NOT NULL,
    rep_id integer NOT NULL,
    latitude numeric(10,7),
    longitude numeric(10,7),
    note text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: visit_diaries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.visit_diaries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: visit_diaries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.visit_diaries_id_seq OWNED BY public.visit_diaries.id;


--
-- Name: warehouse_request_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.warehouse_request_items (
    id integer NOT NULL,
    request_id integer NOT NULL,
    drug_id integer NOT NULL,
    drug_name character varying(255) NOT NULL,
    quantity integer NOT NULL
);


--
-- Name: warehouse_request_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.warehouse_request_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: warehouse_request_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.warehouse_request_items_id_seq OWNED BY public.warehouse_request_items.id;


--
-- Name: warehouse_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.warehouse_requests (
    id integer NOT NULL,
    rep_id integer NOT NULL,
    pharmacy_id integer,
    contract_id integer,
    status character varying(8) DEFAULT 'new'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: warehouse_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.warehouse_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: warehouse_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.warehouse_requests_id_seq OWNED BY public.warehouse_requests.id;


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: ball_transactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ball_transactions ALTER COLUMN id SET DEFAULT nextval('public.ball_transactions_id_seq'::regclass);


--
-- Name: contracts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contracts ALTER COLUMN id SET DEFAULT nextval('public.contracts_id_seq'::regclass);


--
-- Name: daily_reports id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_reports ALTER COLUMN id SET DEFAULT nextval('public.daily_reports_id_seq'::regclass);


--
-- Name: doctors id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.doctors ALTER COLUMN id SET DEFAULT nextval('public.doctors_id_seq'::regclass);


--
-- Name: drug_materials id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drug_materials ALTER COLUMN id SET DEFAULT nextval('public.drug_materials_id_seq'::regclass);


--
-- Name: drugs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drugs ALTER COLUMN id SET DEFAULT nextval('public.drugs_id_seq'::regclass);


--
-- Name: finance_operations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.finance_operations ALTER COLUMN id SET DEFAULT nextval('public.finance_operations_id_seq'::regclass);


--
-- Name: pharmacies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pharmacies ALTER COLUMN id SET DEFAULT nextval('public.pharmacies_id_seq'::regclass);


--
-- Name: regions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regions ALTER COLUMN id SET DEFAULT nextval('public.regions_id_seq'::regclass);


--
-- Name: rep_payments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rep_payments ALTER COLUMN id SET DEFAULT nextval('public.rep_payments_id_seq'::regclass);


--
-- Name: requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests ALTER COLUMN id SET DEFAULT nextval('public.requests_id_seq'::regclass);


--
-- Name: salaries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.salaries ALTER COLUMN id SET DEFAULT nextval('public.salaries_id_seq'::regclass);


--
-- Name: sale_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sale_items ALTER COLUMN id SET DEFAULT nextval('public.sale_items_id_seq'::regclass);


--
-- Name: sales id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales ALTER COLUMN id SET DEFAULT nextval('public.sales_id_seq'::regclass);


--
-- Name: scheduled_deletions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scheduled_deletions ALTER COLUMN id SET DEFAULT nextval('public.scheduled_deletions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: visit_diaries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.visit_diaries ALTER COLUMN id SET DEFAULT nextval('public.visit_diaries_id_seq'::regclass);


--
-- Name: warehouse_request_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouse_request_items ALTER COLUMN id SET DEFAULT nextval('public.warehouse_request_items_id_seq'::regclass);


--
-- Name: warehouse_requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouse_requests ALTER COLUMN id SET DEFAULT nextval('public.warehouse_requests_id_seq'::regclass);


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.audit_logs (id, actor_id, action, entity_type, entity_id, details, created_at) FROM stdin;
1	2	user_invite_created	user	3	role=manager	2026-06-26 17:50:30.622052+00
2	3	invite_activated	user	3	telegram_id=8115824785	2026-06-26 17:50:51.951735+00
3	2	user_invite_created	user	4	role=operator	2026-07-10 12:24:07.055635+00
4	4	invite_activated	user	4	telegram_id=5396535425	2026-07-10 12:25:34.328522+00
5	7	demo_action_1	doctor	1	Demo audit details 1	2026-07-10 18:21:27.213935+00
6	8	demo_action_2	pharmacy	2	Demo audit details 2	2026-07-10 18:20:27.213935+00
7	9	demo_action_3	sale	3	Demo audit details 3	2026-07-10 18:19:27.213935+00
8	10	demo_action_4	user	4	Demo audit details 4	2026-07-10 18:18:27.213935+00
9	11	demo_action_5	doctor	5	Demo audit details 5	2026-07-10 18:17:27.213935+00
10	12	demo_action_6	pharmacy	6	Demo audit details 6	2026-07-10 18:16:27.213935+00
11	13	demo_action_7	sale	7	Demo audit details 7	2026-07-10 18:15:27.213935+00
12	14	demo_action_8	user	8	Demo audit details 8	2026-07-10 18:14:27.213935+00
13	15	demo_action_9	doctor	9	Demo audit details 9	2026-07-10 18:13:27.213935+00
14	16	demo_action_10	pharmacy	10	Demo audit details 10	2026-07-10 18:12:27.213935+00
15	17	demo_action_11	sale	11	Demo audit details 11	2026-07-10 18:11:27.213935+00
16	18	demo_action_12	user	12	Demo audit details 12	2026-07-10 18:10:27.213935+00
17	19	demo_action_13	doctor	13	Demo audit details 13	2026-07-10 18:09:27.213935+00
18	20	demo_action_14	pharmacy	14	Demo audit details 14	2026-07-10 18:08:27.213935+00
19	21	demo_action_15	sale	15	Demo audit details 15	2026-07-10 18:07:27.213935+00
20	22	demo_action_16	user	16	Demo audit details 16	2026-07-10 18:06:27.213935+00
21	23	demo_action_17	doctor	17	Demo audit details 17	2026-07-10 18:05:27.213935+00
22	24	demo_action_18	pharmacy	18	Demo audit details 18	2026-07-10 18:04:27.213935+00
23	25	demo_action_19	sale	19	Demo audit details 19	2026-07-10 18:03:27.213935+00
24	26	demo_action_20	user	20	Demo audit details 20	2026-07-10 18:02:27.213935+00
25	27	demo_action_21	doctor	21	Demo audit details 21	2026-07-10 18:01:27.213935+00
26	28	demo_action_22	pharmacy	22	Demo audit details 22	2026-07-10 18:00:27.213935+00
27	29	demo_action_23	sale	23	Demo audit details 23	2026-07-10 17:59:27.213935+00
28	30	demo_action_24	user	24	Demo audit details 24	2026-07-10 17:58:27.213935+00
29	31	demo_action_25	doctor	25	Demo audit details 25	2026-07-10 17:57:27.213935+00
30	32	demo_action_26	pharmacy	26	Demo audit details 26	2026-07-10 17:56:27.213935+00
31	33	demo_action_27	sale	27	Demo audit details 27	2026-07-10 17:55:27.213935+00
32	34	demo_action_28	user	28	Demo audit details 28	2026-07-10 17:54:27.213935+00
33	35	demo_action_29	doctor	29	Demo audit details 29	2026-07-10 17:53:27.213935+00
34	36	demo_action_30	pharmacy	30	Demo audit details 30	2026-07-10 17:52:27.213935+00
35	\N	ball_transfer_expired	ball_tx	6	80	2026-07-11 00:23:13.920007+00
\.


--
-- Data for Name: ball_transactions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.ball_transactions (id, kind, status, amount, from_user_id, to_user_id, to_doctor_id, sale_id, created_at, decided_at) FROM stdin;
1	transfer	accepted	55	7	8	\N	\N	2026-07-10 17:22:27.213935+00	2026-07-10 18:22:27.213935+00
2	sale_deduct	accepted	60	\N	\N	2	2	2026-07-10 16:22:27.213935+00	2026-07-10 17:22:27.213935+00
3	mint	accepted	65	9	10	\N	\N	2026-07-10 15:22:27.213935+00	2026-07-10 16:22:27.213935+00
4	transfer	accepted	70	10	11	\N	\N	2026-07-10 14:22:27.213935+00	2026-07-10 15:22:27.213935+00
5	sale_deduct	accepted	75	\N	\N	5	5	2026-07-10 13:22:27.213935+00	2026-07-10 14:22:27.213935+00
7	transfer	rejected	85	13	14	\N	\N	2026-07-10 11:22:27.213935+00	2026-07-10 12:22:27.213935+00
8	sale_deduct	accepted	90	\N	\N	8	8	2026-07-10 10:22:27.213935+00	2026-07-10 11:22:27.213935+00
9	mint	accepted	95	15	16	\N	\N	2026-07-10 09:22:27.213935+00	2026-07-10 10:22:27.213935+00
10	transfer	accepted	100	16	17	\N	\N	2026-07-10 08:22:27.213935+00	2026-07-10 09:22:27.213935+00
11	sale_deduct	expired	105	\N	\N	11	11	2026-07-10 07:22:27.213935+00	2026-07-10 08:22:27.213935+00
12	mint	pending	110	18	19	\N	\N	2026-07-10 06:22:27.213935+00	\N
13	transfer	accepted	115	19	20	\N	\N	2026-07-10 05:22:27.213935+00	2026-07-10 06:22:27.213935+00
14	sale_deduct	rejected	120	\N	\N	14	14	2026-07-10 04:22:27.213935+00	2026-07-10 05:22:27.213935+00
15	mint	accepted	125	21	22	\N	\N	2026-07-10 03:22:27.213935+00	2026-07-10 04:22:27.213935+00
16	transfer	accepted	130	22	23	\N	\N	2026-07-10 02:22:27.213935+00	2026-07-10 03:22:27.213935+00
17	sale_deduct	accepted	135	\N	\N	17	17	2026-07-10 01:22:27.213935+00	2026-07-10 02:22:27.213935+00
18	mint	pending	140	24	25	\N	\N	2026-07-10 00:22:27.213935+00	\N
19	transfer	accepted	145	25	26	\N	\N	2026-07-09 23:22:27.213935+00	2026-07-10 00:22:27.213935+00
20	sale_deduct	accepted	150	\N	\N	20	20	2026-07-09 22:22:27.213935+00	2026-07-09 23:22:27.213935+00
21	mint	rejected	155	27	28	\N	\N	2026-07-09 21:22:27.213935+00	2026-07-09 22:22:27.213935+00
22	transfer	expired	160	28	29	\N	\N	2026-07-09 20:22:27.213935+00	2026-07-09 21:22:27.213935+00
23	sale_deduct	accepted	165	\N	\N	23	23	2026-07-09 19:22:27.213935+00	2026-07-09 20:22:27.213935+00
24	mint	pending	170	30	31	\N	\N	2026-07-09 18:22:27.213935+00	\N
25	transfer	accepted	175	31	32	\N	\N	2026-07-09 17:22:27.213935+00	2026-07-09 18:22:27.213935+00
26	sale_deduct	accepted	180	\N	\N	26	26	2026-07-09 16:22:27.213935+00	2026-07-09 17:22:27.213935+00
27	mint	accepted	185	33	34	\N	\N	2026-07-09 15:22:27.213935+00	2026-07-09 16:22:27.213935+00
28	transfer	rejected	190	34	35	\N	\N	2026-07-09 14:22:27.213935+00	2026-07-09 15:22:27.213935+00
29	sale_deduct	accepted	195	\N	\N	29	29	2026-07-09 13:22:27.213935+00	2026-07-09 14:22:27.213935+00
30	mint	pending	200	36	7	\N	\N	2026-07-09 12:22:27.213935+00	\N
6	mint	expired	80	12	13	\N	\N	2026-07-10 12:22:27.213935+00	2026-07-11 00:23:14.44883+00
\.


--
-- Data for Name: contracts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.contracts (id, pharmacy_id, number, signed_date, status, requested_by_id, created_at, updated_at, file_id) FROM stdin;
1	1	DEMO-C-1	09.07.2026	active	25	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_1
2	2	DEMO-C-2	08.07.2026	active	26	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_2
3	3	DEMO-C-3	07.07.2026	active	27	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_3
4	4	DEMO-C-4	06.07.2026	requested	28	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_4
5	5	DEMO-C-5	05.07.2026	active	25	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_5
6	6	DEMO-C-6	04.07.2026	active	26	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_6
7	7	DEMO-C-7	03.07.2026	active	27	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_7
8	8	DEMO-C-8	02.07.2026	requested	28	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_8
9	9	DEMO-C-9	01.07.2026	active	25	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_9
10	10	DEMO-C-10	30.06.2026	active	26	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_10
11	11	DEMO-C-11	29.06.2026	active	27	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_11
12	12	DEMO-C-12	28.06.2026	requested	28	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_12
13	13	DEMO-C-13	27.06.2026	active	25	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_13
14	14	DEMO-C-14	26.06.2026	active	26	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_14
15	15	DEMO-C-15	25.06.2026	active	27	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_15
16	16	DEMO-C-16	24.06.2026	requested	28	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_16
17	17	DEMO-C-17	23.06.2026	active	25	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_17
18	18	DEMO-C-18	22.06.2026	active	26	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_18
19	19	DEMO-C-19	21.06.2026	active	27	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_19
20	20	DEMO-C-20	20.06.2026	requested	28	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_20
21	21	DEMO-C-21	19.06.2026	active	25	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_21
22	22	DEMO-C-22	18.06.2026	active	26	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_22
23	23	DEMO-C-23	17.06.2026	active	27	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_23
24	24	DEMO-C-24	16.06.2026	requested	28	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_24
25	25	DEMO-C-25	15.06.2026	active	25	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_25
26	26	DEMO-C-26	14.06.2026	active	26	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_26
27	27	DEMO-C-27	13.06.2026	active	27	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_27
28	28	DEMO-C-28	12.06.2026	requested	28	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_28
29	29	DEMO-C-29	11.06.2026	active	25	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_29
30	30	DEMO-C-30	10.06.2026	active	26	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	demo_contract_file_30
\.


--
-- Data for Name: daily_reports; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.daily_reports (id, author_id, target_type, target_name, text, voice_file_id, created_at, updated_at) FROM stdin;
1	8	pharmacy	Demo Pharmacy 1	Demo daily report text 1	\N	2026-07-10 17:22:27.213935+00	2026-07-10 17:22:27.213935+00
2	9	doctor	Demo Doctor 2	Demo daily report text 2	\N	2026-07-10 16:22:27.213935+00	2026-07-10 16:22:27.213935+00
3	10	pharmacy	Demo Pharmacy 3	Demo daily report text 3	\N	2026-07-10 15:22:27.213935+00	2026-07-10 15:22:27.213935+00
4	11	doctor	Demo Doctor 4	Demo daily report text 4	\N	2026-07-10 14:22:27.213935+00	2026-07-10 14:22:27.213935+00
5	12	pharmacy	Demo Pharmacy 5	Demo daily report text 5	\N	2026-07-10 13:22:27.213935+00	2026-07-10 13:22:27.213935+00
6	13	doctor	Demo Doctor 6	Demo daily report text 6	demo_voice_file_6	2026-07-10 12:22:27.213935+00	2026-07-10 12:22:27.213935+00
7	14	pharmacy	Demo Pharmacy 7	Demo daily report text 7	\N	2026-07-10 11:22:27.213935+00	2026-07-10 11:22:27.213935+00
8	15	doctor	Demo Doctor 8	Demo daily report text 8	\N	2026-07-10 10:22:27.213935+00	2026-07-10 10:22:27.213935+00
9	16	pharmacy	Demo Pharmacy 9	Demo daily report text 9	\N	2026-07-10 09:22:27.213935+00	2026-07-10 09:22:27.213935+00
10	17	doctor	Demo Doctor 10	Demo daily report text 10	\N	2026-07-10 08:22:27.213935+00	2026-07-10 08:22:27.213935+00
11	18	pharmacy	Demo Pharmacy 11	Demo daily report text 11	\N	2026-07-10 07:22:27.213935+00	2026-07-10 07:22:27.213935+00
12	19	doctor	Demo Doctor 12	Demo daily report text 12	demo_voice_file_12	2026-07-10 06:22:27.213935+00	2026-07-10 06:22:27.213935+00
13	20	pharmacy	Demo Pharmacy 13	Demo daily report text 13	\N	2026-07-10 05:22:27.213935+00	2026-07-10 05:22:27.213935+00
14	21	doctor	Demo Doctor 14	Demo daily report text 14	\N	2026-07-10 04:22:27.213935+00	2026-07-10 04:22:27.213935+00
15	22	pharmacy	Demo Pharmacy 15	Demo daily report text 15	\N	2026-07-10 03:22:27.213935+00	2026-07-10 03:22:27.213935+00
16	23	doctor	Demo Doctor 16	Demo daily report text 16	\N	2026-07-10 02:22:27.213935+00	2026-07-10 02:22:27.213935+00
17	24	pharmacy	Demo Pharmacy 17	Demo daily report text 17	\N	2026-07-10 01:22:27.213935+00	2026-07-10 01:22:27.213935+00
18	8	doctor	Demo Doctor 18	Demo daily report text 18	demo_voice_file_18	2026-07-10 00:22:27.213935+00	2026-07-10 00:22:27.213935+00
19	9	pharmacy	Demo Pharmacy 19	Demo daily report text 19	\N	2026-07-09 23:22:27.213935+00	2026-07-09 23:22:27.213935+00
20	10	doctor	Demo Doctor 20	Demo daily report text 20	\N	2026-07-09 22:22:27.213935+00	2026-07-09 22:22:27.213935+00
21	11	pharmacy	Demo Pharmacy 21	Demo daily report text 21	\N	2026-07-09 21:22:27.213935+00	2026-07-09 21:22:27.213935+00
22	12	doctor	Demo Doctor 22	Demo daily report text 22	\N	2026-07-09 20:22:27.213935+00	2026-07-09 20:22:27.213935+00
23	13	pharmacy	Demo Pharmacy 23	Demo daily report text 23	\N	2026-07-09 19:22:27.213935+00	2026-07-09 19:22:27.213935+00
24	14	doctor	Demo Doctor 24	Demo daily report text 24	demo_voice_file_24	2026-07-09 18:22:27.213935+00	2026-07-09 18:22:27.213935+00
25	15	pharmacy	Demo Pharmacy 25	Demo daily report text 25	\N	2026-07-09 17:22:27.213935+00	2026-07-09 17:22:27.213935+00
26	16	doctor	Demo Doctor 26	Demo daily report text 26	\N	2026-07-09 16:22:27.213935+00	2026-07-09 16:22:27.213935+00
27	17	pharmacy	Demo Pharmacy 27	Demo daily report text 27	\N	2026-07-09 15:22:27.213935+00	2026-07-09 15:22:27.213935+00
28	18	doctor	Demo Doctor 28	Demo daily report text 28	\N	2026-07-09 14:22:27.213935+00	2026-07-09 14:22:27.213935+00
29	19	pharmacy	Demo Pharmacy 29	Demo daily report text 29	\N	2026-07-09 13:22:27.213935+00	2026-07-09 13:22:27.213935+00
30	20	doctor	Demo Doctor 30	Demo daily report text 30	demo_voice_file_30	2026-07-09 12:22:27.213935+00	2026-07-09 12:22:27.213935+00
\.


--
-- Data for Name: doctors; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.doctors (id, full_name, phone_number, location_text, latitude, longitude, class_category, manager_id, notes, created_at, updated_at, bonus_balance, region_id, approval_status, created_by_id, ball_balance, user_id) FROM stdin;
1	Demo Doctor 1	+998910000001	Demo clinic address 1	41.2010000	69.2010000	B	8	Demo doctor note 1	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	10000.00	31	approved	8	25	29
2	Demo Doctor 2	+998910000002	Demo clinic address 2	41.2020000	69.2020000	C	9	Demo doctor note 2	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	20000.00	32	approved	9	50	30
3	Demo Doctor 3	+998910000003	Demo clinic address 3	41.2030000	69.2030000	A	10	Demo doctor note 3	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	30000.00	33	approved	10	75	31
4	Demo Doctor 4	+998910000004	Demo clinic address 4	41.2040000	69.2040000	B	11	Demo doctor note 4	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	40000.00	34	approved	11	100	32
5	Demo Doctor 5	+998910000005	Demo clinic address 5	41.2050000	69.2050000	C	12	Demo doctor note 5	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	50000.00	35	pending	12	125	\N
6	Demo Doctor 6	+998910000006	Demo clinic address 6	41.2060000	69.2060000	A	13	Demo doctor note 6	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	60000.00	36	approved	13	150	\N
7	Demo Doctor 7	+998910000007	Demo clinic address 7	41.2070000	69.2070000	B	14	Demo doctor note 7	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	70000.00	37	rejected	14	175	\N
8	Demo Doctor 8	+998910000008	Demo clinic address 8	41.2080000	69.2080000	C	15	Demo doctor note 8	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	80000.00	38	approved	15	200	\N
9	Demo Doctor 9	+998910000009	Demo clinic address 9	41.2090000	69.2090000	A	16	Demo doctor note 9	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	90000.00	39	approved	16	225	\N
10	Demo Doctor 10	+998910000010	Demo clinic address 10	41.2100000	69.2100000	B	17	Demo doctor note 10	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	100000.00	40	pending	17	250	\N
11	Demo Doctor 11	+998910000011	Demo clinic address 11	41.2110000	69.2110000	C	18	Demo doctor note 11	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	110000.00	41	approved	18	275	\N
12	Demo Doctor 12	+998910000012	Demo clinic address 12	41.2120000	69.2120000	A	19	Demo doctor note 12	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	120000.00	42	approved	19	300	\N
13	Demo Doctor 13	+998910000013	Demo clinic address 13	41.2130000	69.2130000	B	20	Demo doctor note 13	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	130000.00	43	approved	20	325	\N
14	Demo Doctor 14	+998910000014	Demo clinic address 14	41.2140000	69.2140000	C	21	Demo doctor note 14	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	140000.00	44	rejected	21	350	\N
15	Demo Doctor 15	+998910000015	Demo clinic address 15	41.2150000	69.2150000	A	22	Demo doctor note 15	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	150000.00	45	pending	22	375	\N
16	Demo Doctor 16	+998910000016	Demo clinic address 16	41.2160000	69.2160000	B	23	Demo doctor note 16	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	160000.00	46	approved	23	400	\N
17	Demo Doctor 17	+998910000017	Demo clinic address 17	41.2170000	69.2170000	C	24	Demo doctor note 17	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	170000.00	47	approved	24	425	\N
18	Demo Doctor 18	+998910000018	Demo clinic address 18	41.2180000	69.2180000	A	8	Demo doctor note 18	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	180000.00	48	approved	8	450	\N
19	Demo Doctor 19	+998910000019	Demo clinic address 19	41.2190000	69.2190000	B	9	Demo doctor note 19	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	190000.00	49	approved	9	475	\N
20	Demo Doctor 20	+998910000020	Demo clinic address 20	41.2200000	69.2200000	C	10	Demo doctor note 20	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000.00	50	pending	10	500	\N
21	Demo Doctor 21	+998910000021	Demo clinic address 21	41.2210000	69.2210000	A	11	Demo doctor note 21	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	210000.00	51	rejected	11	525	\N
22	Demo Doctor 22	+998910000022	Demo clinic address 22	41.2220000	69.2220000	B	12	Demo doctor note 22	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	220000.00	52	approved	12	550	\N
23	Demo Doctor 23	+998910000023	Demo clinic address 23	41.2230000	69.2230000	C	13	Demo doctor note 23	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	230000.00	53	approved	13	575	\N
24	Demo Doctor 24	+998910000024	Demo clinic address 24	41.2240000	69.2240000	A	14	Demo doctor note 24	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	240000.00	54	approved	14	600	\N
25	Demo Doctor 25	+998910000025	Demo clinic address 25	41.2250000	69.2250000	B	15	Demo doctor note 25	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	250000.00	55	pending	15	625	\N
26	Demo Doctor 26	+998910000026	Demo clinic address 26	41.2260000	69.2260000	C	16	Demo doctor note 26	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	260000.00	56	approved	16	650	\N
27	Demo Doctor 27	+998910000027	Demo clinic address 27	41.2270000	69.2270000	A	17	Demo doctor note 27	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	270000.00	57	approved	17	675	\N
28	Demo Doctor 28	+998910000028	Demo clinic address 28	41.2280000	69.2280000	B	18	Demo doctor note 28	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	280000.00	58	rejected	18	700	\N
29	Demo Doctor 29	+998910000029	Demo clinic address 29	41.2290000	69.2290000	C	19	Demo doctor note 29	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	290000.00	59	approved	19	725	\N
30	Demo Doctor 30	+998910000030	Demo clinic address 30	41.2300000	69.2300000	A	20	Demo doctor note 30	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	300000.00	60	pending	20	750	\N
\.


--
-- Data for Name: drug_materials; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.drug_materials (id, title, file_id, file_name, uploaded_by_id, is_active, created_at, updated_at) FROM stdin;
1	Demo drug material 1	demo_material_file_id_1	demo_material_1.pdf	7	t	2026-07-09 18:22:27.213935+00	2026-07-09 18:22:27.213935+00
2	Demo drug material 2	demo_material_file_id_2	demo_material_2.pdf	8	t	2026-07-08 18:22:27.213935+00	2026-07-08 18:22:27.213935+00
3	Demo drug material 3	demo_material_file_id_3	demo_material_3.pdf	9	t	2026-07-07 18:22:27.213935+00	2026-07-07 18:22:27.213935+00
4	Demo drug material 4	demo_material_file_id_4	demo_material_4.pdf	10	t	2026-07-06 18:22:27.213935+00	2026-07-06 18:22:27.213935+00
5	Demo drug material 5	demo_material_file_id_5	demo_material_5.pdf	11	t	2026-07-05 18:22:27.213935+00	2026-07-05 18:22:27.213935+00
6	Demo drug material 6	demo_material_file_id_6	demo_material_6.pdf	12	t	2026-07-04 18:22:27.213935+00	2026-07-04 18:22:27.213935+00
7	Demo drug material 7	demo_material_file_id_7	demo_material_7.pdf	13	t	2026-07-03 18:22:27.213935+00	2026-07-03 18:22:27.213935+00
8	Demo drug material 8	demo_material_file_id_8	demo_material_8.pdf	14	t	2026-07-02 18:22:27.213935+00	2026-07-02 18:22:27.213935+00
9	Demo drug material 9	demo_material_file_id_9	demo_material_9.pdf	15	t	2026-07-01 18:22:27.213935+00	2026-07-01 18:22:27.213935+00
10	Demo drug material 10	demo_material_file_id_10	demo_material_10.pdf	16	t	2026-06-30 18:22:27.213935+00	2026-06-30 18:22:27.213935+00
11	Demo drug material 11	demo_material_file_id_11	demo_material_11.pdf	17	t	2026-06-29 18:22:27.213935+00	2026-06-29 18:22:27.213935+00
12	Demo drug material 12	demo_material_file_id_12	demo_material_12.pdf	18	t	2026-06-28 18:22:27.213935+00	2026-06-28 18:22:27.213935+00
13	Demo drug material 13	demo_material_file_id_13	demo_material_13.pdf	19	t	2026-06-27 18:22:27.213935+00	2026-06-27 18:22:27.213935+00
14	Demo drug material 14	demo_material_file_id_14	demo_material_14.pdf	20	t	2026-06-26 18:22:27.213935+00	2026-06-26 18:22:27.213935+00
15	Demo drug material 15	demo_material_file_id_15	demo_material_15.pdf	21	t	2026-06-25 18:22:27.213935+00	2026-06-25 18:22:27.213935+00
16	Demo drug material 16	demo_material_file_id_16	demo_material_16.pdf	22	t	2026-06-24 18:22:27.213935+00	2026-06-24 18:22:27.213935+00
17	Demo drug material 17	demo_material_file_id_17	demo_material_17.pdf	23	t	2026-06-23 18:22:27.213935+00	2026-06-23 18:22:27.213935+00
18	Demo drug material 18	demo_material_file_id_18	demo_material_18.pdf	24	t	2026-06-22 18:22:27.213935+00	2026-06-22 18:22:27.213935+00
19	Demo drug material 19	demo_material_file_id_19	demo_material_19.pdf	7	t	2026-06-21 18:22:27.213935+00	2026-06-21 18:22:27.213935+00
20	Demo drug material 20	demo_material_file_id_20	demo_material_20.pdf	8	t	2026-06-20 18:22:27.213935+00	2026-06-20 18:22:27.213935+00
21	Demo drug material 21	demo_material_file_id_21	demo_material_21.pdf	9	t	2026-06-19 18:22:27.213935+00	2026-06-19 18:22:27.213935+00
22	Demo drug material 22	demo_material_file_id_22	demo_material_22.pdf	10	t	2026-06-18 18:22:27.213935+00	2026-06-18 18:22:27.213935+00
23	Demo drug material 23	demo_material_file_id_23	demo_material_23.pdf	11	t	2026-06-17 18:22:27.213935+00	2026-06-17 18:22:27.213935+00
24	Demo drug material 24	demo_material_file_id_24	demo_material_24.pdf	12	t	2026-06-16 18:22:27.213935+00	2026-06-16 18:22:27.213935+00
25	Demo drug material 25	demo_material_file_id_25	demo_material_25.pdf	13	t	2026-06-15 18:22:27.213935+00	2026-06-15 18:22:27.213935+00
26	Demo drug material 26	demo_material_file_id_26	demo_material_26.pdf	14	t	2026-06-14 18:22:27.213935+00	2026-06-14 18:22:27.213935+00
27	Demo drug material 27	demo_material_file_id_27	demo_material_27.pdf	15	t	2026-06-13 18:22:27.213935+00	2026-06-13 18:22:27.213935+00
28	Demo drug material 28	demo_material_file_id_28	demo_material_28.pdf	16	t	2026-06-12 18:22:27.213935+00	2026-06-12 18:22:27.213935+00
29	Demo drug material 29	demo_material_file_id_29	demo_material_29.pdf	17	t	2026-06-11 18:22:27.213935+00	2026-06-11 18:22:27.213935+00
30	Demo drug material 30	demo_material_file_id_30	demo_material_30.pdf	18	t	2026-06-10 18:22:27.213935+00	2026-06-10 18:22:27.213935+00
\.


--
-- Data for Name: drugs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.drugs (id, name, stock, doctor_bonus_per_pack, kpi_plan_qty, kpi_period_months, kpi_bonus_full, is_active, created_at, updated_at, price, ball) FROM stdin;
1	Demo Drug 1	315	1050.00	55	1	52500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	10750.00	3
2	Demo Drug 2	330	1100.00	60	1	55000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	11500.00	4
3	Demo Drug 3	345	1150.00	65	3	57500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	12250.00	5
4	Demo Drug 4	360	1200.00	70	1	60000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	13000.00	6
5	Demo Drug 5	375	1250.00	75	1	62500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	13750.00	7
6	Demo Drug 6	390	1300.00	80	3	65000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	14500.00	8
7	Demo Drug 7	405	1350.00	85	1	67500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	15250.00	9
8	Demo Drug 8	420	1400.00	90	1	70000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	16000.00	10
9	Demo Drug 9	435	1450.00	95	3	72500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	16750.00	2
10	Demo Drug 10	450	1500.00	100	1	75000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	17500.00	3
11	Demo Drug 11	465	1550.00	105	1	77500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	18250.00	4
12	Demo Drug 12	480	1600.00	110	3	80000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	19000.00	5
13	Demo Drug 13	495	1650.00	115	1	82500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	19750.00	6
14	Demo Drug 14	510	1700.00	120	1	85000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	20500.00	7
15	Demo Drug 15	525	1750.00	125	3	87500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	21250.00	8
16	Demo Drug 16	540	1800.00	130	1	90000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	22000.00	9
17	Demo Drug 17	555	1850.00	135	1	92500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	22750.00	10
18	Demo Drug 18	570	1900.00	140	3	95000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	23500.00	2
19	Demo Drug 19	585	1950.00	145	1	97500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	24250.00	3
20	Demo Drug 20	600	2000.00	150	1	100000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	25000.00	4
21	Demo Drug 21	615	2050.00	155	3	102500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	25750.00	5
22	Demo Drug 22	630	2100.00	160	1	105000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	26500.00	6
23	Demo Drug 23	645	2150.00	165	1	107500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	27250.00	7
24	Demo Drug 24	660	2200.00	170	3	110000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	28000.00	8
25	Demo Drug 25	675	2250.00	175	1	112500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	28750.00	9
26	Demo Drug 26	690	2300.00	180	1	115000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	29500.00	10
27	Demo Drug 27	705	2350.00	185	3	117500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	30250.00	2
28	Demo Drug 28	720	2400.00	190	1	120000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	31000.00	3
29	Demo Drug 29	735	2450.00	195	1	122500.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	31750.00	4
30	Demo Drug 30	750	2500.00	200	3	125000.00	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	32500.00	5
\.


--
-- Data for Name: finance_operations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.finance_operations (id, operation_type, amount, title, description, created_by_id, created_at, updated_at) FROM stdin;
1	income	600000.00	Demo finance operation 1	Demo finance description 1	7	2026-07-09 18:22:27.213935+00	2026-07-09 18:22:27.213935+00
2	expense	700000.00	Demo finance operation 2	Demo finance description 2	7	2026-07-08 18:22:27.213935+00	2026-07-08 18:22:27.213935+00
3	debt	800000.00	Demo finance operation 3	Demo finance description 3	7	2026-07-07 18:22:27.213935+00	2026-07-07 18:22:27.213935+00
4	payment	900000.00	Demo finance operation 4	Demo finance description 4	7	2026-07-06 18:22:27.213935+00	2026-07-06 18:22:27.213935+00
5	income	1000000.00	Demo finance operation 5	Demo finance description 5	7	2026-07-05 18:22:27.213935+00	2026-07-05 18:22:27.213935+00
6	expense	1100000.00	Demo finance operation 6	Demo finance description 6	7	2026-07-04 18:22:27.213935+00	2026-07-04 18:22:27.213935+00
7	debt	1200000.00	Demo finance operation 7	Demo finance description 7	7	2026-07-03 18:22:27.213935+00	2026-07-03 18:22:27.213935+00
8	payment	1300000.00	Demo finance operation 8	Demo finance description 8	7	2026-07-02 18:22:27.213935+00	2026-07-02 18:22:27.213935+00
9	income	1400000.00	Demo finance operation 9	Demo finance description 9	7	2026-07-01 18:22:27.213935+00	2026-07-01 18:22:27.213935+00
10	expense	1500000.00	Demo finance operation 10	Demo finance description 10	7	2026-06-30 18:22:27.213935+00	2026-06-30 18:22:27.213935+00
11	debt	1600000.00	Demo finance operation 11	Demo finance description 11	7	2026-06-29 18:22:27.213935+00	2026-06-29 18:22:27.213935+00
12	payment	1700000.00	Demo finance operation 12	Demo finance description 12	7	2026-06-28 18:22:27.213935+00	2026-06-28 18:22:27.213935+00
13	income	1800000.00	Demo finance operation 13	Demo finance description 13	7	2026-06-27 18:22:27.213935+00	2026-06-27 18:22:27.213935+00
14	expense	1900000.00	Demo finance operation 14	Demo finance description 14	7	2026-06-26 18:22:27.213935+00	2026-06-26 18:22:27.213935+00
15	debt	2000000.00	Demo finance operation 15	Demo finance description 15	7	2026-06-25 18:22:27.213935+00	2026-06-25 18:22:27.213935+00
16	payment	2100000.00	Demo finance operation 16	Demo finance description 16	7	2026-06-24 18:22:27.213935+00	2026-06-24 18:22:27.213935+00
17	income	2200000.00	Demo finance operation 17	Demo finance description 17	7	2026-06-23 18:22:27.213935+00	2026-06-23 18:22:27.213935+00
18	expense	2300000.00	Demo finance operation 18	Demo finance description 18	7	2026-06-22 18:22:27.213935+00	2026-06-22 18:22:27.213935+00
19	debt	2400000.00	Demo finance operation 19	Demo finance description 19	7	2026-06-21 18:22:27.213935+00	2026-06-21 18:22:27.213935+00
20	payment	2500000.00	Demo finance operation 20	Demo finance description 20	7	2026-06-20 18:22:27.213935+00	2026-06-20 18:22:27.213935+00
21	income	2600000.00	Demo finance operation 21	Demo finance description 21	7	2026-06-19 18:22:27.213935+00	2026-06-19 18:22:27.213935+00
22	expense	2700000.00	Demo finance operation 22	Demo finance description 22	7	2026-06-18 18:22:27.213935+00	2026-06-18 18:22:27.213935+00
23	debt	2800000.00	Demo finance operation 23	Demo finance description 23	7	2026-06-17 18:22:27.213935+00	2026-06-17 18:22:27.213935+00
24	payment	2900000.00	Demo finance operation 24	Demo finance description 24	7	2026-06-16 18:22:27.213935+00	2026-06-16 18:22:27.213935+00
25	income	3000000.00	Demo finance operation 25	Demo finance description 25	7	2026-06-15 18:22:27.213935+00	2026-06-15 18:22:27.213935+00
26	expense	3100000.00	Demo finance operation 26	Demo finance description 26	7	2026-06-14 18:22:27.213935+00	2026-06-14 18:22:27.213935+00
27	debt	3200000.00	Demo finance operation 27	Demo finance description 27	7	2026-06-13 18:22:27.213935+00	2026-06-13 18:22:27.213935+00
28	payment	3300000.00	Demo finance operation 28	Demo finance description 28	7	2026-06-12 18:22:27.213935+00	2026-06-12 18:22:27.213935+00
29	income	3400000.00	Demo finance operation 29	Demo finance description 29	7	2026-06-11 18:22:27.213935+00	2026-06-11 18:22:27.213935+00
30	expense	3500000.00	Demo finance operation 30	Demo finance description 30	7	2026-06-10 18:22:27.213935+00	2026-06-10 18:22:27.213935+00
\.


--
-- Data for Name: pharmacies; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.pharmacies (id, name, phone_number, location_text, latitude, longitude, responsible_person, manager_id, notes, created_at, updated_at, inn, filial, region_id, approval_status) FROM stdin;
1	Demo Pharmacy 1	+998930000001	Demo pharmacy address 1	41.3010000	69.3010000	Responsible Person 1	8	Demo pharmacy note 1	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000001	Filial 1	31	approved
2	Demo Pharmacy 2	+998930000002	Demo pharmacy address 2	41.3020000	69.3020000	Responsible Person 2	9	Demo pharmacy note 2	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000002	Filial 2	32	approved
3	Demo Pharmacy 3	+998930000003	Demo pharmacy address 3	41.3030000	69.3030000	Responsible Person 3	10	Demo pharmacy note 3	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000003	Filial 3	33	approved
4	Demo Pharmacy 4	+998930000004	Demo pharmacy address 4	41.3040000	69.3040000	Responsible Person 4	11	Demo pharmacy note 4	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000004	Filial 4	34	approved
5	Demo Pharmacy 5	+998930000005	Demo pharmacy address 5	41.3050000	69.3050000	Responsible Person 5	12	Demo pharmacy note 5	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000005	Filial 5	35	approved
6	Demo Pharmacy 6	+998930000006	Demo pharmacy address 6	41.3060000	69.3060000	Responsible Person 6	13	Demo pharmacy note 6	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000006	Filial 1	36	pending
7	Demo Pharmacy 7	+998930000007	Demo pharmacy address 7	41.3070000	69.3070000	Responsible Person 7	14	Demo pharmacy note 7	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000007	Filial 2	37	approved
8	Demo Pharmacy 8	+998930000008	Demo pharmacy address 8	41.3080000	69.3080000	Responsible Person 8	15	Demo pharmacy note 8	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000008	Filial 3	38	approved
9	Demo Pharmacy 9	+998930000009	Demo pharmacy address 9	41.3090000	69.3090000	Responsible Person 9	16	Demo pharmacy note 9	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000009	Filial 4	39	approved
10	Demo Pharmacy 10	+998930000010	Demo pharmacy address 10	41.3100000	69.3100000	Responsible Person 10	17	Demo pharmacy note 10	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000010	Filial 5	40	approved
11	Demo Pharmacy 11	+998930000011	Demo pharmacy address 11	41.3110000	69.3110000	Responsible Person 11	18	Demo pharmacy note 11	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000011	Filial 1	41	rejected
12	Demo Pharmacy 12	+998930000012	Demo pharmacy address 12	41.3120000	69.3120000	Responsible Person 12	19	Demo pharmacy note 12	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000012	Filial 2	42	pending
13	Demo Pharmacy 13	+998930000013	Demo pharmacy address 13	41.3130000	69.3130000	Responsible Person 13	20	Demo pharmacy note 13	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000013	Filial 3	43	approved
14	Demo Pharmacy 14	+998930000014	Demo pharmacy address 14	41.3140000	69.3140000	Responsible Person 14	21	Demo pharmacy note 14	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000014	Filial 4	44	approved
15	Demo Pharmacy 15	+998930000015	Demo pharmacy address 15	41.3150000	69.3150000	Responsible Person 15	22	Demo pharmacy note 15	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000015	Filial 5	45	approved
16	Demo Pharmacy 16	+998930000016	Demo pharmacy address 16	41.3160000	69.3160000	Responsible Person 16	23	Demo pharmacy note 16	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000016	Filial 1	46	approved
17	Demo Pharmacy 17	+998930000017	Demo pharmacy address 17	41.3170000	69.3170000	Responsible Person 17	24	Demo pharmacy note 17	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000017	Filial 2	47	approved
18	Demo Pharmacy 18	+998930000018	Demo pharmacy address 18	41.3180000	69.3180000	Responsible Person 18	8	Demo pharmacy note 18	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000018	Filial 3	48	pending
19	Demo Pharmacy 19	+998930000019	Demo pharmacy address 19	41.3190000	69.3190000	Responsible Person 19	9	Demo pharmacy note 19	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000019	Filial 4	49	approved
20	Demo Pharmacy 20	+998930000020	Demo pharmacy address 20	41.3200000	69.3200000	Responsible Person 20	10	Demo pharmacy note 20	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000020	Filial 5	50	approved
21	Demo Pharmacy 21	+998930000021	Demo pharmacy address 21	41.3210000	69.3210000	Responsible Person 21	11	Demo pharmacy note 21	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000021	Filial 1	51	approved
22	Demo Pharmacy 22	+998930000022	Demo pharmacy address 22	41.3220000	69.3220000	Responsible Person 22	12	Demo pharmacy note 22	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000022	Filial 2	52	rejected
23	Demo Pharmacy 23	+998930000023	Demo pharmacy address 23	41.3230000	69.3230000	Responsible Person 23	13	Demo pharmacy note 23	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000023	Filial 3	53	approved
24	Demo Pharmacy 24	+998930000024	Demo pharmacy address 24	41.3240000	69.3240000	Responsible Person 24	14	Demo pharmacy note 24	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000024	Filial 4	54	pending
25	Demo Pharmacy 25	+998930000025	Demo pharmacy address 25	41.3250000	69.3250000	Responsible Person 25	15	Demo pharmacy note 25	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000025	Filial 5	55	approved
26	Demo Pharmacy 26	+998930000026	Demo pharmacy address 26	41.3260000	69.3260000	Responsible Person 26	16	Demo pharmacy note 26	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000026	Filial 1	56	approved
27	Demo Pharmacy 27	+998930000027	Demo pharmacy address 27	41.3270000	69.3270000	Responsible Person 27	17	Demo pharmacy note 27	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000027	Filial 2	57	approved
28	Demo Pharmacy 28	+998930000028	Demo pharmacy address 28	41.3280000	69.3280000	Responsible Person 28	18	Demo pharmacy note 28	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000028	Filial 3	58	approved
29	Demo Pharmacy 29	+998930000029	Demo pharmacy address 29	41.3290000	69.3290000	Responsible Person 29	19	Demo pharmacy note 29	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000029	Filial 4	59	approved
30	Demo Pharmacy 30	+998930000030	Demo pharmacy address 30	41.3300000	69.3300000	Responsible Person 30	20	Demo pharmacy note 30	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	200000030	Filial 5	60	pending
\.


--
-- Data for Name: regions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.regions (id, name, is_active, created_at, updated_at) FROM stdin;
31	demo_20260710182227218_Region_1	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
32	demo_20260710182227218_Region_2	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
33	demo_20260710182227218_Region_3	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
34	demo_20260710182227218_Region_4	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
35	demo_20260710182227218_Region_5	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
36	demo_20260710182227218_Region_6	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
37	demo_20260710182227218_Region_7	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
38	demo_20260710182227218_Region_8	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
39	demo_20260710182227218_Region_9	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
40	demo_20260710182227218_Region_10	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
41	demo_20260710182227218_Region_11	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
42	demo_20260710182227218_Region_12	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
43	demo_20260710182227218_Region_13	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
44	demo_20260710182227218_Region_14	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
45	demo_20260710182227218_Region_15	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
46	demo_20260710182227218_Region_16	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
47	demo_20260710182227218_Region_17	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
48	demo_20260710182227218_Region_18	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
49	demo_20260710182227218_Region_19	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
50	demo_20260710182227218_Region_20	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
51	demo_20260710182227218_Region_21	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
52	demo_20260710182227218_Region_22	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
53	demo_20260710182227218_Region_23	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
54	demo_20260710182227218_Region_24	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
55	demo_20260710182227218_Region_25	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
56	demo_20260710182227218_Region_26	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
57	demo_20260710182227218_Region_27	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
58	demo_20260710182227218_Region_28	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
59	demo_20260710182227218_Region_29	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
60	demo_20260710182227218_Region_30	t	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00
\.


--
-- Data for Name: rep_payments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.rep_payments (id, rep_id, doctor_id, kind, amount, created_at) FROM stdin;
1	8	1	payout	125000.00	2026-07-10 17:22:27.213935+00
2	9	2	return	150000.00	2026-07-10 16:22:27.213935+00
3	10	\N	issue	175000.00	2026-07-10 15:22:27.213935+00
4	11	4	payout	200000.00	2026-07-10 14:22:27.213935+00
5	12	5	return	225000.00	2026-07-10 13:22:27.213935+00
6	13	\N	issue	250000.00	2026-07-10 12:22:27.213935+00
7	14	7	payout	275000.00	2026-07-10 11:22:27.213935+00
8	15	8	return	300000.00	2026-07-10 10:22:27.213935+00
9	16	\N	issue	325000.00	2026-07-10 09:22:27.213935+00
10	17	10	payout	350000.00	2026-07-10 08:22:27.213935+00
11	18	11	return	375000.00	2026-07-10 07:22:27.213935+00
12	19	\N	issue	400000.00	2026-07-10 06:22:27.213935+00
13	20	13	payout	425000.00	2026-07-10 05:22:27.213935+00
14	21	14	return	450000.00	2026-07-10 04:22:27.213935+00
15	22	\N	issue	475000.00	2026-07-10 03:22:27.213935+00
16	23	16	payout	500000.00	2026-07-10 02:22:27.213935+00
17	24	17	return	525000.00	2026-07-10 01:22:27.213935+00
18	8	\N	issue	550000.00	2026-07-10 00:22:27.213935+00
19	9	19	payout	575000.00	2026-07-09 23:22:27.213935+00
20	10	20	return	600000.00	2026-07-09 22:22:27.213935+00
21	11	\N	issue	625000.00	2026-07-09 21:22:27.213935+00
22	12	22	payout	650000.00	2026-07-09 20:22:27.213935+00
23	13	23	return	675000.00	2026-07-09 19:22:27.213935+00
24	14	\N	issue	700000.00	2026-07-09 18:22:27.213935+00
25	15	25	payout	725000.00	2026-07-09 17:22:27.213935+00
26	16	26	return	750000.00	2026-07-09 16:22:27.213935+00
27	17	\N	issue	775000.00	2026-07-09 15:22:27.213935+00
28	18	28	payout	800000.00	2026-07-09 14:22:27.213935+00
29	19	29	return	825000.00	2026-07-09 13:22:27.213935+00
30	20	\N	issue	850000.00	2026-07-09 12:22:27.213935+00
\.


--
-- Data for Name: requests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.requests (id, title, description, status, created_by_id, assigned_to_id, created_at, updated_at) FROM stdin;
1	Demo request 1	Demo request description 1	new	7	25	2026-07-10 17:22:27.213935+00	2026-07-10 17:22:27.213935+00
2	Demo request 2	Demo request description 2	new	8	26	2026-07-10 16:22:27.213935+00	2026-07-10 16:22:27.213935+00
3	Demo request 3	Demo request description 3	in_progress	9	27	2026-07-10 15:22:27.213935+00	2026-07-10 15:22:27.213935+00
4	Demo request 4	Demo request description 4	new	10	28	2026-07-10 14:22:27.213935+00	2026-07-10 14:22:27.213935+00
5	Demo request 5	Demo request description 5	done	11	25	2026-07-10 13:22:27.213935+00	2026-07-10 13:22:27.213935+00
6	Demo request 6	Demo request description 6	in_progress	12	26	2026-07-10 12:22:27.213935+00	2026-07-10 12:22:27.213935+00
7	Demo request 7	Demo request description 7	canceled	13	27	2026-07-10 11:22:27.213935+00	2026-07-10 11:22:27.213935+00
8	Demo request 8	Demo request description 8	new	14	28	2026-07-10 10:22:27.213935+00	2026-07-10 10:22:27.213935+00
9	Demo request 9	Demo request description 9	in_progress	15	25	2026-07-10 09:22:27.213935+00	2026-07-10 09:22:27.213935+00
10	Demo request 10	Demo request description 10	done	16	26	2026-07-10 08:22:27.213935+00	2026-07-10 08:22:27.213935+00
11	Demo request 11	Demo request description 11	new	17	27	2026-07-10 07:22:27.213935+00	2026-07-10 07:22:27.213935+00
12	Demo request 12	Demo request description 12	in_progress	18	28	2026-07-10 06:22:27.213935+00	2026-07-10 06:22:27.213935+00
13	Demo request 13	Demo request description 13	new	19	25	2026-07-10 05:22:27.213935+00	2026-07-10 05:22:27.213935+00
14	Demo request 14	Demo request description 14	canceled	20	26	2026-07-10 04:22:27.213935+00	2026-07-10 04:22:27.213935+00
15	Demo request 15	Demo request description 15	done	21	27	2026-07-10 03:22:27.213935+00	2026-07-10 03:22:27.213935+00
16	Demo request 16	Demo request description 16	new	22	28	2026-07-10 02:22:27.213935+00	2026-07-10 02:22:27.213935+00
17	Demo request 17	Demo request description 17	new	23	25	2026-07-10 01:22:27.213935+00	2026-07-10 01:22:27.213935+00
18	Demo request 18	Demo request description 18	in_progress	24	26	2026-07-10 00:22:27.213935+00	2026-07-10 00:22:27.213935+00
19	Demo request 19	Demo request description 19	new	25	27	2026-07-09 23:22:27.213935+00	2026-07-09 23:22:27.213935+00
20	Demo request 20	Demo request description 20	done	26	28	2026-07-09 22:22:27.213935+00	2026-07-09 22:22:27.213935+00
21	Demo request 21	Demo request description 21	canceled	27	25	2026-07-09 21:22:27.213935+00	2026-07-09 21:22:27.213935+00
22	Demo request 22	Demo request description 22	new	28	26	2026-07-09 20:22:27.213935+00	2026-07-09 20:22:27.213935+00
23	Demo request 23	Demo request description 23	new	29	27	2026-07-09 19:22:27.213935+00	2026-07-09 19:22:27.213935+00
24	Demo request 24	Demo request description 24	in_progress	30	28	2026-07-09 18:22:27.213935+00	2026-07-09 18:22:27.213935+00
25	Demo request 25	Demo request description 25	done	31	25	2026-07-09 17:22:27.213935+00	2026-07-09 17:22:27.213935+00
26	Demo request 26	Demo request description 26	new	32	26	2026-07-09 16:22:27.213935+00	2026-07-09 16:22:27.213935+00
27	Demo request 27	Demo request description 27	in_progress	33	27	2026-07-09 15:22:27.213935+00	2026-07-09 15:22:27.213935+00
28	Demo request 28	Demo request description 28	canceled	34	28	2026-07-09 14:22:27.213935+00	2026-07-09 14:22:27.213935+00
29	Demo request 29	Demo request description 29	new	35	25	2026-07-09 13:22:27.213935+00	2026-07-09 13:22:27.213935+00
30	Demo request 30	Demo request description 30	done	36	26	2026-07-09 12:22:27.213935+00	2026-07-09 12:22:27.213935+00
\.


--
-- Data for Name: salaries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.salaries (id, user_id, month, base_salary, bonus, penalty, total_amount, status, created_at, updated_at) FROM stdin;
1	7	2026-07	3050000.00	25000.00	5000.00	3070000.00	unpaid	2026-07-09 18:22:27.213935+00	2026-07-09 18:22:27.213935+00
2	8	2026-06	3100000.00	50000.00	10000.00	3140000.00	unpaid	2026-07-08 18:22:27.213935+00	2026-07-08 18:22:27.213935+00
3	9	2026-05	3150000.00	75000.00	15000.00	3210000.00	paid	2026-07-07 18:22:27.213935+00	2026-07-07 18:22:27.213935+00
4	10	2026-04	3200000.00	100000.00	20000.00	3280000.00	unpaid	2026-07-06 18:22:27.213935+00	2026-07-06 18:22:27.213935+00
5	11	2026-03	3250000.00	125000.00	25000.00	3350000.00	unpaid	2026-07-05 18:22:27.213935+00	2026-07-05 18:22:27.213935+00
6	12	2026-02	3300000.00	150000.00	30000.00	3420000.00	paid	2026-07-04 18:22:27.213935+00	2026-07-04 18:22:27.213935+00
7	13	2026-07	3350000.00	175000.00	35000.00	3490000.00	unpaid	2026-07-03 18:22:27.213935+00	2026-07-03 18:22:27.213935+00
8	14	2026-06	3400000.00	200000.00	40000.00	3560000.00	unpaid	2026-07-02 18:22:27.213935+00	2026-07-02 18:22:27.213935+00
9	15	2026-05	3450000.00	225000.00	45000.00	3630000.00	paid	2026-07-01 18:22:27.213935+00	2026-07-01 18:22:27.213935+00
10	16	2026-04	3500000.00	250000.00	50000.00	3700000.00	unpaid	2026-06-30 18:22:27.213935+00	2026-06-30 18:22:27.213935+00
11	17	2026-03	3550000.00	275000.00	55000.00	3770000.00	unpaid	2026-06-29 18:22:27.213935+00	2026-06-29 18:22:27.213935+00
12	18	2026-02	3600000.00	300000.00	60000.00	3840000.00	paid	2026-06-28 18:22:27.213935+00	2026-06-28 18:22:27.213935+00
13	19	2026-07	3650000.00	325000.00	65000.00	3910000.00	unpaid	2026-06-27 18:22:27.213935+00	2026-06-27 18:22:27.213935+00
14	20	2026-06	3700000.00	350000.00	70000.00	3980000.00	unpaid	2026-06-26 18:22:27.213935+00	2026-06-26 18:22:27.213935+00
15	21	2026-05	3750000.00	375000.00	75000.00	4050000.00	paid	2026-06-25 18:22:27.213935+00	2026-06-25 18:22:27.213935+00
16	22	2026-04	3800000.00	400000.00	80000.00	4120000.00	unpaid	2026-06-24 18:22:27.213935+00	2026-06-24 18:22:27.213935+00
17	23	2026-03	3850000.00	425000.00	85000.00	4190000.00	unpaid	2026-06-23 18:22:27.213935+00	2026-06-23 18:22:27.213935+00
18	24	2026-02	3900000.00	450000.00	90000.00	4260000.00	paid	2026-06-22 18:22:27.213935+00	2026-06-22 18:22:27.213935+00
19	25	2026-07	3950000.00	475000.00	95000.00	4330000.00	unpaid	2026-06-21 18:22:27.213935+00	2026-06-21 18:22:27.213935+00
20	26	2026-06	4000000.00	500000.00	100000.00	4400000.00	unpaid	2026-06-20 18:22:27.213935+00	2026-06-20 18:22:27.213935+00
21	27	2026-05	4050000.00	525000.00	105000.00	4470000.00	paid	2026-06-19 18:22:27.213935+00	2026-06-19 18:22:27.213935+00
22	28	2026-04	4100000.00	550000.00	110000.00	4540000.00	unpaid	2026-06-18 18:22:27.213935+00	2026-06-18 18:22:27.213935+00
23	29	2026-03	4150000.00	575000.00	115000.00	4610000.00	unpaid	2026-06-17 18:22:27.213935+00	2026-06-17 18:22:27.213935+00
24	30	2026-02	4200000.00	600000.00	120000.00	4680000.00	paid	2026-06-16 18:22:27.213935+00	2026-06-16 18:22:27.213935+00
25	31	2026-07	4250000.00	625000.00	125000.00	4750000.00	unpaid	2026-06-15 18:22:27.213935+00	2026-06-15 18:22:27.213935+00
26	32	2026-06	4300000.00	650000.00	130000.00	4820000.00	unpaid	2026-06-14 18:22:27.213935+00	2026-06-14 18:22:27.213935+00
27	33	2026-05	4350000.00	675000.00	135000.00	4890000.00	paid	2026-06-13 18:22:27.213935+00	2026-06-13 18:22:27.213935+00
28	34	2026-04	4400000.00	700000.00	140000.00	4960000.00	unpaid	2026-06-12 18:22:27.213935+00	2026-06-12 18:22:27.213935+00
29	35	2026-03	4450000.00	725000.00	145000.00	5030000.00	unpaid	2026-06-11 18:22:27.213935+00	2026-06-11 18:22:27.213935+00
30	36	2026-02	4500000.00	750000.00	150000.00	5100000.00	paid	2026-06-10 18:22:27.213935+00	2026-06-10 18:22:27.213935+00
\.


--
-- Data for Name: sale_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sale_items (id, sale_id, drug_id, drug_name, quantity, bonus, created_at, price, ball) FROM stdin;
1	1	1	Demo Drug 1	6	15000.00	2026-07-10 17:22:27.213935+00	10750.00	3
2	2	2	Demo Drug 2	7	30000.00	2026-07-10 16:22:27.213935+00	11500.00	4
3	3	3	Demo Drug 3	8	45000.00	2026-07-10 15:22:27.213935+00	12250.00	5
4	4	4	Demo Drug 4	9	60000.00	2026-07-10 14:22:27.213935+00	13000.00	6
5	5	5	Demo Drug 5	10	75000.00	2026-07-10 13:22:27.213935+00	13750.00	7
6	6	6	Demo Drug 6	11	90000.00	2026-07-10 12:22:27.213935+00	14500.00	8
7	7	7	Demo Drug 7	12	105000.00	2026-07-10 11:22:27.213935+00	15250.00	9
8	8	8	Demo Drug 8	13	120000.00	2026-07-10 10:22:27.213935+00	16000.00	10
9	9	9	Demo Drug 9	14	135000.00	2026-07-10 09:22:27.213935+00	16750.00	2
10	10	10	Demo Drug 10	15	150000.00	2026-07-10 08:22:27.213935+00	17500.00	3
11	11	11	Demo Drug 11	16	165000.00	2026-07-10 07:22:27.213935+00	18250.00	4
12	12	12	Demo Drug 12	17	180000.00	2026-07-10 06:22:27.213935+00	19000.00	5
13	13	13	Demo Drug 13	18	195000.00	2026-07-10 05:22:27.213935+00	19750.00	6
14	14	14	Demo Drug 14	19	210000.00	2026-07-10 04:22:27.213935+00	20500.00	7
15	15	15	Demo Drug 15	20	225000.00	2026-07-10 03:22:27.213935+00	21250.00	8
16	16	16	Demo Drug 16	21	240000.00	2026-07-10 02:22:27.213935+00	22000.00	9
17	17	17	Demo Drug 17	22	255000.00	2026-07-10 01:22:27.213935+00	22750.00	10
18	18	18	Demo Drug 18	23	270000.00	2026-07-10 00:22:27.213935+00	23500.00	2
19	19	19	Demo Drug 19	24	285000.00	2026-07-09 23:22:27.213935+00	24250.00	3
20	20	20	Demo Drug 20	25	300000.00	2026-07-09 22:22:27.213935+00	25000.00	4
21	21	21	Demo Drug 21	26	315000.00	2026-07-09 21:22:27.213935+00	25750.00	5
22	22	22	Demo Drug 22	27	330000.00	2026-07-09 20:22:27.213935+00	26500.00	6
23	23	23	Demo Drug 23	28	345000.00	2026-07-09 19:22:27.213935+00	27250.00	7
24	24	24	Demo Drug 24	29	360000.00	2026-07-09 18:22:27.213935+00	28000.00	8
25	25	25	Demo Drug 25	30	375000.00	2026-07-09 17:22:27.213935+00	28750.00	9
26	26	26	Demo Drug 26	31	390000.00	2026-07-09 16:22:27.213935+00	29500.00	10
27	27	27	Demo Drug 27	32	405000.00	2026-07-09 15:22:27.213935+00	30250.00	2
28	28	28	Demo Drug 28	33	420000.00	2026-07-09 14:22:27.213935+00	31000.00	3
29	29	29	Demo Drug 29	34	435000.00	2026-07-09 13:22:27.213935+00	31750.00	4
30	30	30	Demo Drug 30	35	450000.00	2026-07-09 12:22:27.213935+00	32500.00	5
\.


--
-- Data for Name: sales; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sales (id, rep_id, pharmacy_id, doctor_id, total_bonus, created_at, updated_at, total_price, total_ball) FROM stdin;
1	8	1	1	15000.00	2026-07-10 17:22:27.213935+00	2026-07-10 18:22:27.213935+00	125000.00	10
2	9	2	2	30000.00	2026-07-10 16:22:27.213935+00	2026-07-10 18:22:27.213935+00	250000.00	20
3	10	3	3	45000.00	2026-07-10 15:22:27.213935+00	2026-07-10 18:22:27.213935+00	375000.00	30
4	11	4	4	60000.00	2026-07-10 14:22:27.213935+00	2026-07-10 18:22:27.213935+00	500000.00	40
5	12	5	5	75000.00	2026-07-10 13:22:27.213935+00	2026-07-10 18:22:27.213935+00	625000.00	50
6	13	6	6	90000.00	2026-07-10 12:22:27.213935+00	2026-07-10 18:22:27.213935+00	750000.00	60
7	14	7	7	105000.00	2026-07-10 11:22:27.213935+00	2026-07-10 18:22:27.213935+00	875000.00	70
8	15	8	8	120000.00	2026-07-10 10:22:27.213935+00	2026-07-10 18:22:27.213935+00	1000000.00	80
9	16	9	9	135000.00	2026-07-10 09:22:27.213935+00	2026-07-10 18:22:27.213935+00	1125000.00	90
10	17	10	10	150000.00	2026-07-10 08:22:27.213935+00	2026-07-10 18:22:27.213935+00	1250000.00	100
11	18	11	11	165000.00	2026-07-10 07:22:27.213935+00	2026-07-10 18:22:27.213935+00	1375000.00	110
12	19	12	12	180000.00	2026-07-10 06:22:27.213935+00	2026-07-10 18:22:27.213935+00	1500000.00	120
13	20	13	13	195000.00	2026-07-10 05:22:27.213935+00	2026-07-10 18:22:27.213935+00	1625000.00	130
14	21	14	14	210000.00	2026-07-10 04:22:27.213935+00	2026-07-10 18:22:27.213935+00	1750000.00	140
15	22	15	15	225000.00	2026-07-10 03:22:27.213935+00	2026-07-10 18:22:27.213935+00	1875000.00	150
16	23	16	16	240000.00	2026-07-10 02:22:27.213935+00	2026-07-10 18:22:27.213935+00	2000000.00	160
17	24	17	17	255000.00	2026-07-10 01:22:27.213935+00	2026-07-10 18:22:27.213935+00	2125000.00	170
18	8	18	18	270000.00	2026-07-10 00:22:27.213935+00	2026-07-10 18:22:27.213935+00	2250000.00	180
19	9	19	19	285000.00	2026-07-09 23:22:27.213935+00	2026-07-10 18:22:27.213935+00	2375000.00	190
20	10	20	20	300000.00	2026-07-09 22:22:27.213935+00	2026-07-10 18:22:27.213935+00	2500000.00	200
21	11	21	21	315000.00	2026-07-09 21:22:27.213935+00	2026-07-10 18:22:27.213935+00	2625000.00	210
22	12	22	22	330000.00	2026-07-09 20:22:27.213935+00	2026-07-10 18:22:27.213935+00	2750000.00	220
23	13	23	23	345000.00	2026-07-09 19:22:27.213935+00	2026-07-10 18:22:27.213935+00	2875000.00	230
24	14	24	24	360000.00	2026-07-09 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	3000000.00	240
25	15	25	25	375000.00	2026-07-09 17:22:27.213935+00	2026-07-10 18:22:27.213935+00	3125000.00	250
26	16	26	26	390000.00	2026-07-09 16:22:27.213935+00	2026-07-10 18:22:27.213935+00	3250000.00	260
27	17	27	27	405000.00	2026-07-09 15:22:27.213935+00	2026-07-10 18:22:27.213935+00	3375000.00	270
28	18	28	28	420000.00	2026-07-09 14:22:27.213935+00	2026-07-10 18:22:27.213935+00	3500000.00	280
29	19	29	29	435000.00	2026-07-09 13:22:27.213935+00	2026-07-10 18:22:27.213935+00	3625000.00	290
30	20	30	30	450000.00	2026-07-09 12:22:27.213935+00	2026-07-10 18:22:27.213935+00	3750000.00	300
\.


--
-- Data for Name: scheduled_deletions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.scheduled_deletions (id, chat_id, message_id, delete_at, ball_tx_id) FROM stdin;
11	9900000011	880011	2026-07-11 05:22:27.213935+00	11
12	9900000012	880012	2026-07-11 06:22:27.213935+00	12
13	9900000013	880013	2026-07-11 07:22:27.213935+00	13
14	9900000014	880014	2026-07-11 08:22:27.213935+00	14
15	9900000015	880015	2026-07-11 09:22:27.213935+00	15
16	9900000016	880016	2026-07-11 10:22:27.213935+00	16
17	9900000017	880017	2026-07-11 11:22:27.213935+00	17
18	9900000018	880018	2026-07-11 12:22:27.213935+00	18
19	9900000019	880019	2026-07-11 13:22:27.213935+00	19
20	9900000020	880020	2026-07-11 14:22:27.213935+00	20
21	9900000021	880021	2026-07-11 15:22:27.213935+00	21
22	9900000022	880022	2026-07-11 16:22:27.213935+00	22
23	9900000023	880023	2026-07-11 17:22:27.213935+00	23
24	9900000024	880024	2026-07-11 18:22:27.213935+00	24
25	9900000025	880025	2026-07-11 19:22:27.213935+00	25
26	9900000026	880026	2026-07-11 20:22:27.213935+00	26
27	9900000027	880027	2026-07-11 21:22:27.213935+00	27
28	9900000028	880028	2026-07-11 22:22:27.213935+00	28
29	9900000029	880029	2026-07-11 23:22:27.213935+00	29
30	9900000030	880030	2026-07-12 00:22:27.213935+00	30
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, telegram_id, username, full_name, role, phone_number, is_active, invite_token, invite_used, invited_by_id, activated_at, created_at, updated_at, language, region_city, region_rayon, balance, region_id, ball_balance) FROM stdin;
1	89245245	\N	Owner 89245245	owner	\N	t	\N	t	\N	2026-06-26 17:43:51.924047+00	2026-06-26 17:43:51.922855+00	2026-06-26 17:43:51.922855+00	\N	\N	\N	0.00	\N	0
3	8115824785	\N	Abaybek2	manager	998500050113	t	snmyd3KthWsUkAHZXloPSDg4GIUtMdYi	t	2	2026-06-26 17:50:51.961828+00	2026-06-26 17:50:30.622052+00	2026-07-06 06:52:36.629839+00	uz_cyrl	\N	\N	0.00	\N	0
2	6087841574	\N	Owner 6087841574	owner	\N	t	\N	t	\N	2026-06-26 17:43:51.92633+00	2026-06-26 17:43:51.922855+00	2026-07-06 06:53:09.542748+00	ru	\N	\N	0.00	\N	0
4	5396535425	\N	Kimdur	operator	998907096136	t	yBLU_UtAZ3PqwGTdq0ag4_bYLNW1NPrp	t	2	2026-07-10 12:25:34.362099+00	2026-07-10 12:24:07.055635+00	2026-07-10 12:25:43.360708+00	uz_cyrl	\N	\N	0.00	\N	0
7	760710000001	demo_20260710182227218_user_1	Demo User 1	owner	+998900000001	t	demo_20260710182227218_invite_1	f	\N	2026-07-09 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Samarqand	Yunusobod	125000.00	31	100
8	760710000002	demo_20260710182227218_user_2	Demo User 2	manager	+998900000002	t	demo_20260710182227218_invite_2	f	\N	2026-07-08 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Buxoro	Chilonzor	250000.00	32	200
9	760710000003	demo_20260710182227218_user_3	Demo User 3	manager	+998900000003	t	demo_20260710182227218_invite_3	f	\N	2026-07-07 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Andijon	Sergeli	375000.00	33	300
10	760710000004	demo_20260710182227218_user_4	Demo User 4	manager	+998900000004	t	demo_20260710182227218_invite_4	f	\N	2026-07-06 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Fargona	Yashnobod	500000.00	34	400
11	760710000005	demo_20260710182227218_user_5	Demo User 5	manager	+998900000005	t	demo_20260710182227218_invite_5	f	\N	2026-07-05 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Namangan	Markaziy	625000.00	35	500
12	760710000006	demo_20260710182227218_user_6	Demo User 6	manager	+998900000006	t	demo_20260710182227218_invite_6	f	\N	2026-07-04 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Toshkent	Yunusobod	750000.00	36	600
13	760710000007	demo_20260710182227218_user_7	Demo User 7	manager	+998900000007	t	demo_20260710182227218_invite_7	f	\N	2026-07-03 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Samarqand	Chilonzor	875000.00	37	700
14	760710000008	demo_20260710182227218_user_8	Demo User 8	manager	+998900000008	t	demo_20260710182227218_invite_8	f	\N	2026-07-02 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Buxoro	Sergeli	1000000.00	38	800
15	760710000009	demo_20260710182227218_user_9	Demo User 9	manager	+998900000009	t	demo_20260710182227218_invite_9	f	\N	2026-07-01 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Andijon	Yashnobod	1125000.00	39	900
16	760710000010	demo_20260710182227218_user_10	Demo User 10	manager	+998900000010	t	demo_20260710182227218_invite_10	f	\N	2026-06-30 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Fargona	Markaziy	1250000.00	40	1000
17	760710000011	demo_20260710182227218_user_11	Demo User 11	manager	+998900000011	t	demo_20260710182227218_invite_11	f	\N	2026-06-29 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Namangan	Yunusobod	1375000.00	41	1100
18	760710000012	demo_20260710182227218_user_12	Demo User 12	manager	+998900000012	t	demo_20260710182227218_invite_12	f	\N	2026-06-28 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Toshkent	Chilonzor	1500000.00	42	1200
19	760710000013	demo_20260710182227218_user_13	Demo User 13	manager	+998900000013	t	demo_20260710182227218_invite_13	f	\N	2026-06-27 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Samarqand	Sergeli	1625000.00	43	1300
20	760710000014	demo_20260710182227218_user_14	Demo User 14	manager	+998900000014	t	demo_20260710182227218_invite_14	f	\N	2026-06-26 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Buxoro	Yashnobod	1750000.00	44	1400
21	760710000015	demo_20260710182227218_user_15	Demo User 15	manager	+998900000015	t	demo_20260710182227218_invite_15	f	\N	2026-06-25 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Andijon	Markaziy	1875000.00	45	1500
22	760710000016	demo_20260710182227218_user_16	Demo User 16	manager	+998900000016	t	demo_20260710182227218_invite_16	f	\N	2026-06-24 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Fargona	Yunusobod	2000000.00	46	1600
23	760710000017	demo_20260710182227218_user_17	Demo User 17	manager	+998900000017	t	demo_20260710182227218_invite_17	f	\N	2026-06-23 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Namangan	Chilonzor	2125000.00	47	1700
24	760710000018	demo_20260710182227218_user_18	Demo User 18	manager	+998900000018	t	demo_20260710182227218_invite_18	f	\N	2026-06-22 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Toshkent	Sergeli	2250000.00	48	1800
25	760710000019	demo_20260710182227218_user_19	Demo User 19	operator	+998900000019	t	demo_20260710182227218_invite_19	f	\N	2026-06-21 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Samarqand	Yashnobod	2375000.00	49	1900
26	760710000020	demo_20260710182227218_user_20	Demo User 20	operator	+998900000020	t	demo_20260710182227218_invite_20	f	\N	2026-06-20 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Buxoro	Markaziy	2500000.00	50	2000
27	760710000021	demo_20260710182227218_user_21	Demo User 21	operator	+998900000021	t	demo_20260710182227218_invite_21	f	\N	2026-06-19 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Andijon	Yunusobod	2625000.00	51	2100
28	760710000022	demo_20260710182227218_user_22	Demo User 22	operator	+998900000022	t	demo_20260710182227218_invite_22	f	\N	2026-06-18 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Fargona	Chilonzor	2750000.00	52	2200
29	760710000023	demo_20260710182227218_user_23	Demo User 23	doctor	+998900000023	t	demo_20260710182227218_invite_23	f	\N	2026-06-17 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Namangan	Sergeli	2875000.00	53	2300
30	760710000024	demo_20260710182227218_user_24	Demo User 24	doctor	+998900000024	t	demo_20260710182227218_invite_24	f	\N	2026-06-16 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Toshkent	Yashnobod	3000000.00	54	2400
31	760710000025	demo_20260710182227218_user_25	Demo User 25	doctor	+998900000025	t	demo_20260710182227218_invite_25	f	\N	2026-06-15 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Samarqand	Markaziy	3125000.00	55	2500
32	760710000026	demo_20260710182227218_user_26	Demo User 26	doctor	+998900000026	t	demo_20260710182227218_invite_26	f	\N	2026-06-14 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Buxoro	Yunusobod	3250000.00	56	2600
33	760710000027	demo_20260710182227218_user_27	Demo User 27	assistant	+998900000027	t	demo_20260710182227218_invite_27	f	\N	2026-06-13 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Andijon	Chilonzor	3375000.00	57	2700
34	760710000028	demo_20260710182227218_user_28	Demo User 28	assistant	+998900000028	t	demo_20260710182227218_invite_28	f	\N	2026-06-12 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Fargona	Sergeli	3500000.00	58	2800
35	760710000029	demo_20260710182227218_user_29	Demo User 29	assistant	+998900000029	t	demo_20260710182227218_invite_29	f	\N	2026-06-11 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	uz_cyrl	Namangan	Yashnobod	3625000.00	59	2900
36	760710000030	demo_20260710182227218_user_30	Demo User 30	assistant	+998900000030	t	demo_20260710182227218_invite_30	f	\N	2026-06-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	2026-07-10 18:22:27.213935+00	ru	Toshkent	Markaziy	3750000.00	60	3000
\.


--
-- Data for Name: visit_diaries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.visit_diaries (id, rep_id, latitude, longitude, note, created_at) FROM stdin;
1	8	41.2510000	69.2510000	Demo visit note 1	2026-07-10 17:22:27.213935+00
2	9	41.2520000	69.2520000	Demo visit note 2	2026-07-10 16:22:27.213935+00
3	10	41.2530000	69.2530000	Demo visit note 3	2026-07-10 15:22:27.213935+00
4	11	41.2540000	69.2540000	Demo visit note 4	2026-07-10 14:22:27.213935+00
5	12	41.2550000	69.2550000	Demo visit note 5	2026-07-10 13:22:27.213935+00
6	13	41.2560000	69.2560000	Demo visit note 6	2026-07-10 12:22:27.213935+00
7	14	41.2570000	69.2570000	Demo visit note 7	2026-07-10 11:22:27.213935+00
8	15	41.2580000	69.2580000	Demo visit note 8	2026-07-10 10:22:27.213935+00
9	16	41.2590000	69.2590000	Demo visit note 9	2026-07-10 09:22:27.213935+00
10	17	41.2600000	69.2600000	Demo visit note 10	2026-07-10 08:22:27.213935+00
11	18	41.2610000	69.2610000	Demo visit note 11	2026-07-10 07:22:27.213935+00
12	19	41.2620000	69.2620000	Demo visit note 12	2026-07-10 06:22:27.213935+00
13	20	41.2630000	69.2630000	Demo visit note 13	2026-07-10 05:22:27.213935+00
14	21	41.2640000	69.2640000	Demo visit note 14	2026-07-10 04:22:27.213935+00
15	22	41.2650000	69.2650000	Demo visit note 15	2026-07-10 03:22:27.213935+00
16	23	41.2660000	69.2660000	Demo visit note 16	2026-07-10 02:22:27.213935+00
17	24	41.2670000	69.2670000	Demo visit note 17	2026-07-10 01:22:27.213935+00
18	8	41.2680000	69.2680000	Demo visit note 18	2026-07-10 00:22:27.213935+00
19	9	41.2690000	69.2690000	Demo visit note 19	2026-07-09 23:22:27.213935+00
20	10	41.2700000	69.2700000	Demo visit note 20	2026-07-09 22:22:27.213935+00
21	11	41.2710000	69.2710000	Demo visit note 21	2026-07-09 21:22:27.213935+00
22	12	41.2720000	69.2720000	Demo visit note 22	2026-07-09 20:22:27.213935+00
23	13	41.2730000	69.2730000	Demo visit note 23	2026-07-09 19:22:27.213935+00
24	14	41.2740000	69.2740000	Demo visit note 24	2026-07-09 18:22:27.213935+00
25	15	41.2750000	69.2750000	Demo visit note 25	2026-07-09 17:22:27.213935+00
26	16	41.2760000	69.2760000	Demo visit note 26	2026-07-09 16:22:27.213935+00
27	17	41.2770000	69.2770000	Demo visit note 27	2026-07-09 15:22:27.213935+00
28	18	41.2780000	69.2780000	Demo visit note 28	2026-07-09 14:22:27.213935+00
29	19	41.2790000	69.2790000	Demo visit note 29	2026-07-09 13:22:27.213935+00
30	20	41.2800000	69.2800000	Demo visit note 30	2026-07-09 12:22:27.213935+00
\.


--
-- Data for Name: warehouse_request_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.warehouse_request_items (id, request_id, drug_id, drug_name, quantity) FROM stdin;
1	1	1	Demo Drug 1	11
2	2	2	Demo Drug 2	12
3	3	3	Demo Drug 3	13
4	4	4	Demo Drug 4	14
5	5	5	Demo Drug 5	15
6	6	6	Demo Drug 6	16
7	7	7	Demo Drug 7	17
8	8	8	Demo Drug 8	18
9	9	9	Demo Drug 9	19
10	10	10	Demo Drug 10	20
11	11	11	Demo Drug 11	21
12	12	12	Demo Drug 12	22
13	13	13	Demo Drug 13	23
14	14	14	Demo Drug 14	24
15	15	15	Demo Drug 15	25
16	16	16	Demo Drug 16	26
17	17	17	Demo Drug 17	27
18	18	18	Demo Drug 18	28
19	19	19	Demo Drug 19	29
20	20	20	Demo Drug 20	30
21	21	21	Demo Drug 21	31
22	22	22	Demo Drug 22	32
23	23	23	Demo Drug 23	33
24	24	24	Demo Drug 24	34
25	25	25	Demo Drug 25	35
26	26	26	Demo Drug 26	36
27	27	27	Demo Drug 27	37
28	28	28	Demo Drug 28	38
29	29	29	Demo Drug 29	39
30	30	30	Demo Drug 30	40
\.


--
-- Data for Name: warehouse_requests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.warehouse_requests (id, rep_id, pharmacy_id, contract_id, status, created_at, updated_at) FROM stdin;
1	8	1	1	new	2026-07-10 17:22:27.213935+00	2026-07-10 17:22:27.213935+00
2	9	2	2	approved	2026-07-10 16:22:27.213935+00	2026-07-10 16:22:27.213935+00
3	10	3	3	new	2026-07-10 15:22:27.213935+00	2026-07-10 15:22:27.213935+00
4	11	4	4	approved	2026-07-10 14:22:27.213935+00	2026-07-10 14:22:27.213935+00
5	12	5	5	rejected	2026-07-10 13:22:27.213935+00	2026-07-10 13:22:27.213935+00
6	13	6	6	approved	2026-07-10 12:22:27.213935+00	2026-07-10 12:22:27.213935+00
7	14	7	7	new	2026-07-10 11:22:27.213935+00	2026-07-10 11:22:27.213935+00
8	15	8	8	approved	2026-07-10 10:22:27.213935+00	2026-07-10 10:22:27.213935+00
9	16	9	9	new	2026-07-10 09:22:27.213935+00	2026-07-10 09:22:27.213935+00
10	17	10	10	rejected	2026-07-10 08:22:27.213935+00	2026-07-10 08:22:27.213935+00
11	18	11	11	new	2026-07-10 07:22:27.213935+00	2026-07-10 07:22:27.213935+00
12	19	12	12	approved	2026-07-10 06:22:27.213935+00	2026-07-10 06:22:27.213935+00
13	20	13	13	new	2026-07-10 05:22:27.213935+00	2026-07-10 05:22:27.213935+00
14	21	14	14	approved	2026-07-10 04:22:27.213935+00	2026-07-10 04:22:27.213935+00
15	22	15	15	rejected	2026-07-10 03:22:27.213935+00	2026-07-10 03:22:27.213935+00
16	23	16	16	approved	2026-07-10 02:22:27.213935+00	2026-07-10 02:22:27.213935+00
17	24	17	17	new	2026-07-10 01:22:27.213935+00	2026-07-10 01:22:27.213935+00
18	8	18	18	approved	2026-07-10 00:22:27.213935+00	2026-07-10 00:22:27.213935+00
19	9	19	19	new	2026-07-09 23:22:27.213935+00	2026-07-09 23:22:27.213935+00
20	10	20	20	rejected	2026-07-09 22:22:27.213935+00	2026-07-09 22:22:27.213935+00
21	11	21	21	new	2026-07-09 21:22:27.213935+00	2026-07-09 21:22:27.213935+00
22	12	22	22	approved	2026-07-09 20:22:27.213935+00	2026-07-09 20:22:27.213935+00
23	13	23	23	new	2026-07-09 19:22:27.213935+00	2026-07-09 19:22:27.213935+00
24	14	24	24	approved	2026-07-09 18:22:27.213935+00	2026-07-09 18:22:27.213935+00
25	15	25	25	rejected	2026-07-09 17:22:27.213935+00	2026-07-09 17:22:27.213935+00
26	16	26	26	approved	2026-07-09 16:22:27.213935+00	2026-07-09 16:22:27.213935+00
27	17	27	27	new	2026-07-09 15:22:27.213935+00	2026-07-09 15:22:27.213935+00
28	18	28	28	approved	2026-07-09 14:22:27.213935+00	2026-07-09 14:22:27.213935+00
29	19	29	29	new	2026-07-09 13:22:27.213935+00	2026-07-09 13:22:27.213935+00
30	20	30	30	rejected	2026-07-09 12:22:27.213935+00	2026-07-09 12:22:27.213935+00
\.


--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 35, true);


--
-- Name: ball_transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.ball_transactions_id_seq', 30, true);


--
-- Name: contracts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.contracts_id_seq', 30, true);


--
-- Name: daily_reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.daily_reports_id_seq', 30, true);


--
-- Name: doctors_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.doctors_id_seq', 30, true);


--
-- Name: drug_materials_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.drug_materials_id_seq', 30, true);


--
-- Name: drugs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.drugs_id_seq', 30, true);


--
-- Name: finance_operations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.finance_operations_id_seq', 30, true);


--
-- Name: pharmacies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.pharmacies_id_seq', 30, true);


--
-- Name: regions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.regions_id_seq', 60, true);


--
-- Name: rep_payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.rep_payments_id_seq', 30, true);


--
-- Name: requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.requests_id_seq', 30, true);


--
-- Name: salaries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.salaries_id_seq', 30, true);


--
-- Name: sale_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.sale_items_id_seq', 30, true);


--
-- Name: sales_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.sales_id_seq', 30, true);


--
-- Name: scheduled_deletions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.scheduled_deletions_id_seq', 30, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_id_seq', 36, true);


--
-- Name: visit_diaries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.visit_diaries_id_seq', 30, true);


--
-- Name: warehouse_request_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.warehouse_request_items_id_seq', 30, true);


--
-- Name: warehouse_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.warehouse_requests_id_seq', 30, true);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: ball_transactions ball_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ball_transactions
    ADD CONSTRAINT ball_transactions_pkey PRIMARY KEY (id);


--
-- Name: contracts contracts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT contracts_pkey PRIMARY KEY (id);


--
-- Name: daily_reports daily_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_reports
    ADD CONSTRAINT daily_reports_pkey PRIMARY KEY (id);


--
-- Name: doctors doctors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_pkey PRIMARY KEY (id);


--
-- Name: drug_materials drug_materials_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drug_materials
    ADD CONSTRAINT drug_materials_pkey PRIMARY KEY (id);


--
-- Name: drugs drugs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drugs
    ADD CONSTRAINT drugs_pkey PRIMARY KEY (id);


--
-- Name: finance_operations finance_operations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.finance_operations
    ADD CONSTRAINT finance_operations_pkey PRIMARY KEY (id);


--
-- Name: pharmacies pharmacies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pharmacies
    ADD CONSTRAINT pharmacies_pkey PRIMARY KEY (id);


--
-- Name: regions regions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regions
    ADD CONSTRAINT regions_pkey PRIMARY KEY (id);


--
-- Name: rep_payments rep_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rep_payments
    ADD CONSTRAINT rep_payments_pkey PRIMARY KEY (id);


--
-- Name: requests requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_pkey PRIMARY KEY (id);


--
-- Name: salaries salaries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.salaries
    ADD CONSTRAINT salaries_pkey PRIMARY KEY (id);


--
-- Name: sale_items sale_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sale_items
    ADD CONSTRAINT sale_items_pkey PRIMARY KEY (id);


--
-- Name: sales sales_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales
    ADD CONSTRAINT sales_pkey PRIMARY KEY (id);


--
-- Name: scheduled_deletions scheduled_deletions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scheduled_deletions
    ADD CONSTRAINT scheduled_deletions_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: visit_diaries visit_diaries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.visit_diaries
    ADD CONSTRAINT visit_diaries_pkey PRIMARY KEY (id);


--
-- Name: warehouse_request_items warehouse_request_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouse_request_items
    ADD CONSTRAINT warehouse_request_items_pkey PRIMARY KEY (id);


--
-- Name: warehouse_requests warehouse_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouse_requests
    ADD CONSTRAINT warehouse_requests_pkey PRIMARY KEY (id);


--
-- Name: ix_audit_logs_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_action ON public.audit_logs USING btree (action);


--
-- Name: ix_audit_logs_actor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_actor_id ON public.audit_logs USING btree (actor_id);


--
-- Name: ix_ball_transactions_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ball_transactions_created_at ON public.ball_transactions USING btree (created_at);


--
-- Name: ix_ball_transactions_from_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ball_transactions_from_user_id ON public.ball_transactions USING btree (from_user_id);


--
-- Name: ix_ball_transactions_kind; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ball_transactions_kind ON public.ball_transactions USING btree (kind);


--
-- Name: ix_ball_transactions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ball_transactions_status ON public.ball_transactions USING btree (status);


--
-- Name: ix_ball_transactions_to_doctor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ball_transactions_to_doctor_id ON public.ball_transactions USING btree (to_doctor_id);


--
-- Name: ix_ball_transactions_to_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ball_transactions_to_user_id ON public.ball_transactions USING btree (to_user_id);


--
-- Name: ix_contracts_pharmacy_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contracts_pharmacy_id ON public.contracts USING btree (pharmacy_id);


--
-- Name: ix_daily_reports_author_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_daily_reports_author_id ON public.daily_reports USING btree (author_id);


--
-- Name: ix_daily_reports_target_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_daily_reports_target_type ON public.daily_reports USING btree (target_type);


--
-- Name: ix_doctors_full_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_doctors_full_name ON public.doctors USING btree (full_name);


--
-- Name: ix_drug_materials_title; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_drug_materials_title ON public.drug_materials USING btree (title);


--
-- Name: ix_drugs_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_drugs_name ON public.drugs USING btree (name);


--
-- Name: ix_finance_operations_created_by_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_finance_operations_created_by_id ON public.finance_operations USING btree (created_by_id);


--
-- Name: ix_finance_operations_operation_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_finance_operations_operation_type ON public.finance_operations USING btree (operation_type);


--
-- Name: ix_pharmacies_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pharmacies_name ON public.pharmacies USING btree (name);


--
-- Name: ix_regions_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_regions_name ON public.regions USING btree (name);


--
-- Name: ix_rep_payments_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rep_payments_created_at ON public.rep_payments USING btree (created_at);


--
-- Name: ix_rep_payments_kind; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rep_payments_kind ON public.rep_payments USING btree (kind);


--
-- Name: ix_rep_payments_rep_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rep_payments_rep_id ON public.rep_payments USING btree (rep_id);


--
-- Name: ix_requests_created_by_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_requests_created_by_id ON public.requests USING btree (created_by_id);


--
-- Name: ix_requests_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_requests_status ON public.requests USING btree (status);


--
-- Name: ix_salaries_month; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_salaries_month ON public.salaries USING btree (month);


--
-- Name: ix_salaries_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_salaries_user_id ON public.salaries USING btree (user_id);


--
-- Name: ix_sale_items_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sale_items_created_at ON public.sale_items USING btree (created_at);


--
-- Name: ix_sale_items_drug_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sale_items_drug_id ON public.sale_items USING btree (drug_id);


--
-- Name: ix_sale_items_sale_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sale_items_sale_id ON public.sale_items USING btree (sale_id);


--
-- Name: ix_sales_rep_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sales_rep_id ON public.sales USING btree (rep_id);


--
-- Name: ix_scheduled_deletions_delete_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scheduled_deletions_delete_at ON public.scheduled_deletions USING btree (delete_at);


--
-- Name: ix_users_invite_token; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_invite_token ON public.users USING btree (invite_token);


--
-- Name: ix_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_role ON public.users USING btree (role);


--
-- Name: ix_users_telegram_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_telegram_id ON public.users USING btree (telegram_id);


--
-- Name: ix_visit_diaries_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_visit_diaries_created_at ON public.visit_diaries USING btree (created_at);


--
-- Name: ix_visit_diaries_rep_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_visit_diaries_rep_id ON public.visit_diaries USING btree (rep_id);


--
-- Name: ix_warehouse_request_items_request_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_warehouse_request_items_request_id ON public.warehouse_request_items USING btree (request_id);


--
-- Name: ix_warehouse_requests_rep_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_warehouse_requests_rep_id ON public.warehouse_requests USING btree (rep_id);


--
-- Name: ix_warehouse_requests_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_warehouse_requests_status ON public.warehouse_requests USING btree (status);


--
-- Name: audit_logs audit_logs_actor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_actor_id_fkey FOREIGN KEY (actor_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: ball_transactions ball_transactions_from_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ball_transactions
    ADD CONSTRAINT ball_transactions_from_user_id_fkey FOREIGN KEY (from_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: ball_transactions ball_transactions_sale_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ball_transactions
    ADD CONSTRAINT ball_transactions_sale_id_fkey FOREIGN KEY (sale_id) REFERENCES public.sales(id) ON DELETE SET NULL;


--
-- Name: ball_transactions ball_transactions_to_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ball_transactions
    ADD CONSTRAINT ball_transactions_to_doctor_id_fkey FOREIGN KEY (to_doctor_id) REFERENCES public.doctors(id) ON DELETE SET NULL;


--
-- Name: ball_transactions ball_transactions_to_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ball_transactions
    ADD CONSTRAINT ball_transactions_to_user_id_fkey FOREIGN KEY (to_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: contracts contracts_pharmacy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT contracts_pharmacy_id_fkey FOREIGN KEY (pharmacy_id) REFERENCES public.pharmacies(id) ON DELETE CASCADE;


--
-- Name: contracts contracts_requested_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT contracts_requested_by_id_fkey FOREIGN KEY (requested_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: daily_reports daily_reports_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.daily_reports
    ADD CONSTRAINT daily_reports_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: doctors doctors_manager_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.doctors
    ADD CONSTRAINT doctors_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: drug_materials drug_materials_uploaded_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drug_materials
    ADD CONSTRAINT drug_materials_uploaded_by_id_fkey FOREIGN KEY (uploaded_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: finance_operations finance_operations_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.finance_operations
    ADD CONSTRAINT finance_operations_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: pharmacies pharmacies_manager_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pharmacies
    ADD CONSTRAINT pharmacies_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: rep_payments rep_payments_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rep_payments
    ADD CONSTRAINT rep_payments_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id) ON DELETE SET NULL;


--
-- Name: rep_payments rep_payments_rep_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rep_payments
    ADD CONSTRAINT rep_payments_rep_id_fkey FOREIGN KEY (rep_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: requests requests_assigned_to_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_assigned_to_id_fkey FOREIGN KEY (assigned_to_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: requests requests_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: salaries salaries_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.salaries
    ADD CONSTRAINT salaries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: sale_items sale_items_drug_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sale_items
    ADD CONSTRAINT sale_items_drug_id_fkey FOREIGN KEY (drug_id) REFERENCES public.drugs(id) ON DELETE SET NULL;


--
-- Name: sale_items sale_items_sale_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sale_items
    ADD CONSTRAINT sale_items_sale_id_fkey FOREIGN KEY (sale_id) REFERENCES public.sales(id) ON DELETE CASCADE;


--
-- Name: sales sales_doctor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales
    ADD CONSTRAINT sales_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id) ON DELETE SET NULL;


--
-- Name: sales sales_pharmacy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales
    ADD CONSTRAINT sales_pharmacy_id_fkey FOREIGN KEY (pharmacy_id) REFERENCES public.pharmacies(id) ON DELETE SET NULL;


--
-- Name: sales sales_rep_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sales
    ADD CONSTRAINT sales_rep_id_fkey FOREIGN KEY (rep_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: scheduled_deletions scheduled_deletions_ball_tx_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scheduled_deletions
    ADD CONSTRAINT scheduled_deletions_ball_tx_id_fkey FOREIGN KEY (ball_tx_id) REFERENCES public.ball_transactions(id) ON DELETE SET NULL;


--
-- Name: users users_invited_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_invited_by_id_fkey FOREIGN KEY (invited_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: visit_diaries visit_diaries_rep_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.visit_diaries
    ADD CONSTRAINT visit_diaries_rep_id_fkey FOREIGN KEY (rep_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: warehouse_request_items warehouse_request_items_drug_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouse_request_items
    ADD CONSTRAINT warehouse_request_items_drug_id_fkey FOREIGN KEY (drug_id) REFERENCES public.drugs(id) ON DELETE SET NULL;


--
-- Name: warehouse_request_items warehouse_request_items_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouse_request_items
    ADD CONSTRAINT warehouse_request_items_request_id_fkey FOREIGN KEY (request_id) REFERENCES public.warehouse_requests(id) ON DELETE CASCADE;


--
-- Name: warehouse_requests warehouse_requests_contract_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouse_requests
    ADD CONSTRAINT warehouse_requests_contract_id_fkey FOREIGN KEY (contract_id) REFERENCES public.contracts(id) ON DELETE SET NULL;


--
-- Name: warehouse_requests warehouse_requests_pharmacy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouse_requests
    ADD CONSTRAINT warehouse_requests_pharmacy_id_fkey FOREIGN KEY (pharmacy_id) REFERENCES public.pharmacies(id) ON DELETE SET NULL;


--
-- Name: warehouse_requests warehouse_requests_rep_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.warehouse_requests
    ADD CONSTRAINT warehouse_requests_rep_id_fkey FOREIGN KEY (rep_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--


