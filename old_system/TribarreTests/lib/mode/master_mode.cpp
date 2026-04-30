#include <master_mode.h>

#include <cstddef>
#include <memory>
#include <type_traits>
#include <utility>

/*-=-=-=-=-=-=-=-=-=-=-=-=-Fonctionnement-=-=-=-=-=-=-=-=-=-=-=-=-

Tous les modes sont stockés dans un dictionnaire : modes_map
Ainsi, on a pas besoin de les créer et détruire à chaque fois.
Plusieurs segments peuvent vouloir avoir accès au même mode, on peut donc en créer plusieurs identiques
Ainsi modes_map = map<vector<int>>
Par exemple:
modes_map[j] = {Modex,ModeX,ModeX} signifie qu'on a 3 ModeX différents
Attention, cela ne veut pas dire que les 3 modeX sont utilisés en permanence, seulement qu'ils sont à notre disposition

Les coordonnées (2 axes) des modes de chaque segments sont stockés dans la liste segmentsMode
ainsi, segmentsMode[j] = { i , k } signifie, l'actuel mode du segment j est le mode numéro i (et c'est le kème stocké)

On va parcourir la liste de nos diférents segments et regarder s'il nécéssitent un nouveau mode (s'ils arrivent en bout de vie).
S'ils arrivent en bout de vie, alors, la combinaison de la liste segmentGroup et segmentsGroupModes
nous permet de choisir le mode suivant selon la méthode suivante:
-segmentGroups retient la liste de toutes les combinaisons de segments possibles incluant ce segment
-segmentsGroupModes retient la liste de toutes les combinaisons de modes possibles incluant ce segment
Par exemple:
segmentsGroups[j]     = { {j} , {j} , {j,i} }
segmentsGroupModes[j] = { {k} , {m} , {k,h} }
Ajors le segment j a 3 possibilités:
    1) être seul en adoptant le mode numéro k
    2) être seul en adoptant le mode numéro m
    3) être en groupe en embarquant le segment i, on aurait alors le segment j avec le mode k et le mode i avec le mode h.

Le choix de la combinaison de modes se fait suivant la liste segmentsProba (en %)
Reprenons notre exemple:
segmentsGroups[j]     = { {j} , {j} , {j,i} }
segmentsGroupModes[j] = { {k} , {m} , {k,h} }
segmentsProba[j]      = { 10  , 40  ,   50  }
Alors la combinaison 1 a une probabilité d'apparition de 10%, la deuxième de 40% et la dernière de 50%

Une fois une combinaison choisie, 2 situation sont possibles:
    1) La combinaison est simple (le segment j est le seul à modifier, (les combinaisons 1 et 2 dans notre exemple))
    2) La combinaison est complexe (Il faut modifier plusieurs segments, (la combinaison 3 dans notre exemple où il faut modifier le segment i également))
Les 2 situation ne se gèrent pas de la même manière!
Dans la situation (1), tout est très simple, mais dans la situation (2), il faut forcer un passage de mode a un segment qui n'est
pas forcément en bout de vie. On va donc vérifier qu'on peut forcer le passage de mode dans chacun des segments associés à la
combinaison complexe (ici 1 seul). Pour cela, on va simplement regarder si le segment a déjà fait la moitié de sa vie.
Si tous les segments de la combinaison peuvent être forcés à changer de mode, alors on effectue les changements.

Une fois le mode suivant choisi, on lance la transition de fin de vie du mode en cours et on prépare le changement comme suit
On mémorise ce mode suivant dans la liste nextModes


Pour effectuer un changement de mode:
2 listes vont nous être nécessaires pour cette tâche:
-segmentsMode mémorise les modes en cours de chaque segment
-nextModes mémorise les modes suivants de chaque. Si nextModes[j]=-1, alors le segment j n'attend aucun nouveau mode

Par exemple:
segmentsMode[j] = { k , 2 }
nextModes[j]    = { h , 0 }
Signifie que, le segment j, actuellement au mode  { k , 2 } (le deuxième mode numéro k) en transition va passer, à la
fin de sa transition au mode { h , 0 } (le 0ème mode numéro h)

            Remarque, si:
            segmentsMode[j] = { k , 2 }
            nextModes[j]    = { -1 , x }
            Alors, le segment j, actuellement au mode  { k , 2 } (le deuxième mode numéro k) n'est pas en transition)



*/


Master_mode::Master_mode(int* bandValues, byte* samplePeak, byte* asservedBandPowers , int* bandSmoothedValues , byte* asservedPower , bool* needsToAnalyse , bool* bandAnalyserNeeds)                                           
{
    allWhite=true;
    //=========Construction de timeDurationOfMode:
    timeDurationOfMode[0] = 2589;          //PB
    timeDurationOfMode[1] = 2837;          //F
    timeDurationOfMode[2] = 2959;          //CMW
    timeDurationOfMode[3] = 2156;          //SW
    timeDurationOfMode[4] = 2829;          //EWM
    timeDurationOfMode[5] = 2250;          //SS
    timeDurationOfMode[6] = 2660;          //RB
    //=========Construction de timeDurationOfMode:
    //[2589, 2837, 2959, 2156, 2829, 2250, 2660]
    
    //=========Construction de transitionTimeOfMode:
    transitionTimeOfMode[0] = 200;          //PB
    transitionTimeOfMode[1] = 120;          //F
    transitionTimeOfMode[2] = 200;          //CMW
    transitionTimeOfMode[3] = 120;          //SW
    transitionTimeOfMode[4] = 200;          //EWM
    transitionTimeOfMode[5] = 150;          //SS
    transitionTimeOfMode[6] = 130;          //RB
    //=========Construction de transitionTimeOfMode:
    //[200, 120, 200, 120, 200, 150, 130, 130]
    
    //=========Construction de sorted_segments:
    CRGB *ptr;
    for (int lsInt=0 ; lsInt<200 ; lsInt++ )
    {
        ptr=&leds[0 + lsInt];
        sorted_segments[0].push_back(ptr);
    }
    for (int lsInt=0 ; lsInt<200 ; lsInt++ )
    {
        ptr=&leds[200 + lsInt];
        sorted_segments[1].push_back(ptr);
    }
    //=========Construction de sorted_segments:
    
    //=========Construction de startingPositions:
    startingPositions[0] = 0;
    startingPositions[1] = 200;
    //=========Construction de startingPositions:
    //[0, 200]
    
    //=========Initialisation des couleurs de transition:
    transitionColors[0]=true;
    transitionColors[1]=true;
    //=========Initialisation des couleurs de transition:
    
    //=========Construction de modes_map:
    
    modes_map[0][0] = (new Power_bar(sorted_segments[0],0,asservedPower));
    modes_map[0][1] = (new Power_bar(sorted_segments[1],1,asservedPower));
    
    modes_map[1][0] = (new Fire_mode(sorted_segments[0],2,samplePeak));
    modes_map[1][1] = (new Fire_mode(sorted_segments[1],3,samplePeak));
    
    modes_map[2][0] = (new Coloured_middle_wave(sorted_segments[0],4,bandSmoothedValues,asservedPower));
    modes_map[2][1] = (new Coloured_middle_wave(sorted_segments[1],5,bandSmoothedValues,asservedPower));
    
    modes_map[3][0] = (new Static_wave(sorted_segments[0],6,asservedBandPowers));
    modes_map[3][1] = (new Static_wave(sorted_segments[1],7,asservedBandPowers));
    
    modes_map[4][0] = (new Extending_waves_mode(sorted_segments[0],8,bandSmoothedValues,asservedPower));
    modes_map[4][1] = (new Extending_waves_mode(sorted_segments[1],9,bandSmoothedValues,asservedPower));
    
    modes_map[5][0] = (new Mode_shining_stars(sorted_segments[0],10,samplePeak,asservedPower));
    modes_map[5][1] = (new Mode_shining_stars(sorted_segments[1],11,samplePeak,asservedPower));
    
    modes_map[6][0] = (new Rainbow_bar(sorted_segments[0],12,asservedBandPowers));
    modes_map[6][1] = (new Rainbow_bar(sorted_segments[1],13,asservedBandPowers));
    
    //=========Construction de modes_map:
    
    //=========Construction de segmentsMode:
    segmentsMode[0] = 0;
    
    segmentsMode[1] = 0;
    
    //=========Construction de segmentsMode:
    //[0, 0]
    
    //=========Construction de timeBeforeNeedingANewMode:
    timeBeforeNeedingANewMode[0]= 2589;
    timeBeforeNeedingANewMode[1]= 2589;
    //=========Construction de timeBeforeNeedingANewMode:
    //[2589, 2589]
    
    //=========activation des bons modes:
    modes_map[0][0]->activate();
    modes_map[0][1]->activate();
    //=========activation des bons modes:
    
    //=========initialisation de nextModes:
    nextModes[0]=-1;
    nextModes[1]=-1;
    //=========initialisation de nextModes:
    //[-1, -1]
    
    //=========initialisation de memoryModes:
    memoryModes[0] = 0;
    memoryModes[1] = 0;
    //=========initialisation de memoryModes:
    //[0, 0]
    
    vector<int> smallList;
    vector<vector<int>> buildingList;
    //=========Construction de segmentsProbas:
    smallList.clear();
    smallList.push_back(1);
    smallList.push_back(36);
    smallList.push_back(36);
    smallList.push_back(38);
    smallList.push_back(36);
    smallList.push_back(36);
    smallList.push_back(36);
    smallList.push_back(36);
    segmentsProbas[0]=smallList;
    
    smallList.clear();
    smallList.push_back(1);
    smallList.push_back(36);
    smallList.push_back(36);
    smallList.push_back(38);
    smallList.push_back(36);
    smallList.push_back(36);
    smallList.push_back(36);
    smallList.push_back(36);
    segmentsProbas[1]=smallList;
    
    //=========Construction de segmentsProbas:
    //[[1, 36, 36, 38, 36, 36, 36, 36], [1, 36, 36, 38, 36, 36, 36, 36]]
    
    //=========Construction de segmentGroups:
    buildingList.clear();
    smallList.clear();
    smallList.push_back(0);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(0);
    smallList.push_back(1);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(0);
    smallList.push_back(1);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(0);
    smallList.push_back(1);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(0);
    smallList.push_back(1);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(0);
    smallList.push_back(1);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(0);
    smallList.push_back(1);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(0);
    smallList.push_back(1);
    buildingList.push_back(smallList);
    segmentGroups[0]=buildingList;
    
    buildingList.clear();
    smallList.clear();
    smallList.push_back(1);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(1);
    smallList.push_back(0);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(1);
    smallList.push_back(0);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(1);
    smallList.push_back(0);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(1);
    smallList.push_back(0);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(1);
    smallList.push_back(0);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(1);
    smallList.push_back(0);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(1);
    smallList.push_back(0);
    buildingList.push_back(smallList);
    segmentGroups[1]=buildingList;
    
    //=========Construction de segmentGroups:
    //[[[0], [0, 1], [0, 1], [0, 1], [0, 1], [0, 1], [0, 1], [0, 1]], [[1], [1, 0], [1, 0], [1, 0], [1, 0], [1, 0], [1, 0], [1, 0]]]
    
    //=========Construction de segmentGroupsMode:
    buildingList.clear();
    smallList.clear();
    smallList.push_back(0);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(1);
    smallList.push_back(1);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(0);
    smallList.push_back(0);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(6);
    smallList.push_back(6);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(7);
    smallList.push_back(7);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(2);
    smallList.push_back(2);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(4);
    smallList.push_back(4);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(3);
    smallList.push_back(3);
    buildingList.push_back(smallList);
    segmentGroupsModes[0]=buildingList;
    
    buildingList.clear();
    smallList.clear();
    smallList.push_back(0);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(1);
    smallList.push_back(1);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(0);
    smallList.push_back(0);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(6);
    smallList.push_back(6);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(7);
    smallList.push_back(7);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(2);
    smallList.push_back(2);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(4);
    smallList.push_back(4);
    buildingList.push_back(smallList);
    smallList.clear();
    smallList.push_back(3);
    smallList.push_back(3);
    buildingList.push_back(smallList);
    segmentGroupsModes[1]=buildingList;
    
    //=========Construction de segmentGroupsMode:
    //[[[0], [1, 1], [0, 0], [6, 6], [7, 7], [2, 2], [4, 4], [3, 3]], [[0], [1, 1], [0, 0], [6, 6], [7, 7], [2, 2], [4, 4], [3, 3]]]
    
    //Initialisation des besoins en analyse:
    this->needsToAnalyse=needsToAnalyse;
    this->bandNeedsToAnalyse=bandAnalyserNeeds;
    for (byte p=0 ; p<numberOfAnalysingOptions ; p++)
    {
        needsToAnalyse[p]=false;
        numberOfNeeds[p]=0;
    }
    for (byte band=0 ; band<16 ; band++)
    {
        bandNeedsToAnalyse[band]=false;
        numberOfBandNeeds[band]=0;
    }
    for (byte i=0 ; i<nbOfSegments ; i++)
    {
        bool* needs = modes_map[segmentsMode[i]][0]->getAnalysingNeeds();
        for (byte option=0 ; option<numberOfAnalysingOptions ; option++)
        {
            if(needs[option])
            {
                needsToAnalyse[option]=true;
                numberOfNeeds[option]+=1;
                if(option==3)
                {
                    for(byte band=0 ; band<16 ; band++)
                    {
                        if(modes_map[segmentsMode[i]][0]->getBandAnalysingNeeds()[band])
                        {
                            bandNeedsToAnalyse[band]=true;
                            numberOfBandNeeds[band]+=1;
                        }
                    }
                }
            }
        }
    }
    //Fin de l'initialisation
    
}

int probaMod;
int probaSum;
bool groupTest;
bool transiColor;
void Master_mode::update()
{
    /*
    if(printini)
    {
        Serial.println();
        printSegmentGroups();
        printSegmentGroupsModes();
        printSegmentsProbas();
        printState();
        printAnalysingNeeds();
        printModeMap();
        printini=false;
    }*/
    for (byte j=0 ; j<nbOfSegments ; j++) //Attention 3 = nb de segments
    {//On parcourt tous les segments 1 par 1
        fadeToBlackBy(&leds[startingPositions[j]],sorted_segments[j].size(),modes_map[segmentsMode[j]][j]->getFadeToBlackCoef());
        //Serial.print("On s occupe du fadeToblack de ");
        //Serial.println(j);
        //Serial.print("startingpo = ");
        //Serial.println(startingPositions[j]);
        //Serial.print("taille = ");
        //Serial.println(sorted_segments[j].size());
        //Serial.println(modes_map[segmentsMode[j][0]][segmentsMode[j][1]]->getFadeToBlackCoef());
        modes_map[segmentsMode[j]][j]->update();
        modes_map[segmentsMode[j]][j]->draw();
        if (nextModes[j]>=0)
        {//Alors on est en transition de fin de vie
            if (modes_map[segmentsMode[j]][j]->isTransitionFinished())
            {//Si cette transition de fin de vie est terminée, on effectue le changement de mode grâce à nextMode
                modes_map[segmentsMode[j]][j]->deactivate();                                                 //On désactive l'ancien
                segmentsMode[j]=nextModes[j];                                                                                  //On met à jour segmentsMode avec le mode suivant
                modes_map[segmentsMode[j]][j]->startTransition(transitionTimeOfMode[segmentsMode[j]],true,transitionColors[j]);  //On lance la transi du mode suivant
                nextModes[j]=-1;                             //A ne pas oublier!!!! , on dit que le segment n'est plus en transi de fin de vie
                timeBeforeNeedingANewMode[j]=timeDurationOfMode[segmentsMode[j]]+transitionTimeOfMode[segmentsMode[j]];   //On attribut un temps de vie   (Idée mettre un peu de random dedans?)
                
                updateNeedsToAnalyse(j);    //A faire avant d'oublier le last mode (memoryModes)
                memoryModes[j]=segmentsMode[j];
                //printState();

                //Mise à jour des choses à analyser:
                
                
            }
        }
        else 
        {//Alors on est en fonctionnementj normal
            timeBeforeNeedingANewMode[j]-=1;            //On fait baiser le temps
            if (timeBeforeNeedingANewMode[j]<=0)
            {//Si on atteint la fin de vie du mode
                //On choisit la couleur de la transition de fin de vie
                if (random8()%2==0)
                {
                    transiColor=true;
                }
                else
                {
                    transiColor=false;
                }

                //On choisit le mode suivant de maniere aléatoire:
                probaSum=0;
                probaMod = random8()%(256);
                //Serial.print("probaMode = ");
                //Serial.println(probaMod);
                for (byte p=0 ; p<segmentsProbas[j].size() ; p++)
                {//On parcoure tous les modes/groupements de modes possibles
                    probaSum+=segmentsProbas[j][p];
                    Serial.println(probaSum);
                    if(probaMod<=probaSum)
                    {//Alors on choisit ce groupement de modes
                        if (segmentGroups[j][p].size()==1)
                        {//Si c'est un groupe de 1, c'est pas compliqué, on trouve un mode adéquat de libre et on lui donne
                            nextModes[j]=segmentGroupsModes[j][p][0];    //On l'enregistre dans nextMode
                            //Serial.print("On choisi le mode suivant pour le segment: ");
                            //Serial.println (j);
                            //Serial.print("On lui donne le mode : ");
                            //Serial.println(nextModes[j]);
                            modes_map[segmentsMode[j]][j]->startTransition(transitionTimeOfMode[segmentsMode[j]],false,transiColor);   //On lance la transi de fin de vie du mode en court
                            transitionColors[j]=transiColor;                //On mémorise la couleur de la transition pour la transition de début de vie du mode suivant
                            modes_map[nextModes[j]][j]->activate();        //On active le mode suivant pour le réserver (du coup il n'est plus dispo pour les autres segments)
                        }
                        else
                        {//Ba la faut faire des trucs compliqués
                            for (byte s=0 ; s<segmentGroups[j][p].size() ; s++)      //PROBLEME si y a un des segments qui ne trouve pas de dispo on fait rien mais les autres changent quand meme oupsi aaaaaaaaaaaaaaaaaaaaaaaaaaaaa c la merde jcp
                            {
                                nextModes[segmentGroups[j][p][s]]=segmentGroupsModes[j][p][s];
                                //Serial.print("GROUPE  On choisi le mode suivant pour le segment: ");
                                //Serial.println (segmentGroups[j][p][s]);
                                //Serial.print("On lui donne le mode : ");
                                //Serial.println(nextModes[segmentGroups[j][p][s]]);
                                transitionColors[segmentGroups[j][p][s]]=transiColor;
                                //Serial.print("Du coup, on lance la transi de fin de vie du mode : [");
                                //Serial.print(segmentsMode[segmentGroups[j][p][s]]);
                                //Serial.print(" : ");
                                //Serial.print(segmentGroups[j][p][s]);
                                //Serial.println(" ]");
                                modes_map[segmentsMode[segmentGroups[j][p][s]]][segmentGroups[j][p][s]]->startTransition(transitionTimeOfMode[segmentsMode[segmentGroups[j][p][s]]],false,transiColor);   //Faut calculer ça putain!
                                //Serial.print("Et on active le mode : [");
                                //Serial.print(nextModes[segmentGroups[j][p][s]]);
                                //Serial.print(" : ");
                                //Serial.print(segmentGroups[j][p][s]);
                                //Serial.println(" ]");
                                modes_map[nextModes[segmentGroups[j][p][s]]][segmentGroups[j][p][s]]->activate();
                                //Serial.println("GROUPE  La transition a bien été enclanchée");
                            }
                        }
                        break;
                    } 
                }
            }
        }
    }
}

void Master_mode::makeItWhite()
{
    allWhite=!allWhite;
}


void Master_mode::updateNeedsToAnalyse(byte changingSegment)
{
    //Serial.println("ON CHANGE LES NEEDS!");
    //printAnalysingNeeds();
    byte lastMode = memoryModes[changingSegment];
    byte newMode = segmentsMode[changingSegment];
    /*
    Serial.print("lastMode = ");
    Serial.print(lastMode);
    Serial.print("  ||  newMode = ");
    Serial.println(newMode);
    */
    bool* lastNeeds = modes_map[lastMode][0] -> getAnalysingNeeds();
    /*
    Serial.print("lastNeeds = { ");
    for (byte p=0 ; p<4 ; p++) 
    {
        if(lastNeeds[p])
        {
            Serial.print("True");
        }
        else
        {
            Serial.print("False");
        }
        if(p!=3) {Serial.print(" , ");}
        else {Serial.print(" ");}
    }
    Serial.println("}");
    */
    bool* newNeeds  = modes_map[newMode][0]  -> getAnalysingNeeds();
    /*
    Serial.print("newNeeds = { ");
    for (byte p=0 ; p<4 ; p++) 
    {
        if(newNeeds[p])
        {
            Serial.print("True");
        }
        else
        {
            Serial.print("False");
        }
        if(p!=3) {Serial.print(" , ");}
        else {Serial.print(" ");}
    }
    Serial.println("}");
    */
    for (byte option=0 ; option<numberOfAnalysingOptions ; option++)
    {
        //Serial.print("  option = ");
        //Serial.println(option);
        if( (lastNeeds[option] != newNeeds[option]) )
        {
            //Serial.println("    Il y a un changement d'option");
            if(lastNeeds[option])
            {
                //Serial.println("    La derniere fois, l'option était activée");
                if(option!=3)
                {
                    //Serial.println("        On s occupe du !=3");
                    numberOfNeeds[option]-=1;
                    if(numberOfNeeds[option]==0)
                    {
                        needsToAnalyse[option]=false;
                    }
                }
                else
                {
                    numberOfNeeds[3]-=1;
                    if(numberOfNeeds[3]==0)
                    {
                        needsToAnalyse[3]=false;
                    }
                    //Serial.println("        On s occupe du 3");
                    for (byte band=0 ; band<16 ; band++)
                    {
                        if( (modes_map[lastMode][0] -> getBandAnalysingNeeds())[band] )
                        {
                            numberOfBandNeeds[band]-=1;
                            if (numberOfBandNeeds[band]==0)
                            {
                                bandNeedsToAnalyse[band]=false;
                            }
                        }
                    }
                }
            }
            else
            {
                needsToAnalyse[option] = true;
                numberOfNeeds[option]+=1;
                if(option==3)
                {
                    for (byte band=0 ; band<16 ; band++)
                    {
                        if( (modes_map[newMode][0] -> getBandAnalysingNeeds())[band] )
                        {
                            numberOfBandNeeds[band]+=1;
                            bandNeedsToAnalyse[band]=true;
                        }
                    }
                }

            }
        }
        else if(lastNeeds[option] && option==3)
        {
            //Serial.println("        les 2 en veulent aux bandValues et il va falloir faire un truc chelou ");
            for (byte band=0 ; band<16 ; band++)
            {
                //Serial.print("          band = ");
                //Serial.println(band);
                if( (modes_map[newMode][0] -> getBandAnalysingNeeds())[band] )
                {
                    //Serial.println("            Le nouveau mode en a besoin");
                    numberOfBandNeeds[band]+=1;
                    bandNeedsToAnalyse[band]=true;
                }
                if( (modes_map[lastMode][0] -> getBandAnalysingNeeds())[band] )
                {
                    //Serial.println("            L'ancien mode l'utilisait");
                    numberOfBandNeeds[band]-=1;
                    if (numberOfBandNeeds[band]==0)
                    {
                        //Serial.println("            On désactive cette bande");
                        bandNeedsToAnalyse[band]=false;
                    }
                }
            }
        }
    }
    //printAnalysingNeeds();
}

void Master_mode::printState()
{
    Serial.print("State = { ");
    for (int k=0 ; k<3 ; k++)
    {
        Serial.print(timeBeforeNeedingANewMode[k]);
        Serial.print(" : ");
        Serial.print(" [ ");
        Serial.print(segmentsMode[k]);
        Serial.print(" ; ");
        Serial.print(segmentsMode[k]);
        Serial.print(" ] ");
        if(k==2) {Serial.print(" ");}
        else {Serial.print(" || ");}
    }
    Serial.println("}");
}

void Master_mode::printSegmentGroups()
{
    Serial.print("segmentGroups      = ");
    Serial.print( " { ");
    for(int i=0;i<nbOfSegments;i++)
    {
        Serial.print("{ ");
        for (int j=0; j<segmentGroups[i].size();j++)
        {
            Serial.print( "{");
            for (int k=0 ; k<segmentGroups[i][j].size() ; k++)
            {
                Serial.print(segmentGroups[i][j][k]);
                if(k!=segmentGroups[i][j].size()-1){Serial.print(",");}
            }
            if(j==segmentGroups[i].size()-1){Serial.print("}");}
            else {Serial.print("},");}
        }
        if(i==nbOfSegments-1){Serial.print(" }");} 
        else {Serial.print(" } , ");}
    }
    Serial.println(" }");
}

void Master_mode::printSegmentGroupsModes()
{
    Serial.print("segmentGroupsModes = ");
    Serial.print( " { ");
    for(int i=0;i<nbOfSegments;i++)
    {
        Serial.print("{ ");
        for (int j=0; j<segmentGroupsModes[i].size();j++)
        {
            Serial.print( "{");
            for (int k=0 ; k<segmentGroupsModes[i][j].size() ; k++)
            {
                Serial.print(segmentGroupsModes[i][j][k]);
                if(k!=segmentGroupsModes[i][j].size()-1){Serial.print(",");}
            }
            if(j==segmentGroupsModes[i].size()-1){Serial.print("}");}
            else {Serial.print("},");}
        }
        if(i==nbOfSegments-1){Serial.print(" }");}
        else {Serial.print(" } , ");}
    }
    Serial.println(" }");
}
void Master_mode::printSegmentsProbas()
{
    Serial.print("segmentsProbas     = ");
    Serial.print( " {");

    for (int j=0; j<nbOfSegments;j++)
    {
        Serial.print( " { ");
        for (int k=0 ; k<segmentsProbas[j].size() ; k++)
        {
            Serial.print(segmentsProbas[j][k]);
            if(k!=segmentsProbas[j].size()-1){Serial.print(" ,");}
        }
        if(j==nbOfSegments-1){Serial.print("} ");}
        else {Serial.print("} ,");}

    }
    Serial.println(" }");
}

void Master_mode::printAnalysingNeeds()
{
    Serial.print("needsToAnalyse     = ");
    Serial.print( " { ");

    for (int j=0; j<numberOfAnalysingOptions;j++)
    {
        if(needsToAnalyse[j])
        {
            Serial.print("True");
        }
        else
        {
            Serial.print("False");
        }
        if(j==numberOfAnalysingOptions-1){Serial.print(" ");}
        else {Serial.print(" , ");}

    }
    Serial.println("}");
    Serial.print("numberOfNeeds     = ");
    Serial.print( " { ");

    for (int j=0; j<numberOfAnalysingOptions;j++)
    {
        Serial.print(numberOfNeeds[j]);
        if(j==numberOfAnalysingOptions-1){Serial.print("  ");}
        else {Serial.print("  ,  ");}

    }
    Serial.println("}");

    if(needsToAnalyse[3])
    {
        Serial.println( "on fait des trucs avec les bandValues");

        Serial.print("    bandNeedsToAnalyse = { ");
        for (byte band=0; band<16 ; band++)
        {
            if(bandNeedsToAnalyse[band])
            {
                Serial.print("True");
            }
            else
            {
                Serial.print("False");
            }
            if(band==15){Serial.print("  ");}
            else {Serial.print("  ,  ");}
        }
        Serial.println("}");

        
        Serial.print("    numberOfBandNeeds = { ");
        for (byte band=0; band<16 ; band++)
        {
            Serial.print(numberOfBandNeeds[band]);
            if(band==15){Serial.print("  ");}
            else {Serial.print("  ,  ");}
        }
        Serial.println("}");

        

    }

}

void Master_mode::printModeMap()
{
    Serial.println("Mode_map = {");
    for (byte mode=0 ; mode<nbOfModes ; mode++)
    {
        Serial.print("{ ");
        for(byte segment=0 ; segment<nbOfSegments ; segment++)
        {
            modes_map[mode][segment]->printID();
            if(segment!=nbOfSegments-1) Serial.print(" , ");
        }
        Serial.println(" }");
    }
    Serial.println("}");
}

void Master_mode::forceNewModes()
{
    byte randomMode = random(nbOfModes);
    for(byte segment=0 ; segment<nbOfSegments ; segment++)
    {
        if( nextModes[segment]==-1)
        {
            nextModes[segment]=randomMode;
            modes_map[segmentsMode[segment]][segment]->startTransition(200+segment,false ,false);
            modes_map[randomMode][segment]->activate();
            transitionColors[segment]=false;
        }
        else
        {
            modes_map[nextModes[segment]][segment]->deactivate();
            nextModes[segment]=randomMode;
            modes_map[randomMode][segment]->activate();
        }
    }
}
