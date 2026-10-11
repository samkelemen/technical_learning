#include <array>
#include <atomic>
#include <bit>
#include <concepts>
#include <cstddef>
#include <iostream>
#include <optional>
#include <random>
#include <ranges>
#include <thread>

template <typename T, std::size_t bufferSize>
    requires std::default_initializable<T> && std::movable<T> && (bufferSize >= 2) &&
    (std::has_single_bit(bufferSize))
class SpscRingBuffer {
   private:
    std::array<std::optional<T>, bufferSize> buffer;
    std::atomic<std::size_t> readNumber;
    std::atomic<std::size_t>
        writeNumber;  // read and writeNumber need to be on different cachee lines
    const std::size_t bufferIndexBitMask = bufferSize - 1;

   public:
    SpscRingBuffer() = default;

    bool push(const T& value) {
        std::size_t currentWriteNumber = writeNumber.load(std::memory_order_relaxed);
        std::size_t currentReadNumber = readNumber.load(std::memory_order_acquire);

        // Check if buffer is full
        if (currentWriteNumber - currentReadNumber == bufferSize) {
            return false;
        }

        buffer[currentWriteNumber & bufferIndexBitMask] = value;
        writeNumber.store(currentWriteNumber + 1, std::memory_order_release);
        return true;
    }

    bool push(T&& value) {
        std::size_t currentWriteNumber = writeNumber.load(std::memory_order_relaxed);
        std::size_t currentReadNumber = readNumber.load(std::memory_order_acquire);

        // Check if buffer is full
        if (currentWriteNumber - currentReadNumber == bufferSize) {
            return false;
        }

        buffer[currentWriteNumber & bufferIndexBitMask] = value;
        writeNumber.store(currentWriteNumber + 1, std::memory_order_release);
        return true;
    }

    std::optional<T> pop() {
        std::size_t currentWriteNumber = writeNumber.load(std::memory_order_acquire);
        std::size_t currentReadNumber = readNumber.load(std::memory_order_relaxed);

        // Check if buffer is empty
        if (currentWriteNumber == currentReadNumber) {
            return std::nullopt;
        }

        std::optional<T> result =
            buffer[currentReadNumber & bufferIndexBitMask];  // Need to fix this to not make a copy
        readNumber.store(currentReadNumber + 1, std::memory_order_release);
        return result;
    }
};

int main() {
    // Create an array of 1,000,000 random numbers to stream to the buffer
    const std::size_t size{2 << 10};
    const int minVal = 1;
    const int maxVal = 1'000;

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<int> dist(minVal, maxVal);

    std::array<int, size> inputArray;
    for (std::size_t i = 0; i < size; ++i) {
        inputArray[i] = dist(gen);
    }

    // Create an array into which to stream the values from the buffer
    std::array<int, size> outputArray;

    // Construct the buffer
    SpscRingBuffer<int, (size >> 2)> buffer;

    {
        // Producer thread
        std::jthread producer([&buffer, &inputArray]() {
            for (auto& val : inputArray) {
                while (!buffer.push(val));
            }
        });

        // Consumer thread
        std::jthread consumer([&buffer, &outputArray]() {
            for (std::size_t i = 0; i < size; ++i) {
                std::optional<int> result;
                do {
                    result = buffer.pop();
                } while (!result);
                outputArray[i] = *result;
            }
        });
    }

    // Print a few values of the two arrays
    auto printArray = [](std::string_view arrayName, const std::array<int, size>& array,
                          std::size_t numValsToPrint) {
        std::cout << arrayName << ": ";
        for (int val : array | std::views::take(numValsToPrint)) {
            std::cout << val << " ";
        }
    };

    printArray("inputArray", inputArray, 5);
    printArray("outputArray", outputArray, 5);
}
