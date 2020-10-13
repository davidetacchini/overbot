--
-- PostgreSQL database dump
--

-- Dumped from database version 12.2
-- Dumped by pg_dump version 12.2

-- Started on 2020-05-13 16:41:30 CEST

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
-- TOC entry 204 (class 1259 OID 16393)
-- Name: command; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.command (
    id integer NOT NULL,
    name text NOT NULL,
    used integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.command OWNER TO davide;

--
-- TOC entry 203 (class 1259 OID 16391)
-- Name: command_id_seq; Type: SEQUENCE; Schema: public; Owner: davide
--

CREATE SEQUENCE public.command_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.command_id_seq OWNER TO davide;

--
-- TOC entry 3221 (class 0 OID 0)
-- Dependencies: 203
-- Name: command_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: davide
--

ALTER SEQUENCE public.command_id_seq OWNED BY public.command.id;


--
-- TOC entry 207 (class 1259 OID 24584)
-- Name: news; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.news (
    id smallint NOT NULL,
    news_id bigint DEFAULT 0 NOT NULL
);


ALTER TABLE public.news OWNER TO davide;

--
-- TOC entry 206 (class 1259 OID 24582)
-- Name: news_id_seq; Type: SEQUENCE; Schema: public; Owner: davide
--

CREATE SEQUENCE public.news_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.news_id_seq OWNER TO davide;

--
-- TOC entry 3222 (class 0 OID 0)
-- Dependencies: 206
-- Name: news_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: davide
--

ALTER SEQUENCE public.news_id_seq OWNED BY public.news.id;


--
-- TOC entry 202 (class 1259 OID 16386)
-- Name: profile; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.profile (
    id bigint NOT NULL,
    platform character varying(15) NOT NULL,
    name character varying(100) NOT NULL,
    track boolean DEFAULT false NOT NULL
);


ALTER TABLE public.profile OWNER TO davide;

--
-- TOC entry 205 (class 1259 OID 16403)
-- Name: server; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.server (
    id bigint NOT NULL,
    prefix character varying(5) NOT NULL,
    news_channel bigint DEFAULT 0 NOT NULL,
    commands_runned integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.server OWNER TO davide;

--
-- TOC entry 3076 (class 2604 OID 16396)
-- Name: command id; Type: DEFAULT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.command ALTER COLUMN id SET DEFAULT nextval('public.command_id_seq'::regclass);


--
-- TOC entry 3081 (class 2604 OID 24592)
-- Name: news id; Type: DEFAULT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.news ALTER COLUMN id SET DEFAULT nextval('public.news_id_seq'::regclass);


--
-- TOC entry 3085 (class 2606 OID 16402)
-- Name: command command_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.command
    ADD CONSTRAINT command_pkey PRIMARY KEY (id);


--
-- TOC entry 3089 (class 2606 OID 24594)
-- Name: news news_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.news
    ADD CONSTRAINT news_pkey PRIMARY KEY (id);


--
-- TOC entry 3083 (class 2606 OID 16390)
-- Name: profile profile_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.profile
    ADD CONSTRAINT profile_pkey PRIMARY KEY (id);


--
-- TOC entry 3087 (class 2606 OID 16409)
-- Name: server server_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.server
    ADD CONSTRAINT server_pkey PRIMARY KEY (id);


-- Completed on 2020-05-13 16:41:31 CEST

--
-- PostgreSQL database dump complete
--

