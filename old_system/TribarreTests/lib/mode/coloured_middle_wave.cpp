#include <Coloured_middle_wave.h>

Coloured_middle_wave::Coloured_middle_wave(vector<CRGB*> local_sorted_leds,byte ID, int* bandSmoothedValues, byte* asservedPower)
{
    initiateVariables(ID,local_sorted_leds);
    
    this->fadeToBlackInt=50;

    //data:
    
    this->bandSmoothedValues=bandSmoothedValues;
    this->asservedPower=asservedPower;

    if(listSize%2==0) oneMiddle=false;      //Si un nombre pair de pixels, le centre est composé de 2 pixels
    middle=listSize/2;
    maxSize=(listSize+1)/2-1;
    ledsPower=200;
    realSize=maxSize/2;
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
    this->size=0;
    this->realSize=0;
    this->fff=0;
    
}
// ================================= Extending_waves_mode()
  

void Coloured_middle_wave::update()
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

    colorMemory+= 0.3 * (float(*asservedPower)/255) * (musicGravityCenter - colorMemory);       //On smoothises suivant la puissance
    size = float((*asservedPower) * maxSize) / 255;
    realSize += 0.7 * (size - realSize);                //On smoothise la taille

    if(transition)
    {       
        if(!blackOrWhite)
        {//White
            if (!transitionUp)
            {//Fin de vie

            //time                        :   0   ->  (-)transitionTime/2   ->  (--)transitionTime
            //firstPhase                  :  true ->       false            ->        false
            //whiteTransiPos              :   0   ->      maxSize           ->          0
            //stopDoingStuffDuringTransi  : false ->                        ->        true

                if(!stopDoingStuffDuringTransi)
                {//S'il faut encore faire des calculs (first ou second phase)
                    if(firstPhase)
                    {
                        whiteTransiPos+=speedWhiteTransi;       //On fait grandir le mur de blanc lege
                        if(whiteTransiPos>=maxSize)
                        {   //Quand il atteint la limite, on change de phase
                            whiteTransiPos=maxSize;
                            firstPhase=false;
                        }
                    }
                    else
                    {//SecondPhase
                        whiteTransiPos-=speedWhiteTransi;       //On fait diminuer (et donc grandir) le mur de blanc intense
                        if(whiteTransiPos<=0)
                        {   //Quand on atteint le bout on arrete les calculs
                            whiteTransiPos=0;
                            stopDoingStuffDuringTransi=true;
                        }
                    }
                }
            }           
            else 
            //White      
            {   //debut de vie

            //time                        :   0     ->  (-)transitionTime/2   ->  (--)transitionTime
            //firstPhase                  :  true   ->       false            ->        false
            //whiteTransiPos              : maxSize ->         0              ->        maxSize
            //stopDoingStuffDuringTransi  : false   ->                        ->        true

                if(!stopDoingStuffDuringTransi)
                {//S'il faut encore faire des calculs (first ou second phase)
                    if(firstPhase)
                    {
                        whiteTransiPos+=speedWhiteTransi;   //On fait grandir (et donc diminuer) le mur de blanc intense
                        if(whiteTransiPos>=maxSize)
                        {//On change de phase
                            whiteTransiPos=maxSize;
                            firstPhase=false;
                        }
                    }
                    else
                    {//SecondPhase
                        whiteTransiPos-=speedWhiteTransi;   //On fait diminuer (et donc diminuer) le mur de blanc lege
                        if(whiteTransiPos<=0)
                        {   //Quand on atteint le bout on arrete les calculs
                            whiteTransiPos=0;
                            stopDoingStuffDuringTransi=true;
                        }
                    }
                }
            }
        }
        else            
        {   //Black
            if(!transitionUp)
            {   //fin de vie

            //time                        :   0   ->  (-)transitionTime/2  ->  transitionTime/2  ->  (--)transitionTime
            //firstPhase                  :  true ->       false           ->         false      ->         false
            //blackTransiPos              :   0   ->      maxSize          ->        maxSize     ->        maxSize
            //blackTransiPosCoef          :   0   ->         1             ->           1        ->           1
            //realSize                    :   ?   ->      maxSize          ->        maxSize     ->        maxSize
            //blackTransiPowerCoef        :   0   ->         0             ->           0        ->           1
            //blackWall                   :   0   ->         0             ->           0        ->        maxSize

                if(firstPhase)
                {
                    blackTransiPos+=speedBlackTransi;           //On fait grandir la position limite
                    blackTransiPosCoef=2*float(timeSinceTransition)/transitionTime; //Coef de position
                    if(blackTransiPos>=maxSize-1)
                    {   //Changement de phase à la limite
                        blackTransiPos = maxSize-1;
                        firstPhase = false;
                        blackTransiPosCoef = 1;
                        realSize=maxSize-1;
                        realBlackSize=realSize;
                    }
                    else
                    {
                        realBlackSize=blackTransiPosCoef * (maxSize-1) + (1-blackTransiPosCoef) * realSize;      //On influe la la taille de la barre en la tirant vers la position de transition
                    }
                    blackWall=0;
                }
                else
                {   //SecondPhase
                    realSize=maxSize-1;
                    realBlackSize=realSize;
                    if(timeSinceTransition>transitionTime/2)
                    {//On commence à faire disparaitre à partir de transitionTime/2
                        blackTransiPowerCoef =float(2.2 * timeSinceTransition-transitionTime)/transitionTime;   
                        blackWall=maxSize*blackTransiPowerCoef;     //BlackWall grandit de part et d'autre du centre
                    }
                    else
                    {
                        blackWall=0;
                        blackTransiPowerCoef=0;
                    }
                    if(blackTransiPowerCoef>1)
                    {//Securite
                        
                        blackTransiPowerCoef=1;
                        blackWall=maxSize;
                        
                    }
                }
            }
            else  
            //Black 
            {   //début de vie

            //time                        :   0   ->   (transitionTime/2    ->    transitionTime
            //blackTransiPowerCoef        :   0   ->         0.5            ->          1
            //ledsPower                   :   0   ->          ?             ->          0 

               blackTransiPowerCoef=float(timeSinceTransition)/transitionTime;  //On fait reapparaitre petit à petit
            }    
        }
        
    }
}
// ================================= update()

void Coloured_middle_wave::draw()
{
   if(!transition)
   {
        ledsPower = 0.5 * (255 + (*asservedPower));
        if(oneMiddle)
        {
            (*local_sorted_leds[middle])=CHSV(colorMemory,255,ledsPower);
            for (int nbLed=1 ; nbLed<=realSize ; nbLed++)
            {
                (*local_sorted_leds[middle+nbLed])=CHSV(colorMemory,255,ledsPower);
                (*local_sorted_leds[middle-nbLed])=CHSV(colorMemory,255,ledsPower);
            }
        }
        else
        {
            (*local_sorted_leds[middle])=CHSV(colorMemory,255,ledsPower);
            (*local_sorted_leds[middle-1])=CHSV(colorMemory,255,ledsPower);
            for (int nbLed=1 ; nbLed<=realSize ; nbLed++)
            {
                (*local_sorted_leds[middle+nbLed])=CHSV(colorMemory,255,ledsPower);
                (*local_sorted_leds[middle-nbLed-1])=CHSV(colorMemory,255,ledsPower);
            }
        }
    }
    else    //Transi
    {
        if(!blackOrWhite)   
        {   //White
            if(!transitionUp)       
            {   //Fin de vie
                ledsPower = 0.5 * (255 + (*asservedPower));
                if(firstPhase)
                {
                    for (int whiteLeds=0 ; whiteLeds<whiteTransiPos ; whiteLeds++)
                    {   //Mur de leds blanches legeres en dessous des barres qui grandit (whiteTransiPos grandit)
                        (*local_sorted_leds[(listSize-1)-whiteLeds])=CHSV(0,0,50);
                        (*local_sorted_leds[whiteLeds])=CHSV(0,0,50);
                    }

                    if(oneMiddle)
                    {

                        (*local_sorted_leds[middle])=CHSV(colorMemory,255,ledsPower);
                        for (int nbLed=1 ; nbLed<=realSize ; nbLed++)
                        {
                            (*local_sorted_leds[middle+nbLed])=CHSV(colorMemory,255,ledsPower);
                            (*local_sorted_leds[middle-nbLed])=CHSV(colorMemory,255,ledsPower);
                        }

                    }
                    else
                    {

                        (*local_sorted_leds[middle])=CHSV(colorMemory,255,ledsPower);
                        (*local_sorted_leds[middle-1])=CHSV(colorMemory,255,ledsPower);
                        for (int nbLed=1 ; nbLed<=realSize ; nbLed++)
                        {
                            (*local_sorted_leds[middle+nbLed])=CHSV(colorMemory,255,ledsPower);
                            (*local_sorted_leds[middle-nbLed-1])=CHSV(colorMemory,255,ledsPower);
                        }

                    }
                }
                else
                {
                    for (int whiteLeds=0 ; whiteLeds<listSize ; whiteLeds++)
                    {//Un fond de blanc lege en dessous de tout
                        (*local_sorted_leds[whiteLeds])=CHSV(0,0,50);
                    }

                    if(oneMiddle)
                    {

                        for (int nbLed=maxSize-whiteTransiPos+1 ; nbLed<=realSize ; nbLed++)
                        {
                            (*local_sorted_leds[middle+nbLed])=CHSV(colorMemory,255,ledsPower);
                            (*local_sorted_leds[middle-nbLed])=CHSV(colorMemory,255,ledsPower);
                        }

                        (*local_sorted_leds[middle])=CHSV(0,0,255);
                        for (int whiteLeds=1 ; whiteLeds<maxSize-whiteTransiPos ; whiteLeds++)
                        {   //Blanc intense grandissant (car whiteTransiPos diminue)
                            (*local_sorted_leds[middle+whiteLeds])=CHSV(0,0,255);
                            (*local_sorted_leds[middle-whiteLeds])=CHSV(0,0,255);
                        }

                    }
                    else
                    {

                        for (int nbLed=maxSize-whiteTransiPos+1 ; nbLed<=realSize ; nbLed++)
                        {
                            (*local_sorted_leds[middle+nbLed])=CHSV(colorMemory,255,ledsPower);
                            (*local_sorted_leds[middle-1-nbLed])=CHSV(colorMemory,255,ledsPower);
                        }

                        (*local_sorted_leds[middle])=CHSV(0,0,255);
                        (*local_sorted_leds[middle-1])=CHSV(0,0,255);
                        for (int whiteLeds=1 ; whiteLeds<maxSize-whiteTransiPos ; whiteLeds++)
                        {   //Blanc intense grandissant (car whiteTransiPos diminue)
                            (*local_sorted_leds[middle+whiteLeds])=CHSV(0,0,255);
                            (*local_sorted_leds[middle-1-whiteLeds])=CHSV(0,0,255);
                        }

                    }
                }
            }
            else 
            //White
            {   //debut de vie
                ledsPower = 0.5 * (255 + (*asservedPower));
                if(firstPhase)
                {   //Fon de blanc lege
                    for (int whiteLeds=0 ; whiteLeds<listSize ; whiteLeds++)
                    {
                        (*local_sorted_leds[whiteLeds])=CHSV(0,0,50);
                    }
                    if(oneMiddle)
                    {
                        for (int nbLed=maxSize-whiteTransiPos+1 ; nbLed<=realSize ; nbLed++)
                        {
                            (*local_sorted_leds[middle+nbLed])=CHSV(colorMemory,255,ledsPower);
                            (*local_sorted_leds[middle-nbLed])=CHSV(colorMemory,255,ledsPower);
                        }
                        (*local_sorted_leds[middle])=CHSV(0,0,255);
                        for (int whiteLeds=1 ; whiteLeds<maxSize-whiteTransiPos ; whiteLeds++)
                        {
                            (*local_sorted_leds[middle+whiteLeds])=CHSV(0,0,255);
                            (*local_sorted_leds[middle-whiteLeds])=CHSV(0,0,255);
                        }
                    }
                    else
                    {
                        for (int nbLed=maxSize-whiteTransiPos+1 ; nbLed<=realSize ; nbLed++)
                        {
                            (*local_sorted_leds[middle+nbLed])=CHSV(colorMemory,255,ledsPower);
                            (*local_sorted_leds[middle-1-nbLed])=CHSV(colorMemory,255,ledsPower);
                        }
                        (*local_sorted_leds[middle])=CHSV(0,0,255);
                        (*local_sorted_leds[middle-1])=CHSV(0,0,255);
                        for (int whiteLeds=1 ; whiteLeds<maxSize-whiteTransiPos ; whiteLeds++)
                        {
                            (*local_sorted_leds[middle+whiteLeds])=CHSV(0,0,255);
                            (*local_sorted_leds[middle-1-whiteLeds])=CHSV(0,0,255);
                        }
                    }
                }
                else
                {
                    for (int whiteLeds=0 ; whiteLeds<whiteTransiPos ; whiteLeds++)
                    {
                        (*local_sorted_leds[(listSize-1)-whiteLeds])=CHSV(0,0,50);
                        (*local_sorted_leds[whiteLeds])=CHSV(0,0,50);
                    }
                    if(oneMiddle)
                    {
                        for (int nbLed=0 ; nbLed<=realSize ; nbLed++)
                        {
                            (*local_sorted_leds[middle+nbLed])=CHSV(colorMemory,255,ledsPower);
                            (*local_sorted_leds[middle-nbLed])=CHSV(colorMemory,255,ledsPower);
                        }
                    }
                    else
                    {
                        for (int nbLed=0 ; nbLed<=realSize ; nbLed++)
                        {
                            (*local_sorted_leds[middle+nbLed])=CHSV(colorMemory,255,ledsPower);
                            (*local_sorted_leds[middle-1-nbLed])=CHSV(colorMemory,255,ledsPower);
                        }
                    }
                }
            }
        }
        else
        {       //Black
            if(!transitionUp)       //Fin de vie
            {
                ledsPower =0.5 * (255 + (*asservedPower));// (1-blackTransiPowerCoef) * 0.5 * (255 + (*asservedPower));
                if(oneMiddle)
                {
                    //(*local_sorted_leds[middle])=CHSV(colorMemory,255,testPower);
                    for (int nbLed=blackWall ; nbLed<=realBlackSize ; nbLed++)
                    {
                        (*local_sorted_leds[middle+nbLed])=CHSV(colorMemory,255,ledsPower);
                        (*local_sorted_leds[middle-nbLed])=CHSV(colorMemory,255,ledsPower);
                    }
                }
                else
                {
                    //(*local_sorted_leds[middle])=CHSV(colorMemory,255,testPower);
                    //(*local_sorted_leds[middle-1])=CHSV(colorMemory,255,testPower);
                    for (int nbLed=blackWall ; nbLed<=realBlackSize ; nbLed++)
                    {
                        (*local_sorted_leds[middle+nbLed])=CHSV(colorMemory,255,ledsPower);
                        (*local_sorted_leds[middle-nbLed-1])=CHSV(colorMemory,255,ledsPower);
                    }
                }
            }
            else        //Black || début de vie
            {
                ledsPower = blackTransiPowerCoef * 0.5 * (255 + (*asservedPower));
                if(ledsPower<0) ledsPower=0;
                if(oneMiddle)
                {
                    (*local_sorted_leds[middle])=CHSV(colorMemory,255,ledsPower);
                    for (int nbLed=1 ; nbLed<=realSize ; nbLed++)
                    {
                        (*local_sorted_leds[middle+nbLed])=CHSV(colorMemory,255,ledsPower);
                        (*local_sorted_leds[middle-nbLed])=CHSV(colorMemory,255,ledsPower);
                    }
                }
                else
                {
                    (*local_sorted_leds[middle])=CHSV(colorMemory,255,ledsPower);
                    (*local_sorted_leds[middle-1])=CHSV(colorMemory,255,ledsPower);
                    for (int nbLed=1 ; nbLed<=realSize ; nbLed++)
                    {
                        (*local_sorted_leds[middle+nbLed])=CHSV(colorMemory,255,ledsPower);
                        (*local_sorted_leds[middle-nbLed-1])=CHSV(colorMemory,255,ledsPower);
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

void Coloured_middle_wave::updateTransitionTimer()
{
    timeSinceTransition+=1;
    if (timeSinceTransition>=transitionTime)
    {
        resetTransition();
    }
}
// ================================= updateTransitionTimer()

void Coloured_middle_wave::activate()
{
    this->activated=true;
}
// ================================= activate()

void Coloured_middle_wave::deactivate()
{
    this->activated=false;
}
// ================================= deactivate()


void Coloured_middle_wave::startTransition(int transitionTime, bool upOrDown, bool blackOrWhite)
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

void Coloured_middle_wave::resetTransition()
{
    this->transition=false;
    Serial.println("                                                             |Coloured_middle_wave|    ");
}
// ================================= resetTransition()