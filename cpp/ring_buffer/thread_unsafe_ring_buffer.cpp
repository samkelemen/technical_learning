#include <array>
#include <bit>
#include <concepts>
#include <cstddef>
#include <optional>
#include <type_traits>
#include <utility>

template <typename T, std::size_t bufferSize>
    requires std::default_initializable<T> && std::movable<T> && (bufferSize >= 2) &&
    (std::has_single_bit(bufferSize))  // is a power of 2
class ThreadUnsafeRingBuffer {
   private:
    std::array<T, bufferSize> buffer;
    std::size_t readPosition{0};
    std::size_t writePosition{0};
    static constexpr std::size_t mask = bufferSize - 1;

    [[nodiscard]] bool bufferIsFull() const { return writePosition - readPosition == bufferSize; }
    [[nodiscard]] bool bufferIsEmpty() const { return readPosition == writePosition; }

   public:
    ThreadUnsafeRingBuffer() = default;

    [[nodiscard("Discarding can result in dropped values when buffer is full")]]
    bool push(T&& value) {
        if (this->bufferIsFull()) return false;
        buffer[writePosition & mask] = std::move(value);
        writePosition++;
        return true;
    }

    [[nodiscard("Discarding can result in dropped values when buffer is full")]]
    bool push(const T& value) {
        if (this->bufferIsFull()) return false;
        buffer[writePosition & mask] = value;
        writePosition++;
        return true;
    }

    [[nodiscard("Discarding can result in dropped values that have been popped")]]
    std::optional<T> pop() {
        if (bufferIsEmpty()) return std::nullopt;
        std::size_t index = readPosition & mask;
        T value = std::move(buffer[index]);
        if constexpr (!std::is_trivially_destructible_v<T>) {
            buffer[index] = T{};
        }
        readPosition++;
        return value;
    }

    [[nodiscard("Why call size if you're not going to use it?")]] std::size_t size() const {
        return writePosition - readPosition;
    }
    [[nodiscard("Why call empty if you're not going to use it?")]] bool empty() const {
        return bufferIsEmpty();
    }
    [[nodiscard("Why call full if you're not going to use it?")]] bool full() const {
        return bufferIsFull();
    }
};
