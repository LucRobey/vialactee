//#include <main_bluetooth.h>
#include "Arduino.h"
#include "FastLED.h"
#include "arduinoFFT.h"
#include "analyser.h"
#include <string>

using namespace std;
#include <vector>
#include <master_mode.h>

Analyser analyser = Analyser();
Master_mode Current_mode = Master_mode(analyser.get_bandValues(),analyser.get_samplePeak(), analyser.getAsservedBandPowers() , analyser.getSmoothedBandValues() , analyser.getAsservedPower() , analyser.getAnalyserNeeds() , analyser.getBandAnalyserNeeds()); // Initialisation du Main_mode contenant tous les modes

//    DEF
#define LED_PIN 32                               // LED strip data
#define COLOR_ORDER GRB                          // If colours look wrong, play with this
#define CHIPSET WS2812B                          // LED strip type
#define NUM_LEDS 250                              // Total number of LEDs   20x4
#define MAX_MILLIAMPS 2000                       // Careful with the amount of power here if running off USB port
const int BRIGHTNESS_SETTINGS[3] = {5, 70, 200}; // 3 Integer array for 3 brightness settings (based on pressing+holding BTN_PIN)
#define LED_VOLTS 5                              // Usually 5 or 12
CRGB leds[NUM_LEDS];

//    Test de performance (voir ligne 86)
int test = 0;
long timeTest = 0;
long timeMode;


void setup()
{
  //Serial.begin(9600);
  //FastLED
  FastLED.addLeds<CHIPSET, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection(TypicalSMD5050);
  FastLED.setMaxPowerInVoltsAndMilliamps(LED_VOLTS, MAX_MILLIAMPS);
  FastLED.setBrightness(BRIGHTNESS_SETTINGS[2]);
  timeMode = millis();
}

void loop()
{
  // Calcul le temps mis pour effectuer 100 itérations:
  /*
  if (test == 0)
  {
    //Serial.print("Temps pour 1000 itérations : ");
    //Serial.print(float(millis() - timeTest) / 1000);
    //Serial.println(" s");
    timeTest = millis();
  }
  if (test >= 1000)
  {
    test = -1;
  }
  test += 1;
  */

  // On écoute et on fait les analyses nécessaires
  analyser.analyse();
  Current_mode.update();
  // On le montre en choisissant le bon fadeToBlack
  FastLED.show();
}




