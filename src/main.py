"""Service entrypoint: bootstrap → wire → run → teardown."""

from __future__ import annotations

from stpstone.utils.parsers.json import JsonFiles
from stpstone.utils.parsers.txt import HandlingTXTFiles

from src.app.bootstrap import cls_create_log, init, teardown
from src.app.container import build, build_jobs
from src.config.startup import (
    CLS_MS_TEAMS,
    ENVIRONMENT,
    LOGGER,
    MSG_MS_TEAMS,
    PATH_JSON,
    PATH_TXT,
    YAML_INPUTS,
    YAML_WEBHOOKS,
)


float_start_time = init()
cls_container = build()

if YAML_INPUTS.get("run_import_trades", True):
    cls_create_log.log_message(LOGGER, "Starting import_trades pipeline", "info")
    list_results = cls_container.fn_import_trades(build_jobs())
    for dict_result in list_results:
        cls_create_log.log_message(
            LOGGER,
            f"Imported {dict_result['rows_processed']} rows into {dict_result['table_name']}",
            "info",
        )
    JsonFiles().dump_message({"import_results": list_results}, str(PATH_JSON))

if YAML_INPUTS.get("run_declaration_rv", True):
    cls_create_log.log_message(LOGGER, "Starting declaration_rv pipeline", "info")
    dict_report = cls_container.fn_generate_declaration()
    cls_create_log.log_message(LOGGER, f"Declaration year: {dict_report['int_year']}", "info")
    HandlingTXTFiles().write_file(str(PATH_TXT), dict_report["str_report"])
    cls_create_log.log_message(LOGGER, f"Report written to {PATH_TXT}", "info")

if ENVIRONMENT == "production":
    CLS_MS_TEAMS.send_message(str_msg=MSG_MS_TEAMS, str_title=YAML_WEBHOOKS["ms_teams"]["title"])

teardown(float_start_time)
