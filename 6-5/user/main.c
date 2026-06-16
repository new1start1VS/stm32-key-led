#include "stm32f10x.h"
#include "Delay.h"   // 假设您有 Delay 函数
#include "OLED.h"
#include "Timer.h"
uint16_t Num;

int main(void)
{
    OLED_Init();
    Timer_Init ();
    
    OLED_ShowString(1, 1, "Num:");
    OLED_ShowString(2, 1, "Tnt:");
    
    
    while(1)
    {
    OLED_ShowNum (1, 5, Num, 5);
    OLED_ShowNum (2, 5, TIM_GetCounter(TIM2),5);
    }
}
