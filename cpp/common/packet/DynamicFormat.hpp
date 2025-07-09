#pragma once
#include <string>
#include <map>
#include "../utils/third_party/json.hpp"

namespace packet {

struct FieldInfo {
    int length{};
    std::string type{"int"};
};

using FieldSpec = std::map<std::string, FieldInfo>;

FieldSpec loadBaseFields(const std::string& fileName = "request_fields.json");
FieldSpec reloadBaseFields(const std::string& fileName = "request_fields.json");
FieldSpec loadExtendedFields(const std::string& fileName = "extended_fields.json");

} // namespace packet
