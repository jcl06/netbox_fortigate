import json
import logging, logging.handlers
from .utils.settings import get_plugin_default




class JSONFormatter(logging.Formatter):
    def format(self, record):
        import inspect

        # Skip internal logging frames and this formatter module
        for frame_info in inspect.stack():
            module = inspect.getmodule(frame_info.frame)
            if module:
                module_name = module.__name__
                # Skip logging and your custom logging formatter module
                if module_name.startswith("logging") or module_name == __name__:
                    continue
                record.full_path = f"{module_name}:{frame_info.function}"
                break
        else:
            record.full_path = "unknown_module:unknown_function"

        # Pretty-print JSON messages
        try:
            if isinstance(record.msg, (dict, list)):
                record.msg = "\n" + json.dumps(record.msg, indent=2, ensure_ascii=False)
            else:
                msg = json.loads(record.getMessage())
                record.msg = "\n" + json.dumps(msg, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            pass

        return super().format(record)
    

logfile = get_plugin_default("logfile", "netbox_fortigate.log")
fortigate_logger = logging.getLogger('FORTIGATE')
formatter = JSONFormatter(
            fmt='%(asctime)s [%(levelname)s] [%(full_path)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
fortigate_logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler(logfile, maxBytes=1048576000, backupCount=10, encoding='utf-8')
handler.setFormatter(formatter)
fortigate_logger.addHandler(handler)
