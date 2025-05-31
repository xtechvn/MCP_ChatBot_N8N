import httpx
import asyncio
from typing import Dict, Any, List
import logging

# Cấu hình logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class APIClient:
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url.rstrip('/')  # loại bỏ chuỗi  bên phải cuối của 1 chữ
        self.headers = {}
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'

    async def get_user_list(self) -> List[Dict]:
        try:
            print(self.base_url)
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/v1/user/", headers=self.headers)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP Error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)

    # Tìm kiếm user linh hoạt theo tiêu chí
    def search_users_flexible(self, users_data: List[Dict], search_criteria: Dict) -> List[Dict]:
        try:
            print(users_data)
            print(search_criteria)
            """
            Tìm kiếm users linh hoạt theo nhiều tiêu chí
            search_criteria format: {
                "field": "value" hoặc
                "field": {"operator": "contains|equals|starts_with|ends_with", "value": "search_value"}
            }
            """
            results = users_data

            # for user in users_data:
            #     match = True
            #
            #     for field, criteria in search_criteria.items():
            #         if field not in user:
            #             match = False
            #             break
            #
            #         user_value = str(user[field]).lower() if user[field] else ""
            #
            #         if isinstance(criteria, dict):
            #             # Advanced search với operator
            #             operator = criteria.get("operator", "contains")
            #             search_value = str(criteria.get("value", "")).lower()
            #
            #             if operator == "contains":
            #                 if search_value not in user_value:
            #                     match = False
            #                     break
            #             elif operator == "equals":
            #                 if user_value != search_value:
            #                     match = False
            #                     break
            #             elif operator == "starts_with":
            #                 if not user_value.startswith(search_value):
            #                     match = False
            #                     break
            #             elif operator == "ends_with":
            #                 if not user_value.endswith(search_value):
            #                     match = False
            #                     break
            #         else:
            #             # Simple search - chỉ cần chứa từ khóa
            #             search_value = str(criteria).lower()
            #             if search_value not in user_value:
            #                 match = False
            #                 break
            #
            #     if match:
            #         results.append(user)

            return results
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP Error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
