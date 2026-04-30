#include <flying_ball.h>

Flying_ball::Flying_ball(byte ID, int* bandSmoothedValues, byte* asservedPower)
{
    this->activated=false;
    this->fadeToBlackInt=45;
    this->ID=ID;
    resetTransition();
    //data:
    this->bandSmoothedValues=bandSmoothedValues;
    this->asservedPower=asservedPower;

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
    this->size=0;
    this->realSize=0;
    this->fff=0;

    this->ID=ID;

    for (byte a=0 ; a<16 ; a++)
    {
        localAsservissement[a]=pow((0.5+0.5*(float(a)/15)),2);
    }
    
}
// ================================= Extending_waves_mode()
  

void Flying_ball::update()
{
    musicGravityCenter=0;
    soundWeight=0;
    for (int s=0 ; s<16 ; s++)                          
    {
        fff=bandSmoothedValues[s];
        fff=localAsservissement[s]*fff/100;
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
    /*
    musicGravityCenter/=(soundWeight);
    if(musicGravityCenter<3)
    {
        musicGravityCenter=0.5*(musicGravityCenter);
    }
    else if (musicGravityCenter>=4)
    {
        musicGravityCenter=0.5*(musicGravityCenter+15);
    }
    if(musicGravityCenter<0) musicGravityCenter=0;
    musicGravityCenter/=15;
    */
    if(musicGravityCenter>0.6) musicGravityCenter=0.5*(1+musicGravityCenter);
    else if(musicGravityCenter<0.4) musicGravityCenter*=0.6;
    colorMemory += 0.35 * (float(*asservedPower)/255) * (180*musicGravityCenter - colorMemory);       //On smoothises suivant la puissance
    ballPosition += 0.15 * (listSize * musicGravityCenter - ballPosition);
    //ballPosition = listSize * musicGravityCenter;
    //colorMemory=180*musicGravityCenter;
    size = float((*asservedPower) * maxSize) / 255;
    //realSize += 0.7 * (size - realSize);                //On smoothise la taille
    realSize=5;
    colorMemory += 0.002 * (90 - colorMemory);
    ballPosition += 0.08 * (listSize/2 - ballPosition);

}
// ================================= update()

void Flying_ball::draw()
{
   if(!transition)
   {
        ledsPower = 0.5 *( 0.5* (*asservedPower+255) + ledsPower);
        (*local_sorted_leds[ballPosition])=CHSV(colorMemory,255,ledsPower);
        for (byte led=1 ; led<realSize ; led++)
        {
            if ((ballPosition + led)<listSize-1)
            {
                (*local_sorted_leds[ballPosition+led])=CHSV(colorMemory,255,ledsPower);
            }
            else if( (ballPosition - led)>=0)
            {
                (*local_sorted_leds[ballPosition-led])=CHSV(colorMemory,255,ledsPower);
            }
        }
   }
   
   
    if(transition)
    {
        updateTransitionTimer();
    }
}
// ================================= draw()

void Flying_ball::updateTransitionTimer()
{
    timeSinceTransition+=1;
    if (timeSinceTransition>=transitionTime)
    {
        resetTransition();
    }
}
// ================================= updateTransitionTimer()

void Flying_ball::activate(vector<CRGB*> local_sorted_leds)
{
    this->activated=true;
    this->transition=false;

    this->local_sorted_leds=local_sorted_leds;
    this->listSize = local_sorted_leds.size();

    maxSize=6;
    ledsPower=200;
    realSize=2;
    ballPosition=listSize/2;
    colorMemory=90;
}
// ================================= activate()

void Flying_ball::deactivate()
{
    this->activated=false;
    local_sorted_leds.clear();
}
// ================================= deactivate()


void Flying_ball::startTransition(int transitionTime, bool upOrDown, bool blackOrWhite)
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
            stopDoingStuffDuringTransi=false;
            speedWhiteTransi=float(listSize)/transitionTime+0.05;
            whiteTransiPos=0;
            firstPhase=true;
            Serial.println("                                                            Coloured_middle_wave  ==>       ( white transition ) ");
        }
        else
        {//debut de vie
            stopDoingStuffDuringTransi=false;
            speedWhiteTransi=float(listSize)/transitionTime+0.05;
            whiteTransiPos=0;
            firstPhase=true;
            Serial.println("                                                            ==>  Coloured_middle_wave     ( white transition ) ");
        }
    }
    else
    {//black
        if (!this->transitionUp)
        {//fin de vie
            speedBlackTransi=2*float(listSize)/transitionTime;
            blackTransiPos=0;
            blackTransiPosCoef=0;
            blackTransiPowerCoef=0;
            firstPhase=true;
            blackWall=0;
            Serial.println("                                                            Coloured_middle_wave  ==>       ( black  transition ) ");
        }
        else
        {//debut de vie
            blackTransiPowerCoef=0;
            blackWall=0;
            Serial.println("                                                             ==>  Coloured_middle_wave     ( black  transition ) ");
        }
    }
}
// ================================= startTransition()

void Flying_ball::resetTransition()
{
    this->transition=false;
    Serial.println("                                                             |Coloured_middle_wave|    ");
}
// ================================= resetTransition()