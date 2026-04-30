#ifndef MAGMA_MODE_H
#define MAGMA_MODE_H


/*          -=-=-=-=-=-=-=-=-=-=-=-=-Fonctionnement-=-=-=-=-=-=-=-=-=-=-=-=-

Ce mode cherche à imiter la lave. Pour cela, chaque LED a une température. Plus la LED est chaude,
plus elle est intense et se rapproche du blanc.

La température de chaque LED varie de 4 façons différentes:
  1) Elle est tirée vers le bas (proportionellement à sa température), comme si l'air ambiant refroidissait 
     la lave.
  2) Elle est modifiée par la diffusion thermique selon un facteur. Les LEDs chaudes (froides) réhauffent
     (refroidissent) les LEDs voisines.
  3) Elle est tirée vers le haut à certains points, les points chauds (ou heatWaves)
  4) Lorsqu'il y a un beat, des "crépitements" apparaissent à des positions random et réchauffent légèrement
     la zone.

La température est un float entre 0 et 255.

    Fonctionnement des heatWaves, heatSpeeds:
Les heatWaves stockent les positions (en float) des points de réchauffement. heatSpeeds stocke la vitesse de ces points
de réchauffement. A chaque itération, on update la position de ces points et on fait légèrement varier de manière random
leurs vitesses.


    Transitions:

Dans toutes les transitions (sauf black début de vie), on rajoute un facteur qui influe sur la température: transitionHeating.
Ce facteur permet de forcer les changements de températures. En plus, on change les coefficients des autres influenceurs
de température.
transitionHeating peut être négatif!

Le transitionCoef permet une continuité dans l'affichage des températures.

White:
    FinDeVie:
             time           : 0  ->  (transitionTime/2)  ->  transitionTime
             transitionCoef : 0  ->            1         ->        1
             temperatures   : ?  ->            ?         ->       255
             transitionHeating = 0.8 * 255.0/transitionTime

            On fait chauffer toute la barre, et plus c'est chaud, plus c'est blanc et intense
            La barre est à la bonne couleur/intensité (pour la transi) quand chaque LED est à 255°C

    DébutDeVie:
             time           :  0   ->  (transitionTime/2)  ->  transitionTime
             transitionCoef :  1   ->            0         ->        0
             temperatures   : 255  ->            ?         ->        ?
             transitionHeating= - 0.5 * 255.0/transitionTime

            On fait refroidir toute la barre et on repasse aux couleurs classiques

Black:
    FinDeVie:
             time           : 0  ->  (transitionTime/2)  ->  transitionTime
             transitionCoef : 0  ->            1         ->        1
             temperatures   : ?  ->            ?         ->        0
             transitionHeating= - 0.2 * 255.0/transitionTime

            On fait refroidir toute la barre, et plus c'est froid, plus c'est rouge et faible
            Ici, le transitionCoef fait baisser l'intensité de lui même ce qui fait qu'on n'est
            pas obligé d'atteindre les 0° pour que la transi soit jolie

    DébutDeVie:
             time           :  0   ->  (transitionTime/2)  ->  transitionTime
             transitionCoef :  1   ->            0         ->        0
             temperatures   :  0   ->            ?         ->        ?

            On fait réchauffer les Leds de manière normale, comme en dehors des transitions
            



Ce qui peut être modifié:
  - Le coefficient de diffusion (0.08), si on l'augmente, la température se déplace plus vite
  - Le coefficient de refroidissement (0.45). Si on l'augmente, la température globale baisse 
    et la taille des heatWaves diminue. Ca rend le mode plus "dynamique", on voit plus le mouvement
  - Le réchauffement des heatWaves (+=4+random(5)). Si on l'augmente, on voit plus le mouvement de
    la heatWaves.
  - la vitesse des heatWaves (ses bornes (-0.25 ; 0.25) ou sa variation (+=float(1-random(3))/100))
  - le nombre de LEDs par heatWaves (nbOfLEDsByHeatWave=30).

*/

#include <Arduino.h>
#include <FastLED.h>
using namespace std;
#include <vector>
#include <mode.h>
#pragma once

class Magma_mode : public Mode
{
public:
  Magma_mode(byte ID, int* bandValues, byte* samplePeak);
  void update();
  void draw();
  void activate(vector<CRGB*> local_sorted_leds);
  void deactivate();
  void startTransition(int transitionTime, bool upOrDown, bool blackOrWhite);
  void resetTransition();

private:
  //data
  byte* samplePeak;
  
  vector<float> temperatures;
  void updateTemperatures();
  void updateTemperaturesDuringTransition();
  vector<float> heatWaves;
  vector<float> heatSpeeds;

  int nbOfLEDsByHeatWave;

  float transitionHeating;

};

#endif