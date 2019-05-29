#include "raylib.h"

void drawText(int x, int y, const char *text, int size, int align);
Font font;

int main(void){
    const int screenWidth = 1280;
    const int screenHeight = 720;

    InitWindow(screenWidth, screenHeight, "Telemetry Server Dashboard");

    SetTargetFPS(60);

    Texture2D bg = LoadTexture("resources/bg.png");
    font = LoadFontEx("resources/fonts/ubuntu/Ubuntu-B.ttf", 32, 0, 0);
    GenTextureMipmaps(&font.texture);

    while (!WindowShouldClose()){
        BeginDrawing();
        DrawTexture(bg, 0,0, WHITE);

        drawText(1270,680,"Hello World!",32,1);

        DrawFPS(10, 10);
        EndDrawing();
    }

    ClearDroppedFiles();
    UnloadFont(font);
    CloseWindow();

    return 0;
}

void drawText(int x, int y, const char *text, int size, int align){
    int width = MeasureTextEx(font, text, size, 0).x;
    int offsetX = 0;
    if (align == 0){
        // Left align
        offsetX = 0;
    } else if (align == 1){
        // right align
        offsetX = -width;
    }
    int shadowOffset = 2;
    DrawTextEx(font, "Hello World!", (Vector2){offsetX + x +shadowOffset,y + shadowOffset}, size, 0, BLACK);
    DrawTextEx(font, "Hello World!", (Vector2){offsetX + x,y}, size, 0, WHITE);
}
