--
-- PostgreSQL database dump
--

-- Dumped from database version 13.0
-- Dumped by pg_dump version 13.0

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
-- Name: command; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.command (
    id smallint NOT NULL,
    total integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.command OWNER TO davide;

--
-- Name: command_id_seq; Type: SEQUENCE; Schema: public; Owner: davide
--

CREATE SEQUENCE public.command_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.command_id_seq OWNER TO davide;

--
-- Name: command_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: davide
--

ALTER SEQUENCE public.command_id_seq OWNED BY public.command.id;


--
-- Name: member; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.member (
    id bigint NOT NULL,
    news_channel bigint DEFAULT 0 NOT NULL,
    commands_runned integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.member OWNER TO davide;

--
-- Name: news; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.news (
    id smallint NOT NULL,
    news_id bigint DEFAULT 0 NOT NULL
);


ALTER TABLE public.news OWNER TO davide;

--
-- Name: profile; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.profile (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    platform character varying(15) NOT NULL,
    name character varying(100) NOT NULL
);


ALTER TABLE public.profile OWNER TO davide;

--
-- Name: profile_id_seq; Type: SEQUENCE; Schema: public; Owner: davide
--

CREATE SEQUENCE public.profile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profile_id_seq OWNER TO davide;

--
-- Name: profile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: davide
--

ALTER SEQUENCE public.profile_id_seq OWNED BY public.profile.id;


--
-- Name: server; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.server (
    id bigint NOT NULL,
    prefix character varying(5) NOT NULL,
    commands_runned integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.server OWNER TO davide;

--
-- Name: command id; Type: DEFAULT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.command ALTER COLUMN id SET DEFAULT nextval('public.command_id_seq'::regclass);


--
-- Name: profile id; Type: DEFAULT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.profile ALTER COLUMN id SET DEFAULT nextval('public.profile_id_seq'::regclass);


--
-- Name: command command_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.command
    ADD CONSTRAINT command_pkey PRIMARY KEY (id);


--
-- Name: member member_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.member
    ADD CONSTRAINT member_pkey PRIMARY KEY (id);


--
-- Name: news news_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.news
    ADD CONSTRAINT news_pkey PRIMARY KEY (id);


--
-- Name: profile profile_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.profile
    ADD CONSTRAINT profile_pkey PRIMARY KEY (id);


--
-- Name: server server_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.server
    ADD CONSTRAINT server_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

