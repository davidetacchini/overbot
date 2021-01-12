# taken from https://github.com/Gelbpunkt/IdleRPG/blob/current/utils/i18n.py

import ast
import gettext
import inspect
import os.path
import contextvars
from os import getcwd
from glob import glob
from typing import Any, Callable

BASE_DIR = getcwd()
default_locale = "en_US"
locale_dir = "locales"

locales: frozenset[str] = frozenset(
    map(
        os.path.basename,
        filter(os.path.isdir, glob(os.path.join(BASE_DIR, locale_dir, "*"))),
    )
)

gettext_translations = {
    locale: gettext.translation(
        "main", languages=(locale,), localedir=os.path.join(BASE_DIR, locale_dir)
    )
    for locale in locales
}

gettext_translations["en_US"] = gettext.NullTranslations()
locales = locales | {"en_US"}


def use_current_gettext(*args: Any, **kwargs: Any) -> str:
    if not gettext_translations:
        return gettext.gettext(*args, **kwargs)

    locale = current_locale.get()
    return gettext_translations.get(
        locale, gettext_translations[default_locale]
    ).gettext(*args, **kwargs)


def i18n_docstring(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
    src = inspect.getsource(func)
    try:
        parsed_tree = ast.parse(src)
    except IndentationError:
        parsed_tree = ast.parse("class Foo:\n" + src)
        assert isinstance(parsed_tree.body[0], ast.ClassDef)
        function_body: ast.ClassDef = parsed_tree.body[0]
        assert isinstance(function_body.body[0], ast.AsyncFunctionDef)
        tree: ast.AsyncFunctionDef = function_body.body[0]
    else:
        assert isinstance(parsed_tree.body[0], ast.AsyncFunctionDef)
        tree = parsed_tree.body[0]

    if not isinstance(tree.body[0], ast.Expr):
        return func

    gettext_call = tree.body[0].value
    if not isinstance(gettext_call, ast.Call):
        return func

    if not isinstance(gettext_call.func, ast.Name) or gettext_call.func.id != "_":
        return func

    assert len(gettext_call.args) == 1
    assert isinstance(gettext_call.args[0], ast.Str)

    func.__doc__ = gettext_call.args[0].s
    return func


current_locale: contextvars.ContextVar[str] = contextvars.ContextVar("i18n")
_ = use_current_gettext
locale = i18n_docstring

current_locale.set(default_locale)
