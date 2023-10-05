--
-- PostgreSQL database dump
--

-- Dumped from database version 15.3 (Homebrew)
-- Dumped by pg_dump version 15.3 (Homebrew)

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
    id integer NOT NULL,
    name text NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    author_id bigint NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.command OWNER TO davide;

--
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
-- Name: command_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: davide
--

ALTER SEQUENCE public.command_id_seq OWNED BY public.command.id;


--
-- Name: member; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.member (
    id bigint NOT NULL,
    embed_color integer,
    premium boolean DEFAULT false NOT NULL
);


ALTER TABLE public.member OWNER TO davide;

--
-- Name: newsboard; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.newsboard (
    id bigint NOT NULL,
    server_id bigint NOT NULL,
    member_id bigint NOT NULL
);


ALTER TABLE public.newsboard OWNER TO davide;

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
    battletag character varying(100) NOT NULL,
    member_id bigint NOT NULL
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
    premium boolean DEFAULT false NOT NULL
);


ALTER TABLE public.server OWNER TO davide;

--
-- Name: trivia; Type: TABLE; Schema: public; Owner: davide
--

CREATE TABLE public.trivia (
    id bigint NOT NULL,
    won integer DEFAULT 0 NOT NULL,
    lost integer DEFAULT 0 NOT NULL,
    started integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.trivia OWNER TO davide;

--
-- Name: command id; Type: DEFAULT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.command ALTER COLUMN id SET DEFAULT nextval('public.command_id_seq'::regclass);


--
-- Name: profile id; Type: DEFAULT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.profile ALTER COLUMN id SET DEFAULT nextval('public.profile_id_seq'::regclass);


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
-- Name: member member_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.member
    ADD CONSTRAINT member_pkey PRIMARY KEY (id);


--
-- Name: newsboard newsboard_pkey; Type: CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.newsboard
    ADD CONSTRAINT newsboard_pkey PRIMARY KEY (id);


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
-- Name: newsboard member_fkey; Type: FK CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.newsboard
    ADD CONSTRAINT member_fkey FOREIGN KEY (member_id) REFERENCES public.member(id) ON UPDATE CASCADE ON DELETE CASCADE;


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
-- Name: newsboard server_fkey; Type: FK CONSTRAINT; Schema: public; Owner: davide
--

ALTER TABLE ONLY public.newsboard
    ADD CONSTRAINT server_fkey FOREIGN KEY (server_id) REFERENCES public.server(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--
