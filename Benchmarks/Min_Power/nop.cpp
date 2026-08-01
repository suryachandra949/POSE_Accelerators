
#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>

#define MOV1    "mov.u32 %0, %0;\n\t"   // marker instruction to track and replace with nops in SASS (architecture machine code)
#define MOV2    MOV1 MOV1
#define MOV4    MOV2 MOV2
#define MOV8    MOV4 MOV4
#define MOV16   MOV8 MOV8
#define MOV32   MOV16 MOV16
#define MOV64   MOV32 MOV32
#define MOV128  MOV64 MOV64
#define MOV256  MOV128 MOV128
#define MOV512  MOV256 MOV256
#define MOV1024 MOV512 MOV512


extern "C"
__global__ void nop_kernel(unsigned long long iterations,
                           unsigned* sink)
{
    unsigned value = threadIdx.x + 1u;

#pragma unroll 1
    for (unsigned long long i = 0; i < iterations; ++i) {
        asm volatile(MOV1024 : "+r"(value));
    }

    if (threadIdx.x == 0)
        sink[blockIdx.x] = value;
}




