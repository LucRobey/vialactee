import asyncio
import json
import logging
import os
from aiohttp import web
from core.Webapp_instruction_logger import WebappInstructionLogger

logger = logging.getLogger(__name__)


class Connector:
    HOST = "0.0.0.0"
    PORT = 8080

    def __init__(self, mode_master, infos):
        self.mode_master = mode_master
        self.printAppDetails = infos.get("printAppDetails", False)
        self.active_websockets = set()
        self.webapp_instruction_logger = WebappInstructionLogger()
        self.last_instruction = None

    async def start_server(self):
        """Start the aiohttp web server with websocket instruction endpoint."""
        app = web.Application()
        app.router.add_get("/", self.handle_index)
        app.router.add_get("/ws", self.websocket_handler)

        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
        if os.path.exists(web_dir):
            app.router.add_static("/static/", path=web_dir, name="static")

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.HOST, self.PORT)
        await site.start()
        logger.info(f"Web Server started on http://{self.HOST}:{self.PORT}")

        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()

    async def handle_index(self, request):
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
        index_path = os.path.join(web_dir, "index.html")
        if os.path.exists(index_path):
            return web.FileResponse(index_path)
        return web.Response(text="Web interface not found. Please create web/index.html", status=404)

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.active_websockets.add(ws)
        if self.printAppDetails:
            logger.debug("(C) New WebSocket connection")

        try:
            async for msg in ws:
                if msg.type != web.WSMsgType.TEXT:
                    if msg.type == web.WSMsgType.ERROR:
                        logger.error(f"ws connection closed with exception {ws.exception()}")
                    continue

                raw_message = msg.data.strip()
                if not raw_message:
                    continue

                self.webapp_instruction_logger.log_raw_instruction(raw_message)
                instruction = self.parse_instruction(raw_message)
                if instruction is None:
                    await ws.send_json({"ok": False, "error": "invalid_instruction_json"})
                    continue

                self.last_instruction = instruction
                if self.printAppDetails:
                    logger.info(
                        "(C) instruction received page=%s action=%s",
                        instruction["page"],
                        instruction["action"],
                    )

                apply_result = await self.mode_master.process_instruction(instruction)
                await ws.send_json({
                    "ok": bool(apply_result.get("applied", False)),
                    "received": instruction["action"],
                    "result": apply_result,
                })
        finally:
            self.active_websockets.discard(ws)
            if self.printAppDetails:
                logger.debug("(C) WebSocket disconnected")

        return ws

    def parse_instruction(self, raw_message):
        """Parse controlBridge instruction JSON payload."""
        try:
            data = json.loads(raw_message)
        except json.JSONDecodeError:
            logger.warning("(C) Invalid JSON instruction received")
            return None

        if not isinstance(data, dict):
            logger.warning("(C) Invalid instruction type (expected object)")
            return None

        page = data.get("page")
        action = data.get("action")
        payload = data.get("payload", {})
        timestamp = data.get("timestamp")

        if not isinstance(page, str) or not isinstance(action, str):
            logger.warning("(C) Invalid instruction fields: page/action")
            return None
        if not isinstance(payload, dict):
            logger.warning("(C) Invalid instruction field: payload")
            return None
        if not isinstance(timestamp, (int, float)):
            logger.warning("(C) Invalid instruction field: timestamp")
            return None

        return {
            "page": page,
            "action": action,
            "payload": payload,
            "timestamp": int(timestamp),
        }
