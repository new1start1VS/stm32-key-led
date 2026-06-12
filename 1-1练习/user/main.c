#include "stm32f10x.h"                  // Device header

//  Delay function
void Delay_ms(uint32_t ms)
{
	uint32_t i, j;
	for( i = 1; i < ms; i++)
	{
		for( j = 1; j < 7200; j++);
	}
}

//  main function & clock function

int main ()
{
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);      //启动时钟
	
	GPIO_InitTypeDef GPIO_InitStruct;
	GPIO_InitStruct.GPIO_Mode =  GPIO_Mode_Out_PP;  //推挽模式  MODE 模式选择
	GPIO_InitStruct.GPIO_Pin = GPIO_Pin_10;			//指定的引脚端口
	GPIO_InitStruct.GPIO_Speed = GPIO_Speed_50MHz;	//cpu核心主频速度
	GPIO_Init (GPIOB, &GPIO_InitStruct);			//函数封装把前面三个封装进GPIO_Init 函数中
	
	
	//点亮->延时->关闭->延时   循环
	while(1)
	{
	GPIO_ResetBits(GPIOB, GPIO_Pin_10);
	Delay_ms(100);
	GPIO_SetBits(GPIOB, GPIO_Pin_10);
	Delay_ms(100);
	}
}
