#!/usr/bin/env python3
import aiohttp
import asyncio
import aioconsole
import argparse
import random
# Diffrent imports for windows or linux/MacOS,
# for reading key press to end the program
try:
    from msvcrt import getch
    win = True
except ImportError:
    import os
    import termios
    import termios
    import sys
    import fcntl
    win = False


URL = 'http://localhost:8080'

# Some color for the output
OK = '\033[92m'
FAIL = '\033[91m'
ENDC = '\033[0m'


def int_check(value):
    # Check if arg for number of clients > 0
    value = int(value)
    if value < 1:
        raise argparse.ArgumentTypeError(f'{value} should be positive!')
    else:
        return value


async def make_requests(session, n):
    # Create tasks to run request for each client id
    await asyncio.gather(
        *[asyncio.create_task(make_request(session, id)) for id in range(n)],
        return_exceptions=False)


async def make_request(session, id):
    # Makes requests for each id and sleeps for random time
    # Returns if cancel_event is set on key press or by a exception
    while not cancel_event.is_set():
        try:
            async with session.get(f'{URL}/?clientId={id}', timeout=2) as response:
                color = OK if response.status == 200 else FAIL
                text = await response.text()
                print(f'Client {id}: {color}{response.status} {text}{ENDC}')
            if cancel_event.is_set():
                return
            await asyncio.sleep(round(random.uniform(0, 2), 2))
        except asyncio.TimeoutError as e:
            print(f'Client {id} Request timed out')
            cancel_event.set()
        except aiohttp.ClientConnectionError as e:
            print(f'Client {id} {e}')
            cancel_event.set()


async def run_clients():
    # Starts aiohttp client session
    async with aiohttp.ClientSession() as session:
        await make_requests(session, args.num_of_clients[0])


async def char_keyboard_nonblock():
    # Convoluted way to read a key press without presing enter
    if win:
        getch()
    else:
        stdin, stdout = await aioconsole.get_standard_streams()
        fd = sys.stdin.fileno()

        oldterm = termios.tcgetattr(fd)
        newattr = termios.tcgetattr(fd)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)

        oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

        try:
            await stdin.read(1)
        except IOError:
            pass

        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)


async def cancel(requests_task):
    # Waits for key press or if event is triggered at the start of the 
    # program by a connection problem
    done, pending = await asyncio.wait([char_keyboard_nonblock(),
                                        cancel_event.wait()],
                                       return_when=asyncio.FIRST_COMPLETED)
    next(iter(pending)).cancel()
    print("Stoping clients...")
    cancel_event.set()
    await requests_task


# Args parser
parser = argparse.ArgumentParser(description='Run N clients')
parser.add_argument('num_of_clients', metavar='N', type=int_check, nargs=1,
                    help='number of clients to run')
args = parser.parse_args()


cancel_event = asyncio.Event()
loop = asyncio.get_event_loop()
requests_task = loop.create_task(run_clients())
loop.run_until_complete(cancel(requests_task))

# Zero-sleep to allow underlying connections to close
loop.run_until_complete(asyncio.sleep(0))
loop.close()
