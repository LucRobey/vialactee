#include <WiFi.h>
#include <AsyncUDP.h>
#define FASTLED_INTERNAL // Suppress harmless SPI pin notices during compilation
#include <FastLED.h>

// -----------------------------------------------------------------------------
// USER CONFIGURATION & SECRETS
// -----------------------------------------------------------------------------
#include "secrets.h"

// Hardware Pin & LED Configuration (Profile: "full")
// Strip 1: 785 LEDs on GPIO 2 (Port 9001)
// Strip 2: 519 LEDs on GPIO 4 (Port 9002)
#define PIN_STRIP_1 2
#define PIN_STRIP_2 4

#define NUM_LEDS_1 785
#define NUM_LEDS_2 519

#define PORT_STRIP_1 9001
#define PORT_STRIP_2 9002

// Stream timeout threshold: if no packet is received within this window,
// switch back to solid GREEN (ready & waiting for stream).
#define STREAM_TIMEOUT_MS 1000

// -----------------------------------------------------------------------------
// GLOBALS & STATE
// -----------------------------------------------------------------------------
CRGB leds1[NUM_LEDS_1];
CRGB leds2[NUM_LEDS_2];

AsyncUDP udp1;
AsyncUDP udp2;

volatile uint32_t lastPacketTimeMs = 0;
volatile bool newPacketReceived = false;

enum DeviceState {
    STATE_DISCONNECTED, // RED: Wi-Fi disconnected or connecting
    STATE_WAITING,      // GREEN: Wi-Fi connected, waiting for stream
    STATE_STREAMING     // LIVE: UDP frames actively displaying
};

DeviceState currentState = STATE_DISCONNECTED;

void showStatusColor(CRGB color) {
    fill_solid(leds1, NUM_LEDS_1, color);
    fill_solid(leds2, NUM_LEDS_2, color);
    FastLED.show();
}

void setup() {
    Serial.begin(115200);
    delay(100);
    Serial.println();
    Serial.println("==================================================");
    Serial.println("   Vialactee ESP32 Firmware — Profile: FULL       ");
    Serial.println("==================================================");
    Serial.printf("Strip 1: %d LEDs on GPIO %d | UDP Port %d\n", NUM_LEDS_1, PIN_STRIP_1, PORT_STRIP_1);
    Serial.printf("Strip 2: %d LEDs on GPIO %d | UDP Port %d\n", NUM_LEDS_2, PIN_STRIP_2, PORT_STRIP_2);

    // Initialize FastLED for both strips
    FastLED.addLeds<WS2812B, PIN_STRIP_1, GRB>(leds1, NUM_LEDS_1);
    FastLED.addLeds<WS2812B, PIN_STRIP_2, GRB>(leds2, NUM_LEDS_2);
    FastLED.setBrightness(100);

    // Immediate diagnostic: solid RED while Wi-Fi is disconnected
    currentState = STATE_DISCONNECTED;
    showStatusColor(CRGB::Red);

    // Connect to Wi-Fi
    WiFi.disconnect(true);
    delay(100);
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    Serial.print("Connecting to Wi-Fi");
    int retries = 0;
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        retries++;
        if (retries > 20) {
            Serial.printf("\nWi-Fi connection taking long (status: %d). Retrying...\n", WiFi.status());
            WiFi.disconnect();
            delay(100);
            WiFi.begin(ssid, password);
            retries = 0;
        }
    }

    Serial.println("\n[Wi-Fi] Connected successfully!");
    Serial.print("[Wi-Fi] IP Address: ");
    Serial.println(WiFi.localIP());

    // Wi-Fi connected: turn solid GREEN (waiting for stream)
    currentState = STATE_WAITING;
    showStatusColor(CRGB::Green);

    // Start UDP Listener for Strip 1 on Port 9001
    if (udp1.listen(PORT_STRIP_1)) {
        Serial.printf("[UDP] Listening for Strip 1 on UDP port %d...\n", PORT_STRIP_1);
        udp1.onPacket([](AsyncUDPPacket packet) {
            if (packet.length() >= 2) {
                uint16_t startIndex = packet.data()[0] | (packet.data()[1] << 8);
                int numLedsInPacket = (packet.length() - 2) / 3;

                if (startIndex + numLedsInPacket <= NUM_LEDS_1) {
                    memcpy(&leds1[startIndex], packet.data() + 2, numLedsInPacket * 3);
                    lastPacketTimeMs = millis();
                    newPacketReceived = true;
                }
            }
        });
    } else {
        Serial.printf("[UDP] ERROR: Failed to bind port %d!\n", PORT_STRIP_1);
    }

    // Start UDP Listener for Strip 2 on Port 9002
    if (udp2.listen(PORT_STRIP_2)) {
        Serial.printf("[UDP] Listening for Strip 2 on UDP port %d...\n", PORT_STRIP_2);
        udp2.onPacket([](AsyncUDPPacket packet) {
            if (packet.length() >= 2) {
                uint16_t startIndex = packet.data()[0] | (packet.data()[1] << 8);
                int numLedsInPacket = (packet.length() - 2) / 3;

                if (startIndex + numLedsInPacket <= NUM_LEDS_2) {
                    memcpy(&leds2[startIndex], packet.data() + 2, numLedsInPacket * 3);
                    lastPacketTimeMs = millis();
                    newPacketReceived = true;
                }
            }
        });
    } else {
        Serial.printf("[UDP] ERROR: Failed to bind port %d!\n", PORT_STRIP_2);
    }
}

void loop() {
    uint32_t now = millis();

    // 1. Wi-Fi connection check
    if (WiFi.status() != WL_CONNECTED) {
        if (currentState != STATE_DISCONNECTED) {
            currentState = STATE_DISCONNECTED;
            Serial.println("[Status] Wi-Fi lost -> LEDs RED");
            showStatusColor(CRGB::Red);
        }
        // Auto-reconnect non-blocking check
        static uint32_t lastReconnectAttempt = 0;
        if (now - lastReconnectAttempt > 5000) {
            lastReconnectAttempt = now;
            WiFi.reconnect();
        }
        delay(20);
        return;
    }

    // 2. Stream activity check
    bool isStreamActive = (lastPacketTimeMs > 0) && ((now - lastPacketTimeMs) < STREAM_TIMEOUT_MS);

    if (isStreamActive) {
        if (currentState != STATE_STREAMING) {
            currentState = STATE_STREAMING;
            Serial.println("[Status] Stream active -> Displaying live frames");
        }

        if (newPacketReceived) {
            static uint32_t lastShowMs = 0;
            if (now - lastShowMs >= 15) { // Cap rendering at ~60 FPS
                newPacketReceived = false;
                lastShowMs = now;
                FastLED.show();
            }
        }
    } else {
        // Stream stopped or waiting for first frame
        if (currentState != STATE_WAITING) {
            currentState = STATE_WAITING;
            Serial.println("[Status] Stream idle -> LEDs GREEN");
            showStatusColor(CRGB::Green);
        }
    }

    delay(2);
}
