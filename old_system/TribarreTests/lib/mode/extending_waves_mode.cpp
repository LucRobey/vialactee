#include <extending_waves_mode.h>

Extending_waves_mode::Extending_waves_mode(vector<CRGB*> local_sorted_leds,byte ID, int* bandSmoothedValues, byte* asservedPower)
{
    initiateVariables(ID,local_sorted_leds);
    this->fadeToBlackInt=0;
    
    colors.clear();
    if(listSize%2==0) oneMiddle=false;      //Si un nombre pair de pixels, le centre est composé de 2 pixels
    middle=listSize/2;
    for (int s=0 ; s<(listSize+1)/2 ; s++)
    {
        colors.push_back(new byte[3]);
        colors[s][2]=0; //Intensité initiale nulle, probablement inutile
    }
    music_color=80;

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
        bandAnalysingNeeds[band]=true;
    }
}
// ================================= Extending_waves_mode()
  
int countFall;
int jcpatrop;
void Extending_waves_mode::update()
{
    music_center=0;
    totalSound=0;
    for (byte s=0 ; s<16 ; s++)                          //On ecoute la musique
    {
        music_center+=s*bandSmoothedValues[s]*bandSmoothedValues[s];    //On pondere par le carré de la valeur pour donner encore plus de poids aux fréquences fortes
        totalSound+=bandSmoothedValues[s]*bandSmoothedValues[s];
    }
    music_center/=totalSound;
    music_color+= 0.3*(80*music_center/15 - music_color);
    music_color+= 0.05*(80-music_color);
    

    if(transition)
    {
        if(!blackOrWhite)
        {   //White
            if (!transitionUp )
            {//Fin de vie
                if(!stopPopingWhite)
                {//S'il faut encore faire apparaître des pixels blancs
                    if(colors[(listSize+1)/2-1 - whiteWallLimit-1][1]==0)
                    {   //si un pixel blanc atteint le mur, on fait augmenter le mur de 1
                        colors[(listSize+1)/2-1 - whiteWallLimit][0]=0;
                        colors[(listSize+1)/2-1 - whiteWallLimit][1]=0;
                        colors[(listSize+1)/2-1 - whiteWallLimit][2]=255;
                        whiteWallLimit+=1;
                        if(whiteWallLimit>=(listSize+1)/2-1)
                        {//Si le mur atteint le centre, on arrete de faire apparaitre des pixels blancs
                            stopPopingWhite=true;
                        }
                    }
                    for (int k=(listSize+1)/2-1 - whiteWallLimit -1 ; k>0 ; k--)
                    {//On fait avancer les pixels
                        colors[k][0]=colors[k-1][0];
                        colors[k][1]=colors[k-1][1];
                        colors[k][2]=colors[k-1][2];
                    }
                    
                }
            }
            else
        //White       RAPPEL: un bloc est 2 pixels blancs à côtés
            {//début de vie
                countFall=0;        //On compte cb de blocs on fait tomber et quand on atteint le bon nombre, on va s arreter
                                    //CountFall vérifie qu'on en fait tomber le bon nombre
                if(colors[1][1]==0)
                {   //On fait disparaitrele bloc
                    colors[1][1]=255;
                    numberOfFallAtTheSameTime-=1;   //On fait donc baisser le nombre de blocs à faire tomber
                }
                jcpatrop=2;   //On va donc parcourir la liste à la recherche de blocs blancs, et en faire tomber le bon nombre    
                while(countFall<numberOfFallAtTheSameTime) //On ne regarde que à partir du pixel numéro 2 (ceux avant ont été géré juste au dessus)
                {
                    if(colors[jcpatrop][1]==0)
                    {   //Si on atteint un pixel blanc, et qu'on a pas encore fait tombé assez de blocs, on le fait tomber
                        colors[jcpatrop-1][1]=0;        //On fait tomber sa whitnsess
                        colors[jcpatrop][1]=255;        //On remet la whitness de l'ancien emplacement à 255
                        countFall+=1;                   //On garde les comptes         
                    }
                    jcpatrop+=1;
                }
                if(timeSinceTransition==nextFall && !waitingForTheEnd)
                {   //S'il est temps de faire tomber un nouveau bloc:
                    if(colors[(listSize+1)/2 - 1][1]==0)
                    {//On vérifie qu'il y a encore des blocs àfaire tomber
                        numberOfFallAtTheSameTime+=1;
                        nextFall+=delta_t;          //On calcul le prochain timing pour faire tomber un nouveau bloc
                        if(colors[(listSize+1)/2 - 2][1]==0)
                        {                                       //Si on peut faire un bloc de 2, on le fait. (imaginons qu'il ne reste plus qu une seule led, alors on ne peut pas faire un bloc de 2)
                            numberOfFallAtTheSameTime+=1;
                        }
                    }
                    else
                    { //Si la derniere led n'est plus blanche, on arrete
                        waitingForTheEnd=true;
                    }
                } 
                for (int k=(listSize+1)/2-1; k>0 ; k--)
                {   //On fait bouger les couleurs et l'intensité, mais pas la whitness!
                    colors[k][0]=colors[k-1][0];
                    colors[k][2]=colors[k-1][2];
                }
            }
        }
        else
        {
            for (int k=(listSize+1)/2-1 ; k>0 ; k--)
            {//On fait avancer tous les pixels
                colors[k][0]=colors[k-1][0];
                colors[k][1]=colors[k-1][1];
                colors[k][2]=colors[k-1][2];
            }
        }
    }
    else
    {
        for (int k=(listSize+1)/2-1 ; k>0 ; k--)
        {//On fait avancer tous les pixels
            colors[k][0]=colors[k-1][0];
            colors[k][1]=colors[k-1][1];
            colors[k][2]=colors[k-1][2];
        }
    }
    if(transition)
    {
        if(!blackOrWhite)
        {//White
            if(!transitionUp)
            {//Fin de vie
                if(!stopPopingWhite)
                {//S'il faut continuer à faire apparaitre des pixels blancs
                    if(timeSinceTransition==nextApparition)
                    {//Si on est à la bonne date
                        colors[0][0]=0;
                        colors[0][1]=0;
                        colors[0][2]=255;
                        nextApparition+=int(whiteApparitionRate);   //On calcul la prochaine date d apparition
                    }
                    else
                    {//Sinon, on fait l'apparition normale
                        colors[0][0]=music_color;
                        colors[0][1]=255;
                        colors[0][2]=(*asservedPower);
                    }
                }
            }
            else
        //White
            {//Début de vie
            //Apparition normale
                colors[0][0]=music_color;
                colors[0][1]=255;
                colors[0][2]=(*asservedPower); 
            }
        }
        else
        {//Black
            if(!transitionUp)
            {//Fin de vie
                if(timeToDesapear>=timeSinceTransition)
                {//On met à jour intensityBlackTransitionCoef
                    intensityBlackTransitionCoef=1-float(timeSinceTransition)/timeToDesapear;
                    if(intensityBlackTransitionCoef<0)
                    {
                        intensityBlackTransitionCoef=0;
                    }
                }
                //Apparition normale
                colors[0][0]=music_color;
                colors[0][1]=255;
                colors[0][2]=intensityBlackTransitionCoef*(*asservedPower);
                
            }
            else
        //Black
            {//Début de vie
                intensityBlackTransitionCoef=float(timeSinceTransition)/transitionTime;    //On met à jour intensityBlackTransitionCoef
                //Apparition normale
                colors[0][0]=music_color;
                colors[0][1]=255;
                colors[0][2]=intensityBlackTransitionCoef*(*asservedPower);
            }
        }
    }
    else
    {
        //Apparition normale
        colors[0][0]=music_color;
        colors[0][1]=255;
        colors[0][2]=(*asservedPower); 
    }
}
// ================================= update()

void Extending_waves_mode::draw()
{
    if(oneMiddle)
    {//S'il n'y a qu un seul milieu: (symétrie simple)
        (*local_sorted_leds[middle])=CHSV(colors[0][0],colors[0][1],colors[0][2]);
        for (int s=1 ; s<(listSize+1)/2 ; s++)
        {
            if(colors[s][1]==0)
            {//Si le pixel est blanc, on met son intensité au max!
                (*local_sorted_leds[middle-s])=CHSV(colors[s][0],0,255);
                (*local_sorted_leds[middle+s])=CHSV(colors[s][0],0,255);
            }
            else
            {//Sinon intensité normale
                (*local_sorted_leds[middle-s])=CHSV(colors[s][0],255,colors[s][2]);
                (*local_sorted_leds[middle+s])=CHSV(colors[s][0],255,colors[s][2]);
            }
        }   
    }
    else
    {//2 centres, symétrie chelou
        (*local_sorted_leds[middle])=CHSV(colors[0][0],colors[0][1],colors[0][2]);
        (*local_sorted_leds[middle-1])=CHSV(colors[0][0],colors[0][1],colors[0][2]);
        for (int s=1 ; s<(listSize+1)/2 ; s++)
        {
            if(colors[s][1]==0)
            {//Si le pixel est blanc, on met son intensité au max!
                (*local_sorted_leds[middle-1-s])=CHSV(colors[s][0],0,255);
                (*local_sorted_leds[middle+s])=CHSV(colors[s][0],0,255);
            }
            else
            {//Sinon intensité normale
                (*local_sorted_leds[middle-1-s])=CHSV(colors[s][0],255,colors[s][2]);
                (*local_sorted_leds[middle+s])=CHSV(colors[s][0],255,colors[s][2]);
            }
        }   
    
    }   
    if(transition)
    {
        updateTransitionTimer();
    }
}
// ================================= draw()

void Extending_waves_mode::updateTransitionTimer()
{
    timeSinceTransition+=1;
    if (timeSinceTransition>=transitionTime)
    {
        resetTransition();
    }
}
// ================================= updateTransitionTimer()

void Extending_waves_mode::activate()
{
    this->activated=true;
}
// ================================= activate()

void Extending_waves_mode::deactivate()
{
    this->activated=false;
}
// ================================= deactivate()


void Extending_waves_mode::startTransition(int transitionTime, bool upOrDown, bool blackOrWhite)
{
    this->transition=true;
    this->blackOrWhite=blackOrWhite;
    this->transitionUp=upOrDown;
    this->timeSinceTransition=0;
    this->transitionTime=transitionTime;
    if (!blackOrWhite)
    {//white
        if (!upOrDown)
        {//fin de vie
            whiteApparitionRate=float(2*transitionTime)/(listSize+1);  // = nb d'apparition / temps total
            nextApparition=int(whiteApparitionRate);
            whiteWallLimit=0;
            stopPopingWhite=false;
            Serial.println("                                                            Extending_waves_mode  ==>       ( white transition ) ");
        }
        else
        {//debut de vie
            for (int pos=0 ; pos <(listSize+1)/2 ; pos++)
            {
                colors[pos][1]=0;   //Initialement blanc
            }
            delta_t=4*(transitionTime)/(listSize+1)-2;          //((n-1)/2)*delta + n = transitionTime
            nextFall=delta_t;
            numberOfFallAtTheSameTime=2;
            waitingForTheEnd=false;
            Serial.println("                                                            ==>  Extending_waves_mode     ( white transition ) ");
        }
    }
    else
    {//black
        if (!upOrDown)
        {//fin de vie
            timeToDesapear=transitionTime-(listSize+1)/2 -2;        //Le temps que le dernier pixel met à traverser la demie-barre
            intensityBlackTransitionCoef=1;
            Serial.println("                                                            Extending_waves_mode  ==>       ( black  transition ) ");
        }
        else
        {//debut de vie
            for (int pos=0 ; pos <(listSize+1)/2 ; pos++)
            {
                colors[pos][2]=0;   //0 intensite
                colors[pos][1]=255;//Pas de blanc surtout
            }
            intensityBlackTransitionCoef=0;
            Serial.println("                                                             ==>  Extending_waves_mode     ( black  transition ) ");
        }
    }
}
// ================================= startTransition()

void Extending_waves_mode::resetTransition()
{
    this->transition=false;
    Serial.println("                                                             |extending_waves|    ");
}
// ================================= resetTransition()