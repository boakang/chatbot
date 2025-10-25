# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.core import ActivityHandler, TurnContext, ConversationState, UserState
from botbuilder.schema import ChannelAccount
from database import DatabaseHelper


class TicketBot(ActivityHandler):
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
                conversation_data["step"] = "waiting_key"
                await turn_context.send_activity("🔑 Vui lòng nhập Admin Key:")
            elif user_input.lower() == "user":
                conversation_data["role"] = "user"
                conversation_data["step"] = "waiting_employee_id"
                await turn_context.send_activity("👤 Vui lòng nhập Mã nhân viên của bạn:")
            else:
                await turn_context.send_activity(
                    "❌ Role không hợp lệ. Vui lòng chọn:\n"
                    "- **Admin**\n"
                    "- **User**"
                )
        
        # ============ ADMIN FLOW ============
        elif conversation_data.get("role") == "admin":
            current_step = conversation_data.get("step")
            
            # Xác thực admin key
            if current_step == "waiting_key":
                if self.db_helper.verify_admin_key(user_input):
                    conversation_data["admin_key"] = user_input
                    conversation_data["step"] = "admin_menu"
                    
                    # Hiển thị danh sách tickets pending
                    pending_tickets = self.db_helper.get_pending_tickets()
                    message = "✅ Key hợp lệ!\n\n"
                    message += self._format_pending_tickets(pending_tickets)
                    message += "\n\n📝 **Hướng dẫn:**\n"
                    message += "- Gõ **Accept [TicketID]** để phê duyệt (VD: Accept 1)\n"
                    message += "- Gõ **Reject [TicketID]** để từ chối (VD: Reject 2)\n"
                    message += "- Gõ **List** để xem lại danh sách\n"
                    message += "- Gõ **Exit** để kết thúc"
                    
                    await turn_context.send_activity(message)
                else:
                    await turn_context.send_activity(
                        "❌ Admin Key không hợp lệ. Vui lòng thử lại:"
                    )
            
            # Admin menu
            elif current_step == "admin_menu":
                user_input_lower = user_input.lower()
                
                # List tickets
                if user_input_lower == "list":
                    pending_tickets = self.db_helper.get_pending_tickets()
                    message = self._format_pending_tickets(pending_tickets)
                    await turn_context.send_activity(message)
                
                # Accept ticket
                elif user_input_lower.startswith("accept "):
                    try:
                        ticket_id = int(user_input.split()[1])
                        admin_key = conversation_data.get("admin_key")
                        
                        if self.db_helper.approve_ticket(ticket_id, admin_key):
                            pending_tickets = self.db_helper.get_pending_tickets()
                            message = f"✅ Đã phê duyệt Ticket #{ticket_id} thành công!\n\n"
                            message += self._format_pending_tickets(pending_tickets)
                            await turn_context.send_activity(message)
                        else:
                            await turn_context.send_activity(
                                f"❌ Không thể phê duyệt Ticket #{ticket_id}. "
                                "Ticket có thể không tồn tại hoặc đã được xử lý."
                            )
                    except (ValueError, IndexError):
                        await turn_context.send_activity(
                            "❌ Format không đúng. Vui lòng gõ: **Accept [TicketID]**"
                        )
                
                # Reject ticket
                elif user_input_lower.startswith("reject "):
                    try:
                        ticket_id = int(user_input.split()[1])
                        admin_key = conversation_data.get("admin_key")
                        
                        if self.db_helper.reject_ticket(ticket_id, admin_key):
                            pending_tickets = self.db_helper.get_pending_tickets()
                            message = f"❌ Đã từ chối Ticket #{ticket_id}!\n\n"
                            message += self._format_pending_tickets(pending_tickets)
                            await turn_context.send_activity(message)
                        else:
                            await turn_context.send_activity(
                                f"❌ Không thể từ chối Ticket #{ticket_id}. "
                                "Ticket có thể không tồn tại hoặc đã được xử lý."
                            )
                    except (ValueError, IndexError):
                        await turn_context.send_activity(
                            "❌ Format không đúng. Vui lòng gõ: **Reject [TicketID]**"
                        )
                
                # Exit
                elif user_input_lower == "exit":
                    await turn_context.send_activity(
                        "👋 Cảm ơn bạn đã sử dụng hệ thống. Tạm biệt!"
                    )
                    conversation_data.clear()
                
                else:
                    await turn_context.send_activity(
                        "❌ Lệnh không hợp lệ. Vui lòng chọn:\n"
                        "- **Accept [TicketID]**\n"
                        "- **Reject [TicketID]**\n"
                        "- **List**\n"
                        "- **Exit**"
                    )
        
        # ============ USER FLOW ============
        elif conversation_data.get("role") == "user":
            current_step = conversation_data.get("step")
            
            # Xác thực mã nhân viên
            if current_step == "waiting_employee_id":
                employee = self.db_helper.verify_employee(user_input)
                
                if employee:
                    conversation_data["employee_id"] = employee["employee_id"]
                    conversation_data["employee_name"] = employee["employee_name"]
                    conversation_data["step"] = "user_menu"
                    
                    await turn_context.send_activity(
                        f"✅ Xin chào **{employee['employee_name']}**!\n\n"
                        "Vui lòng chọn chức năng:\n"
                        "1️⃣ Gõ **Tạo ticket** để tạo yêu cầu mới\n"
                        "2️⃣ Gõ **Check ticket** để xem danh sách ticket của bạn\n"
                        "3️⃣ Gõ **Exit** để kết thúc"
                    )
                else:
                    await turn_context.send_activity(
                        "❌ Mã nhân viên không hợp lệ. Vui lòng thử lại:"
                    )
            
            # User menu
            elif current_step == "user_menu":
                user_input_lower = user_input.lower()
                
                # Tạo ticket
                if "tạo ticket" in user_input_lower or "tao ticket" in user_input_lower:
                    conversation_data["step"] = "creating_ticket"
                    await turn_context.send_activity(
                        "📝 Vui lòng nhập nội dung yêu cầu của bạn:"
                    )
                
                # Check ticket
                elif "check ticket" in user_input_lower:
                    employee_id = conversation_data.get("employee_id")
                    tickets = self.db_helper.get_user_tickets(employee_id)
                    
                    message = self._format_user_tickets(tickets)
                    await turn_context.send_activity(message)
                
                # Exit
                elif user_input_lower == "exit":
                    await turn_context.send_activity(
                        "👋 Cảm ơn bạn đã sử dụng hệ thống. Tạm biệt!"
                    )
                    conversation_data.clear()
                
                else:
                    await turn_context.send_activity(
                        "❌ Lựa chọn không hợp lệ. Vui lòng chọn:\n"
                        "- **Tạo ticket**\n"
                        "- **Check ticket**\n"
                        "- **Exit**"
                    )
            
            # Tạo ticket - nhập nội dung
            elif current_step == "creating_ticket":
                employee_id = conversation_data.get("employee_id")
                
                if self.db_helper.create_ticket(employee_id, user_input):
                    conversation_data["step"] = "user_menu"
                    await turn_context.send_activity(
                        "✅ Tạo ticket thành công!\n\n"
                        "Ticket của bạn đang chờ phê duyệt.\n\n"
                        "Tiếp tục:\n"
                        "- **Tạo ticket** để tạo yêu cầu mới\n"
                        "- **Check ticket** để xem danh sách\n"
                        "- **Exit** để kết thúc"
                    )
                else:
                    await turn_context.send_activity(
                        "❌ Có lỗi xảy ra. Vui lòng thử lại."
                    )
        
        # Lưu conversation state
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)

    def _format_pending_tickets(self, tickets):
        """Format danh sách pending tickets"""
        if not tickets:
            return "📋 **Danh sách Tickets đang chờ:** Không có ticket nào"
        
        message = "📋 **Danh sách Tickets đang chờ phê duyệt:**\n\n"
        for ticket in tickets:
            message += f"🎫 **Ticket #{ticket['ticket_id']}**\n"
            message += f"   👤 NV: {ticket['employee_id']} - {ticket['employee_name']}\n"
            message += f"   📝 Nội dung: {ticket['content']}\n"
            message += f"   📅 Ngày tạo: {ticket['created_at']}\n\n"
        
        return message
    
    def _format_user_tickets(self, tickets):
        """Format danh sách tickets của user"""
        if not tickets:
            return "📋 **Danh sách Tickets của bạn:** Chưa có ticket nào"
        
        message = "📋 **Danh sách Tickets của bạn:**\n\n"
        for ticket in tickets:
            status_icon = {
                'Pending': '⏳',
                'Approved': '✅',
                'Rejected': '❌'
            }.get(ticket['status'], '❓')
            
            message += f"🎫 **Ticket #{ticket['ticket_id']}** {status_icon}\n"
            message += f"   📝 Nội dung: {ticket['content']}\n"
            message += f"   📊 Trạng thái: {ticket['status']}\n"
            message += f"   📅 Ngày tạo: {ticket['created_at']}\n"
            message += f"   🔄 Cập nhật: {ticket['updated_at']}\n\n"
        
        return message

    async def on_turn(self, turn_context: TurnContext):
        await super().on_turn(turn_context)
        
        # Lưu changes sau mỗi turn
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)