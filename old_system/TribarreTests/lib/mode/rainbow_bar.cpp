#include <rainbow_bar.h>

Rainbow_bar::Rainbow_bar(vector<CRGB*> local_sorted_leds,byte ID, byte* asservedBandPowers)
{
    initiateVariables(ID,local_sorted_leds);

    this->fadeToBlackInt=0;

    num_bands=16;
    for (byte s=0 ; s<16 ; s++)
    {
        amortissement[s]=1;
    }
    amortissement[0]=1.3;
    amortissement[1]=1.3;
    amortissement[2]=1.1;
    amortissement[4]=1;
    amortissement[5]=0.9;
    amortissement[6]=0.9;
    amortissement[8]=0.9;
    amortissement[9]=0.9;
    amortissement[10]=0.9;

    //Data
    this->asservedBandPowers=asservedBandPowers;

    this->analysingNeeds[0] = true;
    this->analysingNeeds[1] = true;
    this->analysingNeeds[2] = false;
    this->analysingNeeds[3] = true;
    this->analysingNeeds[4] = false;
    for (byte band=0 ; band<16 ; band++)
    {
        bandAnalysingNeeds[band]=true;
    }
}
// ============================= Rainbow_bar()

void Rainbow_bar::update()
{
    //Serial.print("temps pour la rainbow bar de taill ");
    //Serial.print(listSize);
    //Serial.print(" : ");

    //timeL=micros();
    
    if(transition)
    {
        if (!blackOrWhite)
        { // White transition
            if (!transitionUp)
            {// Fin de vie
                transitionCoef = 1-float(timeSinceTransition) / transitionTime;        // intensité = transitionCoef * intensitéNormale + (1-transitionCoef) * transitionIntensité
                //transitionIntensity = 40 + (100 * timeSinceTransition) / transitionTime; // l'intensité augmente linéairement de 40 à 150
                transitionContrast = 255 * transitionCoef;                                 // Le contraste baisse linéairement de 255 à 0
            }
            else
            { // Début de vie
                transitionCoef = float(timeSinceTransition) / transitionTime;
                //transitionIntensity = 140 - (100 * timeSinceTransition) / transitionTime; // Pour le début de vie, c'est dans l'autre sens
                transitionContrast = 255 * transitionCoef;
            }
        }
        else
        { // Black transition
            if (!transitionUp)
            { // Fin de vie
                transitionCoef = 1-float(timeSinceTransition) / transitionTime;
                //transitionIntensity = 50 * transitionCoef; // l'intensité dimnue linéairement de 50 à 0
            }
            else
            { // Début de vie
                transitionCoef = float(timeSinceTransition) / transitionTime;
                //transitionIntensity = 50 * transitionCoef; // L'intensité augmente linéairement de 0 à 50
            }
        }
    }
}
// ============================= update()

void Rainbow_bar::draw()
{
    for (int i = 0; i < listSize; i++)
    {
        *local_sorted_leds[i] = CHSV(160 * i / local_sorted_leds.size(), getContrast(), getIntensity(i));
    }
    if (transition)
    {
        this->updateTransitionTimer();
    }

    
    //Serial.println(micros()-timeL);
}
// ============================= draw()

static float val;
static int bandInf;
static float prop;
int Rainbow_bar::getIntensity(int i)
{
    val = float((num_bands - 1) * i) / listSize;
    bandInf = int(val);
    if (bandInf == num_bands)
    {
        if (transition)
        {
            return transitionCoef * (40 + (0.843137 * keepItInSegment(asservedBandPowers[num_bands] * amortissement[num_bands]))) + (1 - transitionCoef) * transitionIntensity; //0.843137=215/255
        }
        return 40 + (0.843137 * keepItInSegment(asservedBandPowers[num_bands]* amortissement[num_bands]));
    }
    prop = val - bandInf;
    if (transition)
    {
        return (1 - transitionCoef) * transitionIntensity + transitionCoef * (40 +  0.843137 * ( (1 - prop) * keepItInSegment(asservedBandPowers[bandInf] * amortissement[bandInf])+ prop * keepItInSegment(asservedBandPowers[bandInf+1] * amortissement[bandInf+1])) );
    }
    return 40 + 0.843137 * ((1 - prop) * keepItInSegment(asservedBandPowers[bandInf] * amortissement[bandInf])+ prop * keepItInSegment(asservedBandPowers[bandInf+1]* amortissement[bandInf+1]));
}
// ============================= getIntensity()

int Rainbow_bar::getContrast()
{
    if (transition)
    {
        return transitionContrast;
    }
    return 255;
}
// ============================= getContrast()

void Rainbow_bar::startTransition(int transitionTime, bool upOrDown, bool blackOrWhite)
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
            Serial.println("                                        rainbow_bar  ==>       ( white transition ) ");
            transitionIntensity = 255;
            transitionContrast = 255;
            this->transitionCoef = 1;
        }
        else
        {
            Serial.println("                                        ==>  rainbow_bar     ( white transition ) ");
            transitionIntensity = 255;
            transitionContrast = 0;
            this->transitionCoef = 0;
        }
    }
    else
    {
        if (!upOrDown)
        {
            Serial.println("                                        rainbow_bar  ==>       ( black  transition ) ");
            transitionIntensity = 0;
            transitionContrast = 255;
            this->transitionCoef = 1;
        }
        else
        {
            Serial.println("                                        ==>  rainbow_bar     ( black  transition ) ");
            transitionIntensity = 0;
            transitionContrast = 255;
            this->transitionCoef = 0;
        }
    }
}
// ============================= stratTransition()

void Rainbow_bar::resetTransition()
{
    timeSinceTransition = 0;
    transition = false;
    transitionCoef = 1;
    Serial.println("                                              |rainbow_bar|    ");
}
// ============================= resetTransition()

float Rainbow_bar::keepItInSegment(float a)
{
    if(a>255)
    {
        return 255;
    }
    else if(a<0)
    {
        return 0;
    }
    return a;
}
// ============================= keepItInSegment()


