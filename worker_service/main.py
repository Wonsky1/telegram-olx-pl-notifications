import asyncio
from worker_service.tools.utils import find_new_flats


async def worker_main():
    while True:
        try:
            await find_new_flats()
        except Exception as e:
            print(f"Error in flat finder: {e}")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(worker_main())
