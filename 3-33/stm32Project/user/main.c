#include "stm32f10x.h"                  // Device header

void Delay_ms(uint32_t ms)
{
    // 简单的软件延时，不精确，适用于演示；若需要精确延时，建议使用 SysTick
    uint32_t i, j;
    for(i = 0; i < ms; i++)
        for(j = 0; j < 7200; j++);      // 8MHz 主频下粗略延时，可根据实际时钟调整
}

int main(void)
{
    // 1. 使能 GPIOA 时钟
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);

    // 2. 配置 PA0~PA7 为推挽输出
    GPIO_InitTypeDef GPIO_InitStructure;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2 |
                                  GPIO_Pin_3 | GPIO_Pin_4 | GPIO_Pin_5 | GPIO_Pin_6 | GPIO_Pin_7;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    // 3. 初始状态：全部 LED 熄灭（输出高电平）
    GPIO_SetBits(GPIOA, GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2 |
                        GPIO_Pin_3 | GPIO_Pin_4 | GPIO_Pin_5 | GPIO_Pin_6 | GPIO_Pin_7);

    // 4. 主循环：流水灯
    while(1)
    {
        // 正向流水：PA0 → PA6 逐个点亮
        for(uint8_t i = 0; i <= 7; i++)
        {
            // 点亮第 i 个 LED（拉低对应引脚）
            GPIO_ResetBits(GPIOA, (GPIO_Pin_0 << i));
            Delay_ms(200);                     // 延时 200ms
            // 熄灭第 i 个 LED（拉高）
            GPIO_SetBits(GPIOA, (GPIO_Pin_0 << i));
        }

        // 反向流水：PA6 → PA0 逐个点亮（可选，若不需要可删除此段）
        for(int8_t i = 7; i >= 0; i--)
        {
            GPIO_ResetBits(GPIOA, (GPIO_Pin_0 << i));
            Delay_ms(200);
            GPIO_SetBits(GPIOA, (GPIO_Pin_0 << i));
        }
    }
}
