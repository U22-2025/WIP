#include "packet/core/ExtendedField.hpp"
#include "packet/core/FormatBase.hpp"
#include "packet/DynamicFormat.hpp"
#include <catch2/catch_test_macros.hpp>
#include <fstream>
#include <string>
#include <filesystem>
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
    std::string spec_file = std::string(FORMAT_SPEC_DIR) + "/request_fields.json";
    std::ifstream ifs(spec_file);
    REQUIRE(ifs.is_open());
    ifs >> j;
    j["new_flag"] = {{"length", 1}, {"type", "int"}};
    std::string tmp_file = (std::filesystem::current_path() / "tmp_request.json").string();
    std::ofstream ofs(tmp_file);
    ofs << j;
    ofs.close();

    FormatBase::reloadFieldSpec(tmp_file);
    REQUIRE(FormatBase::FIELD_LENGTH.count("new_flag") == 1);
    FormatBase base;
    base.set("new_flag", 1);
    REQUIRE(base.get("new_flag") == 1);

    // 元に戻す
    FormatBase::reloadFieldSpec(spec_file);
}
