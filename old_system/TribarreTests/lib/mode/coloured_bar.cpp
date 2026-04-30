#include <coloured_bar.h>

Coloured_bar::Coloured_bar(vector<CRGB*> local_sorted_leds,byte ID, int* bandSmoothedValues, byte* asservedPower)
{
    initiateVariables(ID,local_sorted_leds);
    
    this->fadeToBlackInt=0;

    //data:
    
    this->bandSmoothedValues=bandSmoothedValues;
    this->asservedPower=asservedPower;

    ledsPower=200;
    colorMemory=90;

    this->analysingNeeds[0] = true;         //Ecoute
    this->analysingNeeds[1] = true;         //FFT
    this->analysingNeeds[2] = false;        //Peaks
    this->analysingNeeds[3] = true;         //asservBands
    this->analysingNeeds[4] = true;         //Power
    for (byte band=0 ; band<16 ; band++)
    {
        this->bandAnalysingNeeds[band]=true;
    }

    this->colorMemory=80;
    this->musicGravityCenter=0;
    this->soundWeight=0;
    this->fff=0;
    
}
// ================================= Extending_waves_mode()
  

void Coloured_bar::update()
{
    musicGravityCenter=0;
    soundWeight=0;
    for (int s=0 ; s<16 ; s++)                          
    {
        fff=bandSmoothedValues[s];
        fff=fff/100;
        this->musicGravityCenter+=s*pow(fff,2);       //Ca permet de mettre en valeur les peaks
        this->soundWeight+=pow(fff,2);                //On prend le total pour calculer les proportions apres
    }

    /*
    On divise par 5 pour séparer, d'un cote les bandes <5 qui seront alors <1 et les bandes >5 qui seront >1.
    En mettant a la puissance apres, on accentue l'ecart entre ces 2 zones. Ainsi la couleur va plus facilement alterner entre
    rouge et vert.
    */
    musicGravityCenter=musicGravityCenter/(4*soundWeight);
    musicGravityCenter=pow(musicGravityCenter,1.5);
    musicGravityCenter/=7.26;
    musicGravityCenter= 180 * musicGravityCenter;

    colorMemory+= 0.3 * (float(*asservedPower)/255) * (musicGravityCenter - colorMemory);       //On smoothises suivant la puissance

    if(transition)
    {
        if(!blackOrWhite)
        { 
            timeBeforeWhite-=1;
            if(timeBeforeWhite<=0)
            {
                drawAllWhite=true;
                whiteFrequency=15-14*float(timeSinceTransition)/(0.9*transitionTime);
                if(whiteFrequency<1)
                {
                    whiteFrequency=1;
                }
                timeBeforeWhite=whiteFrequency;
            }
                
        }
        else
        {
            timeBeforeBlack-=1;
            if(timeBeforeBlack<=0)
            {
                drawAllBlack=true;
                blackFrequency=15-14*float(timeSinceTransition)/(0.9*transitionTime);
                if(blackFrequency<1)
                {
                    blackFrequency=1;
                }
                timeBeforeBlack=blackFrequency;
            }
        }
    }
}
// ================================= update()

void Coloured_bar::draw()
{

    if(!transition)
    {
        ledsPower = 0.5 * (255 + (*asservedPower));
        
        for (int nbLed=0 ; nbLed<listSize ; nbLed++)
        {
            (*local_sorted_leds[nbLed])=CHSV(colorMemory,255,ledsPower);
        }
    }
    else
    {
        if(!blackOrWhite)
        {
            if(!transitionUp)
            {
                if(drawAllWhite)
                {
                    for(int led=0 ; led<listSize ; led++)
                    {
                        (*local_sorted_leds[led])=CHSV(0,0,255);
                    }
                    drawAllWhite=false;
                }
                else
                {
                    ledsPower = 0.5 * (255 + (*asservedPower));
                    for (int nbLed=0 ; nbLed<listSize ; nbLed++)
                    {
                        (*local_sorted_leds[nbLed])=CHSV(colorMemory,255,ledsPower);
                    }
                }
            }
            else
            {
                if(drawAllWhite)
                {
                    ledsPower = 0.5 * (255 + (*asservedPower));
                    for (int nbLed=0 ; nbLed<listSize ; nbLed++)
                    {
                        (*local_sorted_leds[nbLed])=CHSV(colorMemory,255,ledsPower);
                    }
                    drawAllWhite=false;
                }
                else
                {
                    for(int led=0 ; led<listSize ; led++)
                    {
                        (*local_sorted_leds[led])=CHSV(0,0,255);
                    }
                }
            }
        }
        else
        {
            if(!transitionUp)
            {
                if(drawAllBlack)
                {
                    for(int led=0 ; led<listSize ; led++)
                    {
                        (*local_sorted_leds[led])=CHSV(0,0,0);
                    }
                    drawAllBlack=false;
                }
                else
                {
                    ledsPower = 0.5 * (255 + (*asservedPower));
                    for (int nbLed=0 ; nbLed<listSize ; nbLed++)
                    {
                        (*local_sorted_leds[nbLed])=CHSV(colorMemory,255,ledsPower);
                    }
                }
            }
            else
            {
                if(drawAllBlack)
                {
                    ledsPower = 0.5 * (255 + (*asservedPower));
                    for (int nbLed=0 ; nbLed<listSize ; nbLed++)
                    {
                        (*local_sorted_leds[nbLed])=CHSV(colorMemory,255,ledsPower);
                    }
                    drawAllBlack=false;
                }
                else
                {
                    for(int led=0 ; led<listSize ; led++)
                    {
                        (*local_sorted_leds[led])=CHSV(0,0,0);
                    }
                }
            }
        }
    }

    if(transition)
    {
        updateTransitionTimer();
    }
}
// ================================= draw()

void Coloured_bar::updateTransitionTimer()
{
    timeSinceTransition+=1;
    if (timeSinceTransition>=transitionTime)
    {
        resetTransition();
    }
}
// ================================= updateTransitionTimer()

void Coloured_bar::activate()
{
    this->activated=true;
}
// ================================= activate()

void Coloured_bar::deactivate()
{
    this->activated=false;
}
// ================================= deactivate()


void Coloured_bar::startTransition(int transitionTime, bool upOrDown, bool blackOrWhite)
{
    this->transition=true;
    this->blackOrWhite=blackOrWhite;
    this->transitionUp=upOrDown;
    this->timeSinceTransition=0;
    this->transitionTime=transitionTime;
    if (!this->blackOrWhite)
    {//white
        if (!upOrDown)
        {//fin de vie
            timeBeforeWhite=15;
            drawAllWhite=false;
            Serial.println("                                                            Coloured_Bar  ==>       ( white transition ) ");
        }
        else
        {//debut de vie
            timeBeforeWhite=15;
            drawAllWhite=false;
            Serial.println("                                                            ==>  Coloured_Bar     ( white transition ) ");
        }
    }
    else
    {//black
        if (!this->transitionUp)
        {//fin de vie
            timeBeforeBlack=15;
            drawAllBlack=false;
            Serial.println("                                                            Coloured_Bar  ==>       ( black  transition ) ");
        }
        else
        {//debut de vie
            timeBeforeBlack=15;
            drawAllBlack=false;
            Serial.println("                                                             ==>  Coloured_Bar     ( black  transition ) ");
        }
    }
}
// ================================= startTransition()

void Coloured_bar::resetTransition()
{
    this->transition=false;
    Serial.println("                                                             |Coloured_Bar|    ");
}
// ================================= resetTransition()