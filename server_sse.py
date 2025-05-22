import anyio
import click
import mcp.types as types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.responses import Response, JSONResponse
from starlette.routing import Mount, Route
from starlette.middleware.cors import CORSMiddleware


@click.command()
@click.option("--transport", type=click.Choice(["stdio", "sse"]), default="sse")
@click.option("--port", default=8000, help="Port to listen on for SSE")
def main(transport: str, port: int) -> int:
    # Tạo MCP Server
    app = Server("simple-info-server")

    # 1. TOOL VERSION - Mô tả công cụ
    @app.call_tool()
    async def weather_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name != "Weather_Tool":
            raise ValueError(f"Unknown tool: {name}")

        # Tool version chỉ trả về mô tả
        return [types.TextContent(type="text", text="""
        Đây là công cụ để lấy thông tin thời tiết.

        Tham số:
        - city (bắt buộc): Tên thành phố cần lấy thông tin thời tiết

        Sử dụng phiên bản Execute để lấy dữ liệu thực tế.
        """)]

    # 2. EXECUTE VERSION - Thực thi công cụ
    @app.call_tool()
    async def weather_execute(name: str, arguments: dict) -> list[types.TextContent]:
        if name != "Weather_Execute":
            raise ValueError(f"Unknown tool: {name}")

        if "city" not in arguments:
            raise ValueError("Missing required argument 'city'")

        city = arguments["city"]

        # Mô phỏng dữ liệu thời tiết (thay vì dùng API thật)
        weather_data = {
            "hanoi": "Hà Nội: 32°C, Nắng nhẹ",
            "saigon": "Sài Gòn: 34°C, Có mây",
            "danang": "Đà Nẵng: 30°C, Mưa nhỏ"
        }

        city_key = city.lower().replace(" ", "")
        weather = weather_data.get(city_key, f"Không có thông tin thời tiết cho {city}")

        return [types.TextContent(type="text", text=weather)]

    # Đăng ký danh sách công cụ
    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            # Tool Version - Mô tả
            types.Tool(
                name="Weather_Tool",
                description="Công cụ mô tả cách lấy thông tin thời tiết",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "Tên thành phố"
                        }
                    },
                },
            ),
            # Execute Version - Thực thi
            types.Tool(
                name="Weather_Execute",
                description="Thực thi để lấy thông tin thời tiết",
                inputSchema={
                    "type": "object",
                    "required": ["city"],
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "Tên thành phố"
                        }
                    },
                },
            )
        ]

    # Chạy server với giao thức tương ứng
    if transport == "sse":
        # Cấu hình SSE transport
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.responses import Response, JSONResponse
        from starlette.routing import Mount, Route
        from starlette.middleware.cors import CORSMiddleware

        # Tạo SSE transport tại endpoint "/messages/"
        sse = SseServerTransport("/messages/")

        # Hàm xử lý kết nối SSE
        async def handle_sse(request):
            # Ghi log về request
            print(f"SSE connection received from: {request.client.host}")

            # Kết nối SSE và chạy MCP Server
            async with sse.connect_sse(
                    request.scope, request.receive, request._send
            ) as streams:
                await app.run(
                    streams[0],
                    streams[1],
                    InitializationOptions(
                        server_name="simple-info-server",
                        server_version="1.0.0",
                        capabilities=app.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    )
                )

            return Response()

        # Tạo route hiển thị thông tin server
        async def server_info(request):
            return JSONResponse({
                "name": "Simple Info MCP Server",
                "version": "1.0.0",
                "description": "MCP Server cung cấp thông tin thời tiết",
                "endpoints": {
                    "sse": "/sse",
                    "messages": "/messages/",
                    "info": "/info"
                }
            })

        # Tạo ứng dụng Starlette với CORS và các route
        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/", endpoint=server_info, methods=["GET"]),
                Route("/info", endpoint=server_info, methods=["GET"]),
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

        # Thêm CORS middleware để cho phép kết nối từ bất kỳ nguồn nào
        starlette_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Thông báo cho người dùng
        print(f"Starting Simple Info MCP Server with SSE transport at http://localhost:{port}")
        print(f"SSE endpoint: http://localhost:{port}/sse")
        print(f"Server info endpoint: http://localhost:{port}/info")

        # Chạy ứng dụng Starlette với uvicorn
        import uvicorn
        uvicorn.run(starlette_app, host="0.0.0.0", port=port)
    else:
        # Sử dụng stdio transport (mặc định cho n8n)
        from mcp.server.stdio import stdio_server
        print("Starting Simple MCP Server with stdio transport")

        async def arun():
            async with stdio_server() as streams:
                await app.run(
                    streams[0],
                    streams[1],
                    app.create_initialization_options()
                )

        anyio.run(arun)

    return 0


if __name__ == "__main__":
    main()