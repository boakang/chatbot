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
                await turn_context.send_activity(
                    "🤖 Xin chào! Tôi là Automation Bot.\n\n"
                    "Vui lòng cho biết role của bạn:\n"
                    "- Gõ **Admin** nếu bạn là quản trị viên\n"
                    "- Gõ **User** nếu bạn là nhân viên"
                )

    async def on_message_activity(self, turn_context: TurnContext):
        # Lấy conversation data
        conversation_data = await self.conversation_data_accessor.get(
            turn_context, lambda: {}
        )
        
        user_input = turn_context.activity.text.strip()
        
        # ============ CHỌN ROLE ============
        if not conversation_data.get("role"):
            if user_input.lower() == "admin":
                conversation_data["role"] = "admin"
                conversation_data["step"] = "admin_menu"
                
                # Hiển thị thống kê nhanh cho Admin
                stats = self.db_helper.get_summary_stats()
                message = "📊 **BÁO CÁO TỔNG QUAN (ADMIN)**\n\n"
                message += f"💰 Tổng doanh thu: **${stats.get('total_revenue', 0):,.2f}**\n"
                message += f"🍾 Tổng số chai bán: **{stats.get('total_bottles', 0):,}**\n"
                message += f"🏠 Số cửa hàng ghi nhận: **{stats.get('total_stores', 0)}**\n\n"
                message += "Chọn chức năng:\n"
                message += "- Gõ **Top** để xem Top 5 sản phẩm bán chạy\n"
                message += "- Gõ **Exit** để thoát"
                await turn_context.send_activity(message)
                
            elif user_input.lower() == "user":
                conversation_data["role"] = "user"
                conversation_data["step"] = "user_menu"
                await turn_context.send_activity(
                    "🔍 **HỆ THỐNG TRA CỨU DOANH SỐ RƯỢU IOWA**\n\n"
                    "Dữ liệu sẵn sàng! Bạn có thể:\n"
                    "1️⃣ Gõ **Store [ID]** để tra cứu theo cửa hàng (VD: Store 2501)\n"
                    "2️⃣ Gõ **City [Tên]** để tra cứu theo thành phố (VD: City Ames)\n"
                    "3️⃣ Gõ **Exit** để kết thúc"
                )
            else:
                await turn_context.send_activity(
                    "❌ Vui lòng chọn Role để tiếp tục:\n"
                    "- **Admin** (Xem báo cáo tổng)\n"
                    "- **User** (Tra cứu chi tiết)"
                )
        
        # ============ ADMIN FLOW ============
        elif conversation_data.get("role") == "admin":
            user_input_lower = user_input.lower()
            
            if user_input_lower == "top":
                products = self.db_helper.get_top_products()
                message = "🏆 **TOP 5 SẢN PHẨM DOANH THU CAO NHẤT:**\n\n"
                for i, p in enumerate(products, 1):
                    message += f"{i}. {p['name']}: **${p['revenue']:,.2f}**\n"
                await turn_context.send_activity(message)
            
            elif user_input_lower == "exit":
                await turn_context.send_activity("👋 Đã thoát phiên Admin.")
                conversation_data.clear()
            else:
                await turn_context.send_activity("Lệnh không hợp lệ. Gõ **Top** hoặc **Exit**.")
        
        # ============ USER FLOW ============
        elif conversation_data.get("role") == "user":
            user_input_lower = user_input.lower()
            
            # Tra cứu theo Store
            if user_input_lower.startswith("store "):
                store_id = user_input.split()[1]
                sales = self.db_helper.get_sales_by_store(store_id)
                message = self._format_sales_results(sales, f"Cửa hàng #{store_id}")
                await turn_context.send_activity(message)
            
            # Tra cứu theo City
            elif user_input_lower.startswith("city "):
                city_name = " ".join(user_input.split()[1:])
                sales = self.db_helper.get_sales_by_city(city_name)
                message = self._format_sales_results(sales, f"Thành phố {city_name}")
                await turn_context.send_activity(message)
            
            elif user_input_lower == "exit":
                await turn_context.send_activity("👋 Cảm ơn bạn đã sử dụng hệ thống tra cứu!")
                conversation_data.clear()
            else:
                await turn_context.send_activity(
                    "❌ Vui lòng gõ đúng định dạng:\n"
                    "- **Store [ID]** (VD: Store 2501)\n"
                    "- **City [Tên]** (VD: City Ames)\n"
                    "- **Exit**"
                )
        
        # Lưu conversation state
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
            message += "---"
        return message

    async def on_turn(self, turn_context: TurnContext):
        await super().on_turn(turn_context)
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)
