import json
import logging
import os

logger = logging.getLogger(__name__)

class Data_reader:

    configurations = {}
    playlists = []
    file_path = os.path.join(os.path.dirname(__file__), "configurations.json")

    def __init__(self, infos):
        self.printConfigurationLoads = infos.get("printConfigurationLoads", False)

        self.configurations, self.playlists = self.read_json()

    def read_json(self):
        try:
            if not os.path.exists(self.file_path):
                logger.error(f"Configuration file not found: {self.file_path}")
                return {}, []

            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            configurations = data.get('configurations', {})
            playlists = list(configurations.keys())
            
            if self.printConfigurationLoads:
                logger.debug(f"(DR) Loaded {len(playlists)} playlists from {self.file_path}")
                for playlist in playlists:
                    logger.debug(f"(DR)  Playlist: {playlist} -> {len(configurations.get(playlist, []))} modes")
                    
            return configurations, playlists
            
        except Exception as e:
            logger.error(f"Error reading JSON configuration file: {e}")
            return {}, []