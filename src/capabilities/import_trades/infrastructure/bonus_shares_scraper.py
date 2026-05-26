"""Scrape bonus share data from StatusInvest."""

from __future__ import annotations

import warnings

import pandas as pd
import requests
from stpstone.utils.calendars.calendar_br import DatesBRAnbima
from stpstone.utils.parsers.dicts import HandlingDicts
from stpstone.utils.parsers.html import HtmlHandler


warnings.filterwarnings("ignore", message="Unverified HTTPS request")

_cls_dates = DatesBRAnbima()
_cls_html = HtmlHandler()

_DEFAULT_XPATH = (
    "//div[@class='card p-2 p-xs-3']"
    "[.//h3[@class][contains(translate(., "
    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'bonifica')]]"
    "//strong[@class='d-block lh-3 fs-3 fw-700']"
)
_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "user-agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    ),
}
_DATE_COLS = ["data_anuncio", "data_com", "data_ex", "data_incorporacao"]
_LIST_COLS = [*_DATE_COLS, "valor_base", "proporcao"]


def fetch_bonus_shares(str_ticker: str, str_xpath: str = _DEFAULT_XPATH) -> pd.DataFrame:
    """Fetch bonus share history for a ticker from StatusInvest.

    Parameters
    ----------
    str_ticker : str
        B3 ticker symbol (e.g. ``"PETR4"``).
    str_xpath : str
        XPath to extract bonus share rows from the StatusInvest page.

    Returns
    -------
    pd.DataFrame
        Columns: data_anuncio, data_com, data_ex, data_incorporacao,
        valor_base (float), proporcao (float), TICKER, ano_ref.
    """
    str_url = f"https://statusinvest.com.br/acoes/{str_ticker.lower()}"
    cls_resp = requests.get(str_url, headers=_HEADERS, verify=False, timeout=30)  # noqa: S501
    cls_root = _cls_html.lxml_parser(cls_resp)
    list_spans = _cls_html.lxml_xpath(cls_root, str_xpath)
    list_text = [
        _cls_html.lxml_xpath(el_, "./text()")[0].strip().replace("\n", " ")
        for el_ in list_spans
    ]
    list_text = [x for x in list_text if len(x) > 0]
    list_ser = HandlingDicts().pair_headers_with_data(_LIST_COLS, list_text)
    df_ = pd.DataFrame(list_ser)
    df_["TICKER"] = str_ticker

    df_["valor_base"] = (
        df_["valor_base"]
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )
    df_["proporcao"] = (
        df_["proporcao"]
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
        / 100.0
    )
    for str_col in _DATE_COLS:
        df_[str_col] = pd.to_datetime(df_[str_col], format="%d/%m/%Y", errors="coerce")

    df_["ano_ref"] = [_cls_dates.year_number(d) for d in df_["data_ex"]]
    return df_
