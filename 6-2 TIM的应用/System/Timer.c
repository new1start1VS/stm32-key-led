#include "stm32f10x.h"                  // Device header
extern uint16_t Num;

void Timer_Init(void)
{
    RCC_APB1PeriphClockCmd (RCC_APB1Periph_TIM2,ENABLE);
    
    TIM_InternalClockConfig (TIM2);
    
    TIM_TimeBaseInitTypeDef TIM_TimeBaseInitStruture;
    TIM_TimeBaseInitStruture.TIM_ClockDivision = TIM_CKD_DIV1;
    TIM_TimeBaseInitStruture.TIM_CounterMode = TIM_CounterMode_Up;
    TIM_TimeBaseInitStruture.TIM_Period = 10000 - 1;
    TIM_TimeBaseInitStruture.TIM_Prescaler = 7200 - 1;
    TIM_TimeBaseInitStruture.TIM_RepetitionCounter = 0;
    TIM_TimeBaseInit (TIM2,&TIM_TimeBaseInitStruture);
    
    TIM_ClearFlag (TIM2,TIM_FLAG_Update );//为了避免复位
    //从1开始计数使用一个清楚的操作来完成这个
    TIM_ITConfig (TIM2, TIM_IT_Update ,ENABLE);
    
    NVIC_PriorityGroupConfig (NVIC_PriorityGroup_2);
    
    NVIC_InitTypeDef NVIC_InitStructure;
    NVIC_InitStructure.NVIC_IRQChannel = TIM2_IRQn;
    NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;
    NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 2;
    NVIC_InitStructure.NVIC_IRQChannelSubPriority = 1;
    NVIC_Init(&NVIC_InitStructure);
    
    TIM_Cmd(TIM2,ENABLE);
}

void TIM2_IRQHandler (void)
{
    if (TIM_GetITStatus (TIM2, TIM_IT_Update) == SET )
    {
        Num ++;
        TIM_ClearITPendingBit(TIM2, TIM_IT_Update);
    }
    
}
