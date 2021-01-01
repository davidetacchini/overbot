--
-- PostgreSQL database dump
--

-- Dumped from database version 13.1
-- Dumped by pg_dump version 13.1

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
    id integer DEFAULT 1 NOT NULL,
    total integer DEFAULT 0 NOT NULL,
    CONSTRAINT command_chk CHECK ((id = 1))
);


ALTER TABLE public.command OWNER TO davide;

--
-- Name: member; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.member (
    id bigint NOT NULL,
    commands_run integer DEFAULT 0 NOT NULL,
    main_profile integer
);


ALTER TABLE public.member OWNER TO davide;

--
-- Name: news; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.news (
    id integer DEFAULT 1 NOT NULL,
    news_id integer DEFAULT 0 NOT NULL,
    CONSTRAINT news_chk CHECK ((id = 1))
);


ALTER TABLE public.news OWNER TO davide;

--
-- Name: nickname; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.nickname (
    id bigint NOT NULL,
    server_id bigint NOT NULL,
    profile_id integer NOT NULL
);


ALTER TABLE public.nickname OWNER TO davide;

--
-- Name: profile; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.profile (
    id integer NOT NULL,
    platform character varying(15) NOT NULL,
    username character varying(100) NOT NULL,
    member_id bigint NOT NULL
);


ALTER TABLE public.profile OWNER TO davide;

--
-- Name: profile_id_seq1; Type: SEQUENCE; Schema: public; Owner: davide
--

CREATE SEQUENCE public.profile_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profile_id_seq1 OWNER TO davide;

--
-- Name: profile_id_seq1; Type: SEQUENCE OWNED BY; Schema: public; Owner: davide
--

ALTER SEQUENCE public.profile_id_seq1 OWNED BY public.profile.id;


--
-- Name: rating; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.rating (
    id integer NOT NULL,
    tank smallint,
    damage smallint,
    support smallint,
    date date DEFAULT CURRENT_DATE,
    profile_id integer
);


ALTER TABLE public.rating OWNER TO davide;

--
-- Name: rating_id_seq; Type: SEQUENCE; Schema: public; Owner: davide
--

CREATE SEQUENCE public.rating_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.rating_id_seq OWNER TO davide;

--
-- Name: rating_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: davide
--

ALTER SEQUENCE public.rating_id_seq OWNED BY public.rating.id;


--
-- Name: server; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.server (
    id bigint NOT NULL,
    prefix character varying(5) NOT NULL,
    commands_run integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.server OWNER TO davide;

--
-- Name: trivia; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.trivia (
    id bigint NOT NULL,
    won integer DEFAULT 0 NOT NULL,
    lost integer DEFAULT 0 NOT NULL,
    started integer DEFAULT 0 NOT NULL,
    contribs integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.trivia OWNER TO davide;

--
-- Name: profile id; Type: DEFAULT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.profile ALTER COLUMN id SET DEFAULT nextval('public.profile_id_seq1'::regclass);


--
-- Name: rating id; Type: DEFAULT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.rating ALTER COLUMN id SET DEFAULT nextval('public.rating_id_seq'::regclass);


--
-- Name: command command_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.command
    ADD CONSTRAINT command_pkey PRIMARY KEY (id);


--
-- Name: command command_unq; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.command
    ADD CONSTRAINT command_unq UNIQUE (id);


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
-- Name: news news_unq; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.news
    ADD CONSTRAINT news_unq UNIQUE (id);


--
-- Name: nickname nickname_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.nickname
    ADD CONSTRAINT nickname_pkey PRIMARY KEY (id);


--
-- Name: profile profile_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.profile
    ADD CONSTRAINT profile_pkey PRIMARY KEY (id);


--
-- Name: rating rating_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.rating
    ADD CONSTRAINT rating_pkey PRIMARY KEY (id);


--
-- Name: server server_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.server
    ADD CONSTRAINT server_pkey PRIMARY KEY (id);


--
-- Name: trivia trivia_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.trivia
    ADD CONSTRAINT trivia_pkey PRIMARY KEY (id);


--
-- Name: member member_fkey; Type: FK CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.member
    ADD CONSTRAINT member_fkey FOREIGN KEY (main_profile) REFERENCES public.profile(id) ON UPDATE SET NULL ON DELETE SET NULL NOT VALID;


--
-- Name: profile profile_fkey; Type: FK CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.profile
    ADD CONSTRAINT profile_fkey FOREIGN KEY (member_id) REFERENCES public.member(id) ON UPDATE CASCADE ON DELETE CASCADE NOT VALID;


--
-- Name: nickname profile_fkey; Type: FK CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.nickname
    ADD CONSTRAINT profile_fkey FOREIGN KEY (profile_id) REFERENCES public.profile(id) ON UPDATE CASCADE ON DELETE CASCADE NOT VALID;


--
-- Name: rating rating_fkey; Type: FK CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.rating
    ADD CONSTRAINT rating_fkey FOREIGN KEY (profile_id) REFERENCES public.profile(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: nickname server_fkey; Type: FK CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.nickname
    ADD CONSTRAINT server_fkey FOREIGN KEY (server_id) REFERENCES public.server(id) ON UPDATE CASCADE ON DELETE CASCADE NOT VALID;


--
-- PostgreSQL database dump complete
--

