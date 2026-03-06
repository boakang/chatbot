# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.core import ActivityHandler, TurnContext, ConversationState, UserState
from botbuilder.schema import ChannelAccount
from database import DatabaseHelper


class Bot(ActivityHandler):
    def __init__(self, conversation_state: ConversationState, user_state: UserState):
        self.conversation_state = conversation_state
        self.user_state = user_state
        self.db_helper = DatabaseHelper()
        
        # Tạo state property accessors
        self.conversation_data_accessor = self.conversation_state.create_property("ConversationData")
        self.user_data_accessor = self.user_state.create_property("UserData")

    async def on_members_added_activity(
        self, members_added: [ChannelAccount], turn_context: TurnContext
    ):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                # Ngay khi user vào, hiển thị báo cáo tổng quát và menu
                stats = self.db_helper.get_summary_stats()
                message = "🤖 **XIN CHÀO! TÔI LÀ AUTOMATION BOT**\n\n"
                message += "📊 **BÁO CÁO NHANH HÔM NAY:**\n"
                message += f"- Tổng doanh thu: **${stats.get('total_revenue', 0):,.2f}**\n"
                message += f"- Số chai đã bán: **{stats.get('total_bottles', 0):,}**\n"
                message += f"- Tổng số cửa hàng: **{stats.get('total_stores', 0)}**\n\n"
                
                message += "🔍 **CÁC LỆNH HỖ TRỢ:**\n"
                message += "1️⃣ Gõ **Top** để xem 5 sản phẩm bán chạy nhất\n"
                message += "2️⃣ Gõ **Store [ID]** để xem doanh số cửa hàng (VD: Store 2501)\n"
                message += "3️⃣ Gõ **City [Tên]** để xem doanh số thành phố (VD: City Ames)\n"
                message += "4️⃣ Gõ **Help** để hiện lại menu này"
                
                await turn_context.send_activity(message)

    async def on_message_activity(self, turn_context: TurnContext):
        user_input = turn_context.activity.text.strip()
        user_input_lower = user_input.lower()
        
        # 1. Lệnh TOP
        if user_input_lower == "top":
            products = self.db_helper.get_top_products()
            message = "🏆 **TOP 5 SẢN PHẨM DOANH THU CAO NHẤT:**\n\n"
            for i, p in enumerate(products, 1):
                message += f"{i}. {p['name']}: **${p['revenue']:,.2f}**\n"
            await turn_context.send_activity(message)

        # 2. Lệnh STORE
        elif user_input_lower.startswith("store "):
            try:
                store_id = user_input.split()[1]
                sales = self.db_helper.get_sales_by_store(store_id)
                message = self._format_sales_results(sales, f"Cửa hàng #{store_id}")
                await turn_context.send_activity(message)
            except IndexError:
                await turn_context.send_activity("❌ Thiếu Store ID. VD: **Store 2501**")

        # 3. Lệnh CITY
        elif user_input_lower.startswith("city "):
            try:
                city_name = " ".join(user_input.split()[1:])
                sales = self.db_helper.get_sales_by_city(city_name)
                message = self._format_sales_results(sales, f"Thành phố {city_name}")
                await turn_context.send_activity(message)
            except IndexError:
                await turn_context.send_activity("❌ Thiếu tên thành phố. VD: **City Ames**")

        # 4. Lệnh HELP
        elif user_input_lower in ["help", "menu", "hello", "hi", "xin chào", "chào"]:
            await self.on_members_added_activity(None, turn_context)

        # 5. Xử lý các trường hợp khác
        else:
            await turn_context.send_activity(
                "❓ Tôi không hiểu lệnh đó. Bạn có thể thử:\n"
                "- **Top**\n"
                "- **Store [ID]**\n"
                "- **City [Tên]**\n"
                "- **Help**"
            )
        
        # Lưu state
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)

    def _format_sales_results(self, sales, criteria):
        """Format kết quả tra cứu doanh số"""
        if not sales:
            return f"❓ Không tìm thấy dữ liệu cho **{criteria}**."
        
        message = f"📋 **KẾT QUẢ GẦN ĐÂY - {criteria.upper()}:**\n\n"
        for s in sales:
            message += f"📅 Ngày: {s['date']}\n"
            message += f"🏪 CH: {s['store_name']}\n"
            message += f"🍾 SP: {s['product_name']}\n"
            message += f"💰 Doanh thu: **${s['revenue']:,.2f}**\n"
            if 'bottles' in s:
                message += f"📦 Số chai: {s['bottles']}\n"
            message += "---\n"
        return message

    async def on_turn(self, turn_context: TurnContext):
        await super().on_turn(turn_context)
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)
