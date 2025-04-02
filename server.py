#!/usr/bin/env python3
#
# This is just a demo server for playing with the UI if you don't
# have a real server to play with.

import asyncio
import random
import signal

from asyncua import Server

_URL = "opc.tcp://localhost:48400/opc-explorer/server"


async def _generate_values(server: Server, shutdown_event: asyncio.Event):
    index = await server.register_namespace("demo")
    object_node = await server.nodes.objects.add_object(index, "TestObject")
    variable = await object_node.add_variable(index, "TestVariable", 42)

    while not shutdown_event.is_set():
        await variable.write_value(random.randint(1, 100))
        await asyncio.sleep(1)


async def main():
    server = Server()
    await server.init()
    server.set_endpoint(_URL)
    await server.start()

    shutdown_event = asyncio.Event()

    def _shutdown(signal_received, frame):
        shutdown_event.set()

    signal.signal(signal.SIGINT, _shutdown)

    await asyncio.gather(_generate_values(server, shutdown_event))
    await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
