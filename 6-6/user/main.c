#include "stm32f10x.h"
#include "Delay.h"   // 假设您有 Delay 函数
#include "OLED.h"
#include "PWM.h"
uint16_t i;
uint16_t Num;

int main(void)
{
    OLED_Init();
    PWM_Init ();
    
   
    
    
    while(1)
    {
    for (i = 0; i <= 1000; i++)
        {
            PWM_SetComparel (i);
            Delay_ms(100);

        }
    for (i = 1000; i > 0; i--)
        {
            PWM_SetComparel (i);
            Delay_ms(100);

        }     
    }
}
