from faststream.rabbit import ExchangeType, RabbitExchange, RabbitQueue

from app.broker.rabbitmq import broker


async def declare_topology():
    # Основной обменник (topic)
    payments_exchange = RabbitExchange("payments", type=ExchangeType.TOPIC)

    # Основная очередь платежей
    payments_queue = RabbitQueue(
        "payments.new",
        routing_key="new",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "payments.dlx",
            "x-dead-letter-routing-key": "dead",
        },
    )

    # Dead Letter Exchange и очередь
    dlx_exchange = RabbitExchange("payments.dlx", type=ExchangeType.TOPIC)
    dlq_queue = RabbitQueue("payments.dlq", routing_key="dead", durable=True)

    # Объявляем через broker (получаем объекты aio_pika)
    rb_exchange = await broker.declare_exchange(payments_exchange)
    rb_queue = await broker.declare_queue(payments_queue)

    rb_dlx_exchange = await broker.declare_exchange(dlx_exchange)
    rb_dlq_queue = await broker.declare_queue(dlq_queue)

    # Привязки
    await rb_queue.bind(rb_exchange, routing_key="new")
    await rb_dlq_queue.bind(rb_dlx_exchange, routing_key="dead")

    print("Topology declared: payments exchange, payments.new queue, DLQ")
