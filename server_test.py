import anyio
import click
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.responses import Response, JSONResponse
from starlette.routing import Mount, Route


@click.command()
@click.option("--port", default=8000, help="Port to listen on")
def main(port: int) -> int:
    app = Server("test-server")

    @app.call_tool()
    async def hello_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name != "hello":
            raise ValueError(f"Unknown tool: {name}")

        message = "Hello, World!"
        if "name" in arguments:
            message = f"Hello, {arguments['name']}!"

        print(f"Called hello tool with: {arguments}")
        return [types.TextContent(type="text", text=message)]

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        print("Tools requested!")
        return [
            types.Tool(
                name="hello",
                description="A simple hello world tool",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name to greet"
                        }
                    }
                }
            )
        ]

    # Tạo SSE transport
    sse = SseServerTransport("/messages/")

    # Hàm xử lý kết nối SSE
    async def handle_sse(request):
        print(f"SSE connection received from: {request.client.host}")

        async with sse.connect_sse(
                request.scope, request.receive, request._send
        ) as streams:
            await app.run(
                streams[0],
                streams[1],
                app.create_initialization_options()
            )

        return Response()

    # Tạo route hiển thị thông tin server
    async def server_info(request):
        print("Info endpoint called")
        return JSONResponse({
            "name": "Test MCP Server",
            "version": "1.0.0",
            "description": "Test server to verify functionality",
            "endpoints": {
                "sse": "/sse",
                "messages": "/messages/",
                "info": "/info"
            }
        })

    # Tạo ứng dụng Starlette
    starlette_app = Starlette(
        debug=True,
        routes=[
            Route("/", endpoint=server_info, methods=["GET"]),
            Route("/info", endpoint=server_info, methods=["GET"]),
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

    print(f"Starting test MCP Server on http://localhost:{port}")
    print(f"- SSE endpoint: http://localhost:{port}/sse")
    print(f"- Info endpoint: http://localhost:{port}/info")

    # Chạy ứng dụng với uvicorn
    import uvicorn
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)

    return 0


if __name__ == "__main__":
    main()