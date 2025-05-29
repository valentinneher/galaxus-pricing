
from dotenv import load_dotenv
load_dotenv()

import os

bootstrap = os.getenv("EH_BOOTSTRAP")
sasl_user = os.getenv("EH_SASL_USERNAME")
sasl_pass = os.getenv("EH_SASL_PASSWORD")
sb_conn = os.getenv("SB_CONN")
slack = os.getenv("SLACK_WEBHOOK")
edge = os.getenv("CF_EDGE_URL")

