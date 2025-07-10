#include "DynamicFormat.hpp"
#include <fstream>
#include "core/Exceptions.hpp"
#include "../utils/third_party/json.hpp"

namespace packet {

// 仕様ファイルディレクトリを取得するヘルパー関数
static const std::string& get_spec_dir() {
#ifdef FORMAT_SPEC_DIR
    static const std::string dir = FORMAT_SPEC_DIR;
#else
    static const std::string dir = "../python/common/packet/format_spec";
#endif
    return dir;
}

static nlohmann::json load_json(const std::string& fileName) {
    std::string path = fileName;
    if (path.find('/') == std::string::npos) {
        path = get_spec_dir() + "/" + fileName;
    }
    std::ifstream ifs(path);
    if (!ifs) {
        throw BitFieldError("failed to open spec file: " + path);
    }
    nlohmann::json j;
    ifs >> j;
    return j;
}

static FieldSpec parse_field_spec(const nlohmann::json& j) {
    FieldSpec spec;
    for (auto it = j.begin(); it != j.end(); ++it) {
        FieldInfo info;
        if (it->is_object()) {
            info.length = (*it)["length"].get<int>();
            if (it->contains("type")) info.type = (*it)["type"].get<std::string>();
        } else if (it->is_number()) {
            info.length = it->get<int>();
        }
        spec[it.key()] = info;
    }
    return spec;
}

FieldSpec loadBaseFields(const std::string& fileName) {
    auto j = load_json(fileName);
    return parse_field_spec(j);
}

FieldSpec reloadBaseFields(const std::string& fileName) {
    return loadBaseFields(fileName);
}

FieldSpec loadExtendedFields(const std::string& fileName) {
    auto j = load_json(fileName);
    FieldSpec spec;
    for (auto it = j.begin(); it != j.end(); ++it) {
        FieldInfo info;
        if (it->is_object()) {
            info.length = (*it)["id"].get<int>();
            if (it->contains("type")) info.type = (*it)["type"].get<std::string>();
        } else if (it->is_number()) {
            info.length = it->get<int>();
        }
        spec[it.key()] = info;
    }
    return spec;
}

} // namespace packet
