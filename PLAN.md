Here is a project I've been working on.

The goal is to create a music reactive light system using LED rubans, an ESP32 and a rasberry PI.

The system is composed of several segments of LEDs. Each one works independantly (with modes) or in group (with global modes).

For now, the esp32 is in charge of listening and sending the fft to the rasberryPI that calculates the choreography of the leds.

The ESP32 listens for delta_t and makes a fft and divides it into 8 values (from the low to the high frequencies) and sends it to the rasberry.
