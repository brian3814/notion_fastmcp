import os
import json
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from fastmcp import FastMCP, Context

from .logger import logger

# Find and load .env file from project root
project_root = Path(__file__).parent.parent
env_path = project_root / '../.env'

if not env_path.exists():
    raise FileNotFoundError(f"No .env file found at {env_path}")

load_dotenv(env_path)

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_BASE_URL = os.getenv("NOTION_BASE_URL", "https://api.notion.com/v1")
NOTION_VERSION = os.getenv("NOTION_VERSION", "2022-06-28")

if not NOTION_API_KEY:
    raise ValueError("NOTION_API_KEY not found in .env file")
if not DATABASE_ID:
    raise ValueError("NOTION_DATABASE_ID not found in .env file")

mcp = FastMCP("Notion Task Manager", dependencies=["httpx", "python-dotenv"])

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION
}

async def fetch_tasks() -> Dict:
    """
    Fetch tasks from Notion database
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{NOTION_BASE_URL}/databases/{DATABASE_ID}/query",
            headers=headers,
            json={
                "sorts": [
                    {
                        "property": "Created time",
                        "direction": "descending"
                    }
                ]
            }
        )
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def show_today_tasks() -> str:
    """Show today's task items from Notion database"""
    try:
        tasks = await fetch_tasks()
        formatted_tasks = []
        today = datetime.now().date().isoformat()
        
        for task in tasks.get("results", []):
            props = task["properties"]
            
            # Extract task title
            task = ""
            if props.get("Task") and props["Task"].get("title"):
                task = props["Task"]["title"][0]["text"]["content"] if props["Task"]["title"] else ""
            
            # Extract completion status
            completed = False
            if props.get("Checkbox"):
                completed = props["Checkbox"]["checkbox"]
            
            # Extract deadline
            deadline = None
            if props.get("Deadline") and props["Deadline"].get("date"):
                deadline = props["Deadline"]["date"]["start"]
            
            formatted_task = {
                "id": task["id"],
                "task": task,
                "completed": completed,
                "deadline": deadline,
                "created": task["created_time"]
            }
            
            # Only include today's items
            if deadline and deadline.startswith(today):
                formatted_tasks.append(formatted_task)
        
        if not formatted_tasks:
            return "No tasks scheduled for today."
        
        return json.dumps(formatted_tasks, indent=2)
        
    except Exception as e:
        logger.error(f"Notion API error: {str(e)}")
        return f"Error fetching tasks: {str(e)}\nPlease make sure your Notion integration is properly set up and has access to the database."

@mcp.tool()
async def list_all_tasks() -> str:
    """List all task items from Notion database"""
    try:
        tasks = await fetch_tasks()
        formatted_tasks = []
        
        for task in tasks.get("results", []):
            props = task["properties"]
            
            # Extract task title
            task = ""
            if props.get("Task") and props["Task"].get("title"):
                task = props["Task"]["title"][0]["text"]["content"] if props["Task"]["title"] else ""
            
            # Extract completion status
            completed = False
            if props.get("Checkbox"):
                completed = props["Checkbox"]["checkbox"]
            
            # Extract deadline
            deadline = None
            if props.get("Deadline") and props["Deadline"].get("date"):
                deadline = props["Deadline"]["date"]["start"]
            
            formatted_task = {
                "id": task["id"],
                "task": task,
                "completed": completed,
                "deadline": deadline,
                "created": task["created_time"]
            }
            
            formatted_tasks.append(formatted_task)
        
        if not formatted_tasks:
            return "No tasks found in the database."
        
        return json.dumps(formatted_tasks, indent=2)
        
    except Exception as e:
        logger.error(f"Notion API error: {str(e)}")
        return f"Error fetching tasks: {str(e)}\nPlease make sure your Notion integration is properly set up and has access to the database."

@mcp.resource("notion://database/schema")
async def get_database_schema() -> str:
    """Get the schema of the Notion database"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{NOTION_BASE_URL}/databases/{DATABASE_ID}",
                headers=headers
            )
            response.raise_for_status()
            database = response.json()
            
            # Extract and format the schema
            properties = database.get("properties", {})
            schema = {name: prop["type"] for name, prop in properties.items()}
            
            return json.dumps(schema, indent=2)
    except Exception as e:
        logger.error(f"Failed to fetch database schema: {str(e)}")
        return f"Error fetching database schema: {str(e)}"