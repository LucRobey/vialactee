//+------------------------------------------------------------------------------------------------------------------------------------
//
//  LegoLED.analyser.h
//
//  File : analyser.h
//
//  Description:
//
// 
//  
//
//
//  History: creation  :18/10/2022       ||    last modif : 18/10/2022 (Luc)
//
//
// Idées d'améliorations :
//
//--------------------------------------------------------------------------------------------------------------------------------------
#ifndef ANALYSER_H
#define ANALYSER_H

#include <Arduino.h>
#include <FastLED.h>
#include "arduinoFFT.h"

#include <math.h>

using namespace std;    
#include <vector>
#define AUDIO_IN_PIN 32

class Analyser{
    public:
        Analyser();

        void listen();
        void FFT_analyse();
        int* get_bandValues();
        int* getSmoothedBandValues();
        int* get_bandSmoothedValues();
        int* get_bandLocalMaxs();
        int* get_bandGlobalMaxs();

        void analyse();

        void detectBeats();
        byte* get_samplePeak();

        double* getFFTValues();

        void temporal_analyse();
        vector<float> get_localMax();

        bool* getAnalyserNeeds();
        bool* getBandAnalyserNeeds();
        byte* getAsservedBandPowers();
        byte* getAsservedPower();

    private:
        long timeL;
        void amortiseBandValues();

        //Power
        int instantPower;
        float localMaxPower;
        float globalMaxPower;
        int smoothedPower;
        byte asservedPower;
        float meanPower10sec;
        float meanPower1min;
        void asservPower();

        //bandAnalyse
        float bandMeans[16];
        int bandSmoothedValues[16];
        void updateBandMeansAndSmoothedValues();

        
        int bandLocalMaxs[16];
        int bandGlobalMaxs[16];
        byte asservedBandPowers[16];
        void asservBandPowers();


        //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
        //                                      FFT                                                                                         
        int SAMPLES=        256;           // Must be a power of 2
        int SAMPLING_FREQ=  40000;         // Hz, must be 40000 or less due to ADC conversion time. Determines maximum frequency that can be analysed by the FFT Fmax=sampleF/2.
        int NUM_BANDS=       16;             // To change this, you will need to change the bunch of if statements describing the mapping from bins to bands
        int NOISE=           500;           // Used as a crude noise filter, values below this are ignored

        // Sampling and FFT stuff
        unsigned int sampling_period_us;
        //fer

        double vReal[256];                  //=vReal[SAMPLES]
        double vImag[256];
        unsigned long newTime;
        arduinoFFT FFT = arduinoFFT(vReal, vImag, SAMPLES, SAMPLING_FREQ);
        int bandValues[16];
        uint8_t colorTimer = 0;


        
        //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


        //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
        //                              Détection de Beats                                                                                          
        bool activateBeatDetection = false;
        float amortissement[16];                                // amortissement permettre de compenser la surprésence de certaines longueurs d'ondes
        long peakTime[16];                                      //Temps du dernier peak
        byte samplePeak[16];                                    //garde en mémoire s'il y a eu peak ou pas
        float sensitivity=800;                                 //Sensibilité de détection de peak
        int total;                                             //nombre total de peaks

        //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

        bool analyserNeeds[5];  //[listen , FFT , peak , asservedBandValues , power]
        bool bandAnalyserNeeds[16];
};

#endif