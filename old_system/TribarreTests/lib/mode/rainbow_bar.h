//+------------------------------------------------------------------------------------------------------------------------------------
//
//  LegoLED.rainbow_bar.h
//
//  File : rainbow_bar.h
//
//  Description:
//
//  Represent the results of the FFT.
//  On a un long segment représentant un arc en ciel. L'intensité de chaque couleur est liée à l'intensité
//  de sa gamme de fréquence
//
//  History: creation  :17/10/2022       ||    last modif : 30/10/2022 (Luc)
//
//
// Idées d'améliorations :
//      Pour ce qui est des max, on pourrait faire le process dans le listener
//--------------------------------------------------------------------------------------------------------------------------------------
#ifndef RAINBOW_BAR_H
#define RAINBOW_BAR_H

#include <Arduino.h>
#include <FastLED.h>
using namespace std;    
#include <vector>
#include <mode.h>

class Rainbow_bar : public Mode{
    public:
        Rainbow_bar(vector<CRGB*> local_sorted_leds,byte ID, byte* asservedBandPowers) ;
        void update();
        void draw();
        void startTransition(int transitionTime , bool upOrDown , bool blackOrWhite);
        void resetTransition();

    private:
        //data
        byte* asservedBandPowers;

        // The length of these arrays must be >= NUM_BANDS
        float amortissement[16];// = {1,1.3,0.95,0.9,0.8,0.9,1,1};                     // amortissement permettre de compenser la surprésence de certaines longueurs d'ondes
                                                                                        // On peut potentiellement l'asservir
        int getIntensity(int i);
        int getContrast();

        int transitionIntensity;
        int transitionContrast;
        int smoothedValuef;
        float transitionCoef;

        int num_bands;

        long timeL;

        float keepItInSegment(float a);
};



#endif