#ifndef FLYING_BALL_H
#define FLYING_BALL_H
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

class Flying_ball : public Mode
{
public:
  Flying_ball(byte ID, int* bandSmoothedValues, byte* asservedPower);
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

  float musicGravityCenter;           //Calcul le "centre de gravité de la barre"
  int colorMemory;                    //Permet de smoothiser la couleur
  float soundWeight;                  //Permet de smoothiser l'intensité
  int ledsPower;                      //puissance de l'intensité de la barre (moyenne enntre 255 et soundWeight)

  float fff;

  int ballPosition;
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