#pragma once
#include <string>
#include <map>
#include <vector>
#include <utility>
#include "Exceptions.hpp"
#include "../DynamicFormat.hpp"

namespace packet {

class ExtendedField {
public:
    ExtendedField() = default;
    explicit ExtendedField(const std::map<std::string, std::string>& data);

    void set(const std::string& key, const std::string& value);
    std::string get(const std::string& key) const;
    std::map<std::string, std::string> toDict() const;

    uint64_t toBits() const;
    static ExtendedField fromBits(uint64_t bits, int totalBits);

private:
    std::map<std::string, std::string> data_;
};

} // namespace packet
