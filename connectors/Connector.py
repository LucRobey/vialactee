import asyncio
import logging
from aiohttp import web
import os
import json
from core.Webapp_instruction_logger import WebappInstructionLogger

logger = logging.getLogger(__name__)

class Connector:
    HOST = '0.0.0.0'
    PORT = 8080

    def __init__(self , mode_master , infos):

        self.printAppDetails = infos["printAppDetails"]
        self.current_page = "Main"
        self.list_of_pages = ["Main","Playlists","Configuration","Shot","Parametres","Calibration"]

        self.list_of_segments = ["Segment h00","Segment v1","Segment h10","Segment h11","Segment v2",
                                 "Segment h20","Segment v3","Segment h30","Segment h31","Segment h32",
                                 "Segment v4"]
        
        self.mode_master = mode_master
        self.active_websockets = set()
        self.webapp_instruction_logger = WebappInstructionLogger()
        
    async def start_server(self):
        """Start the aiohttp web server with websockets."""
        app = web.Application()
        
        # Setup routes
        app.router.add_get('/', self.handle_index)
        app.router.add_get('/ws', self.websocket_handler)
        
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web')
        if os.path.exists(web_dir):
            app.router.add_static('/static/', path=web_dir, name='static')

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
        web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web')
        index_path = os.path.join(web_dir, 'index.html')
        if os.path.exists(index_path):
            return web.FileResponse(index_path)
        return web.Response(text="Web interface not found. Please create web/index.html", status=404)

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.active_websockets.add(ws)
        if self.printAppDetails:
            logger.debug(f"(C) New WebSocket connection")

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    message = msg.data.strip()
                    if not message:
                        continue
                    self.webapp_instruction_logger.log_raw_instruction(message)
                        
                    if self.printAppDetails:
                        logger.debug(f"(C) WS Message received: {message}")
                    
                    response = self.process_message(message)
                    
                    if response is not None:
                        await ws.send_str(str(response))
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f"ws connection closed with exception {ws.exception()}")
        finally:
            self.active_websockets.remove(ws)
            if self.printAppDetails:
                logger.debug(f"(C) WebSocket disconnected")

        return ws

    def process_message(self, message):
        """Process the incoming message and execute the appropriate command."""
        # New webapp controls currently send JSON instructions.
        # We log them elsewhere for now; skip the legacy colon parser.
        if message.lstrip().startswith("{"):
            try:
                json.loads(message)
                return None
            except json.JSONDecodeError:
                pass

        if(self.printAppDetails):
            logger.debug(f"(C) message reçu : {message}")
        splited_message = message.split(":")
        category = splited_message[0]
        rest_of_the_message = message[len(splited_message[0])+1:]

        if (category == "chgpage"):
            category = splited_message[1]
            page = splited_message[2]
            order , response = self.change_page(category,page)

        elif (category == "chgmode"):
            segment = splited_message[1]
            new_mode = splited_message[2]
            order , response = self.change_mode(segment , new_mode)
        
        elif (category == "chgway"):
            segment = splited_message[1]
            new_way = splited_message[2]
            order , response = self.change_way(segment , new_way)

        elif (category == "switchway"):
            segment = splited_message[1]
            order , response = self.switch_way(segment)

        elif (category == "chgconf"):
            mode_orders = splited_message[1]
            ways_orders = splited_message[2]
            order , response = self.change_conf(mode_orders,ways_orders)

        elif (category == "lockseg"):
            segment = splited_message[1]
            lock_unlock = splited_message[2]
            order , response = self.block_seg(segment,lock_unlock)

        elif (category == "chgparam"):
            parametre = splited_message[1]
            nouvelle_valeur = splited_message[2]
            order , response = self.change_param(parametre,nouvelle_valeur)

        elif (category == "calibration"):
            calibration_type = splited_message[1]
            phase = splited_message[2]
            order , response = self.calibrate_fft(calibration_type , phase)
            
        elif (category == "ping"):
            order = []
            response = "pong"
            
        elif (category == "special"):
            order , response = self.handle_special(rest_of_the_message)
            
        else:
            logger.warning("(C) invalid category")
            return None

        if(self.printAppDetails):
            logger.debug(f"(C)          state : {self.current_page}")
            logger.debug(f"(C)          order : {order}")
        self.mode_master.obey_orders(order)
        return response

    def get_current_modes(self):
        current_modes = []
        for segment in self.mode_master.segments_list:
            current_modes.append(segment.modes_names[segment.activ_mode])
        return current_modes
        
        
    def change_page(self , category , page):
        order = []
        response = None
        if (category == "enter"):
            self.current_page = page
            self.check_current_page()
            if(self.current_page == "Configuration"):
                response = self.get_current_modes()
            if (self.current_page == "Shot"):
                order.append("force:Segment h00:Shot")
                order.append("block:Segment h00")
                order.append("force:Segment h20:Shot")
                order.append("block:Segment h20")
        elif (category == "leave"):
            self.current_page = "Main"
            if(page == "Shot"):
                order.append("unblock:Segment h00")
                order.append("force:Segment h00:Rainbow")
                order.append("unblock:Segment h20")
                order.append("force:Segment h20:Rainbow")
        else :
            logger.warning("(C) ON ENTRE DANS AUCUNE CATEGORIE!")

        return order , response


    def check_current_page(self):
        if (not self.current_page in self.list_of_pages):
            logger.warning("(C) CURRENT PAGE PAS DANS LA LISTE")

    def change_mode(self , segment , new_mode):
        order = []
        response = None
        order.append("change_mode:"+segment+":"+new_mode)
        return order , response
    
    def change_way(self , segment , new_way):
        order = []
        response = None
        order.append("change_way:"+segment+":"+new_way)
        return order , response
    
    def switch_way(self , segment):
        order = []
        response = None
        order.append("switch_way:"+segment)
        return order , response
    
    def change_conf(self , mode_orders , ways_orders):
        order = []
        response = None
        modes = mode_orders[1:-1].split(',')  #on enleve les "{" et  "}" au debut et a la fin
        ways = ways_orders[1:-1].split(',')
        for segment_index in range(len(self.list_of_segments)):
            order.append("change_mode:"+self.list_of_segments[segment_index]+":"+modes[segment_index])
            order.append("change_way:"+self.list_of_segments[segment_index]+":"+ways[segment_index])
        return order , response
    
    def block_seg(self , segment , lock_unlock):
        order = []
        response = None
        if(lock_unlock == "true"):
            order.append("block:"+segment)
        elif(lock_unlock == "false"):
            order.append("unblock:"+segment)
        else:
            logger.warning("(C) ON N EST NI LOCK NI UNLOCK")
        return order , response
    
    def change_param(self , parametre , nouvelle_valeur):
        order = ["update:"+parametre+":"+str(nouvelle_valeur)]
        response = None
        return order , response
    
    def calibrate_fft(self , calibration_type , phase):
        order = []
        response = None
        if (phase == "start"):
            for segment_name in self.list_of_segments:              # On bloque les segments pdt la calibration
                order.append("block:"+segment_name)
            order.append("calibration:"+calibration_type+":"+phase)
        
        elif (phase == "end"):
            for segment_name in self.list_of_segments:
                order.append("unblock:"+segment_name)               # On les debloque à la fin
            order.append("calibration:"+calibration_type+":"+phase)

        else:
            logger.warning("(C) ON NE START NI END LA CALIBRATION!")
        return order , response

    
    def handle_special(self , message):
        return ["special:Shot"] , None
