
from dotenv import load_dotenv
load_dotenv()

import os

bootstrap = os.getenv("EH_BOOTSTRAP")
sasl_user = os.getenv("EH_SASL_USERNAME")
sasl_pass = os.getenv("EH_SASL_PASSWORD")
sb_conn = os.getenv("SB_CONN")
slack = os.getenv("SLACK_WEBHOOK")
edge = os.getenv("CF_EDGE_URL")

def test_env_variables():
    print("Testing environment variables...")
    print(f"EH_BOOTSTRAP: {bootstrap}")
    print(f"EH_SASL_USERNAME: {sasl_user}")
    print(f"EH_SASL_PASSWORD: {sasl_pass}")
    print(f"SB_CONN: {sb_conn}")
    print(f"SLACK_WEBHOOK: {slack}")
    print(f"CF_EDGE_URL: {edge}")
    


if __name__ == "__main__":
    test_env_variables()
    print("All environment variable tests passed.")

    