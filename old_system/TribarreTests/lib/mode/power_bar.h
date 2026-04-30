#ifndef POWER_BAR_H
#define POWER_BAR_H

//-------------------------------------------------------------------------------------------------------------------------------------
//
//  LegoLED.power_bar.h
//
//  File : power_bar.h
//
//  Description:
//
//
//  Setup:
//
//
//  History: creation  :15/10/2022       ||    last modif : 30/10/2022 (Luc)
//
//
// Idées d'améliorations :
//
//
//--------------------------------------------------------------------------------------------------------------------------------------


#include <Arduino.h>
#include <FastLED.h>
using namespace std;
#include <vector>
#include <mode.h>

class Power_bar : public Mode
{
public:
  Power_bar(vector<CRGB*> local_sorted_leds,byte ID, byte* asservedPower);
  void update();
  void draw();
  void startTransition(int transitionTime, bool upOrDown, bool blackOrWhite);
  void resetTransition();
  void activate();

private:
  //data
  byte *asservedPower;
  
  int max_size;        // Limite de la taille atteignable par la static wave

  int intensity;
  float white_dot_pos;    // Taille de la limite supérieure blanche qui met plus de temps à redescendre pour un effet visuel sympa
  float white_dot_speed;
  int real_size; // Taille réel de la vague centrale

  // Transition:
  int whiteTransitionUpperLimit; // Limite haute de coloriage en blanc pour la white Transition
  int blackTransitionLowerLimit; // Limite basse de coloriage en noir pour la black Transition
  float transitionPositionCoef;  // Coefficient permettant d'artificiellement augmenter la valeur de real_size
  float transitionProportion;    // La transitio est divisée en 2 phases. Permet de controler le temps de chaque phase
  int valuePower;

  byte testColorChange;
};

#endif