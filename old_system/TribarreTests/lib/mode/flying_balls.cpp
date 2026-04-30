#include <flying_balls.h>

Flying_balls::Flying_balls(byte ID, int* bandSmoothedValues, byte* asservedPower)
{
    this->activated=false;
    this->fadeToBlackInt=55;
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

    this->ID=ID;

    for (byte a=0 ; a<16 ; a++)
    {
        localAsservissement[a]=pow((0.6+0.4*(float(a)/15)),2);
    }
    
}
// ================================= Extending_waves_mode()
  

void Flying_balls::update()
{
    musicBassCenter=0;
    bassWeight=0;
    middleWeight=0;
    musicAiguCenter=0;
    aiguWeight=0;
    for (int s=0 ; s<5 ; s++)                          
    {
        fff=bandSmoothedValues[s];
        fff=localAsservissement[s]*fff/100;
        this->musicBassCenter+=s*pow(fff,2);       //Ca permet de mettre en valeur les peaks
        this->bassWeight+=pow(fff,2);                //On prend le total pour calculer les proportions apres
    }
    for(byte s=5 ; s<8; s++)
    {
        fff=bandSmoothedValues[s];
        fff=localAsservissement[s]*fff/100;
        this->middleWeight+=pow(fff,2);       
    }
    for (int s=6 ; s<15 ; s++)                          
    {
        fff=bandSmoothedValues[s];
        fff=localAsservissement[s]*fff/100;
        this->musicAiguCenter+=(s-5)*pow(fff,2);       //Ca permet de mettre en valeur les peaks
        this->aiguWeight+=pow(fff,2);                //On prend le total pour calculer les proportions apres
    }

    /*
    On divise par 5 pour séparer, d'un cote les bandes <5 qui seront alors <1 et les bandes >5 qui seront >1.
    En mettant a la puissance apres, on accentue l'ecart entre ces 2 zones. Ainsi la couleur va plus facilement alterner entre
    rouge et vert.
    */
    musicBassCenter/=(6*bassWeight);
    musicAiguCenter/=(9*aiguWeight);

    if(musicAiguCenter>0.6) musicAiguCenter=0.5*(1+musicAiguCenter);
    else if(musicAiguCenter<0.4) musicAiguCenter*=0.6;
    if(musicBassCenter>0.6) musicBassCenter=0.5*(1+musicBassCenter);
    else if(musicBassCenter<0.4) musicBassCenter*=0.6;
    aiguCoef = aiguWeight/(2*bassWeight+aiguWeight+middleWeight);
    bassCoef = 2*bassWeight/(2*bassWeight+middleWeight+aiguWeight);
    colorMemory1 += 0.6 * (float(*asservedPower)/255) * (90*musicBassCenter - colorMemory1);       //On smoothises suivant la puissance
    ballPosition1 +=  0.1 * (1+6*bassCoef) * ((listSize/2) - ((listSize/2) *  (2*(1-musicBassCenter) + bassCoef)/3) - ballPosition1);

    colorMemory2 += 0.6 * (float(*asservedPower)/255) * (90 + 90*musicAiguCenter - colorMemory2);       //On smoothises suivant la puissance
    ballPosition2 += 0.1 * (1+6*aiguCoef) * ( listSize/2 + (listSize/2) * ( 2*musicAiguCenter + aiguCoef)/3 - ballPosition2);

    //size = float((*asservedPower) * maxSize) / 255;
    //realSize += 0.7 * (size - realSize);                //On smoothise la taille
    realSize=3;
    colorMemory1 += 0.004 * (45 - colorMemory1);
    ballPosition1 += 0.5 *(float(*asservedPower)/255)* (listSize/2 - ballPosition1);
    colorMemory2 += 0.004 * (135 - colorMemory2);
    ballPosition2 += 0.4 *(float(*asservedPower)/255)* (listSize/2 - ballPosition2);

    

}
// ================================= update()

void Flying_balls::draw()
{
   if(!transition)
   {
        bassPower = 0.4 *( 0.5* (255*(1+bassCoef)) + bassPower);
        (*local_sorted_leds[ballPosition1])=CHSV(colorMemory1,100,255);
        for (byte led=1 ; led<2+5*bassCoef ; led++)
        {
            if ((ballPosition1 + led)<=listSize/2)
            {
                (*local_sorted_leds[ballPosition1+led])=CHSV(colorMemory1,255,bassPower);
            }
            if( (ballPosition1 - led)>=0)
            {
                (*local_sorted_leds[ballPosition1-led])=CHSV(colorMemory1,255,bassPower);
            }
        }
        aiguPower = 0.4 *( 0.5* (255*(1+aiguCoef)) + aiguPower);
        (*local_sorted_leds[ballPosition2])=CHSV(colorMemory2,100,255);
        for (byte led=1 ; led<2+5*(1+aiguCoef) ; led++)
        {
            if ((ballPosition2 + led)<=listSize-1)
            {
                (*local_sorted_leds[ballPosition2+led])=CHSV(colorMemory2,255,aiguPower);
            }
            if( (ballPosition2 - led)>=listSize/2)
            {
                (*local_sorted_leds[ballPosition2-led])=CHSV(colorMemory2,255,aiguPower);
            }
        }
   }
   
   
    if(transition)
    {
        updateTransitionTimer();
    }
}
// ================================= draw()

void Flying_balls::updateTransitionTimer()
{
    timeSinceTransition+=1;
    if (timeSinceTransition>=transitionTime)
    {
        resetTransition();
    }
}
// ================================= updateTransitionTimer()

void Flying_balls::activate(vector<CRGB*> local_sorted_leds)
{
    this->activated=true;
    this->transition=false;

    this->local_sorted_leds=local_sorted_leds;
    this->listSize = local_sorted_leds.size();

    maxSize=6;
    bassPower=200;
    realSize=2;
    ballPosition1=listSize/4;
    colorMemory1=45;
    ballPosition2=3*listSize/4;
    colorMemory2=135;
}
// ================================= activate()

void Flying_balls::deactivate()
{
    this->activated=false;
    local_sorted_leds.clear();
}
// ================================= deactivate()


void Flying_balls::startTransition(int transitionTime, bool upOrDown, bool blackOrWhite)
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

void Flying_balls::resetTransition()
{
    this->transition=false;
    Serial.println("                                                             |Coloured_middle_wave|    ");
}
// ================================= resetTransition()