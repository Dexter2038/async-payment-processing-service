import asyncio
import sys


async def main():
    print("Consumer is starting...")
    # Здесь будет логика consumer'а
    await asyncio.Event().wait()  # бесконечное ожидание


if __name__ == "__main__":
    asyncio.run(main())
