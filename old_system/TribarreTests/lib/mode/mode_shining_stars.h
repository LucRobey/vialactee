//+------------------------------------------------------------------------------------------------------------------------------------
//
//  LegoLED.Mode_shining_stars.h
//
//  File : Mode_shining_stars.h
//
//  Description:
//
//  Represent the results of the FFT.
//  Un lumière apparait de manière random en fonction de la bande qui a produit un peak.
//  Si la valeur d'une bande dépasse la moyenne de cette bande plus une sensibilité variables, il y a peak.
//  S'il y a peak, alors on fait apparaitre une lumiere
//  La puissance des lumières est directement liée au nombres de bandes en peak.
//  Pour économiser du calcul, on le fait pour les 50 premières leds puis on fait un copié/collé
//
//  Setup:
//      sensibility reste autour de 500 en général
//
//  History: creation  :11/10/2022       ||    last modif : 30/10/2022 (Luc)
//
//
// Idées d'améliorations :
//      -Trop brutal pour l'instant, c'est tout ou rien.
//              -> Mieux calculer la puissance pour que ce soit plus linéaire
//
//--------------------------------------------------------------------------------------------------------------------------------------

#ifndef MODE_SHINING_STARS_H
#define MODE_SHINING_STARS_H

#include <Arduino.h>
#include <FastLED.h>
using namespace std;
#include <vector>
#include <mode.h>

class Mode_shining_stars : public Mode
{
public:
  Mode_shining_stars(vector<CRGB*> local_sorted_leds,byte ID, byte* samplePeak , byte* asservedPower);
  void update(); // Takes the result of the FFT and does all the calculations
  void draw();
  void startTransition(int transitionTime, bool upOrDown, bool blackOrWhite);
  void resetTransition();
  void activate();

private:

  long timeL;
  
  int segment_division_number;
  int rests;
  int segment_division_size;
  
  ///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
  // Beatdetection:
  byte* samplePeak; // garde en mémoire s'il y a eu peak ou pas
  byte* asservedPower;
  int total;               // nombre total de peaks
  ///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

  // Transition:
  float black_power_coef;  // Pour la black Transition, contrôle la puissance
  int posSS;                 // position random d'apparition de la lumière
  int powerSS;

  vector<int> permutationForWhiteTransition;
  int whiteTransitionCounter; 

  float global_power_coef;
};

#endif
