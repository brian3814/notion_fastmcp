import os
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from . import server

def main():
    server.mcp.run()