#include <static_wave.h>

Static_wave::Static_wave(vector<CRGB*> local_sorted_leds,byte ID, byte* asservedBandValues)
{
    initiateVariables(ID,local_sorted_leds);
    
    this->fadeToBlackInt=140;

    color=random(160);

    real_size = listSize/4;
    size = real_size+1;              // Limite de la taille atteignable par la static wave
    
    // Transition:
    transitionLimitSW = 0;
    max_size = listSize/2-1;
    middle = listSize/2;


    this->asservedBandValues=asservedBandValues;

    this->analysingNeeds[0] = true;         //ecoute
    this->analysingNeeds[1] = true;         //FFT
    this->analysingNeeds[2] = false;        //peak
    this->analysingNeeds[3] = true;         //asservbands
    this->analysingNeeds[4] = false;        //power
    for (byte band=0 ; band<16 ; band++)
    {
        bandAnalysingNeeds[band]=false;
    }
    bandAnalysingNeeds[0]=true;
    bandAnalysingNeeds[1]=true;
};

Static_wave::Static_wave(vector<CRGB*> local_sorted_leds,byte ID, byte* asservedBandValues , byte color)
{
    initiateVariables(ID,local_sorted_leds);
    
    this->fadeToBlackInt=140;

    this->color=color;

    real_size = listSize/4;
    size = real_size+1;              // Limite de la taille atteignable par la static wave
    
    // Transition:
    transitionLimitSW = 0;
    max_size = listSize/2-1;
    middle = listSize/2;

    this->asservedBandValues=asservedBandValues;

    this->analysingNeeds[0] = true;         //ecoute
    this->analysingNeeds[1] = true;         //FFT
    this->analysingNeeds[2] = false;        //peak
    this->analysingNeeds[3] = true;         //asservbands
    this->analysingNeeds[4] = false;        //power
    for (byte band=0 ; band<16 ; band++)
    {
        bandAnalysingNeeds[band]=false;
    }
    bandAnalysingNeeds[0]=true;
    bandAnalysingNeeds[1]=true;
};

// Valeur affichée
void Static_wave::update()
{
    //Serial.print("temps pour la static_wave:");
    //timeL=millis();
    valuef = (int(asservedBandValues[0]) + asservedBandValues[1] + asservedBandValues[2] + asservedBandValues[3])/4;

    real_size = 0.5 * (real_size + ( float(valuef * max_size) / 255));
    if(real_size>=max_size)
    {
        real_size=max_size-1;
    }

    if (real_size > size)
    { // size>real_size tj
        size = real_size + 1;
    }
    if (real_size < size - 1)
    { // Quand real_size diminue, on fait baisser size 5 fois moins vite
        size -= 0.2;
    }

    if (transition)
    {
        if (!blackOrWhite)
        { // White Transition
            if (!transitionUp)
            {                                                                              // Fin de vie
                transitionLimitSW = (max_size * timeSinceTransition) / transitionTime; // Taille est proportionelle au temps
                if(transitionLimitSW>=max_size) transitionLimitSW=max_size;
            }
            else
            {                                                                                         // Début de vie
                transitionLimitSW = max_size * (1 - float(timeSinceTransition) / transitionTime); // La taille diminue linéairement
                if(transitionLimitSW<0) transitionLimitSW=0;
            }
        }
        else
        { // Black Transition
            if (!transitionUp)
            {                                                                                     // Fin de vie
                blackTransitionPowerCoef = (1 - float(timeSinceTransition) / transitionTime); // luminosité diminue
            }
            else
            {                                                                               // Début de vie
                blackTransitionPowerCoef = float(timeSinceTransition) / transitionTime; // Luminosité augmente
            }
        }
    }
};
// =============================== Update()

void Static_wave::draw()
{
    power = 255 * blackTransitionPowerCoef;
    for (int pos = 0; pos <= real_size; pos++)
    {
        *local_sorted_leds[middle + pos] = CHSV(color, 255, power);
        *local_sorted_leds[middle - pos] = CHSV(color, 255, power);
    }

    // The moving limit:
    *local_sorted_leds[middle + size] = CHSV(color, 0, power);

    if (middle > size)
    { // Juste pour gérer des pb de symétrie, ne pas preter attention
        *local_sorted_leds[middle - size] = CHSV(color, 0, power);
    }
    else
    {
        *local_sorted_leds[0] = CHSV(color, 0, power);
    }
    // Show the limits:
    *local_sorted_leds[listSize-1] = CHSV(color, 255, power);
    *local_sorted_leds[0] = CHSV(color, 255, power);

    if (transition)
    {
        if (!blackOrWhite)
        {//white
            for (int i = 0; i < transitionLimitSW; i++)
            { // On colorie tout à partir de max_size-limit , et la symétrie aussi
                *local_sorted_leds[middle + max_size - i] = CHSV(color, 0, 255 );
                *local_sorted_leds[middle - (max_size - i)] = CHSV(color, 0, 255 );
            }
        }
    }

    if (transition)
    {
        updateTransitionTimer();
    }
    
    //Serial.println(millis()-timeL);
}
// =============================== draw()

void Static_wave::startTransition(int transitionTime, bool upOrDown, bool blackOrWhite)
{
    this->transition = true;
    this->transitionUp = upOrDown;
    this->transitionTime = transitionTime;
    this->timeSinceTransition = 0;
    this->blackOrWhite = blackOrWhite;

    if (!blackOrWhite)
    {
        if (!upOrDown)
        {
            Serial.println("                                                             static_wave  ==>       ( white transition ) ");
        }
        else
        {
            Serial.println("                                                             ==>  static_wave     ( white transition ) ");
        }
    }
    else
    {
        if (!upOrDown)
        {
            blackTransitionPowerCoef = 1;
            Serial.println("                                                            static_wave  ==>       ( black  transition ) ");
        }
        else
        {
            blackTransitionPowerCoef = 0;
            Serial.println("                                                             ==>  static_wave     ( black  transition ) ");
        }
    }
}
// =============================== stratTransition()

void Static_wave::resetTransition()
{
    this->transition = false;
    this->timeSinceTransition = 0;
    blackTransitionPowerCoef = 1;
    Serial.println("                                                             |static_wave|    ");
}
// =============================== resetTransition()

void Static_wave::activate()
{
    this->activated = true;
}