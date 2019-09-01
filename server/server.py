#!/usr/bin/env python3
from aiohttp import web
import asyncio
from datetime import datetime

async def reset_client_count(q, id):
    # Clears request counter for a client every 5s
    # After if clears the counter it waits for an event to start 
    # a new time frame
    while True:
        await asyncio.sleep(5)
        clients[id][0] = 0
        print(
            f'{datetime.now().strftime("%H:%M:%S.%f")[:-4]} ' \
            f'Client {id}: Reset time frame {id}')
        await clients[id][1].wait()
        clients[id][1].clear()


async def handle(request):
    # Crates a counter and an event for every new client, and start a task
    # for every clients time frame.
    # When counter reaches >= 5 it start returning 503, else it returns 200
    # Every time a client sends a request after the last time frame has passed 
    # it triggers an event to start a new time frame
    id = request.rel_url.query['clientId']
    text = f'{datetime.now().strftime("%H:%M:%S.%f")[:-4]} ' \
           f'Requests in current time frame:'
    if id in clients:
        if clients[id][0] >= 5:
            clients[id][0] += 1
            response = web.HTTPServiceUnavailable(
                text=f'{text} {clients[id][0]}')
            return response
        else:
            if clients[id][0] == 0:
                clients[id][1].set()
            clients[id][0] += 1
            return web.Response(text=f'{text} {clients[id][0]}')
    else:
        clients[id] = [1, asyncio.Event()]
        loop.create_task(reset_client_count(clients[id], id))
        return web.Response(text=f'{text} {clients[id][0]}')

clients = {}
loop = asyncio.get_event_loop()

app = web.Application()
app.add_routes([web.get('/', handle)])
web.run_app(app, port=8080, host='localhost')


