from mcp.server.fastmcp import FastMCP
import httpx
import anyio
import click
import json
import os
from pathlib import Path
import mcp.types as types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions

# Tao MCP server voi ten la Demo
mcp = FastMCP("Demo")


# Them cong cu cong 2 so
@mcp.tool()
def add(a: int, b: int) -> int:
    # Cong 2 so
    return a + b

#Công cụ tìm kiếm thông tin
@mcp.tool()
async def fetch_weather(city:str) -> str:
    #lay thông tin thời tiết hiện tại cho 1 thành phố
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.weather.com/{city}")
        return response.text

# them tai nguyen dynamic de tao loi chao:
# Công khai dữ liệu cho AI
@mcp.resource("greeting://{name}")
def get_greeting(name:str)-> str:
    #lấy dữ liệu trong database
    return f"""
    Tên công ty: Fpt Online
    Địa chỉ: số 10 Phạm Văn Bạch
    """
    return  f"Xin chao, {name} "

#Neu chay truc tiep
if __name__ == "__main__":
    mcp.run()