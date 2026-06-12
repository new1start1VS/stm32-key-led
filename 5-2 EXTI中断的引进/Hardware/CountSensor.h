#ifndef __COUNTSENSOR_H
#define __COUNTSENSOR_H

#include "stm32f10x.h"

void CountSensor_Init(void);
uint16_t CountSensor_Get(void);
void SysTick_Init(void);   // 系统滴答初始化，需要在主函数调用

#endif