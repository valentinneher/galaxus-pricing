import os
import json
import yaml
import itertools
import time
from azure.servicebus import ServiceBusClient, ServiceBusMessage

# config
YAML_PATH = "config/sites.yml"
BATCH_SIZE = 25
QUEUE = os.getenv("SB_QUEUE", "scrape-tasks")
SB_CONN = os.getenv("SB_CONN")


def batches(iterable, n):
    it = iter(iterable)
    while (chunk := list(itertools.islice(it, n))):
        yield chunk


def main():
    # load the per-SKU map
    with open(YAML_PATH, encoding="utf-8") as f:
        sites = yaml.safe_load(f)["interdiscount"]

    client = ServiceBusClient.from_connection_string(SB_CONN)
    sender = client.get_queue_sender(queue_name=QUEUE)

    with sender:
        for batch in batches(sites.items(), BATCH_SIZE):
            task = {
                "shop": "interdiscount",
                "mode": "edge",
                "batch": [
                    {"code": code, **data} for code, data in batch
                ],
            }
            sender.send_messages(ServiceBusMessage(json.dumps(task)))

    print(f"Scheduler sent {len(sites)} tasks @ {time.asctime()}")


if __name__ == "__main__":
    main()