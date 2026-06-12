#include "stm32f10x.h"                  // Device header
void Delay_ms(uint32_t ms)
{
    uint32_t i, j;
    for(i = 0; i < ms; i++)
        for(j = 0; j < 7200; j++);      // 8MHz 主频下粗略延时，可根据实际时钟调整
}
int main(void)
{
    // 1. 使能 GPIOA 时钟
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);

    // 2. 配置 PA0~PA7 为推挽输出
    GPIO_InitTypeDef GPIO_InitStructure;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_12;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    

    // 4. 主循环：流水灯
    while(1)
    {
        GPIO_ResetBits(GPIOB, GPIO_Pin_12);
		Delay_ms(200);
		GPIO_SetBits(GPIOB, GPIO_Pin_12);
		Delay_ms(200);		
    }
}
