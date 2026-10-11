cmake_minimum_required(VERSION 4.3.0)
project(RingBuffer)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Default to a debug build so assertions and debug info are on unless asked otherwise
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Debug)
endif()

# ThreadSanitizer catches data races / bad memory orderings in the SPSC buffer.
# Enable with: cmake -B build -DRING_BUFFER_TSAN=ON
option(RING_BUFFER_TSAN "Build with ThreadSanitizer" OFF)

find_package(Threads REQUIRED)

# No main() yet, so build as an object library; switch to add_executable once one exists
add_library(ThreadUnsafeRingBuffer OBJECT thread_unsafe_ring_buffer.cpp)
target_compile_options(ThreadUnsafeRingBuffer PRIVATE -Wall -Wextra)

add_executable(SpscRingBuffer spsc_thread_safe_ring_buffer.cpp)
target_compile_options(SpscRingBuffer PRIVATE -Wall -Wextra)
target_link_libraries(SpscRingBuffer PRIVATE Threads::Threads)

if(RING_BUFFER_TSAN)
    target_compile_options(SpscRingBuffer PRIVATE -fsanitize=thread -g)
    target_link_options(SpscRingBuffer PRIVATE -fsanitize=thread)
endif()
