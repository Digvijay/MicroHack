"""Azure Functions entry point (Python v2 model). One HTTP-triggered ASGI function serves every route."""

import logging

import azure.functions as func

from workiq_emulator.app import create_app

logging.getLogger("workiq").setLevel(logging.INFO)
# The Azure SDK logs from worker threads during the optional model call. Logging from worker
# threads can block inside the Functions Python worker, and the app logs model failures itself.
logging.getLogger("azure").setLevel(logging.CRITICAL)

app = func.AsgiFunctionApp(app=create_app(), http_auth_level=func.AuthLevel.ANONYMOUS)