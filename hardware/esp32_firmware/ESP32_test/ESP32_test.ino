#define FASTLED_INTERNAL
#include <FastLED.h>

// =============================================================================
// HARDWARE TEST FOR SMALL PROFILE (249 LEDs, 3 Segments)
// No Wi-Fi, No UDP — Pure hardware validation
// =============================================================================

// Pin connected to WS2812B Data IN:
// Default: GPIO 2 (labeled "D2" on board)
// If D2 doesn't work, try D4, D18, or D21.
#define DATA_PIN 21

#define NUM_LEDS 249

// Segment sizes (from config/segments_small.json)
#define S1_SIZE 49    // Segment s1: LEDs 0 to 48
#define S2_SIZE 108   // Segment s2: LEDs 49 to 156
#define S3_SIZE 92    // Segment s3: LEDs 157 to 248

CRGB leds[NUM_LEDS];

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n============================================");
    Serial.println("   Vialactee ESP32 Hardware Segment Test    ");
    Serial.println("============================================");
    Serial.printf("Data Pin: GPIO %d\n", DATA_PIN);
    Serial.printf("Total LEDs: %d\n", NUM_LEDS);
    Serial.printf("  - Segment s1 (0-%d): RED (%d LEDs)\n", S1_SIZE - 1, S1_SIZE);
    Serial.printf("  - Segment s2 (%d-%d): GREEN (%d LEDs)\n", S1_SIZE, S1_SIZE + S2_SIZE - 1, S2_SIZE);
    Serial.printf("  - Segment s3 (%d-%d): BLUE (%d LEDs)\n", S1_SIZE + S2_SIZE, NUM_LEDS - 1, S3_SIZE);

    // Initialize FastLED
    // Set brightness to a safe 40/255 to avoid drawing too much current during testing
    FastLED.addLeds<WS2812B, DATA_PIN, GRB>(leds, NUM_LEDS);
    FastLED.setBrightness(50);

    // Clear all LEDs first
    fill_solid(leds, NUM_LEDS, CRGB::Black);
    FastLED.show();
    delay(200);

    // Segment s1 (0 to 48): RED
    for (int i = 0; i < S1_SIZE; i++) {
        leds[i] = CRGB::Red;
    }

    // Segment s2 (49 to 156): GREEN
    for (int i = S1_SIZE; i < S1_SIZE + S2_SIZE; i++) {
        leds[i] = CRGB::Green;
    }

    // Segment s3 (157 to 248): BLUE
    for (int i = S1_SIZE + S2_SIZE; i < NUM_LEDS; i++) {
        leds[i] = CRGB::Blue;
    }

    FastLED.show();
    Serial.println("Colors sent to strip! Check your LEDs now.");
}

void loop() {
    // Keep running and print a heartbeat every 2 seconds
    Serial.println("Heartbeat: test running. If LEDs are not lit, check wiring (DIN, GND, 5V).");
    
    // Toggle the first LED between Red and White each second as a life indicator
    static bool flip = false;
    flip = !flip;
    leds[0] = flip ? CRGB::White : CRGB::Red;
    FastLED.show();
    
    delay(1000);
}
