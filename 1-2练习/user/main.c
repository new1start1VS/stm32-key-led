#include "stm32f10x.h"                  // Device header
#include "stm32f10x_adc.h"

void Delay_ms(uint32_t ms)
{
	uint32_t i, j;
	for( i = 1; i < ms; i++)
		for( j = 1; j < 7200; j++);
}

void ADC_Light_Init(void)
{
    ADC_InitTypeDef ADC_InitStruct;
    GPIO_InitTypeDef GPIO_InitStruct;
    //时钟配置    
    RCC_ADCCLKConfig(RCC_PCLK2_Div6);  //时钟分频
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_ADC1,ENABLE);
    //ADC 参数配置    
    ADC_InitStruct.ADC_ContinuousConvMode =  ENABLE;
    ADC_InitStruct.ADC_DataAlign = ADC_DataAlign_Right;
    ADC_InitStruct.ADC_ExternalTrigConv = ADC_ExternalTrigConv_None;
    ADC_InitStruct.ADC_Mode = ADC_Mode_Independent;
    ADC_InitStruct.ADC_NbrOfChannel = 1;
    ADC_InitStruct.ADC_ScanConvMode = DISABLE;
    
    ADC_Init( ADC1, &ADC_InitStruct);
   	//GPIO 参数配置
	GPIO_InitStruct.GPIO_Mode =  GPIO_Mode_AIN;
	GPIO_InitStruct.GPIO_Pin = GPIO_Pin_0;				//3、4口为调试口，需要屏蔽
	GPIO_InitStruct.GPIO_Speed = GPIO_Speed_50MHz;        
    
	GPIO_Init(GPIOB, &GPIO_InitStruct);
    
    ADC_RegularChannelConfig(ADC1, ADC_Channel_0, 1, ADC_SampleTime_239Cycles5);
    
    ADC_Cmd(ADC1, ENABLE);
    
    ADC_SoftwareStartConvCmd(ADC1, ENABLE);
}

int main(void) 
{
	ADC_Light_Init();  
           
	while(1)
	{
	GPIO_ResetBits(GPIOB, GPIO_Pin_1);
	Delay_ms(200);
	GPIO_SetBits(GPIOB, GPIO_Pin_1);
	Delay_ms(200);
	}
	
}
