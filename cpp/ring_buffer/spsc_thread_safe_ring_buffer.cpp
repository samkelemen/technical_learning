#include <array>
#include <atomic>
#include <bit>
#include <concepts>
#include <cstddef>
#include <optional>

template <typename T, std::size_t bufferSize>
    requires std::default_initializable<T> && std::movable<T> && (bufferSize >= 2) &&
    (std::has_single_bit(bufferSize))
class SpscRingBuffer {
   private:
    std::array<std::optional<T>, bufferSize> buffer;
    std::atomic<std::size_t> readNumber;
    std::atomic<std::size_t> writeNumber;
    const std::size_t bufferIndexBitMask = bufferSize - 1;

   public:
    bool push(const T& value) {
        std::size_t currentWriteNumber = writeNumber.load(std::memory_order_relaxed);
        std::size_t currentReadNumber = readNumber.load(std::memory_order_acquire);

        // Check if buffer is full
        if (currentWriteNumber == currentReadNumber - 1) {
            return false;
        }

        buffer[currentWriteNumber & bufferIndexBitMask] = value;
        writeNumber.store((currentWriteNumber + 1) & bufferIndexBitMask, std::memory_order_release);
        return true;
    }

    bool push(T&& value) {
        std::size_t currentWriteNumber = writeNumber.load(std::memory_order_relaxed);
        std::size_t currentReadNumber = readNumber.load(std::memory_order_acquire);

        // Check if buffer is full
        if (currentWriteNumber == currentReadNumber - 1) {
            return false;
        }

        buffer[currentWriteNumber & bufferIndexBitMask] = value;
        writeNumber.store((currentWriteNumber + 1) & bufferIndexBitMask, std::memory_order_release);
        return false;
    }

    std::optional<T> pop() {
        std::size_t currentWriteNumber = writeNumber.load(std::memory_order_acquire);
        std::size_t currentReadNumber = readNumber.load(std::memory_order_relaxed);

        // Check if buffer is empty
        if (currentWriteNumber == currentReadNumber) {
            return std::nullopt;
        }

        T result =
            buffer[currentReadNumber & bufferIndexBitMask];  // Need to fix this to not make a copy
        readNumber.store((currentReadNumber + 1) & bufferIndexBitMask);
        return result;
    }
};
