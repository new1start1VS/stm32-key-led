#include "stm32f10x.h"




void Delay_ms(uint32_t ms)
{
    uint32_t i, j;
    for(i = 0; i < ms; i++)
        for(j = 0; j < 800; j++);
}

// ==================== 初始化 ====================
void ADC_LightSensor_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;
    ADC_InitTypeDef ADC_InitStructure;
    
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_ADC1, ENABLE);
    RCC_ADCCLKConfig(RCC_PCLK2_Div6);   // ADC 时钟分频
    
    // PA0 模拟输入
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_0;   
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AIN;   // 模拟输入
    GPIO_Init(GPIOA, &GPIO_InitStructure);
    
    // ADC 配置
    ADC_InitStructure.ADC_Mode = ADC_Mode_Independent;
    ADC_InitStructure.ADC_ScanConvMode = DISABLE;
    ADC_InitStructure.ADC_ContinuousConvMode = ENABLE;   // 连续转换
    ADC_InitStructure.ADC_ExternalTrigConv = ADC_ExternalTrigConv_None;
    ADC_InitStructure.ADC_DataAlign = ADC_DataAlign_Right;
    ADC_InitStructure.ADC_NbrOfChannel = 1;
    ADC_Init(ADC1, &ADC_InitStructure);
    
    ADC_RegularChannelConfig(ADC1, ADC_Channel_0, 1, ADC_SampleTime_239Cycles5);
    ADC_Cmd(ADC1, ENABLE);
    
    ADC_SoftwareStartConvCmd(ADC1, ENABLE);   // 开始转换
}

void Buzzer_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);
    
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_8;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOB, &GPIO_InitStructure);
    
    GPIO_ResetBits(GPIOB, GPIO_Pin_8);   // 初始关闭蜂鸣器
}

// 读取光敏传感器 ADC 值（0~4095）
uint16_t Get_Light_ADC(void)
{
    while(!ADC_GetFlagStatus(ADC1, ADC_FLAG_EOC));   // 等待转换完成
    return ADC_GetConversionValue(ADC1);
}

// ==================== 主函数 ====================
int main(void)
{
    uint16_t light_value = 0;
    
    ADC_LightSensor_Init();
    Buzzer_Init();
    
    while(1)
    {
        light_value = Get_Light_ADC();
        
        // 根据光照强度控制蜂鸣器
        if(light_value < 1500)        // 光线较暗（数值越小越暗，根据实际调试）
        {
            GPIO_SetBits(GPIOB, GPIO_Pin_8);    // 蜂鸣器响
        }
        else
        {
            GPIO_ResetBits(GPIOB, GPIO_Pin_8);  // 蜂鸣器关
        }
        
        Delay_ms(100);   // 控制检测频率
    }
}
