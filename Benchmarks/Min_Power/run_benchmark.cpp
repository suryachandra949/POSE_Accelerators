#include <cuda.h>

#include <cstdio>
#include <cstdlib>

#define CUDA_CHECK(call)                                                   \
    do {                                                                   \
        CUresult status_ = (call);                                         \
        if (status_ != CUDA_SUCCESS) {                                     \
            const char* name_ = nullptr;                                   \
            const char* message_ = nullptr;                                \
            cuGetErrorName(status_, &name_);                               \
            cuGetErrorString(status_, &message_);                          \
            std::fprintf(stderr,                                           \
                         "CUDA error at %s:%d: %s: %s\n",                   \
                         __FILE__, __LINE__,                                \
                         name_ ? name_ : "unknown",                         \
                         message_ ? message_ : "unknown");                  \
            std::exit(EXIT_FAILURE);                                       \
        }                                                                  \
    } while (0)

int main(int argc, char** argv)
{
    if (argc != 5) {
        std::fprintf(
            stderr,
            "Usage: %s <cubin> <blocks> <threads> <iterations>\n"
            "Example: %s nop.nop.cubin 108 256 1000000\n",
            argv[0], argv[0]);
        return EXIT_FAILURE;
    }

    const char* cubin_path = argv[1];
    const unsigned blocks =
        static_cast<unsigned>(std::strtoul(argv[2], nullptr, 10));
    const unsigned threads =
        static_cast<unsigned>(std::strtoul(argv[3], nullptr, 10));
    unsigned long long iterations =
        std::strtoull(argv[4], nullptr, 10);

    if (blocks == 0 || threads == 0 || threads > 1024 ||
        iterations == 0) {
        std::fprintf(stderr, "Invalid launch parameters.\n");
        return EXIT_FAILURE;
    }

    CUDA_CHECK(cuInit(0));

    CUdevice device;
    CUDA_CHECK(cuDeviceGet(&device, 0));

    char device_name[256] = {};
    CUDA_CHECK(cuDeviceGetName(
        device_name,
        sizeof(device_name),
        device));

    CUcontext context;
    CUDA_CHECK(cuCtxCreate(&context, 0, device));

    // Load the patched CUBIN.
    CUmodule module;
    CUDA_CHECK(cuModuleLoad(&module, cubin_path));

    // Requires: extern "C" __global__ void nop_kernel(...)
    CUfunction kernel;
    CUDA_CHECK(cuModuleGetFunction(
        &kernel,
        module,
        "nop_kernel"));

    // One output value per block.
    CUdeviceptr sink;
    const size_t sink_bytes =
        static_cast<size_t>(blocks) * sizeof(unsigned);

    CUDA_CHECK(cuMemAlloc(&sink, sink_bytes));
    CUDA_CHECK(cuMemsetD8(sink, 0, sink_bytes));

    /*
     * Each entry points to the host variable holding the argument value.
     *
     * Kernel arguments:
     *   0: unsigned long long iterations
     *   1: unsigned* sink
     */
    void* kernel_args[] = {
        &iterations,
        &sink
    };

    CUevent start;
    CUevent stop;

    CUDA_CHECK(cuEventCreate(&start, CU_EVENT_DEFAULT));
    CUDA_CHECK(cuEventCreate(&stop, CU_EVENT_DEFAULT));

    std::printf("GPU:        %s\n", device_name);
    std::printf("CUBIN:      %s\n", cubin_path);
    std::printf("Blocks:     %u\n", blocks);
    std::printf("Threads:    %u\n", threads);
    std::printf("Warps/block:%u\n", (threads + 31) / 32);
    std::printf("Iterations: %llu\n", iterations);

    CUDA_CHECK(cuEventRecord(start, nullptr));

    CUDA_CHECK(cuLaunchKernel(
        kernel,
        blocks, 1, 1,       // Grid: blocks
        threads, 1, 1,      // Block: threads
        0,                  // Dynamic shared memory
        nullptr,            // Default stream
        kernel_args,
        nullptr));

    CUDA_CHECK(cuEventRecord(stop, nullptr));
    CUDA_CHECK(cuEventSynchronize(stop));

    float elapsed_ms = 0.0f;
    CUDA_CHECK(cuEventElapsedTime(
        &elapsed_ms,
        start,
        stop));

    // Also reports asynchronous launch/runtime errors.
    CUDA_CHECK(cuCtxSynchronize());

    std::printf("Runtime:    %.6f seconds\n",
                elapsed_ms / 1000.0f);

    CUDA_CHECK(cuEventDestroy(start));
    CUDA_CHECK(cuEventDestroy(stop));
    CUDA_CHECK(cuMemFree(sink));
    CUDA_CHECK(cuModuleUnload(module));
    CUDA_CHECK(cuCtxDestroy(context));

    return EXIT_SUCCESS;
}