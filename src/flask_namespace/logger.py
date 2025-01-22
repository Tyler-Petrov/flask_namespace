import datetime
import json
import logging
import sys
import traceback
import uuid
from zoneinfo import ZoneInfo

from bson import json_util
from flask import g, request


class JsonLogWrapper:
    """create logging object to wrap Python logger and feed it JSON strings as the log message
    (see https://docs.python.org/3.7/howto/logging-cookbook.html#implementing-structured-logging)
    emulate exc_info=True flag of regular logger to conveniently record exception data
    """

    def __init__(self, logger: logging.Logger, log_filepath: str):
        self.log_filepath = log_filepath
        self.logger = logger

    def critical(self, message, exc_info=True, **kwargs):
        self.log(logging.CRITICAL, "critical", message, exc_info, **kwargs)

    def debug(self, message, exc_info=True, **kwargs):
        self.log(logging.DEBUG, "debug", message, exc_info, **kwargs)

    def error(self, message, exc_info=True, **kwargs):
        self.log(logging.ERROR, "error", message, exc_info, **kwargs)

    def info(self, message, exc_info=True, **kwargs):
        self.log(logging.INFO, "info", message, exc_info, **kwargs)

    def warning(self, message, exc_info=True, **kwargs):
        self.log(logging.WARNING, "warning", message, exc_info, **kwargs)

    def build_payload(
        self, log_value, log_level, message, exc_info=True, **kwargs
    ) -> dict:
        now = datetime.datetime.now(ZoneInfo("UTC"))
        time = now.replace(microsecond=((now.microsecond // 1000) * 1000))

        unique_id = str(uuid.uuid4())
        payload = {
            "log_value": log_value,
            "log_level": log_level,
            "message": message,
            "timestamp": time.isoformat(),
            "formatted_timestamp": time.strftime("%A, %B %e, %Y at %I:%M %p"),
            "log_unique_id": unique_id,
        }

        # also add request information
        try:
            payload["remote_addr"] = request.remote_addr
            payload["request_url"] = request.url
            payload["request_method"] = request.method
        except:
            pass

        # if we're handling an exception, attach the traceback by default
        if exc_info:
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            if exc_value is not None:
                payload["exc_type"] = str(exc_type)
                payload["exc_value"] = str(exc_value)
                payload["exc_traceback"] = traceback.format_exception(
                    exc_type, exc_value, exc_traceback
                )

        # Apply kwargs last to override defaults if desired
        payload.update(**kwargs)

        return payload

    def log(
        self,
        log_value,
        log_level,
        message,
        exc_info=True,
        **kwargs,
    ):
        self.logger.log(
            log_value,
            json.dumps(
                self.build_payload(log_value, log_level, message, exc_info, **kwargs),
                default=self.json_default_serializer,
            ),
        )

    @staticmethod
    def json_default_serializer(o):
        """JSON serializer for objects not serializable by default json code"""

        return json_util.default(o)

    def all_logs(self, rotation_number=0) -> list:

        def safe_log_line(log_line):
            try:
                return json.loads(log_line)
            except ValueError:
                return False

        filename_suffix = f".{rotation_number}" if rotation_number != 0 else ""

        with open(f"{self.log_filepath}{filename_suffix}") as lf:
            return list(
                reversed(
                    [safe_log_line(log) for log in lf.readlines() if safe_log_line(log)]
                )
            )

    def grouped_logs(self, rotation_number=0) -> list:
        class Log(dict):
            log_keys = [
                "message",
                "log_level",
                "log_value",
                "log_id",
                "request_url",
                "request_method",
                "exc_type",
                "exc_value",
                "exc_traceback",
            ]

            @property
            def request_keys(self):
                return self.keys() - self.log_keys

            @property
            def request_dict(self):
                return {key: self.get(key) for key in self.request_keys}

            def identifier(self):
                return ";".join(str(self.get(key)) for key in self.log_keys)

            def create_log(self) -> dict:
                """
                Added a new log to grouped_json_logs with the log_keys and the request_keys
                :return: The log dictionary for the grouped_json_logs
                """
                return_dict = {key: self.get(key) for key in self.log_keys}
                return_dict.update({"requests": [self.request_dict]})
                return return_dict

            def add_request(self) -> dict:
                """
                For adding request log data to the similar log in grouped_json_logs
                :return: the similar log in grouped_json_logs
                """
                grouped_json_logs[self.identifier()]["requests"].append(
                    self.request_dict
                )
                return grouped_json_logs[self.identifier()]["requests"]

        grouped_json_logs = {}

        # Loop through the logs
        for log in self.all_logs(rotation_number):
            log = Log(log)  # Convert dict to Log
            if (
                grouped_json_logs.get(log.identifier()) is not None
            ):  # If there is a similar log in grouped_json_logs
                log.add_request()  # Then just add the request data
                continue

            # If there isn't a similar log, then create one with the request log
            grouped_json_logs[log.identifier()] = log.create_log()

        # Return the grouped logs
        return list(grouped_json_logs.values())
