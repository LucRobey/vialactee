#ifndef MASTER_MODE_H
#define MASTER_MODE_H

using namespace std;

#include <string.h>
#include <mode_test_uniform_color.h>
#include <mode_shining_stars.h>
#include <rainbow_bar.h>
#include <power_bar.h>
#include <coloured_bar.h>
#include <fire_mode.h>
#include <static_wave.h>
#include <coloured_middle_wave.h>
#include <extending_waves_mode.h>
#include <flying_ball.h>
#include <flying_balls.h>
#include <band_wars.h>
#include <magnetic_ball.h>
#include <vector>
#include <map>
#include <iostream>
#include <memory>
// Nombre de modes
extern CRGB leds[];
#define nbOfSegments 2
#define nbOfModes 10

class Master_mode
{
public:
    Master_mode(int* bandValues, byte* samplePeak, byte* asservedBandPowers , int* bandSmoothedValues, byte* asservedPower , bool* needsToAnalyse , bool* bandAnalyserNeeds );
    void update();
    void makeItWhite();
    void forceNewModes();
    
private:
    bool allWhite;
    bool* needsToAnalyse;               //pointeur vers le needsToAnalyse de l'analyser
    bool* bandNeedsToAnalyse;           //Pointeur vers le bandNeedsToAnalyse de l'analyser
    byte numberOfNeeds[5];              //Memoire du nombre de segments necessitant chaque needs
    byte numberOfBandNeeds[16];          //Memoire du nombre de segments necessitant l'aaservissement pour chaque bande
    byte numberOfAnalysingOptions=5;
    void updateNeedsToAnalyse(byte changingSegment);

    Mode* modes_map[nbOfModes][nbOfSegments];
    vector<Mode *> Mode_list;               // Liste des modes , chaque mode est là 2 fois
    int timeDurationOfMode[nbOfModes];         
    int transitionTimeOfMode[nbOfModes];
    vector<CRGB*> sorted_segments[nbOfSegments]; 
    int segmentsMode[nbOfSegments];               //mémorise l'indice i associé à chaaque segment  .  LES MOPES NE SE SUPERPOSENT PAS!!!        
    int timeBeforeNeedingANewMode [nbOfSegments];
    int nextModes[nbOfSegments];                 //si nextMode[i]>=-1, alors le mode du segment de fin de vie est actuellement en transition de fin de vie et ce numéro est le mode suivant prévu pour ce groupement de segments
    vector<vector<int>> segmentGroups[nbOfSegments];           
    vector<vector<int>> segmentGroupsModes[nbOfSegments];      
    vector<int> segmentsProbas[nbOfSegments];                  //some des probas pour un segment = 100;
    bool transitionColors[nbOfSegments];

    int startingPositions[nbOfSegments];


    int memoryModes[nbOfSegments];

    
    bool printini = true;
    void printState();
    void printSegmentGroups();
    void printSegmentGroupsModes();
    void printSegmentsProbas();
    void printAnalysingNeeds();
    void printModeMap();

};

#endif