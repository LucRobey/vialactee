#ifndef FIRE_MODE_H
#define FIRE_MODE_H

/*          -=-=-=-=-=-=-=-=-=-=-=-=-Fonctionnement-=-=-=-=-=-=-=-=-=-=-=-=-

Ce mode cherche à imiter un feu. Pour cela, chaque LED a une température. Plus la LED est chaude,
plus elle est intense et se rapproche du blanc/orange.

La température de chaque LED varie de 4 façons différentes:
  1) Dans le brasier, la température varie sous l'influence de la musique et du random:
      - De manière random, la température varie brutalement (grâce à l'utilisation de bytes et non d'int)
      - Lors d'un beat, la température d'une LED du brasier augmente brutalement
  2) La température monte par la suite, chaque LED est influencée par elle-même et les 2 LEDs en dessous
  3) Elle est refroidie de manière random. Plus elle est loin du brasier, plus elle peut potentiellement refroidir vite

La température est un byte entre 0 et 255.

    Transitions:

Il n'y a que la transition blanche de fin de vie qui modifie le fonctionnement "thermique"
Durant cette transition, on arrête le refroidissement, et on arrête l'apparition de trous froids dans le brasier
Ainsi, toute la barre se met à chauffer jusqu'aux 255°
Par contre, les transitions blanches n'influent pas l'affichage
Dans les transitions noires, on ne fait que changer l'affichage, en le faisant virer au noir

Le transitionCoef permet une continuité dans l'affichage des températures.

White:
    FinDeVie:
             time           : 0   ->  transitionTime
             temperatures   : ?   ->       255

            On fait chauffer toute la barre, et plus c'est chaud, plus c'est blanc et intense
            La barre est à la bonne couleur/intensité (pour la transi) quand chaque LED est à 255°C

    DébutDeVie:
             time           :  0   ->  transitionTime
             temperatures   : 255  ->            ?    

            On laisse la barre se refroidir toute seule et récupérer son état normal

Black:
    FinDeVie:
             time           : 0  ->  95%*transitionTime  ->  transitionTime
             transitionCoef : 0  ->            1         ->        1

            Ici, le transitionCoef fait baisser l'intensité de lui même ce qui fait qu'on s'en fou de 
            la température

    DébutDeVie:
             time           :  0   ->  (transitionTime/2)  ->  transitionTime
             transitionCoef :  1   ->            0         ->        0

            Ici, le transitionCoef fait baisser l'intensité de lui même ce qui fait qu'on s'en fou de 
            la température
            
Ce qui peut être modifié:
  - Le refroidissement random (random(0, (((30+i) * 10) / listSize) + 2))
  - La manière dont la chaleur monte (temperatures[k] = (temperatures[k - 1] + temperatures[k - 2] + temperatures[k]) / 3)
  - La taille du brasier (3+listSize/6)
  - l'apparition des pics/trous de chaleur dans le brasier

*/

#include <Arduino.h>
#include <FastLED.h>
using namespace std;
#include <vector>
#include <mode.h>
#pragma once

class Fire_mode : public Mode
{
public:
  Fire_mode(vector<CRGB*> local_sorted_leds,byte ID, byte* samplePeak);
  void update();
  void draw();
  void activate();
  void deactivate();
  void startTransition(int transitionTime, bool upOrDown, bool blackOrWhite);
  void resetTransition();

private:
  //date
  byte* samplePeak;

  vector<byte> temperatures;            //stock les valeurs des températures
  int refroidissement;                  //refroidissement à chaque itération

  int brasier;                          //taille du brasier,où apparaissent les flammes avant de grandir
  float transiCoef;
};

#endif