#ifndef EXTENDING_WAVES_MODE_H
#define EXTENDING_WAVES_MODE_H

/*          -=-=-=-=-=-=-=-=-=-=-=-=-Fonctionnement-=-=-=-=-=-=-=-=-=-=-=-=-

Dans ce mode, la lumière apparaît au centre de la barre et se répend de part et d'autre du centre. (A l'image d'une
goutte d'eau qui tombe au milieu d'une flaque). Pour cela, on écoute la musique, et celle-ci influe la/les LEd(s) centrale(s).
Cette modification sedéplace par la suite, à une vitesse de 1 LED/itération à hgauche et à droite du centre.

1) Pour cela, à partir de bandValues, on détermine le centre de gravité (music_center) des fréquences. En ramenant cette valeur
   sur 255, on obtient la couleur.
2) Pour l'intensité, on regarde le nombre de peaks. On ramène ensuite cette valeur sur 255.

Toutes ces valurs sont mémorisées dans le vecteur colors<[couleur,whitness,intensité]> de taille (listSize+1)/2.
A chaque itération, on décale toutes les valeurs vers la droite, et on update la valeur 0. On fait apparai^tre à gauche
et à droite par symétrie par rapport au centre.

Si le nombre de LED de la barre est pair, alors il n'existe pas un centre (oneMiddle). 2 Leds font alors office de centre:middle
et middle-1.
La symétrie etant donc différente en fonction de la parité, on a 2 manières différentes de dessiner d'où le if(oneMiddle) dans draw().


    Transitions:

    IMPORTANT: le blanc n'est pas une coleur!!!!! c'est simplement whitness=0!!!!

White:
    FinDeVie:
             time             : 0   ->  transitionTime
             whiteWallLimit   : ?   ->  (listSize+1)/2

            On fait apparaître des pixels blancs qui vont s'entasser sur les bords de la barre. A mesure qu'ils s'entassent
            whitewallLimit grandit. Quand il atteint (listSize+1)/2, alors toute la barre est blanche et la transition est terminée.
            Pour cela, on fait apparaître le pixel blanc toutes les int(whiteApparitionRate) itérations. Le tout est calculé
            au startTransition pour que peu importe transitionTime, la barre sera toute blanche à la fin!

    DébutDeVie:
             time           :  0   ->  transitionTime
            
            On fait l'opposé de la fin de vie.
            Le "whiteWall" va être attiré vers le centre petit à petit. tous les delta_t itérations, un nouveau bloc de 2 pixels
            blancs se détache et tombe vers le centre où il disparaîtra.

            Dans ce mode, la couleur et l'intensité se déplacent à droite, alors que la whitness bouge vers la gauche


Black:
    FinDeVie:
             time                         : 0  ->  timeToDesapear  ->  transitionTime
             intensityBlackTransitionCoef : 1  ->        0         ->        0

             Les pixels apparaissants au centre sont de moins en moins intense (d'un facteur intensityBlackTransitionCoef).
             On utilise timeToDesapear, car il faut que la barre soit noire à transitionTime. Il ne faut donc pas oublier
             le temps que met le pixel pour traverser la barre. Ainsi, le dernier pixel lumineux émis à timeToDesapear
             atteindra le bout de la barre juste avant la fin de la transi

    DébutDeVie:
             time                         :  0   ->   transitionTime
             intensityBlackTransitionCoef :  0   ->         1

             On fait simplement augmenter petit à petit l'intensité des pixels apparaissants en 0.
            
Ce qui peut être modifié:
  - l'intensité est pas dingue ( a refaire avec les nouveaux peaks)
  - la taille des blocs tombants dans white/début de vie. 

*/

#include <Arduino.h>
#include <FastLED.h>
using namespace std;
#include <vector>
#include <mode.h>
#pragma once

class Extending_waves_mode : public Mode
{
public:
  Extending_waves_mode(vector<CRGB*> local_sorted_leds,byte ID, int* bandSmoothedValues, byte* asservedPower);
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
  vector<byte*> colors;               //mémorise le couleur/whitness/intensité de chaque pixel
  bool oneMiddle;                     //Est-ce que la barre a un seul milieu ou 2? (en fonction de sa parité)

  float music_center;
  float music_color;
  int totalSound;

  //Transition
    //white fin de vie
  float whiteApparitionRate;            //Temps entre l'apparition de pixels blanc
  int nextApparition;                   // temps de la prochaine apparition d un pixel blanc
  bool stopPopingWhite;                 //Quand on en a fait apparaitre assez, on s arrete
  int whiteWallLimit;                   //Limite (en partant de l ext) de la taille de la pile de blanc

    //white début de vie
  int delta_t;                          //Temps entre chaque chute de bloc de blanc
  int nextFall;                         //Temps avant la prochaine chute
  byte numberOfFallAtTheSameTime;       //Nombre de blocs en train de tomber en meme temps
  bool waitingForTheEnd;                //Quand tout est tombé, on ne fait qu attendre la fin de la transi

    //black
  float intensityBlackTransitionCoef;
      //Fin de vie
  int timeToDesapear;                   //Date à laquelle plus aucun pixel lumineux n'apparait
  
};

#endif