#include "json.h"
#include "raylib.h"
#include "requests.h"
#include <math.h>
#include <stdio.h>
#include <sys/time.h>
#define DEG_TO_RAD (3.14159265 / 180.0)
#define MAX(x, y) (((x) > (y)) ? (x) : (y))
#define MIN(x, y) (((x) < (y)) ? (x) : (y))

long long millis() {
  struct timeval te;
  gettimeofday(&te, NULL);
  long long milliseconds = te.tv_sec * 1000LL + te.tv_usec / 1000;
  return milliseconds;
}

void drawText(int x, int y, char *text, int size, int align);
void drawDataPointWithMinMax(int x, int y, char *name, int index);
void drawLargeDial(int x, int y, int bottomVal, int topVal, int index, int size,
                   int label);
Font font;
Color colorTextShadow;
Color fgColor;

int fps = 10;

int x1 = 105;
int x2 = 350;
int x3 = 640;
int x4 = 930;
int x5 = 1175;
int font_xlarge = 32;
int font_large = 28;
int font_med = 22;
int font_small = 18;
int font_xsmall = 14;
int telemetryOnline = 0;
long long startTime = 0;
Texture2D gauge;

int SAMPLE_INTERVAL = 200;

char current[50][16];
char minmax[50][64];
double values[50];
char tempText[16];
char statusText[256];

int main(void) {
  const int screenWidth = 1280;
  const int screenHeight = 720;

  InitWindow(screenWidth, screenHeight, "Telemetry Server Dashboard");
  SetTargetFPS(fps);

  Texture2D bg = LoadTexture("resources/bg.png");
  Texture2D offlineOverlay = LoadTexture("resources/telemetry-offline.png");
  gauge = LoadTexture("resources/gauge_large.png");
  font = LoadFontEx("resources/fonts/ubuntu/Ubuntu-B.ttf", 64, 0, 0);
  GenTextureMipmaps(&font.texture);

  colorTextShadow = Fade(BLACK, 0.2);
  fgColor = (Color){68, 68, 68, 255};

  startTime = millis();

  // Initialize arrays
  for (int i = 0; i < 50; i++) {
    strcpy(current[i], "---");
    strcpy(minmax[i], "min: --- max: ---");
  }

  fprintf(stdout, "ready\n");

  char mouseXStr[5];
  char mouseYStr[5];

  // Initialize curl
  while (!WindowShouldClose()) {
    // handle periodic sampling of data from server
    if (millis() - startTime > SAMPLE_INTERVAL) {
      startTime = millis();
      req_t request;
      CURL *curl = requests_init(&request);
      requests_get(curl, &request, "http://localhost:5000/live_formatted");
      if (request.code == 200) {
        json_value *parsedValue =
            json_parse((json_char *)request.text, request.size);

        // Parse through the live data
        if (parsedValue != NULL) {
          for (int x = 0; x < parsedValue->u.object.length; x++) {
            char *name = parsedValue->u.object.values[x].name;
            json_value *valuesObject = parsedValue->u.object.values[x].value;

            // last element is a status indicator
            if (x == parsedValue->u.object.length - 1) {
              if (valuesObject->type == json_string) {
                strcpy(statusText, valuesObject->u.string.ptr);
              }
            } else {
              json_value *currentValue = valuesObject->u.object.values[0].value;
              json_value *minMaxValue = valuesObject->u.object.values[1].value;
              json_value *numericalValue =
                  valuesObject->u.object.values[2].value;
              if (currentValue->type == json_string) {
                strcpy(current[x], currentValue->u.string.ptr);
              }
              if (minMaxValue->type == json_string) {
                strcpy(minmax[x], minMaxValue->u.string.ptr);
              }
              if (numericalValue->type == json_double) {
                values[x] = numericalValue->u.dbl;
              }
              if (numericalValue->type == json_integer) {
                values[x] = numericalValue->u.integer;
              }
            }

            // json_value_free(valuesObject);
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
    DrawTexture(bg, 0, 0, WHITE);

    // Draw large labels
    drawText(x2, 20, "Throttle AAA", font_large, 2);
    drawText(x3, 20, "GPS Speed", font_large, 2);
    drawText(x4, 20, "Total Current", font_large, 2);
    drawText(x2, 300, "Throttle", font_large, 2);
    drawText(x3, 300, "Motor RPM", font_large, 2);
    drawText(x4, 300, "Solar Charging", font_large, 2);

    // Draw smaller data point labels
    drawDataPointWithMinMax(x1, 10, "Motor Temp", 23);
    drawDataPointWithMinMax(x1, 130, "GPS Fix", 13);
    drawDataPointWithMinMax(x1, 253, "Num Satellites", 17);
    drawDataPointWithMinMax(x1, 550, "IMU Pitch (Trim)", 20);

    drawDataPointWithMinMax(x3, 550, "Prop RPM", 24);
    drawDataPointWithMinMax(x5, 10, "Voltage", 6);
    drawDataPointWithMinMax(x5, 130, "Power", 3);
    drawDataPointWithMinMax(x5, 253, "State of Charge", 4);

    if (values[31] == 0) {
      drawText(x2, 348, "Throttle Mode: Duty Cycle", font_med, 2);
    } else {
      drawText(x2, 348, "Throttle Mode: Current", font_med, 2);
    }
    if (values[37] == 0) {
      drawText(x2, 392, "Boat Config: Endurance", font_med, 2);
    } else {
      drawText(x2, 392, "Boat Config: Sprint", font_med, 2);
    }
    drawText(x2, 438, "Throttle Input", font_med, 2);
    drawText(x2, 438 + 25, current[30], font_xlarge, 2);
    drawText(x2, 512, "Throttle Current Target", font_med, 2);
    drawText(x2, 512 + 25, current[29], font_xlarge, 2);
    drawText(x2, 590, "Throttle Recommendation", font_med, 2);
    drawText(x2, 590 + 25, current[32], font_xlarge, 2);

    drawText(x4, 355, "Current (Panel 1)", font_med, 2);
    drawText(x4, 355 + 25, current[25], font_xlarge, 2);
    drawText(x4, 435, "Current (Panel 2)", font_med, 2);
    drawText(x4, 435 + 25, current[26], font_xlarge, 2);
    drawText(x4, 515, "Combined Output Current", font_med, 2);
    drawText(x4, 515 + 25, current[27], font_xlarge, 2);

    DrawTextEx(
        font, statusText,
        (Vector2){1260 - MeasureTextEx(font, statusText, font_med, 0).x, 678},
        font_med, 0, LIGHTGRAY);

    /*
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
    */
    // draw data point values

    // draw indicators
    drawLargeDial(x2, 180, 0, 255, 28, 120, 1); // throttle
    drawText(x2, 170 + 80, minmax[28], font_small, 2);
    drawLargeDial(x3, 180, 0, 25, 19, 120, 1); // gps speed
    drawText(x3, 170 + 80, minmax[19], font_small, 2);
    drawLargeDial(x3, 445, 0, 3500, 22, 110, 1); // rpm
    drawText(x3, 450 + 61, minmax[22], font_small, 2);
    drawLargeDial(x4, 180, 200, -200, 2, 120, 1); // motor current
    drawText(x4, 170 + 80, minmax[2], font_small, 2);
    drawLargeDial(x1, 505, -15, 15, 20, 80, 0); // imu pitch
    drawText(x1, 380, "Trim", font_large, 2);

    // if telemetry offline, draw overlay
    if (!telemetryOnline) {
      DrawTexture(offlineOverlay, 0, 0, WHITE);
    }

    DrawFPS(10, 10);
    EndDrawing();
  }

  // ClearDroppedFiles();
  UnloadFont(font);
  CloseWindow();

  return 0;
}

void drawDataPointWithMinMax(int x, int y, char *name, int index) {
  drawText(x, y + 10, name, font_med, 2);
  drawText(x, y + 39, current[index], font_xlarge, 2);
  drawText(x, y + 80, minmax[index], font_xsmall, 2);
}

void drawLargeDial(int x, int y, int bottomVal, int topVal, int index, int size,
                   int label) {
  DrawCircleSector((Vector2){x, y}, size, 165, 375, 64, LIGHTGRAY);
  DrawCircleSector((Vector2){x, y}, size - 3, 165, 375, 64,
                   (Color){68, 68, 68, 255});
  for (int i = 1; i < 10; i++) {
    int xx = x + (cos(((i * 21) - 195) * DEG_TO_RAD) * (size - 8));
    int yy = y + (sin(((i * 21) - 195) * DEG_TO_RAD) * (size - 8));
    DrawLineEx((Vector2){x, y}, (Vector2){xx, yy}, 2, LIGHTGRAY);
  }
  DrawCircleSector((Vector2){x, y}, (size - 20), 165, 375, 64,
                   (Color){68, 68, 68, 255});
  DrawTriangle((Vector2){x, y}, (Vector2){x - (size * 0.8), y + 30},
               (Vector2){x + (size * 0.8), y + 30}, (Color){68, 68, 68, 255});
  // DrawRectangleV((Vector2){x-70,y+18},(Vector2){140,28}, BLACK);

  sprintf(tempText, "%d", bottomVal);
  DrawTextEx(font, tempText, (Vector2){x - (size - 15), y + 10}, font_small, 0,
             LIGHTGRAY);
  sprintf(tempText, "%d", topVal);
  DrawTextEx(font, tempText,
             (Vector2){-MeasureTextEx(font, tempText, font_small, 0).x + x +
                           (size - 15),
                       y + 10},
             font_small, 0, LIGHTGRAY);
  if (label != 0) {
    drawText(x, y + 20, current[index], font_large, 2);
  }
  float positionValue =
      (values[index] - bottomVal) * (1 - 0) / (topVal - bottomVal) + 0;
  positionValue = MAX(positionValue, 0);
  positionValue = MIN(positionValue, 1);
  float angle = (210 * positionValue) - 15;
  float dist = (size - 30);
  int x1 = x + (cos((angle - 180) * DEG_TO_RAD) * dist);
  int y1 = y + (sin((angle - 180) * DEG_TO_RAD) * dist);
  DrawLineEx((Vector2){x, y}, (Vector2){x1, y1}, 5, ORANGE);
  DrawCircle(x1, y1, 2.5, ORANGE);
  DrawCircle(x, y, size / 12, LIGHTGRAY);
}

void drawText(int x, int y, char *text, int size, int align) {
  int width = MeasureTextEx(font, text, size, 0).x;
  int offsetX = 0;
  if (align == 0) {
    // Left align
    offsetX = 0;
  } else if (align == 1) {
    // right align
    offsetX = -width;
  } else if (align == 2) {
    // center align
    offsetX = -width / 2;
  }
  int shadowOffset = 2;
  DrawTextEx(font, text,
             (Vector2){offsetX + x + shadowOffset, y + shadowOffset}, size, 0,
             colorTextShadow);
  DrawTextEx(font, text, (Vector2){offsetX + x, y}, size, 0, WHITE);
}
