import anyio
import json
import click
from mcp.types import (
    CallToolRequest,
    ListToolsRequest,
    Tool,
    TextContent,
)
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from sqlalchemy.util import to_column_set
from starlette.applications import Starlette
from starlette.responses import Response, JSONResponse
from starlette.routing import Mount, Route
from starlette.middleware.cors import CORSMiddleware
import api_conn


@click.command()
@click.option("--transport", type=click.Choice(["stdio", "sse"]), default="sse")
@click.option("--port", default=8002, help="Port to listen on for SSE mcp")
def main(transport: str, port: int) -> int:
    # Tạo MCP Server
    app = Server("simple-info-server")

    # 1. TOOL VERSION - Mô tả công cụ
    @app.call_tool()
    async def weather_tool(name: str, arguments: dict) -> list[TextContent]:
        """Xử lý khi AI agent gọi tool"""
        print(name)
        if name == "Weather_Tool":  # ✅ Sửa logic
            city = arguments.get("city", "")

            if not city:
                return [TextContent(
                    type="text",
                    text="Vui lòng cung cấp tên thành phố."
                )]

            # Mô phỏng lấy thông tin thời tiết
            weather_info = f"""
        Thông tin thời tiết tại {city}:
        - Nhiệt độ: 25°C
        - Độ ẩm: 70%
        - Tình trạng: Nắng ít mây
        - Tốc độ gió: 10 km/h
                """

            return [TextContent(
                type="text",
                text=weather_info.strip()
            )]

        elif name == "Weather_Execute":

            city = arguments["city"]

            # Mô phỏng dữ liệu thời tiết (thay vì dùng API thật)
            weather_data = {
                "hanoi": "Hà Nội: 32°C, Nắng nhẹ",
                "saigon": "Sài Gòn: 34°C, Có mây",
                "danang": "Đà Nẵng: 30°C, Mưa nhỏ"
            }

            city_key = city.lower().replace(" ", "")
            weather = weather_data.get(city_key, f"Không có thông tin thời tiết cho {city}")

            return [TextContent(type="text", text=weather)]
        elif name == "search_users":
            print(arguments)
            # Kiểm tra các đối số truyền vào tool có đủ không
            if "search_criteria" not in arguments:
                raise ValueError("Missing required argument 'search_criteria'")
            else:
                text_search = arguments["search_criteria"]["query"]["search_criteria"]["field"] # lấy giá trị từ param query khi AI truyền
                limit = arguments.get("limit", 20)

            if not text_search:
                return [TextContent(type="text", text="Vui lòng cung cấp tiêu chí tìm kiếm")]

            print(arguments)
            # Khởi tạo API Client
            api_client = api_conn.APIClient(
                base_url="http://103.163.216.33:8001"
            )
            # Thiết lập tham số gọi tới API
            api_response = await api_client.get_user_list()
            # Lấy ra tất cả dữ liệu user
            user_data = api_response.get("data", [])

            # Tìm kiếm linh hoạt
            result = api_client.search_users_flexible(user_data, text_search)
            print(result)
            result = result[:limit]  # Giới hạn kết quả từ 0 tới limit
            if not result:
                msg_result = json.dumps(text_search, ensure_ascii=False)
                return [TextContent(type="text", text=f"Không tìm thấy user nào với tiêu chí:{msg_result}")]

            # Format kết quả
            format_result = []
            for user in result:
                format_result.append({
                    "id": user.get("id"),
                    "username": user.get("username"),
                    "fullname": user.get("fullname"),
                    "email": user.get("email"),
                    "phone": user.get("phone")
                })
            return [TextContent(
                type="text",
                text=f"Tìm thấy {len(format_result)} user(s) với tiêu chí '{json.dumps(text_search, ensure_ascii=False)}':\n\n" +
                     json.dumps(format_result, indent=2, ensure_ascii=False)
            )]
        else:
            return [TextContent(type="text", text=f"Không tìm thấy công cụ nào có tên {name}")]

    # 2. EXECUTE VERSION - Thực thi công cụ

    # async def weather_execute(name: str, arguments: dict) -> list[TextContent]:

    # 3. My tool: Lấy ra thông tin danh sách user từ API

    # async def user_execute(name: str, arguments: dict) -> list[TextContent]:
    #     # Kiểm tra tool name truyền vào có đúng không
    #     if name != "user_execute":
    #         raise ValueError(f"user_execute Unknown Tool: {name}")
    #

    # Đăng ký danh sách công cụ
    @app.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            # Tool tìm kiếm thông tin user
            Tool(
                name="search_users",
                description="Tìm kiếm users theo bất kỳ trường nào. Hỗ trợ tìm kiếm đơn giản và nâng cao với operators.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "search_criteria": {
                            "description": "Tiêu chí tìm kiếm. Có thể là JSON string hoặc object.",
                            "oneOf": [
                                {
                                    "type": "string",
                                    "description": "JSON string của tiêu chí tìm kiếm. VD: '{\"fullname\": \"cuong\"}'"
                                },
                                {
                                    "type": "object",
                                    "description": "Object chứa tiêu chí tìm kiếm",
                                    "additionalProperties": {
                                        "oneOf": [
                                            {
                                                "type": "string",
                                                "description": "Tìm kiếm đơn giản - chứa từ khóa"
                                            },
                                            {
                                                "type": "object",
                                                "properties": {
                                                    "operator": {
                                                        "type": "string",
                                                        "enum": ["contains", "equals", "starts_with", "ends_with"],
                                                        "description": "Toán tử so sánh"
                                                    },
                                                    "value": {
                                                        "type": "string",
                                                        "description": "Giá trị cần tìm"
                                                    }
                                                },
                                                "required": ["value"],
                                                "description": "Tìm kiếm nâng cao với operator"
                                            }
                                        ]
                                    }
                                }
                            ]
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Số lượng kết quả tối đa",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 100
                        }
                    },
                    "required": ["search_criteria"],
                    "examples": [
                        {
                            "search_criteria": {"fullname": "cuong"},
                            "limit": 10
                        },
                        {
                            "search_criteria": {
                                "fullname": {"operator": "contains", "value": "nguyen"},
                                "email": {"operator": "ends_with", "value": "@adavigo.com"}
                            },
                            "limit": 5
                        }
                    ]
                }
            ),
            # Tool Version - Mô tả
            Tool(
                name="Weather_Tool",
                description="Công cụ mô tả cách lấy thông tin thời tiết !",
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
            Tool(
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
