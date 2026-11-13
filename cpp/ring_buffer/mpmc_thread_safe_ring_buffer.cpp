#include <array>
#include <atomic>
#include <bit>
#include <concepts>
#include <new>
#include <optional>

template <typename T, std::size_t bufferSize>
    requires std::default_initializable<T> && std::movable<T> && (bufferSize >= 2) &&
    (std::has_single_bit(bufferSize))
class MpmcRingBuffer {
   private:
    std::size_t indexMask = bufferSize - 1;
    static constexpr std::size_t cacheLineSize = std::hardware_destructive_interference_size;

    alignas(cacheLineSize) std::atomic<std::size_t> pushCount{0};
    alignas(cacheLineSize) std::atomic<std::size_t> popCount{0};

    bool isFull(std::size_t currPushCount, std::size_t currPopCount) {
        return currPushCount - currPopCount == bufferSize;
    }

    bool isEmpty(std::size_t currPushCount, std::size_t currPopCount) {
        return currPushCount == currPopCount;
    }

   public:
    bool push(T&& value) {};

    bool push(const T& value) {};

    std::optional<T> pop() {};
};
