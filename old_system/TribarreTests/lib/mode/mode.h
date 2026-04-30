//+------------------------------------------------------------------------------------------------------------------------------------
//
//  LegoLED.mode.h
//
//  File : mode.h
//
//  Description:
//
//  Mother class of all modes
//
//  Setup:
//
//  Better to use Num_BANDS=8 but can be used with 16 if the Led is bigger (must be equal to the NUM_BANDS in main.cpp)
//
//  History: creation  :08/10/2022       ||    last modif : 08/10/2022 (Luc)
//
//
// Idées d'améliorations :
//      -à passer en HSV!!
//      -amortissement qu'on peut peut-être asservir?
//
//--------------------------------------------------------------------------------------------------------------------------------------

#ifndef MODE_H
#define MODE_H

using namespace std;
#include <vector>
#include <FastLED.h>

#define NUM_BANDS 16
#define NUM_LEDS 250

class Mode
{
public:
  Mode(){};
  Mode(vector<CRGB*> local_sorted_leds);
  virtual void update(); 
  virtual void draw();
  virtual int getFadeToBlackCoef();
  virtual void startTransition(int transitionTime, bool upOrDown, bool blackOrWhite);
  virtual bool isTransitionFinished();
  virtual void resetTransition();

  virtual bool isActivated();
  void activate();
  virtual void deactivate();
  virtual void updateTransitionTimer();
  bool* getAnalysingNeeds();
  bool* getBandAnalysingNeeds();
  void printID();
  void initiateVariables(byte ID ,vector<CRGB*> local_sorted_leds);

protected:
  byte ID;

  bool analysingNeeds[5];    //[écouter ; FFT ; peaks ; asservedBandValues ; asservedPower]
  bool bandAnalysingNeeds[16];   //Demande d'asservissements de bandes en particulier

  vector<CRGB*> local_sorted_leds;          // Domaine de définition du mode
  int listSize;                           //Size of the local list

  int fadeToBlackInt;

  bool transition;
  int timeSinceTransition;
  bool transitionUp;
  bool blackOrWhite;
  int transitionTime;

  bool activated;
};

#endif