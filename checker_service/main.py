import asyncio

from checker_service.tools.utils import check_and_send_flats


async def checker_main():
    while True:
        try:
            await check_and_send_flats()
        except Exception as e:
            print(f"Error in checker: {e}")
        await asyncio.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    asyncio.run(checker_main())
