#include "stm32f10x.h"
#include "Delay.h"   // 假设您有 Delay 函数
#include "OLED.h"
#include "PWM.h"
uint8_t i;
uint16_t Num;

int main(void)
{
    OLED_Init();
    PWM_Init ();
    
   
    
    PWM_SetCompare2(1400);
   
    while (1)
	{
		
	}
}
