//-------------------------------------------------------------------------------------------------------------------------------------
//
//  LegoLED.static_wave.h
//
//  File : static_wave.h
//
//  Description:
//
//  Objet Static_wave
//  Une ”Static Wave” est une vague dont le centre ne bouge pas. Elle représente, en général, une valeur sortant de la FFT.
//  Elle grandit de part et d'autre du centre en fonction de la valeur qu'on lui donne.
//
//  Setup:
//
//  History: creation  :12/10/2022       ||    last modif : 30/10/2022 (Luc)
//
//
// Idées d'améliorations :
//
//--------------------------------------------------------------------------------------------------------------------------------------

#ifndef STATIC_WAVE_H
#define STATIC_WAVE_H
#include <Arduino.h>
#include <FastLED.h>
using namespace std;
#include <vector>
#include <mode.h>

class Static_wave : public Mode
{
public:
  Static_wave(vector<CRGB*> local_sorted_leds,byte ID, byte* asservedBandValues);
  Static_wave(vector<CRGB*> local_sorted_leds,byte ID, byte* asservedBandValues, byte color);
  void update();
  void draw();
  void startTransition(int transitionTime, bool upOrDown, bool blackOrWhite);
  void resetTransition();
  void activate();

private:
  //data
  byte* asservedBandValues;
  
  int middle;
  int max_size;            // Limite de la taille atteignable par la static wave
  int color;

  float size;    // Taille de la limite supérieure blanche qui met plus de temps à redescendre pour un effet visuel sympa
  int real_size; // Taille réel de la vague centrale

  // Transition:
  float blackTransitionPowerCoef;
  int transitionLimitSW;
  int valuef;

  int power;

  long timeL;
};

#endif