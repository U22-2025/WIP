#pragma once
#include <cstdint>
#include <map>
#include <string>
#include "Exceptions.hpp"
#include "BitUtils.hpp"
#include "../DynamicFormat.hpp"

namespace packet {

class FormatBase {
public:
    static FieldSpec FIELD_SPEC;
    static std::map<std::string,int> FIELD_LENGTH;
    static std::map<std::string,std::string> FIELD_TYPE;
    static std::map<std::string,int> FIELD_POSITION;
    static std::map<std::string,std::pair<int,int>> BIT_FIELDS;

    static void initFieldSpec();
    static void reloadFieldSpec(const std::string& fileName = "request_fields.json");

    FormatBase();
    explicit FormatBase(uint64_t bitstr);

    void fromBits(uint64_t bitstr);
    uint64_t toBits() const;
    std::vector<uint8_t> toBytes();
    static FormatBase fromBytes(const std::vector<uint8_t>& data);

    uint64_t get(const std::string& name) const;
    void set(const std::string& name, uint64_t value);
    virtual int getMinPacketSize() const;

protected:
    std::map<std::string,uint64_t> fields_;
    void recalcChecksum();
};

} // namespace packet
