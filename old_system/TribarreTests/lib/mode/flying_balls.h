#ifndef FLYING_BALLS_H
#define FLYING_BALLS_H
//+------------------------------------------------------------------------------------------------------------------------------------
//
//  LegoLED.flying_ball.h
//
//  File : flying_ball.h
//
//  Description:
//
//  Represent the results of the FFT.
//  Une balle qui est sur la moyenne pondérée des fréquences
//
//  History: creation  :15/02/23       ||    last modif : 15/02/23 (Luc)
//
//
// Idées d'améliorations :
//      
//--------------------------------------------------------------------------------------------------------------------------------------
#include <Arduino.h>
#include <FastLED.h>
using namespace std;
#include <vector>
#include <mode.h>
#pragma once

class Flying_balls : public Mode
{
public:
  Flying_balls(byte ID, int* bandSmoothedValues, byte* asservedPower);
  void update();
  void draw();
  void activate(vector<CRGB*> local_sorted_leds);
  void deactivate();
  void startTransition(int transitionTime, bool upOrDown, bool blackOrWhite);
  void resetTransition();
  void updateTransitionTimer();

private:

  float localAsservissement[16];
  //data
  int* bandSmoothedValues;
  byte *asservedPower;

  float musicBassCenter;           //Calcul le "centre de gravité de la barre"
  float musicAiguCenter;           //Calcul le "centre de gravité de la barre"

  int colorMemory1;                    //Permet de smoothiser la couleur
  int colorMemory2;                    //Permet de smoothiser la couleur

  float bassWeight;                  //Permet de smoothiser l'intensité
  float aiguWeight;                  //Permet de smoothiser l'intensité
  float middleWeight;

  int bassPower;                      //puissance de l'intensité de la barre (moyenne enntre 255 et soundWeight)
  int aiguPower;

  float bassCoef;
  float aiguCoef;
  float totalWeight;
  float fff;

  float ballPosition1;
  float ballPosition2;
  int size;                           //Taille théorique (fonctionne comme une accélération, un objectif)
  int realSize;                       //Taille smoothisée
  int maxSize;         

  //Transition

    //white
  float speedWhiteTransi;             //Vitesse de croissance la barre de blanc
  float whiteTransiPos;               //Position limite du mur blanc
  bool firstPhase;
  bool stopDoingStuffDuringTransi;    //Permet d'arreter de faire des calculs quand on a fini
    

    //black
  float speedBlackTransi;             //Vitesse de grandissement de la barre, et du mur noir (fin de vie)
  float blackTransiPowerCoef;         //Coef d'influence sur l'intensité
  float blackTransiPosCoef;           //Coef d'influence sur la taille de la barre (fin de vie)
  int blackWall;                      //Position de la limite du blackWall(fin de vie)
  float blackTransiPos;               //Position limite de l'influence sur la taille de la barre (fin de vie)

  
};

#endif