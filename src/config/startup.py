"""Startup: logger, MS Teams webhook, and runtime constants."""

from __future__ import annotations

from getpass import getuser
import os
from pathlib import Path
from socket import gethostname

from dotenv import load_dotenv
from stpstone.utils.calendars.calendar_br import DatesBRAnbima
from stpstone.utils.loggs.create_logs import CreateLog
from stpstone.utils.parsers.yaml import reading_yaml
from stpstone.utils.webhooks.teams import WebhookTeams


load_dotenv()

cls_dates_br = DatesBRAnbima()
cls_create_log = CreateLog()

_CONFIG_DIR = Path(__file__).parent

USER: str = getuser()
HOSTNAME: str = gethostname()
ENVIRONMENT: str = os.getenv("ENV", "development").lower()
APP_NAME: str = os.getenv("APP_NAME", "irpf")
TAXPAYER: str = os.environ["TAXPAYER"]
TAXPAYER_FULL_NAME: str = os.environ["TAXPAYER_FULL_NAME"]
TAXPAYER_CPF: str = os.environ["TAXPAYER_CPF"]

YAML_OUTPUTS: dict = reading_yaml(str(_CONFIG_DIR / "outputs.yaml"))
YAML_WEBHOOKS: dict = reading_yaml(str(_CONFIG_DIR / "webhooks.yaml"))
YAML_INPUTS: dict = reading_yaml(str(_CONFIG_DIR / "inputs.yaml"))

YAML_INPUTS["declaration_rv"]["contributor"]["full_name"] = TAXPAYER_FULL_NAME
YAML_INPUTS["declaration_rv"]["contributor"]["cpf"] = TAXPAYER_CPF

CLS_MS_TEAMS = WebhookTeams(YAML_WEBHOOKS["ms_teams"]["url"])

_dt_run = cls_dates_br.curr_date()
_dt_run_time = cls_dates_br.curr_time()

_daily_infos_root: Path = Path(YAML_INPUTS["daily_infos_base_path"]).expanduser()
_daily_infos_dir: Path = _daily_infos_root / str(_dt_run)
_daily_infos_dir.mkdir(parents=True, exist_ok=True)

_dt_str: str = _dt_run.strftime("%Y%m%d")
_time_str: str = _dt_run_time.strftime("%H%M%S")

PATH_LOG: Path = _daily_infos_dir / YAML_OUTPUTS["log_name"].format(
    ENVIRONMENT, APP_NAME, USER, _dt_str, _time_str
)
PATH_JSON: Path = _daily_infos_dir / YAML_OUTPUTS["json_name"].format(
    ENVIRONMENT, APP_NAME, USER, _dt_str, _time_str
)
PATH_TXT: Path = _daily_infos_dir / YAML_OUTPUTS["txt_name"].format(
    ENVIRONMENT, APP_NAME, USER, _dt_str, _time_str
)

DIR_PARENT = str(_daily_infos_dir)
LOGGER = cls_create_log.basic_conf(complete_path=str(PATH_LOG), basic_level="info")

MSG_MS_TEAMS: str = YAML_WEBHOOKS["ms_teams"]["message"].format(
    YAML_WEBHOOKS["ms_teams"]["title"],
    cls_dates_br.curr_date(),
    HOSTNAME,
    USER,
    str(PATH_JSON),
    str(PATH_LOG),
)
