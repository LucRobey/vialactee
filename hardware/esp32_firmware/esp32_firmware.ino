#include <WiFi.h>
#include <AsyncUDP.h>
#define FASTLED_INTERNAL // Suppresses the harmless "No hardware SPI pins defined" message during compilation
#include <FastLED.h>

// -----------------------------------------------------------------------------
// USER CONFIGURATION
// -----------------------------------------------------------------------------
const char* ssid = "freebox_LAURE";
const char* password = "laure128";

// Physical ESP32 pins connected to the Data IN of the LED strips
#define PIN_STRIP_1 2
#define PIN_STRIP_2 4

// Hardware Configuration (Matches Python settings)
#define NUM_LEDS_1 785
#define NUM_LEDS_2 519

// UDP Ports
#define PORT_STRIP_1 9001
#define PORT_STRIP_2 9002

// -----------------------------------------------------------------------------
// GLOBALS
// -----------------------------------------------------------------------------
CRGB leds1[NUM_LEDS_1];
CRGB leds2[NUM_LEDS_2];

AsyncUDP udp1;
AsyncUDP udp2;

void setup() {
    Serial.begin(115200);
    
    // Initialize FastLED
    // Note: WS2812B typical color order is GRB. The python code sends RGB. 
    // FastLED's 'GRB' flag here automatically translates the RGB array in memory to the GRB signal on the wire.
    FastLED.addLeds<WS2812B, PIN_STRIP_1, GRB>(leds1, NUM_LEDS_1);
    FastLED.addLeds<WS2812B, PIN_STRIP_2, GRB>(leds2, NUM_LEDS_2);
    
    // Start with a safe brightness limit to prevent drawing too much current during boot
    FastLED.setBrightness(100); 
    
    // Set LEDs to Red to indicate we are trying to connect
    fill_solid(leds1, NUM_LEDS_1, CRGB::Red);
    fill_solid(leds2, NUM_LEDS_2, CRGB::Red);
    FastLED.show(); // <-- This was missing, so they never actually turned red!

    // Robust Wi-Fi Connection
    WiFi.disconnect(true); // Clear old stuck credentials
    delay(100);
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    
    Serial.print("Connecting to WiFi");
    int retries = 0;
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        retries++;
        // If it hangs for 10 seconds, force a reconnect attempt
        if (retries > 20) {
            Serial.printf("\nWi-Fi connection taking too long. Status Code: %d. Restarting Wi-Fi...\n", WiFi.status());
            WiFi.disconnect();
            delay(100);
            WiFi.begin(ssid, password);
            retries = 0;
        }
    }
    
    // Flash Green to indicate successful connection
    fill_solid(leds1, NUM_LEDS_1, CRGB::Green);
    fill_solid(leds2, NUM_LEDS_2, CRGB::Green);
    FastLED.show();
    delay(1000); // Wait 1 second so you can see the green
    
    // Clear the LEDs once connected successfully
    FastLED.clear();
    FastLED.show();
    Serial.println("\nConnected!");
    Serial.print("ESP32 IP Address: ");
    Serial.println(WiFi.localIP());

    // Listen on Port 9001 for Strip 1
    if(udp1.listen(PORT_STRIP_1)) {
        Serial.println("Listening for Strip 1 on UDP port 9001...");
        udp1.onPacket([](AsyncUDPPacket packet) {
            if (packet.length() >= 2) {
                uint16_t startIndex = packet.data()[0] | (packet.data()[1] << 8);
                int numLedsInPacket = (packet.length() - 2) / 3;
                
                if (startIndex + numLedsInPacket <= NUM_LEDS_1) {
                    memcpy(&leds1[startIndex], packet.data() + 2, numLedsInPacket * 3);
                }
            } else {
                Serial.printf("Strip 1: Received wrong size packet: %d bytes\n", packet.length());
            }
        });
    }

    // Listen on Port 9002 for Strip 2
    if(udp2.listen(PORT_STRIP_2)) {
        Serial.println("Listening for Strip 2 on UDP port 9002...");
        udp2.onPacket([](AsyncUDPPacket packet) {
            if (packet.length() >= 2) {
                uint16_t startIndex = packet.data()[0] | (packet.data()[1] << 8);
                int numLedsInPacket = (packet.length() - 2) / 3;
                
                if (startIndex + numLedsInPacket <= NUM_LEDS_2) {
                    memcpy(&leds2[startIndex], packet.data() + 2, numLedsInPacket * 3);
                }
            } else {
                Serial.printf("Strip 2: Received wrong size packet: %d bytes\n", packet.length());
            }
        });
    }
}

void loop() {
    // Blast the LEDs
    // Calling show() disables interrupts momentarily, so we throttle it slightly 
    // to give the Wi-Fi stack plenty of time to process UDP packets in the background.
    FastLED.show();
    delay(15); // Cap at roughly ~60 FPS
}
