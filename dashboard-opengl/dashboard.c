#include "raylib.h"
#include "requests.h"
#include <stdio.h>
#include "json.h"
#include <sys/time.h>

long long millis() {
    struct timeval te;
    gettimeofday(&te, NULL);
    long long milliseconds = te.tv_sec*1000LL + te.tv_usec/1000;
    return milliseconds;
}

void drawText(int x, int y, char *text, int size, int align);
void drawDataPointWithMinMax(int x, int y, char *name,  int index);
void drawLargeDial(int x, int y, int bottomVal, int topVal, int val, char* label);
Font font;
Color colorTextShadow;

int x1 = 105;
int x2 = 350;
int x3 = 640;
int x4 = 930;
int x5 = 1175;
int font_large = 28;
int font_med = 24;
int font_small = 18;
int telemetryOnline = 0;
long long startTime = 0;
Texture2D gauge;

int SAMPLE_INTERVAL = 250;

char current[34][16];
char minmax[34][32];
double values[34];

int main(void){
    const int screenWidth = 1280;
    const int screenHeight = 720;

    InitWindow(screenWidth, screenHeight, "Telemetry Server Dashboard");

    SetTargetFPS(60);

    Texture2D bg = LoadTexture("resources/bg.png");
    Texture2D offlineOverlay = LoadTexture("resources/telemetry-offline.png");
    gauge = LoadTexture("resources/gauge_large.png");
    font = LoadFontEx("resources/fonts/ubuntu/Ubuntu-B.ttf", 64, 0, 0);
    GenTextureMipmaps(&font.texture);

    colorTextShadow = Fade(BLACK,0.2);

    startTime = millis();

    // Initialize arrays
    for (int i = 0; i < 34; i++){
        strcpy(current[i],"---");
        strcpy(minmax[i],"min: --- max: ---");
    }

    fprintf(stdout,"ready\n");

    char mouseXStr[5];
    char mouseYStr[5];

    // Initialize curl
    while (!WindowShouldClose()){
        // handle periodic sampling of data from server
        if (millis() - startTime > SAMPLE_INTERVAL){
            startTime = millis();
            req_t request;
            CURL *curl = requests_init(&request);
            requests_get(curl, &request, "http://localhost:5000/live_formatted");
            if (request.code == 200){
                json_value *parsedValue = json_parse((json_char*)request.text, request.size);

                // Parse through the live data
                if (parsedValue != NULL){
                    for (int x = 0; x < parsedValue->u.object.length; x++) {
                        char *name = parsedValue->u.object.values[x].name;
                        json_value *valuesObject = parsedValue->u.object.values[x].value;

                        json_value *currentValue = valuesObject->u.object.values[0].value;
                        json_value *minMaxValue = valuesObject->u.object.values[1].value;
                        json_value *numericalValue = valuesObject->u.object.values[2].value;

                        if (currentValue->type == json_string) { strcpy(current[x],currentValue->u.string.ptr); }
                        if (minMaxValue->type == json_string) { strcpy(minmax[x],minMaxValue->u.string.ptr); }
                        if (numericalValue->type == json_double) { values[x]=numericalValue->u.dbl; }

                        //json_value_free(valuesObject);
                    }
                    telemetryOnline = 1;
                } else {
                    // Couldn't get request, telemetry is offline
                    telemetryOnline = 0;
                }
                json_value_free(parsedValue);
            } else {
                telemetryOnline = 0;
            }
            requests_close(&request);
        }

        BeginDrawing();
        DrawTexture(bg, 0,0, WHITE);

        // Draw large labels
        drawText(x2,20,"Throttle",font_large,2);
        drawText(x3,20,"GPS Speed",font_large,2);
        drawText(x4,20,"Total Current",font_large,2);
        drawText(x2,300,"Throttle",font_large,2);
        drawText(x3,300,"Motor RPM",font_large,2);
        drawText(x4,300,"Solar Charging",font_large,2);

        // Draw smaller data point labels
        drawDataPointWithMinMax(x1,10,"Motor Temp",23);
        drawDataPointWithMinMax(x1,130,"GPS Fix",13);
        drawDataPointWithMinMax(x1,253,"Num Satellites",17);
        drawDataPointWithMinMax(x1,550,"IMU Pitch (Trim)",20);

        drawDataPointWithMinMax(x3,550,"Prop RPM",24);
        drawDataPointWithMinMax(x5,10,"Voltage",6);
        drawDataPointWithMinMax(x5,130,"Power",3);
        drawDataPointWithMinMax(x5,253,"State of Charge",4);

        drawText(x2,340,"Throttle Mode:",font_med,2);
        drawText(x2,340,current[10],font_large,2);
        drawText(x2,390,"Throttle Input",font_med,2);
        drawText(x2,360,current[10],font_large,2);
        drawText(x2,470,"Throttle Current Target",font_med,2);
        drawText(x2,420,current[10],font_large,2);
        drawText(x2,560,"Throttle Recommendation",font_med,2);
        drawText(x2,600,current[10],font_large,2);


        drawText(x4,355,"Current (Panel 1)",font_med,2);
        drawText(x4,385,current[6],font_large,2);
        drawText(x4,435,"Current (Panel 2)",font_med,2);
        drawText(x4,470,current[6],font_large,2);
        drawText(x4,515,"Combined Output Current",font_med,2);
        drawText(x4,550,current[6],font_large,2);

        int mouseX = GetMouseX();
        int mouseY = GetMouseY();
        mouseX = mouseX * 2;
        mouseY = mouseY * 2;
        sprintf(mouseXStr,"%d",mouseX);
        sprintf(mouseYStr,"%d",mouseY);
        DrawLine(0,mouseY,1280,mouseY, RED);
        DrawLine(mouseX,0,mouseX,720, RED);
        drawText(mouseX + 10, mouseY + 10,mouseXStr,font_small,0);
        drawText(mouseX + 10, mouseY + 30,mouseYStr,font_small,0);
        //DrawCircle(mouseX,mouseY,10,RED);

        // draw data point values

        // draw indicators
        drawLargeDial(x2,170,0,255,values[6],current[6]);

        // if telemetry offline, draw overlay
        if (!telemetryOnline){
            DrawTexture(offlineOverlay, 0,0, WHITE);
        }

        DrawFPS(10, 10);
        EndDrawing();
    }

    ClearDroppedFiles();
    UnloadFont(font);
    CloseWindow();

    return 0;
}

void drawDataPointWithMinMax(int x, int y, char *name,  int index){
    drawText(x,y+10,name,font_med,2);
    drawText(x,y+40,current[index],font_large,2);
    drawText(x,y+75,minmax[index],font_small,2);
}

void drawLargeDial(int x, int y, int bottomVal, int topVal, int val, char* label){
    DrawTexturePro(gauge, (Rectangle){0,0,512,512}, (Rectangle){x-100,y-100,200,200}, (Vector2){0,0}, 0, WHITE);
    DrawCircle(x,y,10,LIGHTGRAY);
    drawText(x,y+20,label,font_med,2);
}

void drawText(int x, int y, char *text, int size, int align){
    int width = MeasureTextEx(font, text, size, 0).x;
    int offsetX = 0;
    if (align == 0){
        // Left align
        offsetX = 0;
    } else if (align == 1){
        // right align
        offsetX = -width;
    } else if (align == 2){
        // center align
        offsetX = -width/2;
    }
    int shadowOffset = 2;
    DrawLine(x-100,y,x+100,y, RED);
    DrawTextEx(font, text, (Vector2){offsetX + x +shadowOffset,y + shadowOffset}, size, 0, colorTextShadow);
    DrawTextEx(font, text, (Vector2){offsetX + x,y}, size, 0, WHITE);
}
