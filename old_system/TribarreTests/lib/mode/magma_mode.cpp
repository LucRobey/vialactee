#include <Magma_mode.h>

Magma_mode::Magma_mode(byte ID, int* bandValues, byte* samplePeak)
{
    this->activated=false;
    this->fadeToBlackInt=0;
    this->ID=ID;
    resetTransition();

    nbOfLEDsByHeatWave=30;

    this->samplePeak = samplePeak;

    this->analysingNeeds[0] = true;
    this->analysingNeeds[1] = true;
    this->analysingNeeds[2] = true;
    this->analysingNeeds[3] = true;
    this->analysingNeeds[3] = false;
    for (byte band=0 ; band<16 ; band++)
    {
        bandAnalysingNeeds[band]=true;
    }
}
// =================================== Magma_mode()

int totalBeats;
int power;
int randomPosition;
void Magma_mode::update()
{
    if(!transition)
    {
        updateTemperatures();                                       

        //crépitements:
        power=0;
        totalBeats=0;
        for (byte l=0; l<16 ; l++)
        {
            if(samplePeak[l]>0)
            {
                totalBeats+=1;
                power+=(255-power)/3;
                if (totalBeats>=3)
                {//A partir de 3 beats, on fait apparître des crépitements
                    randomPosition=random(listSize);
                    (*local_sorted_leds[randomPosition])=CHSV(random(30),200,power);
                    if (temperatures[randomPosition]<=250)
                    {//On fait varier légèrement la température
                        temperatures[randomPosition]+=5;
                    }
                }
            }
        }
    }
    else
    {
        updateTemperaturesDuringTransition();                                       

        //crépitements:
        if ( !(transitionUp && blackOrWhite))
        {
            power=0;
            totalBeats=0;
            for (byte l=0; l<16 ; l++)
            {
                if(samplePeak[l]>0)
                {
                    totalBeats+=1;
                    power+=(255-power)/3;
                    if (totalBeats>=3)
                    {//A partir de 3 beats, on fait apparître des crépitements
                        randomPosition=random(listSize);
                        (*local_sorted_leds[randomPosition])=CHSV(0,0,255);
                    }
                }
            }
        }
    }
}
// =================================== update()

float temperatureCoef;;
void Magma_mode::updateTemperatures()
{
    for (int p=0 ; p<heatWaves.size() ; p++)
    { //D'abord, l'effet de réchauffement 
        if(temperatures[int(heatWaves[p])]<=247)
        { //On fait augmenter la température des points chauds
            temperatures[int(heatWaves[p])]+=4+random(5);
        }
        // On update la position des points chauds et leurs vitesses en faisant gaffe de pas dépasser les bornes
        heatWaves[p]+=heatSpeeds[p];
        if (heatWaves[p]<0)
        {
            heatSpeeds[p]*=-1;
            heatWaves[p]=0.1;
        }
        else if (heatWaves[p]>listSize-1)
        {
            heatSpeeds[p]*=-1;
            heatWaves[p]=listSize-1.1;
        }
        else
        {
            heatSpeeds[p]+=float(1-random(3))/100;
        }
        if (heatSpeeds[p]>=0.25)
        {
            heatSpeeds[p]=0.24;
        }
        else if (heatSpeeds[p]<=-0.25)
        {
            heatSpeeds[p]=-0.24;
        }
    }
    //Puis c'est la diffusion et le refroidissement ambiant
    //Il faut gérer les LEDs des bornes différemment car ils n'ont qu'un seul voisin, ce voisin compte donc double
    temperatures[0]+= 0.08* (temperatures[1]-temperatures[0])-0.45*(temperatures[0]/255);
    if (temperatures[0]<0)
        {
            temperatures[0]=0;
        }
    for (int s=1 ; s<temperatures.size()-1 ; s++)
    {
        temperatures[s]+= 0.08*((temperatures[s-1]+temperatures[s+1])/2 - temperatures[s])-0.45*(temperatures[s]/255);
        if (temperatures[s]<0)
        {
            temperatures[s]=0;
        }
    }
    temperatures[listSize-1]+= 0.08* (temperatures[listSize-2]-temperatures[listSize-1])-0.45*(temperatures[listSize-1]/255);
    if (temperatures[listSize-1]<0)
    {
        temperatures[listSize-1]=0;
    }

    //On dessine
    for (int s=0 ; s<listSize ; s++)
    {
        temperatureCoef=(temperatures[s]/255);
        (*local_sorted_leds[s])=CHSV(40*temperatureCoef,255-60*temperatureCoef,(60+190*temperatureCoef));
    }
}
// =================================== updateTemperatures()

float transitionCoef;
void Magma_mode::updateTemperaturesDuringTransition()
{
    if(!blackOrWhite)
    {//white
        if (!transitionUp)
        { //Fin de vie
                //On va faire chauffer la barre de partout
            for (int p=0 ; p<heatWaves.size() ; p++)
            { //D'abord, l'effet de réchauffement 
                if(temperatures[int(heatWaves[p])]<=250)
                { //On fait augmenter la température des points chauds
                    temperatures[int(heatWaves[p])]+=5;
                }
                //On ne fait pas bouger les points chauds pour que la barre devienne blanche partout
                //Si les points chauds se rassemblait, une partie de la led ne chaufferait pas assez
                //et ne deviendrait donc pas blanche
            }
            //Puis c'est la diffusion (pas de refroidissement)
            //Il faut gérer les LEDs des bornes différemment car ils n'ont qu'un seul voisin, ce voisin compte donc double
            //Ici transitionHeating>0 et participe donc au rechauffement, il permet d'être certain qu'on atteint les 255° PARTOUT!
            if (temperatures[0]>255)
                {
                    temperatures[0]=255;
                }
            else
            {
                temperatures[0]+= 0.2* (temperatures[1]-temperatures[0])+transitionHeating;
            }
            if (temperatures[0]>255)
                {
                    temperatures[0]=255;
                }
            for (int s=1 ; s<temperatures.size()-1 ; s++)
            {
                if (temperatures[s]>255)
                {
                    temperatures[s]=255;
                }
                else
                {
                    temperatures[s]+= 0.2*((temperatures[s-1]+temperatures[s+1])/2 - temperatures[s]) + transitionHeating;
                }
                if (temperatures[s]>255)
                {
                    temperatures[s]=255;
                }
            }
            if (temperatures[listSize-1]>255)
            {
                temperatures[listSize-1]=255;
            }
            else
            {
                temperatures[listSize-1]+= 0.2* (temperatures[listSize-2]-temperatures[listSize-1]) +transitionHeating;
            }
            if (temperatures[listSize-1]>255)
            {
                temperatures[listSize-1]=255;
            }
            //On utilise un coefficient de transition pour la continuité
            // coef : 0  ->            1         ->        1
            // time : 0  ->  (transitionTime/2)  ->  transitionTime
            if(transitionCoef<1)
            {
                transitionCoef=float(timeSinceTransition)/(transitionTime/2);
            }
        }
        else
        {//début de vie
                //La température, au début de la transition est de 255 partout!, on va donc la faire baisser
            for (int p=0 ; p<heatWaves.size() ; p++)
            { //D'abord, l'effet de réchauffement 
                if(temperatures[int(heatWaves[p])]<=250)
                { //On fait augmenter la température des points chauds
                    temperatures[int(heatWaves[p])]+=2;
                }
                heatWaves[p]+=heatSpeeds[p];
                if (heatWaves[p]<0)
                {
                    heatSpeeds[p]*=-1;
                    heatWaves[p]=0.1;
                }
                else if (heatWaves[p]>listSize-1)
                {
                    heatSpeeds[p]*=-1;
                    heatWaves[p]=listSize-1.1;
                }
                else
                {
                    heatSpeeds[p]+=float(1-random(3))/100;
                }
                if (heatSpeeds[p]>=0.25)
                {
                    heatSpeeds[p]=0.24;
                }
                else if (heatSpeeds[p]<=-0.25)
                {
                    heatSpeeds[p]=-0.24;
                }
            }
            //Puis c'est la diffusion et le refroidissement ambiant
            //Il faut gérer les LEDs des bornes différemment car ils n'ont qu'un seul voisin, ce voisin compte donc double
            //Ici transitionHeating<0 et participe donc au refroidissement
            temperatures[0]+= 0.2* (temperatures[1]-temperatures[0]) - 0.45*(temperatures[0]/255) + transitionHeating ;
            if (temperatures[0]<0)
                {
                    temperatures[0]=0;
                }
            for (int s=1 ; s<temperatures.size()-1 ; s++)
            {
                temperatures[s]+= 0.2*((temperatures[s-1]+temperatures[s+1])/2 - temperatures[s]) -0.45*(temperatures[s]/255) + transitionHeating;
                
                if (temperatures[s]<0)
                {
                    temperatures[s]=0;
                }
            }
            temperatures[listSize-1]+= 0.2* (temperatures[listSize-2]-temperatures[listSize-1]) - 0.45*(temperatures[listSize-1]/255) + transitionHeating;
            if (temperatures[listSize-1]<0)
            {
                temperatures[listSize-1]=0;
            }
            //On utilise un coefficient de transition pour la continuité
            // coef : 1  ->            0         ->        0
            // time : 1  ->  (transitionTime/2)  ->  transitionTime
            if(transitionCoef>0)
            {
                transitionCoef=1-float(timeSinceTransition)/(transitionTime/2);
            }
        }
        for (int s=0 ; s<listSize ; s++)
        {
            temperatureCoef=(temperatures[s]/255);
            (*local_sorted_leds[s])=CHSV(40*temperatureCoef,(1-transitionCoef)*(255-60*temperatureCoef) + transitionCoef*(255*(1-temperatureCoef)),(60+190*temperatureCoef));
        }
    }
    else
    { //BlackTransition
        if (!transitionUp)
        { //Fin de vie
                //La on va faire baisser la température petit à petit
                //Les heatWaves de viennent des points froids et la température globale baisse petit à petit
            for (int p=0 ; p<heatWaves.size() ; p++)
            { //D'abord, l'effet de refroidissement 
                if(temperatures[int(heatWaves[p])]>=5)
                { //On fait baisser la température des points chauds (froids)
                    temperatures[int(heatWaves[p])]-=2;
                }
            }
            //Puis c'est la diffusion et le refroidissement ambiant
            //Il faut gérer les LEDs des bornes différemment car ils n'ont qu'un seul voisin, ce voisin compte donc double
            //Ici transitionHeating<0 et participe donc au refroidissement
            if (temperatures[0]<0)
                {
                    temperatures[0]=0;
                }
            else
            {
                temperatures[0]+= 0.2* (temperatures[1]-temperatures[0]) + transitionHeating;
            }
            if (temperatures[0]<0)
                {
                    temperatures[0]=0;
                }
            for (int s=1 ; s<temperatures.size()-1 ; s++)
            {
                if (temperatures[s]<0)
                {
                    temperatures[s]=0;
                }
                else
                {
                    temperatures[s]+= 0.2*((temperatures[s-1]+temperatures[s+1])/2 - temperatures[s]) + transitionHeating;
                }
                if (temperatures[s]<0)
                {
                    temperatures[s]=0;
                }
            }
            if (temperatures[listSize-1]<0)
            {
                temperatures[listSize-1]=0;
            }
            else
            {
                temperatures[listSize-1]+= 0.2* (temperatures[listSize-2]-temperatures[listSize-1]) +transitionHeating;
            }
            if (temperatures[listSize-1]<0)
            {
                temperatures[listSize-1]=0;
            }
            //On utilise un coefficient de transition pour la continuité
            // coef : 0  ->            1         ->        1
            // time : 0  ->  (transitionTime/2)  ->  transitionTime
            if(transitionCoef<1)
            {
                transitionCoef=float(timeSinceTransition)/(transitionTime/2);
            }
        }
        else
        {//Début de vie
            //On fait pas grand chose, on attend juste que la barre "chauffe" toute seule
            updateTemperatures();
            //On utilise un coefficient de transition pour la continuité
            // coef : 1  ->            0         ->        0
            // time : 1  ->  (transitionTime/2)  ->  transitionTime
            if(transitionCoef>0)
            {
                transitionCoef=1-float(timeSinceTransition)/(transitionTime/2);
            } 
        }
        for (int s=0 ; s<listSize ; s++)
        {
            temperatureCoef=(temperatures[s]/255);
            (*local_sorted_leds[s])=CHSV(40*temperatureCoef,255-60*temperatureCoef,(1-transitionCoef)*(60+190*temperatureCoef));
        }
    }
}
// =================================== updateTemperaturesDuringTransition()

void Magma_mode::draw()
{
    if (transition)
    {
        updateTransitionTimer();
    }
}
// =================================== draw()

void Magma_mode::activate(vector<CRGB*> local_sorted_leds)
{
    this->activated=false;
    resetTransition();

    this->local_sorted_leds=local_sorted_leds;
    listSize=local_sorted_leds.size();

    for (int k=0 ; k<listSize ; k++)
    {
        temperatures.push_back(0);
    }
    for (int s=0 ; s<listSize/nbOfLEDsByHeatWave ; s++)
    {
        heatWaves.push_back( (listSize%nbOfLEDsByHeatWave)/2 + nbOfLEDsByHeatWave*s + nbOfLEDsByHeatWave/2);
        heatSpeeds.push_back( float(1-random(3)) /5 );
    }
}
// =================================== activate()

void Magma_mode::deactivate()
{
    this->activated=false;
    local_sorted_leds.clear();
    temperatures.clear();
    heatWaves.clear();
    heatSpeeds.clear();
}
// ================================== deactivate()

void Magma_mode::startTransition(int transitionTime, bool upOrDown, bool blackOrWhite)
{
    this->transition = true;
    this->transitionUp = upOrDown;
    this->transitionTime = transitionTime;
    this->timeSinceTransition = 0;
    this->blackOrWhite = blackOrWhite;
    if (!blackOrWhite)
    {//white
        if (!upOrDown)
        {//fin de vie
            for (int s=0 ; s<listSize/nbOfLEDsByHeatWave ; s++)
            {
                heatWaves.push_back( (listSize%nbOfLEDsByHeatWave)/2 + nbOfLEDsByHeatWave*s + nbOfLEDsByHeatWave/2);
            }
            transitionHeating=0.8*255.0/transitionTime;         //En gros, le transitionHeating s'assure qu'on atteigne 80% de 255° PARTOUT 
                                                                //au temps transitionTime/2
                                                                //Les points chauds font le reste du boulot
            transitionCoef=0;
            Serial.println("                                                             magma_mode  ==>       ( white transition ) ");
        }
        else
        {//debut de vie
            for (int l=0 ; l<listSize ; l++)
            {
                temperatures[l]=255;
            }
            transitionHeating=-0.5*255.0/transitionTime;        //En gros, le transitionHeating s'assure qu'on atteigne 50% de 0° PARTOUT 
                                                                //au temps transitionTime/2
                                                                //Les points chauds font le reste du boulot
            transitionCoef=1;
            Serial.println("                                                              ==>  magma_mode     ( white transition ) ");
        }
    }
    else
    {//black
        if (!upOrDown)
        {//fin de vie
            transitionCoef=0;
            transitionHeating=-0.2*255.0/transitionTime;        //En gros, le transitionHeating s'assure qu'on atteigne 20% de 0° PARTOUT 
                                                                //au temps transitionTime/2
                                                                //Les points chauds(froids) et le refroidissement de l'air  font le reste du boulot
            Serial.println("                                                             Extending_waves_mode  ==>       ( black  transition ) ");
        }
        else
        {//debut de vie
            transitionCoef=1;
            Serial.println("                                                              ==>  fire_mode     ( black  transition ) ");
        }
    }
}
// =================================== startTransition()

void Magma_mode::resetTransition()
{
    this->transition=false;
    transitionHeating=0;
    transitionCoef=0;
    Serial.println("                                                                |magma_mode|    ");

}
// =================================== resetTransition()