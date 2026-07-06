import asyncio

from faststream.rabbit.schemas.constants import ExchangeType

from app.broker.rabbitmq import broker
from app.services.outbox_publisher import outbox_poller


async def main():
    # Запускаем брокер (соединение с RabbitMQ)
    await broker.start()
    print("Broker started")
    # Временно объявим exchange и очередь, чтобы poller мог публиковать
    from faststream.rabbit import RabbitExchange, RabbitQueue

    exchange = RabbitExchange("payments", type=ExchangeType.TOPIC)
    queue = RabbitQueue("payments.new", routing_key="new")
    # Объявляем обменник и очередь, получаем их реальные объекты aio-pika
    rb_exchange = await broker.declare_exchange(exchange)
    rb_queue = await broker.declare_queue(queue)
    # Привязываем очередь к обменнику
    await rb_queue.bind(rb_exchange, routing_key="new")
    print("Topology declared")

    # Запускаем outbox poller
    await outbox_poller()


if __name__ == "__main__":
    asyncio.run(main())
