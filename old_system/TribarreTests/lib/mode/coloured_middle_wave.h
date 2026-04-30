#ifndef COLOURED_MIDDLE_WAVE_H
#define COLOURED_MIDDLE_WAVE_H

/*          -=-=-=-=-=-=-=-=-=-=-=-=-Fonctionnement-=-=-=-=-=-=-=-=-=-=-=-=-

Dans ce mode, inspiré de la static_wave, c'est une vague statique, centrale, aux couleurs changeantes
La taille de la barre est directement proportionnelle (avec smoothage) à la puissance asservie et la couleur aux proportions
de chaque longueur d'onde.

1) Pour cela, à partir de bandValues, on détermine le centre de gravité (music_center) des fréquences. En ramenant cette valeur
   sur 180, on obtient la couleur. On fait une petite manip mathématique pour mettre en valeur les extremes
   Tout ce qui est avant 5 sera poussé vers 0 et tout ce qui est apres sera poussé vers 15;
2) Pour l'intensité, asservedPower. On ramène ensuite cette valeur sur 255.

Toutes ces valurs sont smoothisées. Notamment la couleur est smoothisées en fonction de la puissance à l'instant T.
Cela évite que la couleur soit choisie par des moments de silence. Ce sont les notes fortes qui dictent la couleur.

Si le nombre de LED de la barre est pair, alors il n'existe pas un centre (oneMiddle). 2 Leds font alors office de centre:middle
et middle-1.
La symétrie etant donc différente en fonction de la parité, on a 2 manières différentes de dessiner d'où le if(oneMiddle) dans draw().


    Transitions:
Noter que (-) transitionTime/2 signifie qu'on est presque à la transitionTime/2, juste avant.
C'est parcequ'on fait nos changements de phase en fonction du mouvement des limites et pas d temps
Par exemple,dans white fin de vie, c'est quand whiteTransiPos atteint maxSize qu'on enclanche la secondPhase, pas à transiTime/2.

White:
    FinDeVie:

             time                        :   0   ->  (-)transitionTime/2   ->  (--)transitionTime
             firstPhase                  :  true ->       false            ->        false
             whiteTransiPos              :   0   ->      maxSize           ->          0
             stopDoingStuffDuringTransi  : false ->                        ->        true

            FirstPhase : une lumière blanche légère, de puissance 60 apparaît venant de l'exterieur. Une fois arrivée au centre
            SecondPhase: elle rebondit et se dirige vers l'exterieur, cette fois de maniere intense et en recouvrant la barre centrele.

    DébutDeVie:
             time                        :   0     ->  (-)transitionTime/2   ->  (--)transitionTime
             firstPhase                  :  true   ->       false            ->        false
             whiteTransiPos              : maxSize ->         0              ->        maxSize
             stopDoingStuffDuringTransi  : false   ->                        ->        true
            
            Ce mode effectue la transition de fin de vie dans l'autre sens

            FirstPhase : La lumière intense disparait petit à petit à partir du centre, laissant apparaitre la bande centrale et une lumière blanche légère
                        sur les ext de la bande centrale.
            SecondPhase: La lumière blanche légère disparait petit à petit depuis l ext

Black:
    FinDeVie:
             time                        :   0   ->  (-)transitionTime/2  ->  transitionTime/2  ->  (--)transitionTime
             firstPhase                  :  true ->       false           ->         false      ->         false
             blackTransiPos              :   0   ->      maxSize          ->        maxSize     ->        maxSize
             blackTransiPosCoef          :   0   ->         1             ->           1        ->           1
             realSize                    :   ?   ->      maxSize          ->        maxSize     ->        maxSize
             blackTransiPowerCoef        :   0   ->         0             ->           0        ->           1
             blackWall                   :   0   ->         0             ->           0        ->        maxSize

             FirstPhase : La barre centrale va grandir petit à petit jusqu'à remplir toute la LED
             SecondPhase: Le noir envahit la LED depuis le centre (blackWall grandit de part et d autre du centre)

    DébutDeVie:
             time                        :   0   ->   (transitionTime/2    ->    transitionTime
             blackTransiPowerCoef        :   0   ->         0.5            ->          1
             ledsPower                   :   0   ->          ?             ->          0 

             On fait simplement augmenter petit à petit l'intensité des pixels.
            
Ce qui peut être modifié:
  - Mieux asservir la couleur (dépendant du style?)
  - Peut etre opti pendant les transi notamment ave le fond lege blanc, pas besoin de tout colorier

*/

#include <Arduino.h>
#include <FastLED.h>
using namespace std;
#include <vector>
#include <mode.h>
#pragma once

class Coloured_middle_wave : public Mode
{
public:
  Coloured_middle_wave(vector<CRGB*> local_sorted_leds,byte ID, int* bandSmoothedValues, byte* asservedPower);
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

  int middle;
  bool oneMiddle;                     //Est-ce que la barre a un seul milieu ou 2? (en fonction de sa parité)

  float musicGravityCenter;           //Calcul le "centre de gravité de la barre"
  int colorMemory;                    //Permet de smoothiser la couleur
  float soundWeight;                  //Permet de smoothiser l'intensité
  int ledsPower;                      //puissance de l'intensité de la barre (moyenne enntre 255 et soundWeight)

  float fff;

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
  int realBlackSize;
  float speedBlackTransi;             //Vitesse de grandissement de la barre, et du mur noir (fin de vie)
  float blackTransiPowerCoef;         //Coef d'influence sur l'intensité
  float blackTransiPosCoef;           //Coef d'influence sur la taille de la barre (fin de vie)
  int blackWall;                      //Position de la limite du blackWall(fin de vie)
  float blackTransiPos;               //Position limite de l'influence sur la taille de la barre (fin de vie)

  
};

#endif