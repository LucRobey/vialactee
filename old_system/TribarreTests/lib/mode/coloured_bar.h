#ifndef COLOURED_BAR_H
#define COLOURED_BAR_H

/*          -=-=-=-=-=-=-=-=-=-=-=-=-Fonctionnement-=-=-=-=-=-=-=-=-=-=-=-=-

Dans ce mode, inspiré de la coloured_middle_wave, toute la barre est de la couleur et de l'intensité d'une coloured_middle_wave

    Transitions:
On fait clignoter la barre en noir ou en blanc

White:
    FinDeVie:
      on fait alterner le drawWhite de plus en plus vite jusqu'à ce que ce soit tout blanc
             
    DébutDeVie:
      on fait alterner le drawWhite de moins en moins vite jusqu'à ce que ce la barre soit normale


Black:
    FinDeVie:
        on fait alterner le drawBlack de plus en plus vite jusqu'à ce que ce soit tout blanc
             
    DébutDeVie:
        on fait alterner le drawBlack de moins en moins vite jusqu'à ce que ce soit normal
             

Ce qui peut être modifié:
  -transi trop violente
*/

#include <Arduino.h>
#include <FastLED.h>
using namespace std;
#include <vector>
#include <mode.h>
#pragma once

class Coloured_bar : public Mode
{
public:
  Coloured_bar(vector<CRGB*> local_sorted_leds,byte ID, int* bandSmoothedValues, byte* asservedPower);
  void update();
  void draw();
  void activate();
  void deactivate();
  void startTransition(int transitionTime, bool upOrDown, bool blackOrWhite);
  void resetTransition();
  void updateTransitionTimer();

private:
  //data
  int* bandSmoothedValues;
  byte *asservedPower;

  float musicGravityCenter;           //Calcul le "centre de gravité de la barre"
  int colorMemory;                    //Permet de smoothiser la couleur
  float soundWeight;                  //Permet de smoothiser l'intensité
  int ledsPower;                      //puissance de l'intensité de la barre (moyenne enntre 255 et soundWeight)

  float fff;

  bool drawAllWhite;
  int timeBeforeWhite;
  int whiteFrequency;

  bool drawAllBlack;
  int timeBeforeBlack;
  int blackFrequency;


  
};

#endif