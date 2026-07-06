import asyncio

from app.broker.rabbitmq import broker
from app.broker.topology import declare_topology
from app.services.outbox_publisher import outbox_poller


async def main():
    await broker.start()
    print("Broker started")
    await declare_topology()
    await outbox_poller()


if __name__ == "__main__":
    asyncio.run(main())
