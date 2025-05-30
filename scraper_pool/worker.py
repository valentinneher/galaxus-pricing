import os
import json
import asyncio
import importlib
import aiohttp
from azure.servicebus.aio import ServiceBusClient
from confluent_kafka import Producer

# Env vars
SB_CONN = os.getenv("SB_CONN")
SB_QUEUE = os.getenv("SB_QUEUE", "scrape-tasks")
BOOT = os.getenv("EH_BOOTSTRAP")
SASLU = os.getenv("EH_SASL_USERNAME")
SASLP = os.getenv("EH_SASL_PASSWORD")
TOPIC = os.getenv("EH_TOPIC", "competitor-prices")

# Kafka producer
producer = Producer({
    "bootstrap.servers": BOOT,
    "security.protocol": "SASL_SSL",
    "sasl.mechanisms": "PLAIN",
    "sasl.username": SASLU,
    "sasl.password": SASLP,
})


async def handle_message(raw_msg):
    payload = json.loads(str(raw_msg))
    shop = payload["shop"]
    plugin = importlib.import_module(f"plugins.{shop}")

    async with aiohttp.ClientSession() as session:
        async for event in plugin.fetch_batch(session, payload["batch"]):
            producer.produce(TOPIC, json.dumps(event).encode())


async def main():
    sb = ServiceBusClient.from_connection_string(SB_CONN)
    async with sb:
        receiver = sb.get_queue_receiver(queue_name=SB_QUEUE)
        async with receiver:
            async for msg in receiver:
                try:
                    await handle_message(msg)
                    await receiver.complete_message(msg)
                except Exception as e:
                    print("✗", e)
                    await receiver.abandon_message(msg)


if __name__ == "__main__":
    asyncio.run(main())