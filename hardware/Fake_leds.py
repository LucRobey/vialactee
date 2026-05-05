import numpy as np
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

class FakeLedsVisualizer:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FakeLedsVisualizer, cls).__new__(cls)
            try:
                pygame.init()
            except:
                pass
            
            # Larger window to fit the mapped schematic
            cls._instance.screen = pygame.display.set_mode((1300, 900))
            pygame.display.set_caption("Vialactée - LED Simulator")
            cls._instance.strips = []
            cls._instance.clock = pygame.time.Clock()
            
            # Exact chandelier geometry mapping
            cls._instance.segments_def = [
                # Strip 0 (segs_1)
                [
                    (173, "vertical", 962, 164, "segment_v4", (50, 100, 255)),
                    (48, "horizontal", 866, 270, "segment_h32", (255, 50, 50)),
                    (48, "horizontal", 866, 442, "segment_h31", (255, 0, 255)),
                    (47, "horizontal", 866, 102, "segment_h30", (150, 150, 150)),
                    (173, "vertical", 684, 246, "segment_v3", (0, 255, 255)),
                    (91, "horizontal", 684, 132, "segment_h20", (150, 255, 150)),
                    (205, "horizontal", 100, 132, "segment_h00", (0, 0, 255))
                ],
                # Strip 1 (segs_2)
                [
                    (173, "vertical", 510, 132, "segment_v2", (0, 255, 0)),
                    (87, "horizontal", 510, 246, "segment_h11", (255, 150, 100)),
                    (86, "horizontal", 510, 478, "segment_h10", (150, 50, 200)),
                    (173, "vertical", 866, 132, "segment_v1", (255, 255, 0))
                ]
            ]
            
        return cls._instance

    def register_strip(self, nb_of_leds):
        strip_id = len(self.strips)
        self.strips.append(np.zeros((nb_of_leds, 3), dtype=int))
        return strip_id

    def update_strip(self, strip_id, data):
        self.strips[strip_id] = data
        
    def show(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
        
        self.screen.fill((15, 15, 15))
        
        for strip_id, strip_data in enumerate(self.strips):
            if strip_id >= len(self.segments_def):
                continue
                
            cursor = 0
            for (size, orientation, start_x, start_y, name, border_color) in self.segments_def[strip_id]:
                
                # Draw the Text Label Box
                if not hasattr(self, 'font'):
                    pygame.font.init()
                    self.font = pygame.font.SysFont('arial', 16, bold=True)
                
                text_surface = self.font.render(name, True, (0, 0, 0))
                text_rect = text_surface.get_rect()
                
                if orientation == "horizontal":
                    text_rect.center = (start_x + size, start_y + 25)
                elif orientation == "vertical_up":
                    text_rect.center = (start_x - 55, start_y - size)
                else: # fallback for normal vertical
                    text_rect.center = (start_x - 55, start_y + size)
                    
                bg_rect = text_rect.inflate(10, 8)
                pygame.draw.rect(self.screen, (245, 245, 245), bg_rect)
                pygame.draw.rect(self.screen, border_color, bg_rect, 2)
                self.screen.blit(text_surface, text_rect)
            
                x, y = start_x, start_y
                for _ in range(size):
                    if cursor >= len(strip_data):
                        break
                    
                    color = strip_data[cursor]
                    r = max(0, min(255, int(color[0])))
                    g = max(0, min(255, int(color[1])))
                    b = max(0, min(255, int(color[2])))
                    
                    pygame.draw.circle(self.screen, (r, g, b), (x, y), 2) # small dot
                    
                    if orientation == "horizontal":
                        x += 2
                    elif orientation == "vertical_up":
                        y -= 2
                    else:
                        y += 2
                        
                    cursor += 1
            
        pygame.display.flip()

visualizer = FakeLedsVisualizer()

from hardware.HardwareInterface import HardwareInterface

class Fake_leds(HardwareInterface):
    def __init__(self, nb_of_leds):
        self.nb_of_leds = nb_of_leds
        self.data = np.zeros((nb_of_leds, 3), dtype=int)
        self.strip_id = visualizer.register_strip(nb_of_leds)

    def __getitem__(self, index):
        return self.data[index]

    def __setitem__(self, index, value):
        self.data[index] = value

    def __len__(self):
        return len(self.data)

    def set_pixel(self, index, color):
        self.data[index] = color

    def clear(self):
        self.data.fill(0)
        self.show()

    def append(self, value):
        pass

    def show(self):
        visualizer.update_strip(self.strip_id, self.data)
        visualizer.show()
