#include "packet/core/ExtendedField.hpp"
#include "packet/core/FormatBase.hpp"
#include "packet/DynamicFormat.hpp"
#include <catch2/catch_test_macros.hpp>
#include <fstream>
#include "utils/third_party/json.hpp"

using namespace packet;

TEST_CASE("ExtendedField encode decode", "[dynamic]") {
    ExtendedField ex({{"alert", "test"}});
    uint64_t bits = ex.toBits();
    ExtendedField restored = ExtendedField::fromBits(bits, 0);
    REQUIRE(restored.toDict().at("alert") == "test");
}

TEST_CASE("Reload request field spec", "[dynamic]") {
    // 元ファイルを読み込み
    nlohmann::json j;
    std::ifstream ifs("/workspace/WIP/python/common/packet/format_spec/request_fields.json");
    REQUIRE(ifs.is_open());
    ifs >> j;
    j["new_flag"] = {{"length", 1}, {"type", "int"}};
    std::ofstream ofs("/workspace/WIP/build/tests/tmp_request.json");
    ofs << j;
    ofs.close();

    FormatBase::reloadFieldSpec("/workspace/WIP/build/tests/tmp_request.json");
    REQUIRE(FormatBase::FIELD_LENGTH.count("new_flag") == 1);
    FormatBase base;
    base.set("new_flag", 1);
    REQUIRE(base.get("new_flag") == 1);

    // 元に戻す
    FormatBase::reloadFieldSpec("/workspace/WIP/python/common/packet/format_spec/request_fields.json");
}
