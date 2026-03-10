# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.core import ActivityHandler, TurnContext, ConversationState, UserState
from botbuilder.schema import ChannelAccount
from database import DatabaseHelper

# ─── CONVERSATION STATES ────────────────────────────────────────────────────
STATE_MAIN_MENU         = "MAIN_MENU"
STATE_DATE_FROM         = "DATE_FROM"          # chờ nhập ngày bắt đầu
STATE_DATE_TO           = "DATE_TO"            # chờ nhập ngày kết thúc
STATE_COUNTY_LIST       = "COUNTY_LIST"        # hiện list county
STATE_CITY_LIST         = "CITY_LIST"          # hiện list city của county đã chọn
STATE_STORE_LIST        = "STORE_LIST"         # hiện list store của city đã chọn
STATE_TOP5              = "TOP5"               # kết quả top 5 bán nhiều
STATE_BOTTOM5           = "BOTTOM5"            # kết quả top 5 bán ít


def _fmt_date_range(from_date, to_date):
    """Chuỗi mô tả khoảng thời gian"""
    if from_date or to_date:
        f = from_date or "đầu"
        t = to_date or "nay"
        return f" (từ {f} đến {t})"
    return " (toàn bộ thời gian)"


class Bot(ActivityHandler):
    def __init__(self, conversation_state: ConversationState, user_state: UserState):
        self.conversation_state = conversation_state
        self.user_state = user_state
        self.db_helper = DatabaseHelper()
        self.conv_accessor = self.conversation_state.create_property("ConvData")

    # ─── WELCOME ─────────────────────────────────────────────────────────────

    async def on_members_added_activity(self, members_added, turn_context: TurnContext):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                conv = await self.conv_accessor.get(turn_context, dict)
                conv.clear()
                conv["state"] = STATE_MAIN_MENU
                await self.conv_accessor.set(turn_context, conv)
                await turn_context.send_activity(self._main_menu_message())

    # ─── MESSAGE HANDLER ─────────────────────────────────────────────────────

    async def on_message_activity(self, turn_context: TurnContext):
        text = turn_context.activity.text.strip() if turn_context.activity.text else ""
        text_lower = text.lower()

        # Lệnh reset về menu bất cứ lúc nào
        if text_lower in ["menu", "help", "hello", "hi", "xin chào", "chào", "restart"]:
            conv = await self.conv_accessor.get(turn_context, dict)
            conv.clear()
            conv["state"] = STATE_MAIN_MENU
            await self.conv_accessor.set(turn_context, conv)
            await turn_context.send_activity(self._main_menu_message())
        else:
            conv = await self.conv_accessor.get(turn_context, dict)
            if not conv.get("state"):
                conv["state"] = STATE_MAIN_MENU
            await self._dispatch(turn_context, conv, text, text_lower)

        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)

    # ─── STATE MACHINE DISPATCH ───────────────────────────────────────────────

    async def _dispatch(self, ctx: TurnContext, conv: dict, text: str, text_lower: str):
        state = conv.get("state", STATE_MAIN_MENU)

        # ── MAIN MENU ──
        if state == STATE_MAIN_MENU:
            if text in ["1", "2", "3"]:
                conv["menu_choice"] = text
                conv["state"] = STATE_DATE_FROM
                await self.conv_accessor.set(ctx, conv)
                await ctx.send_activity(
                    "📅 **Nhập ngày bắt đầu** (định dạng YYYY-MM-DD)\n"
                    "hoặc gõ **skip** để bỏ qua bộ lọc ngày:"
                )
            else:
                await ctx.send_activity(self._main_menu_message())

        # ── NHẬP NGÀY BẮT ĐẦU ──
        elif state == STATE_DATE_FROM:
            conv["from_date"] = None if text_lower == "skip" else text
            conv["state"] = STATE_DATE_TO
            await self.conv_accessor.set(ctx, conv)
            await ctx.send_activity(
                "📅 **Nhập ngày kết thúc** (định dạng YYYY-MM-DD)\n"
                "hoặc gõ **skip** để bỏ qua:"
            )

        # ── NHẬP NGÀY KẾT THÚC ──
        elif state == STATE_DATE_TO:
            conv["to_date"] = None if text_lower == "skip" else text
            await self.conv_accessor.set(ctx, conv)

            choice = conv.get("menu_choice")
            if choice == "1":
                # Doanh thu → hiện list county
                await self._show_county_list(ctx, conv)
            elif choice == "2":
                # Top 5 bán nhiều nhất
                await self._show_top5(ctx, conv)
            elif choice == "3":
                # Top 5 bán ít nhất
                await self._show_bottom5(ctx, conv)

        # ── CHỌN COUNTY ──
        elif state == STATE_COUNTY_LIST:
            counties = conv.get("counties", [])
            try:
                idx = int(text) - 1
                if 0 <= idx < len(counties):
                    conv["selected_county"] = counties[idx]
                    await self.conv_accessor.set(ctx, conv)
                    await self._show_city_list(ctx, conv)
                else:
                    await ctx.send_activity("❌ Số không hợp lệ. " + self._retype_hint(counties))
            except ValueError:
                await ctx.send_activity("❌ Vui lòng nhập **số thứ tự** của county.")

        # ── CHỌN CITY ──
        elif state == STATE_CITY_LIST:
            cities = conv.get("cities", [])
            # Option 0 = Exit (doanh thu toàn county)
            if text == "0":
                county = conv.get("selected_county", "")
                await self._show_county_revenue(ctx, conv, county)
            else:
                try:
                    idx = int(text) - 1
                    if 0 <= idx < len(cities):
                        conv["selected_city"] = cities[idx]
                        await self.conv_accessor.set(ctx, conv)
                        await self._show_store_list(ctx, conv)
                    else:
                        await ctx.send_activity("❌ Số không hợp lệ. " + self._retype_hint(cities, with_exit=True))
                except ValueError:
                    await ctx.send_activity("❌ Vui lòng nhập **số thứ tự** của thành phố hoặc **0** để xem doanh thu toàn county.")

        # ── CHỌN STORE ──
        elif state == STATE_STORE_LIST:
            stores = conv.get("stores", [])
            try:
                idx = int(text) - 1
                if 0 <= idx < len(stores):
                    store = stores[idx]
                    await self._show_store_revenue(ctx, conv, store)
                else:
                    await ctx.send_activity("❌ Số không hợp lệ. Vui lòng chọn lại.")
            except ValueError:
                await ctx.send_activity("❌ Vui lòng nhập **số thứ tự** của cửa hàng.")

        # ── KẾT QUẢ CUỐI (TOP / BOTTOM) → về menu ──
        elif state in [STATE_TOP5, STATE_BOTTOM5]:
            conv.clear()
            conv["state"] = STATE_MAIN_MENU
            await self.conv_accessor.set(ctx, conv)
            await ctx.send_activity(self._main_menu_message())

        else:
            conv.clear()
            conv["state"] = STATE_MAIN_MENU
            await self.conv_accessor.set(ctx, conv)
            await ctx.send_activity(self._main_menu_message())

    # ─── HELPER: SHOW SCREENS ─────────────────────────────────────────────────

    async def _show_county_list(self, ctx: TurnContext, conv: dict):
        from_date = conv.get("from_date")
        to_date = conv.get("to_date")
        counties = self.db_helper.get_counties(from_date, to_date)
        conv["counties"] = counties
        conv["state"] = STATE_COUNTY_LIST
        await self.conv_accessor.set(ctx, conv)

        if not counties:
            await ctx.send_activity("❌ Không có dữ liệu county trong khoảng thời gian này.")
            conv.clear()
            conv["state"] = STATE_MAIN_MENU
            await self.conv_accessor.set(ctx, conv)
            return

        date_info = _fmt_date_range(from_date, to_date)
        msg = f"🗺️ **DANH SÁCH COUNTY**{date_info}\n\n"
        msg += "Nhập **số thứ tự** để chọn county:\n\n"
        for i, c in enumerate(counties, 1):
            msg += f"  {i}. {c}\n"
        await ctx.send_activity(msg)

    async def _show_city_list(self, ctx: TurnContext, conv: dict):
        county = conv.get("selected_county", "")
        from_date = conv.get("from_date")
        to_date = conv.get("to_date")
        cities = self.db_helper.get_cities_by_county(county, from_date, to_date)
        conv["cities"] = cities
        conv["state"] = STATE_CITY_LIST
        await self.conv_accessor.set(ctx, conv)

        if not cities:
            await ctx.send_activity(f"❌ Không có dữ liệu thành phố cho county **{county}**.")
            return

        date_info = _fmt_date_range(from_date, to_date)
        msg = f"🏙️ **THÀNH PHỐ TRONG COUNTY {county.upper()}**{date_info}\n\n"
        msg += "Nhập **số thứ tự** để chọn thành phố:\n\n"
        for i, c in enumerate(cities, 1):
            msg += f"  {i}. {c}\n"
        msg += "\n**0.** ⬅️ Xem doanh thu toàn bộ county (bỏ qua chọn city)"
        await ctx.send_activity(msg)

    async def _show_store_list(self, ctx: TurnContext, conv: dict):
        city = conv.get("selected_city", "")
        county = conv.get("selected_county", "")
        from_date = conv.get("from_date")
        to_date = conv.get("to_date")
        stores = self.db_helper.get_stores_by_city(city, county, from_date, to_date)
        conv["stores"] = stores
        conv["state"] = STATE_STORE_LIST
        await self.conv_accessor.set(ctx, conv)

        if not stores:
            await ctx.send_activity(f"❌ Không có cửa hàng nào tại **{city}**.")
            return

        date_info = _fmt_date_range(from_date, to_date)
        msg = f"🏪 **CỬA HÀNG TẠI {city.upper()}**{date_info}\n\n"
        msg += "Nhập **số thứ tự** để xem doanh thu:\n\n"
        for i, s in enumerate(stores, 1):
            msg += f"  {i}. {s['store_name']} (ID: {s['store_id']})\n"
        await ctx.send_activity(msg)

    async def _show_county_revenue(self, ctx: TurnContext, conv: dict, county: str):
        from_date = conv.get("from_date")
        to_date = conv.get("to_date")
        data = self.db_helper.get_revenue_by_county(county, from_date, to_date)
        date_info = _fmt_date_range(from_date, to_date)

        if not data:
            await ctx.send_activity(f"❌ Không tìm thấy dữ liệu cho county **{county}**.")
        else:
            msg = f"📊 **DOANH THU COUNTY {county.upper()}**{date_info}\n\n"
            msg += f"💰 Tổng doanh thu: **${data['total_revenue']:,.2f}**\n"
            msg += f"📦 Số chai bán: **{data['total_bottles']:,}**\n"
            msg += f"🏪 Số cửa hàng: **{data['total_stores']}**\n\n"
            msg += "Gõ **Menu** để quay lại menu chính."
            await ctx.send_activity(msg)

        conv.clear()
        conv["state"] = STATE_MAIN_MENU
        await self.conv_accessor.set(ctx, conv)

    async def _show_store_revenue(self, ctx: TurnContext, conv: dict, store: dict):
        from_date = conv.get("from_date")
        to_date = conv.get("to_date")
        data = self.db_helper.get_revenue_by_store(store["store_id"], from_date, to_date)
        date_info = _fmt_date_range(from_date, to_date)

        if not data:
            await ctx.send_activity(f"❌ Không tìm thấy dữ liệu cho cửa hàng **{store['store_name']}**.")
        else:
            msg = f"🏪 **DOANH THU CỬA HÀNG**{date_info}\n\n"
            msg += f"🏷️ Tên: **{data['store_name']}** (ID: {store['store_id']})\n"
            msg += f"💰 Tổng doanh thu: **${data['total_revenue']:,.2f}**\n"
            msg += f"📦 Số chai bán: **{data['total_bottles']:,}**\n\n"
            msg += "Gõ **Menu** để quay lại menu chính."
            await ctx.send_activity(msg)

        conv.clear()
        conv["state"] = STATE_MAIN_MENU
        await self.conv_accessor.set(ctx, conv)

    async def _show_top5(self, ctx: TurnContext, conv: dict):
        from_date = conv.get("from_date")
        to_date = conv.get("to_date")
        products = self.db_helper.get_top_products(5, from_date, to_date)
        date_info = _fmt_date_range(from_date, to_date)

        if not products:
            await ctx.send_activity("❌ Không có dữ liệu sản phẩm.")
        else:
            msg = f"🏆 **TOP 5 RƯỢU BÁN NHIỀU NHẤT**{date_info}\n\n"
            for i, p in enumerate(products, 1):
                msg += f"{i}️⃣ **{p['name']}**\n"
                msg += f"   📦 Số chai: {p['bottles']:,}\n"
                msg += f"   💰 Doanh thu: ${p['revenue']:,.2f}\n\n"
            msg += "Gõ **Menu** để quay lại menu chính."
            await ctx.send_activity(msg)

        conv["state"] = STATE_TOP5
        await self.conv_accessor.set(ctx, conv)

    async def _show_bottom5(self, ctx: TurnContext, conv: dict):
        from_date = conv.get("from_date")
        to_date = conv.get("to_date")
        products = self.db_helper.get_bottom_products(5, from_date, to_date)
        date_info = _fmt_date_range(from_date, to_date)

        if not products:
            await ctx.send_activity("❌ Không có dữ liệu sản phẩm.")
        else:
            msg = f"📉 **TOP 5 RƯỢU BÁN ÍT NHẤT**{date_info}\n\n"
            for i, p in enumerate(products, 1):
                msg += f"{i}️⃣ **{p['name']}**\n"
                msg += f"   📦 Số chai: {p['bottles']:,}\n"
                msg += f"   💰 Doanh thu: ${p['revenue']:,.2f}\n\n"
            msg += "Gõ **Menu** để quay lại menu chính."
            await ctx.send_activity(msg)

        conv["state"] = STATE_BOTTOM5
        await self.conv_accessor.set(ctx, conv)

    # ─── UI HELPERS ───────────────────────────────────────────────────────────

    def _main_menu_message(self) -> str:
        msg  = "🤖 **XIN CHÀO! TÔI LÀ AUTOMATION BOT**\n\n"
        msg += "📋 **CHỌN CHỨC NĂNG:**\n\n"
        msg += "1️⃣  **Doanh thu** — Xem doanh thu theo County / City / Cửa hàng\n"
        msg += "2️⃣  **Top 5 rượu bán nhiều nhất**\n"
        msg += "3️⃣  **Top 5 rượu bán ít nhất**\n\n"
        msg += "👉 Nhập **1**, **2** hoặc **3** để bắt đầu.\n"
        msg += "_(Mỗi lựa chọn đều có thể lọc theo khoảng thời gian)_"
        return msg

    def _retype_hint(self, items: list, with_exit: bool = False) -> str:
        hint = f"Vui lòng nhập số từ 1 đến {len(items)}."
        if with_exit:
            hint += " Hoặc **0** để xem doanh thu toàn county."
        return hint

    async def on_turn(self, turn_context: TurnContext):
        await super().on_turn(turn_context)
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)
