#ifndef MAGNETIC_BALL_H
#define MAGNETIC_BALL_H
/*          -=-=-=-=-=-=-=-=-=-=-=-=-Fonctionnement-=-=-=-=-=-=-=-=-=-=-=-=-

Ce mode comporte 2 principaux éléments: un boule centrale représentant à peu près la moyenne des fréquences en présence
et 2 bandes représentants les puissances des aigus et des basss.
Une bande bleue, en haut et une bande rouge (basses) en bas.

3 valeurs nous intéressent donc:
  -valeur des basses (->bassSize)
  -valeur des aigus (->aiguSize)
  -valeur de la boule centrale, soit la fréquence moyenne (->midBallPos et -> midBallColor)

Pour cela, on fait un centre de gravité asservi. On en tire la valeur des basses et des aigus et une position du centre des
fréquences.
On va essayer d'augmenter les variations entre aigus et graves. Pour cela on va, à la valeur de la moyenne des fréquences (musicCenter)
, une fois ramener entre 0 et 1, écarter toutes les valeurs à l'aide d'un coefficient. Par exemple, si ce coef est 0.3,
on veut que toutes les valeurs en dessous de 0.3 soit VRAIMENT inférieures à 0.3 et de même pour celle au dessus.
Cela permet d'accentuer l'eefet de beat.

On procède par la suite par accélération. La valeur musicCenter, après petits calculs, va servir d'accélération pour la position
de la balle. On rajoute en plus une force qui tire la balle vers le centre.

La couleur de la balle est simplement calculée par rapport à sa position, à la manière de la rainbow_bar.

      Transitions:

      Toutes les transitions se font en 2 ou 3 phases. Tout est linéaire

bool firstPhase;
  bool secondPhase;
  bool thirdPhase;
  int firstPhaseLimit;
  int secondPhaseLimit;
  int barsMaxSize;

    //white
    vector<int> permutationForWhiteTransition;
    int whiteTransitionCounter; 
    byte whiteIntensity;
    
    byte midBallWhitness;

    //black
    float midBallPowerCoef;         //Coef d'infl

WHITE:
    Fin de vie:
             time             :     0    ->  firstPhaseLimit  ->  secondPhaseLimit  ->  0.95* transitionTime
             firstPhase       :   true   ->      false        ->       false        ->         false
             secondPhase      :   false  ->      true         ->       false        ->         false
             thirdPhase       :   false  ->      false        ->       true         ->         true
             whiteIntensity   :     0    ->       255         ->        255         ->          255
             barsMaxSize      :  maxSize ->     maxSize       ->         0          ->           0
             midBallWhitness  :    255   ->       255         ->        255         ->           0

          -1ère phase: le fond devient progressivement blanc
          -2ème phase: les barres disparaîssent
          -3eme phase: la boule devient blanche

    Début de vie:
             time             :     0    ->  firstPhaseLimit  ->  secondPhaseLimit  ->  0.95* transitionTime
             firstPhase       :   true   ->      false        ->       false        ->         false
             secondPhase      :   false  ->      true         ->       false        ->         false
             thirdPhase       :   false  ->      false        ->       true         ->         true
             barsMaxSize      :     0    ->     maxSize       ->      maxSize       ->        maxSize
             midBallWhitness  :     0    ->        0          ->        255         ->          255
             whiteIntensity   :     0    ->        0          ->         0          ->          255
             
             

          -1ère phase: les barres réapparaîssent
          -2ème phase: la balle réapparaît
          -3eme phase: le fond redevioent noir

BLACK:
    Fin de vie:
             time             :     0    ->  firstPhaseLimit  ->   0.95* transitionTime
             firstPhase       :   true   ->      false        ->        false      
             secondPhase      :   false  ->      true         ->        false    
             barsMaxSize      :  maxSize ->        0          ->          0     
             midBallPowerCoef :     1    ->        1          ->          0    
             
             

          -1ère phase: les barres disparaissent car leur taille limite va vers 0
          -2ème phase: la balle disparait car son intensité diminue


    Début de vie:
             time             :     0    ->  firstPhaseLimit  ->   0.95* transitionTime
             firstPhase       :   true   ->      false        ->        false      
             secondPhase      :   false  ->      true         ->        false    
             barsMaxSize      :     0    ->     maxSize       ->        maxSize    
             midBallPowerCoef :     0    ->        0          ->          1    
             
             

          -1ère phase: les barres réapparaîssent car leur taille réaugment
          -2ème phase: la balle réapparaît car son intensité diminue
             
  Ce qui peut être modifié:
  - l'asservissement de la boule centrale
  -la valeur donnée aux barres latérales pour mieux visualiser les basses et les aigus.

*/

#include <Arduino.h>
#include <FastLED.h>
using namespace std;
#include <vector>
#include <mode.h>
#pragma once

class Magnetic_ball : public Mode
{
public:
  Magnetic_ball(vector<CRGB*> local_sorted_leds,byte ID, int* bandSmoothedValues, byte* asservedPower, byte* asservedBandPower);
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


  float localAsservissement[16];        //Permet de mettre les basses en valeur
  float bassSize;                       //Tailmle de la bande représentant les basses (en bas en rouge)
  float aiguSize;
  float bassValue;
  float aiguValue;

  float acceleration;                   //accélération de la boule centrale
  float speed;

  byte bassPower;                       //Intensité lumineuse de la bande basse
  byte aiguPower;

  byte bassColor;
  byte aiguColor;

  float coefToMiddle;                    //Permet d'asservir la boule centrale
  int timeForCoef;                       //Si la boule est tj en haut pendant uin temps trop long, on la force à redescendre
  bool lastSign;

  float midBallPos;
  byte midBallColor;
  byte midPower;

  float musicCenter;
  float musicWeight;

  float fff;            //Plus d'idée de nom (probablement inutile)
  int maxSize;          //Taille maximale des bandes latérales

  //Transition
  bool firstPhase;
  bool secondPhase;
  bool thirdPhase;
  int firstPhaseLimit;
  int secondPhaseLimit;
  int barsMaxSize;

    //white
    byte whiteIntensity;
    
    byte midBallWhitness;

    //black
    float midBallPowerCoef;         //Coef d'influence sur l'intensité
};

#endif