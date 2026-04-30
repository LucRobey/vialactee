#ifndef BAND_WARS_H
#define BAND_WARS_H

/*          -=-=-=-=-=-=-=-=-=-=-=-=-Fonctionnement-=-=-=-=-=-=-=-=-=-=-=-=-

Dans ce mode, inspiré de la magnetic_ball, ce sont 2 bandes, l'une représentant les basses et l'autre les aigus, qui bataillent.
La taille de chacune représente la proportion de la longueur d'onde représentée.

Une boule centrale ayant la même valeur que cell de la magnetic_ball divise la barre en 2: le roouge en bas (les basses) et le
bleu en haut ( les aigus)

Ce qui peut être modifié:
  -transi drapeau fr?
  

*/

#include <Arduino.h>
#include <FastLED.h>
using namespace std;
#include <vector>
#include <mode.h>
#pragma once

class Band_wars : public Mode
{
public:
  Band_wars(vector<CRGB*> local_sorted_leds,byte ID, int* bandSmoothedValues, byte* asservedPower, byte* asservedBandPower);
  void update();
  void draw();
  void startTransition(int transitionTime, bool upOrDown, bool blackOrWhite);
  void resetTransition();
  void updateTransitionTimer();

private:

  
  //data
  int* bandSmoothedValues;
  byte *asservedPower;
  byte* asservedBandPower;

  float localAsservissement[16];

  float bassSize;
  float aiguSize;

  float acceleration;
  float speed;

  byte bassPower;                     
  byte aiguPower;

  byte bassColor;
  byte aiguColor;

  float coefToMiddle;
  int timeForCoef;
  bool lastSign;

  float bassValue;
  float aiguValue;

  float midBallPos;
  byte midBallColor;
  byte midPower;

  float musicCenter;
  float musicWeight;

  float fff;
  int maxSize;         

  //Transition

    //white
   byte whiteness; 

    //black
  float blackTransiPowerCoef;         //Coef d'influence sur l'intensité
};

#endif